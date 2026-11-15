"""Recompute development-pilot paired metrics from hash-verified saved arrays."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
ARMS = ("pooled_fixed", "profile_estimated", "oracle_true_p", "nominal_no_burst")
P_VALUES = (0.0, 0.004, 0.008, 0.012, 0.016)
SHOTS = 2000
ROOTS = 10
REPS = 100000


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def paired_bootstrap(root_differences: np.ndarray, rng: np.random.Generator,
                     replicates: int = REPS) -> np.ndarray:
    x = np.asarray(root_differences, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] == 0 or x.shape[1] < 2:
        raise ValueError("expected [conditions, independent roots] paired differences")
    result = []
    for condition in x:
        idx = rng.integers(0, len(condition), size=(replicates, len(condition)))
        result.append(condition[idx].mean(axis=1))
    return np.mean(np.stack(result, axis=0), axis=0)


def load_verified_roots() -> tuple[list[dict], dict]:
    status = json.loads((SAMPLES / "status.json").read_text(encoding="utf-8"))
    if status.get("status") != "completed" or status.get("verified_shots_committed") != 130000:
        raise RuntimeError("runner status is not a verified complete 130,000-shot pilot")
    rows = []
    arrays_by_key = {}
    for p_index, p in enumerate(P_VALUES):
        for root in range(ROOTS):
            stem = f"eval_p{p_index}_r{root:02d}"
            archive = SAMPLES / f"{stem}.npz"
            marker_path = SAMPLES / f"{stem}.commit.json"
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            if marker.get("archive_sha256") != sha_file(archive):
                raise RuntimeError(f"archive hash mismatch: {stem}")
            if marker.get("sample_id") != f"eval:p{p_index}:r{root:02d}" or marker.get("shots") != SHOTS:
                raise RuntimeError(f"root identity/count mismatch: {stem}")
            with np.load(archive, allow_pickle=False) as data:
                d = np.asarray(data["detectors"], dtype=np.uint8)
                y = np.asarray(data["observables"], dtype=np.uint8)
                pred = {arm: np.asarray(data[f"pred_{arm}"], dtype=np.uint8) for arm in ARMS}
            if d.shape != (SHOTS, 40) or y.shape != (SHOTS, 1):
                raise RuntimeError(f"sample shape mismatch: {stem}")
            if any(a.shape != y.shape or not np.isin(a, [0, 1]).all() for a in pred.values()):
                raise RuntimeError(f"prediction shape/value mismatch: {stem}")
            if not np.isin(d, [0, 1]).all() or not np.isin(y, [0, 1]).all():
                raise RuntimeError(f"nonbinary saved sample: {stem}")
            errs = {arm: int(np.count_nonzero(pred[arm] != y)) for arm in ARMS}
            disagree = {arm: int(np.count_nonzero(pred[arm] != pred["pooled_fixed"]))
                        for arm in ARMS if arm != "pooled_fixed"}
            row = {
                "p_burst": p, "p_index": p_index, "root": root, "sample_id": marker["sample_id"],
                "seed": marker["seed"], "shots": SHOTS,
                "p_hat": marker["p_hat"], "p_global": marker["p_global"],
                "detector_sha256": marker["detector_sha256"],
                "observable_sha256": marker["observable_sha256"],
                "archive_sha256": marker["archive_sha256"],
                "fixed_errors": errs["pooled_fixed"],
                "profile_errors": errs["profile_estimated"],
                "oracle_errors": errs["oracle_true_p"],
                "nominal_errors": errs["nominal_no_burst"],
                "fixed_ler": errs["pooled_fixed"] / SHOTS,
                "profile_ler": errs["profile_estimated"] / SHOTS,
                "oracle_ler": errs["oracle_true_p"] / SHOTS,
                "nominal_ler": errs["nominal_no_burst"] / SHOTS,
                "profile_disagreements_vs_fixed": disagree["profile_estimated"],
                "profile_only_errors": int(np.count_nonzero(
                    (pred["profile_estimated"] != y) & (pred["pooled_fixed"] == y))),
                "fixed_only_errors": int(np.count_nonzero(
                    (pred["pooled_fixed"] != y) & (pred["profile_estimated"] == y))),
            }
            rows.append(row)
            arrays_by_key[(p_index, root)] = (d, y, pred)
    return rows, {"status": status, "arrays": arrays_by_key}


def analyze() -> dict:
    rows, loaded = load_verified_roots()
    ROOT.joinpath("root_results.csv").parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with (ROOT / "root_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    by_p = {}
    for i, p in enumerate(P_VALUES):
        group = [r for r in rows if r["p_index"] == i]
        by_p[str(p)] = {
            "shots": sum(r["shots"] for r in group),
            "roots": len(group),
            "rates": {
                arm: sum(r[f"{arm}_errors"] for r in group) / sum(r["shots"] for r in group)
                for arm in ("fixed", "profile", "oracle", "nominal")
            },
            "errors": {
                arm: sum(r[f"{arm}_errors"] for r in group)
                for arm in ("fixed", "profile", "oracle", "nominal")
            },
            "mean_root_p_hat": float(np.mean([r["p_hat"] for r in group])),
            "root_profile_minus_fixed": [
                r["profile_ler"] - r["fixed_ler"] for r in group
            ],
            "paired_disagreements": sum(r["profile_disagreements_vs_fixed"] for r in group),
            "profile_only_errors": sum(r["profile_only_errors"] for r in group),
            "fixed_only_errors": sum(r["fixed_only_errors"] for r in group),
        }
    nonzero = [by_p[str(p)]["root_profile_minus_fixed"] for p in P_VALUES[1:]]
    diffs = np.asarray(nonzero, dtype=np.float64)
    point = float(diffs.mean())
    fixed_rate = float(np.mean([by_p[str(p)]["rates"]["fixed"] for p in P_VALUES[1:]]))
    profile_rate = float(np.mean([by_p[str(p)]["rates"]["profile"] for p in P_VALUES[1:]]))
    relative = None if fixed_rate == 0 else float((fixed_rate - profile_rate) / fixed_rate)
    seed_inventory = json.loads((ROOT / "seed_inventory.json").read_text())["seeds"]
    primary_rng = np.random.default_rng(seed_inventory["statistics:primary-bootstrap"])
    boot = paired_bootstrap(diffs, primary_rng)
    ci = [float(np.quantile(boot, 0.025, method="linear")),
          float(np.quantile(boot, 0.975, method="linear"))]
    condition_rng = np.random.default_rng(seed_inventory["statistics:condition-bootstrap"])
    condition_intervals = {}
    for p in P_VALUES:
        key = str(p)
        condition_d = np.asarray([by_p[key]["root_profile_minus_fixed"]], dtype=np.float64)
        condition_boot = paired_bootstrap(condition_d, condition_rng)
        condition_intervals[key] = [
            float(np.quantile(condition_boot, 0.025, method="linear")),
            float(np.quantile(condition_boot, 0.975, method="linear")),
        ]
    zero = np.asarray([by_p["0.0"]["root_profile_minus_fixed"]], dtype=np.float64)
    zero_rng = np.random.default_rng(seed_inventory["statistics:zero-gate"])
    zero_boot = paired_bootstrap(zero, zero_rng)
    zero_bounds = [float(np.quantile(zero_boot, 0.05, method="linear")),
                   float(np.quantile(zero_boot, 0.95, method="linear"))]
    calibration_diag = json.loads((ROOT / "calibration_estimates.json").read_text(encoding="utf-8"))
    estimate_residuals = [
        float(row["p_hat"]) - float(row["simulation_p_for_diagnostic_only"])
        for row in calibration_diag["estimates"]
    ]
    noise_estimation = {
        "calibration_batch_count": len(estimate_residuals),
        "mean_bias": float(np.mean(estimate_residuals)),
        "mae": float(np.mean(np.abs(estimate_residuals))),
        "p_global": float(calibration_diag["p_global"]),
        "p_grid_equal_weight_mean": float(np.mean(P_VALUES)),
        "p_global_minus_grid_mean": float(calibration_diag["p_global"] - np.mean(P_VALUES)),
        "per_condition": {
            str(p): {
                "mean_p_hat": float(np.mean([row["p_hat"] for row in calibration_diag["estimates"]
                                             if row["simulation_p_for_diagnostic_only"] == p])),
                "bias": float(np.mean([row["p_hat"] - p for row in calibration_diag["estimates"]
                                       if row["simulation_p_for_diagnostic_only"] == p])),
                "mae": float(np.mean([abs(row["p_hat"] - p) for row in calibration_diag["estimates"]
                                      if row["simulation_p_for_diagnostic_only"] == p])),
            } for p in P_VALUES
        },
    }
    nonzero_fixed_errors = sum(by_p[str(p)]["errors"]["fixed"] for p in P_VALUES[1:])
    condition_favorable = sum(by_p[str(p)]["rates"]["profile"] < by_p[str(p)]["rates"]["fixed"]
                              for p in P_VALUES[1:])
    condition_harm = any(by_p[str(p)]["rates"]["profile"] - by_p[str(p)]["rates"]["fixed"] > 0.0005
                         for p in P_VALUES[1:])
    if (nonzero_fixed_errors >= 100 and ci[1] < 0 and relative is not None and relative >= 0.50
            and condition_favorable >= 3 and not condition_harm and zero_bounds[1] < 0.0005):
        decision = "GO"
    elif ci[0] >= 0 or zero_bounds[0] > 0.0005:
        decision = "NO-GO"
    else:
        decision = "INCONCLUSIVE"
    result = {
        "schema": "qshift-performance-analysis-v1",
        "status": loaded["status"]["status"],
        "verified_total_shots": loaded["status"]["verified_shots_committed"],
        "roots": loaded["status"]["roots_complete"],
        "primary": {
            "estimand": "equal-weight nonzero-condition root-paired profile-minus-pooled-fixed LER",
            "difference": point, "profile_ler": profile_rate, "fixed_ler": fixed_rate,
            "relative_reduction": relative, "percentile_95_ci": ci,
            "bootstrap_replicates": REPS, "roots_per_condition": ROOTS,
            "fixed_errors_nonzero": nonzero_fixed_errors,
        },
        "zero_burst_no_harm": {
            "p": 0.0, "profile_minus_fixed": float(zero.mean()),
            "one_sided_95_lower_and_upper": zero_bounds,
            "tolerance": 0.0005,
        },
        "noise_estimation": noise_estimation,
        "favorable_nonzero_conditions": condition_favorable,
        "per_condition": {
            key: {**value, "profile_minus_fixed_95_ci": condition_intervals[key]}
            for key, value in by_p.items()
        },
        "decision": decision,
        "interpretation": "Development-only result on this synthetic model; oracle arm is excluded from the primary decision.",
        "runtime": {
            "wall_seconds": loaded["status"].get("wall_seconds"),
            "peak_working_set_bytes": loaded["status"].get("peak_working_set_bytes"),
            "artifact_bytes": loaded["status"].get("artifact_bytes"),
            "training_sampling_seconds_by_p": calibration_diag.get("training_sampling_seconds_by_p"),
            "calibration_sampling_seconds_by_seed": calibration_diag.get("calibration_sampling_seconds_by_seed"),
            "evaluation_sampling_seconds": loaded["status"].get("evaluation_sampling_seconds_total"),
            "decoder_seconds": loaded["status"].get("evaluation_decoder_seconds_total"),
            "construction_seconds": loaded["status"].get("construction_seconds"),
        },
    }
    (ROOT / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), indent=2, sort_keys=True))