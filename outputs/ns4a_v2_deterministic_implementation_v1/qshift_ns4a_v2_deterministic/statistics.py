"""Prespecified NS-4A V2 root-cluster statistics (no scientific data source)."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Mapping, Sequence

import numpy as np
from scipy.stats import t as student_t

from .protocol import (
    CONDITIONS, EVALUATION_ARMS, EVALUATION_ROOTS_PER_CONDITION,
    EVALUATION_SHOTS_PER_ROOT, PRIMARY_BOOTSTRAP_REPLICATES, make_root_id,
    SIGN_FLIP_REPLICATES,
)


class StatisticsError(ValueError):
    """Statistical input does not match the frozen root-paired design."""


PRIMARY_CANDIDATE = "beliefmatching_same_selected_dem"
PRIMARY_REFERENCE = "pooled_selected_fixed_pymatching"
SECONDARY_CONTRASTS = (
    "bm_vs_selected_dem_ordinary_pm",
    "bm_vs_selected_dem_correlation_enabled_pm",
    "selected_pm_vs_nominal_ordinary_pm",
)


@dataclass(frozen=True)
class EvaluationRootCounts:
    condition_id: str
    root_index: int
    root_id: str
    shots: int
    errors_by_arm: Mapping[str, int]


@dataclass(frozen=True)
class PrimaryBootstrapResult:
    point_estimate: float
    lower_95: float
    upper_95: float
    replicates: int
    quantile_method: str
    bootstrap_distribution: np.ndarray


@dataclass(frozen=True)
class SignFlipResult:
    observed_statistic: float
    p_value: float
    extreme_assignments: int
    assignments: int
    two_sided: bool = True
    add_one: bool = True
    sensitivity_only: bool = True


def validate_evaluation_roots(records: Sequence[EvaluationRootCounts]) -> dict[str, tuple[EvaluationRootCounts, ...]]:
    by_condition: dict[str, dict[int, EvaluationRootCounts]] = {c: {} for c in CONDITIONS}
    seen_ids: set[str] = set()
    for record in records:
        if record.condition_id not in by_condition or type(record.root_index) is not int or not 0 <= record.root_index < 10:
            raise StatisticsError("invalid evaluation condition/root index.")
        if record.root_index in by_condition[record.condition_id]:
            raise StatisticsError("duplicate evaluation condition/root index.")
        if record.root_id != make_root_id("evaluation", record.condition_id, record.root_index):
            raise StatisticsError("evaluation root_id does not match its condition/root index.")
        if not record.root_id or record.root_id in seen_ids:
            raise StatisticsError("evaluation root IDs must be nonempty and globally unique.")
        seen_ids.add(record.root_id)
        if record.shots != EVALUATION_SHOTS_PER_ROOT:
            raise StatisticsError("every evaluation root must contain exactly 4000 paired shots.")
        if tuple(record.errors_by_arm.keys()) != EVALUATION_ARMS:
            raise StatisticsError("each root must contain all five named evaluation arms in frozen order.")
        for count in record.errors_by_arm.values():
            if type(count) is not int or not 0 <= count <= record.shots:
                raise StatisticsError("error counts must be integers between 0 and shots.")
        by_condition[record.condition_id][record.root_index] = record
    for condition, roots in by_condition.items():
        if tuple(sorted(roots)) != tuple(range(EVALUATION_ROOTS_PER_CONDITION)):
            raise StatisticsError(f"condition {condition} must have root indices 0..9 exactly once.")
    return {condition: tuple(by_condition[condition][i] for i in range(10)) for condition in CONDITIONS}


def paired_root_differences(
    records: Sequence[EvaluationRootCounts], candidate: str, reference: str,
) -> np.ndarray:
    if candidate not in EVALUATION_ARMS or reference not in EVALUATION_ARMS or candidate == reference:
        raise StatisticsError("candidate/reference must be distinct frozen arm names.")
    by_condition = validate_evaluation_roots(records)
    result = np.empty((6, 10), dtype=np.float64)
    for ci, condition in enumerate(CONDITIONS):
        for ri, record in enumerate(by_condition[condition]):
            result[ci, ri] = (
                record.errors_by_arm[candidate] - record.errors_by_arm[reference]
            ) / EVALUATION_SHOTS_PER_ROOT
    return result


def primary_point_estimate(records: Sequence[EvaluationRootCounts]) -> float:
    # Equal condition weighting; each root's BM/reference outcomes remain paired.
    return float(paired_root_differences(records, PRIMARY_CANDIDATE, PRIMARY_REFERENCE).mean(axis=1).mean())


def relative_error_reduction(candidate_ler: float, baseline_ler: float) -> float | None:
    """Return relative LER reduction, undefined when baseline LER is zero."""
    values = (float(candidate_ler), float(baseline_ler))
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in values):
        raise StatisticsError("LER values must be finite and in [0,1].")
    if baseline_ler == 0:
        return None
    return (baseline_ler - candidate_ler) / baseline_ler


def primary_bootstrap(
    records: Sequence[EvaluationRootCounts], rng: np.random.Generator,
) -> PrimaryBootstrapResult:
    """100k root-stratified paired percentile bootstrap; linear quantiles."""
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a caller-supplied independent NumPy Generator.")
    differences = paired_root_differences(records, PRIMARY_CANDIDATE, PRIMARY_REFERENCE)
    draws = np.empty(PRIMARY_BOOTSTRAP_REPLICATES, dtype=np.float64)
    rng_states = np.arange(6, dtype=np.int64)[None, :, None]
    start = 0
    while start < PRIMARY_BOOTSTRAP_REPLICATES:
        count = min(2_000, PRIMARY_BOOTSTRAP_REPLICATES - start)
        indices = rng.integers(0, 10, size=(count, 6, 10), dtype=np.int16)
        selected = differences[rng_states, indices]
        draws[start:start + count] = selected.mean(axis=2).mean(axis=1)
        start += count
    lower, upper = np.quantile(draws, (0.025, 0.975), method="linear")
    return PrimaryBootstrapResult(
        primary_point_estimate(records), float(lower), float(upper),
        PRIMARY_BOOTSTRAP_REPLICATES, "linear", draws,
    )


def _rng_state_fingerprint(rng: np.random.Generator) -> str:
    state = json.dumps(rng.bit_generator.state, sort_keys=True, default=lambda x: x.tolist())
    import hashlib
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def validate_independent_rngs(rngs: Mapping[str, np.random.Generator], expected_names: Sequence[str]) -> None:
    if tuple(rngs.keys()) != tuple(expected_names):
        raise StatisticsError("analysis RNGs must be supplied in the exact predeclared contrast order.")
    if any(not isinstance(rng, np.random.Generator) for rng in rngs.values()):
        raise TypeError("each analysis stream must be an explicit NumPy Generator.")
    if len({id(rng) for rng in rngs.values()}) != len(rngs):
        raise StatisticsError("each contrast requires an independent RNG object.")
    if len({_rng_state_fingerprint(rng) for rng in rngs.values()}) != len(rngs):
        raise StatisticsError("analysis RNG initial states collide; provide disjoint stream seeds.")


def root_sign_flip(
    differences: np.ndarray, rng: np.random.Generator,
) -> SignFlipResult:
    """Two-sided absolute-statistic root-cluster sign flip with add-one p.

    Each independent condition-root cluster gets one sign per assignment.
    Equality is counted as extreme. This is sensitivity inference, not a
    randomized treatment test; it assumes independent clusters and a
    symmetric root-level null distribution (or justified exchangeability).
    """
    values = np.asarray(differences, dtype=np.float64)
    if values.shape != (6, 10) or not np.isfinite(values).all():
        raise StatisticsError("sign-flip input must be a finite [6,10] root-difference matrix.")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be an explicit NumPy Generator.")
    assignments = SIGN_FLIP_REPLICATES
    observed = float(values.mean(axis=1).mean())
    extreme = 0
    start = 0
    while start < assignments:
        count = min(2_000, assignments - start)
        signs = rng.integers(0, 2, size=(count, 6, 10), dtype=np.int8).astype(np.int8) * 2 - 1
        simulated = (values[None, :, :] * signs).mean(axis=2).mean(axis=1)
        extreme += int(np.count_nonzero(np.abs(simulated) >= abs(observed)))
        start += count
    return SignFlipResult(observed, (extreme + 1) / (assignments + 1), extreme, assignments)


def secondary_sign_flip_holm(
    records: Sequence[EvaluationRootCounts], rngs: Mapping[str, np.random.Generator],
    *, selected_mode: str,
) -> dict[str, object]:
    """Three secondary root sign-flip p-values followed by exact-size Holm."""
    validate_independent_rngs(rngs, SECONDARY_CONTRASTS)
    if selected_mode not in {"ordinary_pymatching", "correlation_enabled_pymatching"}:
        raise StatisticsError("selected_mode must identify the globally selected PyMatching mode.")
    other_mode = ("correlation_enabled_pymatching" if selected_mode == "ordinary_pymatching"
                  else "ordinary_pymatching")
    selected_arm = PRIMARY_REFERENCE
    other_mode_arm = "matched_selected_dem_pymatching_other_mode_control"
    ordinary_arm = selected_arm if selected_mode == "ordinary_pymatching" else other_mode_arm
    correlated_arm = selected_arm if selected_mode == "correlation_enabled_pymatching" else other_mode_arm
    contrasts = (
        ("bm_vs_selected_dem_ordinary_pm", PRIMARY_CANDIDATE, ordinary_arm),
        ("bm_vs_selected_dem_correlation_enabled_pm", PRIMARY_CANDIDATE, correlated_arm),
        ("selected_pm_vs_nominal_ordinary_pm", PRIMARY_REFERENCE, "nominal_ordinary_pymatching"),
    )
    raw: dict[str, float] = {}
    details: dict[str, SignFlipResult] = {}
    for name, candidate, reference in contrasts:
        difference = paired_root_differences(records, candidate, reference)
        result = root_sign_flip(difference, rngs[name])
        raw[name] = result.p_value
        details[name] = result
    adjusted = holm_adjust(raw, expected_names=SECONDARY_CONTRASTS)
    return {"raw_p_values": raw, "holm_adjusted_p_values": adjusted, "details": details,
            "family_size": 3, "selected_mode": selected_mode, "other_mode": other_mode,
            "method": "root-cluster sign-flip Monte Carlo; two-sided absolute statistic; add-one"}


def holm_adjust(raw_p_values: Mapping[str, float], *, expected_names: Sequence[str]) -> dict[str, float]:
    names = tuple(expected_names)
    if len(names) != 3 or tuple(raw_p_values.keys()) != names:
        raise StatisticsError("Holm input must contain exactly the three prespecified hypotheses in frozen order.")
    values = [float(raw_p_values[name]) for name in names]
    if any(not math.isfinite(p) or p < 0 or p > 1 for p in values):
        raise StatisticsError("raw p-values must be finite and in [0,1].")
    order = sorted(range(3), key=lambda i: (values[i], i))
    adjusted = [0.0] * 3
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (3 - rank) * values[index])
        adjusted[index] = min(1.0, running)
    return {name: adjusted[i] for i, name in enumerate(names)}


def leave_one_root_out(records: Sequence[EvaluationRootCounts]) -> dict[str, dict[str, float]]:
    by_condition = validate_evaluation_roots(records)
    out: dict[str, dict[str, float]] = {}
    for condition in CONDITIONS:
        for removed_index in range(10):
            means = []
            for current in CONDITIONS:
                values = [
                    (r.errors_by_arm[PRIMARY_CANDIDATE] - r.errors_by_arm[PRIMARY_REFERENCE]) / r.shots
                    for i, r in enumerate(by_condition[current])
                    if current != condition or i != removed_index
                ]
                # The affected condition has 9 roots; others retain all 10.
                means.append(float(np.mean(values)))
            out[f"{condition}:root{removed_index:02d}-omitted"] = {"theta": float(np.mean(means))}
    return out


def root_t_interval_sensitivity(records: Sequence[EvaluationRootCounts], alpha: float = 0.05) -> dict[str, object]:
    """Stratified Welch/Satterthwaite root-level t interval; sensitivity only."""
    if not 0 < alpha < 1:
        raise StatisticsError("alpha must be in (0,1).")
    differences = paired_root_differences(records, PRIMARY_CANDIDATE, PRIMARY_REFERENCE)
    point = float(differences.mean(axis=1).mean())
    n = differences.shape[1]
    component_variances = np.var(differences, axis=1, ddof=1) / (6.0 ** 2 * n)
    variance = float(component_variances.sum())
    if variance == 0.0:
        return {"estimate": point, "lower": point, "upper": point, "df": None,
                "status": "degenerate_zero_root_variance_sensitivity_only"}
    denominator = float(np.sum(component_variances ** 2 / (n - 1)))
    df = variance ** 2 / denominator
    critical = float(student_t.ppf(1 - alpha / 2, df))
    half = critical * math.sqrt(variance)
    return {"estimate": point, "lower": point - half, "upper": point + half,
            "df": df, "status": "welch_satterthwaite_root_level_sensitivity_only"}
