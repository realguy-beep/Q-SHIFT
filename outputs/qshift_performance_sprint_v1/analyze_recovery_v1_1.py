"""Analyze only hash-committed V1.1 paired arrays; never samples or decodes."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from recovery_support_v1_1 import RECOVERY, ROOT, sha_file

P_VALUES = (0.0, 0.004, 0.008, 0.012, 0.016)
ARMS = ("pooled_fixed", "profile_estimated", "oracle_true_p", "nominal_no_burst")
ROOTS = 10
SHOTS = 2000
REPS = 100000


def paired_bootstrap(differences: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Resample independent roots inside each condition, preserving decoder pairing."""
    by_condition = []
    for condition in differences:
        index = rng.integers(0, len(condition), size=(REPS, len(condition)))
        by_condition.append(condition[index].mean(axis=1))
    return np.mean(np.stack(by_condition, axis=0), axis=0)


def analyze() -> dict:
    status = json.loads((RECOVERY / "status.json").read_text(encoding="utf-8"))
    if (status.get("status") != "completed" or status.get("committed_roots") != 50
            or status.get("committed_evaluation_rows") != 100000
            or status.get("verified_unique_total_rows") != 130000):
        raise RuntimeError("V1.1 recovery status is not complete")
    inventory = json.loads((ROOT / "seed_inventory.json").read_text(encoding="utf-8"))["seeds"]
    rows = []
    by_p: dict[float, dict] = {}
    for i, p in enumerate(P_VALUES):
        group = []
        for root in range(ROOTS):
            stem = f"eval_p{i}_r{root:02d}"
            archive = RECOVERY / f"{stem}.npz"
            marker = json.loads((RECOVERY / f"{stem}.commit.json").read_text(encoding="utf-8"))
            if marker.get("archive_sha256") != sha_file(archive):
                raise RuntimeError(f"archive hash mismatch: {stem}")
            sample_id = f"eval:p{i}:r{root:02d}"
            if (marker.get("sample_id") != sample_id or marker.get("seed") != inventory[sample_id]
                    or marker.get("p_index") != i or marker.get("root") != root
                    or marker.get("shots") != SHOTS):
                raise RuntimeError(f"sample identity mismatch: {stem}")
            with np.load(archive, allow_pickle=False) as data:
                detectors = np.asarray(data["detectors"], dtype=np.uint8)
                labels = np.asarray(data["observables"], dtype=np.uint8)
                pred = {arm: np.asarray(data[f"pred_{arm}"], dtype=np.uint8) for arm in ARMS}
            if detectors.shape != (SHOTS, 40) or labels.shape != (SHOTS, 1):
                raise RuntimeError(f"invalid paired sample shape: {stem}")
            if not np.isin(detectors, [0, 1]).all() or not np.isin(labels, [0, 1]).all():
                raise RuntimeError(f"nonbinary paired sample: {stem}")
            if any(a.shape != labels.shape or not np.isin(a, [0, 1]).all() for a in pred.values()):
                raise RuntimeError(f"invalid saved prediction array: {stem}")
            errors = {arm: int(np.count_nonzero(pred[arm] != labels)) for arm in ARMS}
            row = {
                "p_burst": p, "p_index": i, "root": root, "sample_id": sample_id,
                "seed": marker["seed"], "shots": SHOTS, "p_hat": marker["p_hat"],
                "p_global": marker["p_global"], "archive_sha256": marker["archive_sha256"],
                "fixed_errors": errors["pooled_fixed"], "profile_errors": errors["profile_estimated"],
                "oracle_errors": errors["oracle_true_p"], "nominal_errors": errors["nominal_no_burst"],
                "fixed_ler": errors["pooled_fixed"] / SHOTS,
                "profile_ler": errors["profile_estimated"] / SHOTS,
                "oracle_ler": errors["oracle_true_p"] / SHOTS,
                "nominal_ler": errors["nominal_no_burst"] / SHOTS,
                "paired_disagreements": int(np.count_nonzero(pred["profile_estimated"] != pred["pooled_fixed"])),
                "profile_only_errors": int(np.count_nonzero(
                    (pred["profile_estimated"] != labels) & (pred["pooled_fixed"] == labels))),
                "fixed_only_errors": int(np.count_nonzero(
                    (pred["pooled_fixed"] != labels) & (pred["profile_estimated"] == labels))),
            }
            rows.append(row)
            group.append(row)
        fixed_n = sum(r["fixed_errors"] for r in group)
        profile_n = sum(r["profile_errors"] for r in group)
        error_names = {"pooled_fixed": "fixed_errors", "profile_estimated": "profile_errors",
                       "oracle_true_p": "oracle_errors", "nominal_no_burst": "nominal_errors"}
        by_p[p] = {
            "roots": ROOTS, "shots": ROOTS * SHOTS,
            "errors": {arm: sum(r[error_names[arm]] for r in group) for arm in ARMS},
            "rates": {"pooled_fixed": fixed_n / (ROOTS * SHOTS),
                      "profile_estimated": profile_n / (ROOTS * SHOTS),
                      "oracle_true_p": sum(r["oracle_errors"] for r in group) / (ROOTS * SHOTS),
                      "nominal_no_burst": sum(r["nominal_errors"] for r in group) / (ROOTS * SHOTS)},
            "root_paired_profile_minus_fixed": [r["profile_ler"] - r["fixed_ler"] for r in group],
            "paired_disagreements": sum(r["paired_disagreements"] for r in group),
            "profile_only_errors": sum(r["profile_only_errors"] for r in group),
            "fixed_only_errors": sum(r["fixed_only_errors"] for r in group),
            "mean_p_hat": float(np.mean([r["p_hat"] for r in group])),
        }

    diffs = np.asarray([by_p[p]["root_paired_profile_minus_fixed"] for p in P_VALUES[1:]], dtype=np.float64)
    point = float(diffs.mean())
    fixed_ler = float(np.mean([by_p[p]["rates"]["pooled_fixed"] for p in P_VALUES[1:]]))
    profile_ler = float(np.mean([by_p[p]["rates"]["profile_estimated"] for p in P_VALUES[1:]]))
    relative = None if fixed_ler == 0 else (fixed_ler - profile_ler) / fixed_ler
    seeds = json.loads((ROOT / "seed_inventory.json").read_text(encoding="utf-8"))["seeds"]
    boot = paired_bootstrap(diffs, np.random.default_rng(seeds["statistics:primary-bootstrap"]))
    ci = [float(np.quantile(boot, 0.025, method="linear")),
          float(np.quantile(boot, 0.975, method="linear"))]
    zero = np.asarray([by_p[0.0]["root_paired_profile_minus_fixed"]], dtype=np.float64)
    zero_boot = paired_bootstrap(zero, np.random.default_rng(seeds["statistics:zero-gate"]))
    zero_bounds = [float(np.quantile(zero_boot, 0.05, method="linear")),
                   float(np.quantile(zero_boot, 0.95, method="linear"))]
    condition_ci = {}
    condition_rng = np.random.default_rng(seeds["statistics:condition-bootstrap"])
    for p in P_VALUES:
        condition = np.asarray([by_p[p]["root_paired_profile_minus_fixed"]], dtype=np.float64)
        condition_boot = paired_bootstrap(condition, condition_rng)
        condition_ci[str(p)] = [float(np.quantile(condition_boot, 0.025, method="linear")),
                                float(np.quantile(condition_boot, 0.975, method="linear"))]
    favorable = sum(by_p[p]["rates"]["profile_estimated"] < by_p[p]["rates"]["pooled_fixed"]
                    for p in P_VALUES[1:])
    harm = any(by_p[p]["rates"]["profile_estimated"] - by_p[p]["rates"]["pooled_fixed"] > 0.0005
               for p in P_VALUES[1:])
    fixed_errors = sum(by_p[p]["errors"]["pooled_fixed"] for p in P_VALUES[1:])
    if (fixed_errors >= 100 and ci[1] < 0 and relative is not None and relative >= 0.50
            and favorable >= 3 and not harm and zero_bounds[1] < 0.0005):
        decision = "GO"
    elif ci[0] >= 0 or zero_bounds[0] > 0.0005:
        decision = "NO-GO"
    else:
        decision = "INCONCLUSIVE"

    with (ROOT / "root_results_v1_1.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "schema": "qshift-performance-analysis-v1.1", "status": "completed",
        "unique_shots": 130000, "evaluation_shots": 100000, "roots": 50,
        "primary": {"estimand": "equal-weight nonzero-condition root-paired profile-minus-pooled-fixed LER",
                    "difference": point, "profile_ler": profile_ler, "fixed_ler": fixed_ler,
                    "relative_reduction": relative, "percentile_95_ci": ci,
                    "bootstrap_replicates": REPS, "root_count_per_condition": ROOTS,
                    "fixed_errors_nonzero": fixed_errors},
        "zero_burst_no_harm": {"difference": float(zero.mean()), "bootstrap_lower_upper_5_95": zero_bounds,
                                "tolerance": 0.0005},
        "per_condition": {str(p): {**by_p[p], "profile_minus_fixed_95_ci": condition_ci[str(p)]}
                          for p in P_VALUES},
        "favorable_nonzero_conditions": favorable, "decision": decision,
        "runtime": {"combined_wall_seconds": status.get("combined_wall_seconds"),
                    "recovery_wall_seconds": status.get("recovery_wall_seconds"),
                    "peak_working_set_bytes": status.get("peak_working_set_bytes"),
                    "artifact_bytes": status.get("artifact_bytes"),
                    "evaluation_sampling_seconds": status.get("evaluation_sampling_seconds"),
                    "evaluation_decoder_seconds": status.get("evaluation_decoder_seconds"),
                    "construction_seconds": status.get("construction_seconds")},
        "recovery_disclosure": status.get("replay_limitation"),
        "interpretation": "Exploratory development-only result on the synthetic correlated-noise model; oracle arm is not a fair deployable comparator and is excluded from primary decision.",
    }
    (ROOT / "analysis_v1_1.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), indent=2, sort_keys=True))
