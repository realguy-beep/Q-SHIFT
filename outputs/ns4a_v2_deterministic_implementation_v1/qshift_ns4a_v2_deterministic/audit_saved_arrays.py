"""Independent saved-array audit.

This module intentionally duplicates the small archive/aggregation checks and
imports neither selection.py nor statistics.py nor checkpoint.py. It reads
only explicitly supplied NPZ paths with allow_pickle=False.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


_CONDITIONS = (
    "balanced_no_burst", "x_biased_no_burst", "z_biased_no_burst",
    "balanced_burst_0.005", "balanced_burst_0.010", "balanced_burst_0.015",
)
_MODELS = _CONDITIONS
_MODES = ("ordinary_pymatching", "correlation_enabled_pymatching")
_SELECTION_IDS = tuple(f"{model}::{mode}" for model in _MODELS for mode in _MODES)
_EVAL_ARMS = (
    "nominal_ordinary_pymatching", "nominal_correlation_enabled_pymatching",
    "pooled_selected_fixed_pymatching", "matched_selected_dem_pymatching_other_mode_control",
    "beliefmatching_same_selected_dem",
)
_SCHEMA = "qshift-ns4a-v2-root-archive-v1"
_KEYS = {
    "schema_version", "partition", "condition_id", "root_id", "sample_ids",
    "detectors", "observables", "candidate_ids", "predictions", "metadata_json",
}


class IndependentAuditError(ValueError):
    """Saved evidence fails the independent auditor's literal checks."""


def _text_scalar(array: np.ndarray, field: str) -> str:
    if array.shape != () or array.dtype.kind not in "US":
        raise IndependentAuditError(f"{field} is not a scalar string.")
    return str(array.item())


def _expected_keys(partition: str) -> tuple[tuple[str, str, int], ...]:
    n = 8 if partition == "selection" else 10
    return tuple((partition, condition, index) for condition in _CONDITIONS for index in range(n))


def _root_id(partition: str, condition: str, index: int) -> str:
    return f"{partition}:{condition}:r{index:02d}"


def _expected_shots(partition: str, condition_index: int, root_index: int) -> int:
    if partition == "evaluation":
        return 4_000
    return 1_333 + int(root_index < (3 if condition_index < 4 else 2))


def audit_saved_arrays(
    paths: Sequence[str | Path], *, partition: str,
    expected_root_keys: Iterable[tuple[str, str, int]] | None = None,
) -> dict[str, Any]:
    """Verify archives and independently recompute root/count/paired metrics.

    Production calls must omit `expected_root_keys`, requiring the exact full
    partition roster. Tests may pass a documented deterministic fixture roster.
    """
    if partition not in {"selection", "evaluation"}:
        raise IndependentAuditError("partition must be selection or evaluation.")
    expected = tuple(_expected_keys(partition) if expected_root_keys is None else expected_root_keys)
    if not expected or any(key[0] != partition or key[1] not in _CONDITIONS for key in expected):
        raise IndependentAuditError("expected root roster is empty or has invalid cells.")
    expected_set = set(expected)
    if len(expected_set) != len(expected):
        raise IndependentAuditError("expected root roster contains duplicates.")

    seen_roots: set[tuple[str, str, str]] = set()
    seen_samples: set[str] = set()
    record_rows: list[dict[str, Any]] = []
    arm_totals: dict[str, dict[str, int]] = {}
    condition_differences: dict[str, list[float]] = {c: [] for c in _CONDITIONS}
    condition_discordances: dict[str, dict[str, int]] = {c: {"BM_wrong_PM_correct": 0, "BM_correct_PM_wrong": 0} for c in _CONDITIONS}
    total_shots = 0

    for archive_path in paths:
        path = Path(archive_path)
        if not path.is_file():
            raise IndependentAuditError(f"missing archive: {path.name}")
        archive_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            with np.load(path, allow_pickle=False) as npz:
                if set(npz.files) != _KEYS:
                    raise IndependentAuditError(f"{path.name} has unexpected archive keys.")
                schema = _text_scalar(np.asarray(npz["schema_version"]), "schema_version")
                part = _text_scalar(np.asarray(npz["partition"]), "partition")
                condition = _text_scalar(np.asarray(npz["condition_id"]), "condition_id")
                root_id = _text_scalar(np.asarray(npz["root_id"]), "root_id")
                sample_ids_array = np.asarray(npz["sample_ids"])
                detectors = np.asarray(npz["detectors"])
                labels = np.asarray(npz["observables"])
                candidate_ids_array = np.asarray(npz["candidate_ids"])
                predictions = np.asarray(npz["predictions"])
                metadata_text = _text_scalar(np.asarray(npz["metadata_json"]), "metadata_json")
        except IndependentAuditError:
            raise
        except Exception as exc:
            raise IndependentAuditError(f"cannot read {path.name}: {type(exc).__name__}: {exc}") from exc

        if schema != _SCHEMA or part != partition or condition not in _CONDITIONS:
            raise IndependentAuditError(f"{path.name} schema/partition/condition mismatch.")
        if sample_ids_array.ndim != 1 or sample_ids_array.dtype.kind not in "US":
            raise IndependentAuditError(f"{path.name} sample IDs are malformed.")
        sample_ids = tuple(str(x) for x in sample_ids_array.tolist())
        if not sample_ids:
            raise IndependentAuditError(f"{path.name} contains no rows.")
        condition_index = _CONDITIONS.index(condition)
        prefix = f"ns4a-v2|{partition}|{condition}|{root_id}|"
        expected_ids = tuple(f"{prefix}{i:06d}" for i in range(len(sample_ids)))
        if sample_ids != expected_ids or len(set(sample_ids)) != len(sample_ids):
            raise IndependentAuditError(f"{path.name} sample IDs/order are invalid.")
        if any(sid in seen_samples for sid in sample_ids):
            raise IndependentAuditError(f"{path.name} duplicates sample IDs already seen.")
        seen_samples.update(sample_ids)

        root_prefix = f"{partition}:{condition}:r"
        if not root_id.startswith(root_prefix) or len(root_id) != len(root_prefix) + 2 or not root_id[-2:].isdigit():
            raise IndependentAuditError(f"{path.name} root ID is not canonical.")
        root_index = int(root_id[-2:])
        key = (partition, condition, root_index)
        if key not in expected_set or root_id != _root_id(partition, condition, root_index):
            raise IndependentAuditError(f"{path.name} root is not in expected roster.")
        if (partition, condition, root_id) in seen_roots:
            raise IndependentAuditError(f"duplicate archive root {root_id}.")
        seen_roots.add((partition, condition, root_id))
        shots = len(sample_ids)
        if shots != _expected_shots(partition, condition_index, root_index):
            raise IndependentAuditError(f"{path.name} shot count differs from V2 allocation.")
        if detectors.dtype != np.uint8 or detectors.shape != (shots, 40) or np.any(detectors > 1):
            raise IndependentAuditError(f"{path.name} detector array is not binary uint8 [shots,40].")
        if labels.dtype != np.uint8 or labels.shape != (shots, 1) or np.any(labels > 1):
            raise IndependentAuditError(f"{path.name} observable array is not binary uint8 [shots,1].")
        candidate_ids = tuple(str(x) for x in candidate_ids_array.tolist())
        expected_candidates = _SELECTION_IDS if partition == "selection" else _EVAL_ARMS
        if candidate_ids_array.ndim != 1 or candidate_ids_array.dtype.kind not in "US" or candidate_ids != expected_candidates:
            raise IndependentAuditError(f"{path.name} candidate/arm order differs from the frozen roster.")
        if predictions.dtype != np.uint8 or predictions.shape != (len(candidate_ids), shots, 1) or np.any(predictions > 1):
            raise IndependentAuditError(f"{path.name} predictions are not binary uint8 [candidate,shots,1].")
        try:
            metadata = json.loads(metadata_text)
        except json.JSONDecodeError as exc:
            raise IndependentAuditError(f"{path.name} metadata JSON is malformed.") from exc
        row_hash = hashlib.sha256("\n".join(sample_ids).encode("utf-8")).hexdigest()
        if metadata.get("row_identity_sha256") != row_hash:
            raise IndependentAuditError(f"{path.name} row identity digest mismatch.")
        if set(metadata.get("model_identity_sha256_by_candidate", {})) != set(candidate_ids):
            raise IndependentAuditError(f"{path.name} model identity map is incomplete.")

        errors = {candidate: int(np.count_nonzero(predictions[i] != labels))
                  for i, candidate in enumerate(candidate_ids)}
        for candidate, value in errors.items():
            arm_totals.setdefault(candidate, {"shots": 0, "errors": 0})
            arm_totals[candidate]["shots"] += shots
            arm_totals[candidate]["errors"] += value
        row: dict[str, Any] = {"condition_id": condition, "root_index": root_index,
                               "root_id": root_id, "shots": shots, "archive_sha256": archive_hash,
                               "errors": errors}
        if partition == "evaluation":
            bm_index = candidate_ids.index("beliefmatching_same_selected_dem")
            pm_index = candidate_ids.index("pooled_selected_fixed_pymatching")
            bm_wrong = predictions[bm_index, :, 0] != labels[:, 0]
            pm_wrong = predictions[pm_index, :, 0] != labels[:, 0]
            condition_discordances[condition]["BM_wrong_PM_correct"] += int(np.count_nonzero(bm_wrong & ~pm_wrong))
            condition_discordances[condition]["BM_correct_PM_wrong"] += int(np.count_nonzero(~bm_wrong & pm_wrong))
            difference = (errors["beliefmatching_same_selected_dem"] - errors["pooled_selected_fixed_pymatching"]) / shots
            condition_differences[condition].append(difference)
            row["paired_difference_bm_minus_selected_pm"] = difference
        record_rows.append(row)
        total_shots += shots

    found = {(part, condition, int(root_id[-2:])) for part, condition, root_id in seen_roots}
    if found != expected_set:
        missing, extra = sorted(expected_set - found), sorted(found - expected_set)
        raise IndependentAuditError(f"root coverage mismatch; missing={missing}, extra={extra}.")

    result: dict[str, Any] = {
        "audit": "PASS",
        "partition": partition,
        "verified_roots": len(seen_roots),
        "unique_shots": total_shots,
        "per_arm": {
            name: {"shots": row["shots"], "errors": row["errors"],
                  "ler": row["errors"] / row["shots"] if row["shots"] else None}
            for name, row in arm_totals.items()
        },
        "per_root": record_rows,
    }
    if partition == "selection":
        scores: list[tuple[str, Fraction]] = []
        for candidate in _SELECTION_IDS:
            cell_means = []
            for condition in _CONDITIONS:
                roots = [row for row in record_rows if row["condition_id"] == condition]
                cell_means.append(sum((Fraction(row["errors"][candidate], row["shots"]) for row in roots), Fraction()) / len(roots))
            scores.append((candidate, sum(cell_means, Fraction()) / 6))
        best = min(value for _, value in scores)
        tie_set = [name for name, value in scores if value == best]
        result["selection"] = {
            "score_by_candidate_fraction": {name: f"{value.numerator}/{value.denominator}" for name, value in scores},
            "selected_candidate": tie_set[0], "exact_tie_set": tie_set,
            "tie_order": "frozen family-major order; ordinary before correlation-enabled",
        }
    else:
        per_condition = {condition: float(np.mean(condition_differences[condition])) for condition in _CONDITIONS}
        result["primary"] = {
            "estimand": "equal-condition mean of root-paired BM minus selected pooled-fixed PM LER",
            "per_condition_difference": per_condition,
            "theta": float(np.mean(list(per_condition.values()))),
            "paired_discordances_by_condition": condition_discordances,
            "zero_error_cells_retained_as_zero": True,
        }
    return result
