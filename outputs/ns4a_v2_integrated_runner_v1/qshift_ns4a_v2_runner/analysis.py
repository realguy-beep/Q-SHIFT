"""V2 analysis adapter; inference runs only after saved-array auditing."""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from qshift_ns4a_v2_deterministic.protocol import CONDITIONS, EVALUATION_ARMS
from qshift_ns4a_v2_deterministic.selection import SelectionRootScore
from qshift_ns4a_v2_deterministic.selection_rank import selection_rank_bootstrap
from qshift_ns4a_v2_deterministic.statistics import (
    EvaluationRootCounts,
    primary_bootstrap,
    primary_point_estimate,
    root_sign_flip,
    paired_root_differences,
    secondary_sign_flip_holm,
)


class AnalysisError(RuntimeError):
    """Saved auditor records cannot be mapped to the prespecified analysis."""


def _selection_records(audit: Mapping[str, Any]) -> list[SelectionRootScore]:
    per_root = audit["selection_archive_audit"].get("per_root")
    if not isinstance(per_root, list) or len(per_root) != 48:
        raise AnalysisError("independent selection auditor did not return all 48 root records.")
    return [
        SelectionRootScore(
            row["condition_id"], row["root_index"], row["root_id"], row["shots"],
            {name: int(value) for name, value in row["errors"].items()},
        )
        for row in per_root
    ]


def _evaluation_records(audit: Mapping[str, Any]) -> list[EvaluationRootCounts]:
    per_root = audit["evaluation_archive_audit"].get("per_root")
    if not isinstance(per_root, list) or len(per_root) != 60:
        raise AnalysisError("independent evaluation auditor did not return all 60 root records.")
    return [
        EvaluationRootCounts(
            row["condition_id"], row["root_index"], row["root_id"], row["shots"],
            {name: int(value) for name, value in row["errors"].items()},
        )
        for row in per_root
    ]


def analyze_verified_archives(
    audit: Mapping[str, Any], *, selected_candidate: str,
    analysis_seeds: Mapping[str, int],
) -> dict[str, Any]:
    """Compute prespecified V2 summaries from independently recomputed counts."""
    if audit.get("audit") != "PASS" or audit.get("total_shots") != 304_000:
        raise AnalysisError("full independent archive audit must pass before statistical analysis.")
    if selected_candidate not in {
        f"{condition}::{mode}"
        for condition in CONDITIONS
        for mode in ("ordinary_pymatching", "correlation_enabled_pymatching")
    }:
        raise AnalysisError("selected global candidate is outside the frozen 12-candidate grid.")
    required = (
        "selection_rank_bootstrap", "primary_bootstrap", "primary_sign_flip",
        "secondary_sign_flip_bm_vs_selected_dem_ordinary_pm",
        "secondary_sign_flip_bm_vs_selected_dem_correlation_enabled_pm",
        "secondary_sign_flip_selected_pm_vs_nominal_ordinary_pm",
    )
    if tuple(analysis_seeds) != required or any(type(analysis_seeds[name]) is not int for name in required):
        raise AnalysisError("analysis seeds must match all six frozen streams in order.")
    selection_records = _selection_records(audit)
    evaluation_records = _evaluation_records(audit)
    selection_rng = np.random.default_rng(analysis_seeds["selection_rank_bootstrap"])
    primary_rng = np.random.default_rng(analysis_seeds["primary_bootstrap"])
    secondary_rngs = {
        "bm_vs_selected_dem_ordinary_pm": np.random.default_rng(
            analysis_seeds["secondary_sign_flip_bm_vs_selected_dem_ordinary_pm"]
        ),
        "bm_vs_selected_dem_correlation_enabled_pm": np.random.default_rng(
            analysis_seeds["secondary_sign_flip_bm_vs_selected_dem_correlation_enabled_pm"]
        ),
        "selected_pm_vs_nominal_ordinary_pm": np.random.default_rng(
            analysis_seeds["secondary_sign_flip_selected_pm_vs_nominal_ordinary_pm"]
        ),
    }
    rank = selection_rank_bootstrap(selection_records, selection_rng)
    primary = primary_bootstrap(evaluation_records, primary_rng)
    selected_mode = selected_candidate.split("::", 1)[1]
    secondary = secondary_sign_flip_holm(evaluation_records, secondary_rngs, selected_mode=selected_mode)
    differences = paired_root_differences(
        evaluation_records, "beliefmatching_same_selected_dem", "pooled_selected_fixed_pymatching"
    )
    condition_means = {condition: float(differences[i].mean()) for i, condition in enumerate(CONDITIONS)}
    arm_totals = audit["evaluation_archive_audit"]["per_arm"]
    return {
        "analysis_status": "COMPUTED_AFTER_INDEPENDENT_SAVED_ARRAY_AUDIT",
        "scope": audit.get("scope"),
        "selected_candidate": selected_candidate,
        "selected_mode": selected_mode,
        "arm_totals": arm_totals,
        "primary": {
            "estimand": "equal-condition mean of root-paired BeliefMatching minus pooled-selected fixed PyMatching LER",
            "point_estimate": primary.point_estimate,
            "percentile_95_interval": [primary.lower_95, primary.upper_95],
            "bootstrap_replicates": primary.replicates,
            "quantile_method": primary.quantile_method,
            "condition_mean_differences": condition_means,
            "root_sign_flip_sensitivity": root_sign_flip(differences, np.random.default_rng(analysis_seeds["primary_sign_flip"])).__dict__,
        },
        "secondary": {
            "method": secondary["method"],
            "family_size": secondary["family_size"],
            "raw_p_values": secondary["raw_p_values"],
            "holm_adjusted_p_values": secondary["holm_adjusted_p_values"],
            "sensitivity_only": True,
        },
        "selection_rank_stability": rank,
        "interpretation": "The protocol is exploratory; this software does not authorize expansion or confirmation.",
    }
