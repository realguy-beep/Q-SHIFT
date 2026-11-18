"""Independent test of equal-variance vs heteroscedastic score SPRTs."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import beta

from adaptive_basis_sprt import PROFILES
from adaptive_basis_sprt import THRESHOLD
from bias_identification import feature_masks, make_features
from basis_alignment_distance7 import build

HERE = Path(__file__).resolve().parent
NOMINAL = json.loads((HERE / "adaptive_basis_sprt_results.json").read_text())
LDA = json.loads((HERE / "bias_identification_results.json").read_text())["training"]
MEANS = NOMINAL["training_score_means"]
VARS = NOMINAL["training_score_variances"]
POOL_VAR = 0.5 * (float(VARS["x_biased"]) + float(VARS["z_biased"]))
REGIMES = (("nominal", 0.003), ("measurement_shift", 0.006))
PRE_SEEDS = (2026115921, 2026115922, 2026115923, 2026115924)
MAIN_SEEDS = (2026115931, 2026115932, 2026115933, 2026115934)
PRE_WINDOWS, MAIN_WINDOWS, SHOTS_PER_WINDOW = 100, 1_000, 500
MAX_SHOTS = 500


def exact_ci(errors: int, n: int) -> list[float]:
    return [
        0.0 if errors == 0 else float(beta.ppf(0.025, errors, n - errors + 1)),
        1.0 if errors == n else float(beta.ppf(0.975, errors + 1, n - errors)),
    ]


def llr_stream(scores: np.ndarray, model: str) -> np.ndarray:
    if model == "heteroscedastic":
        mu_x, mu_z = float(MEANS["x_biased"]), float(MEANS["z_biased"])
        var_x, var_z = float(VARS["x_biased"]), float(VARS["z_biased"])
        log_x = -0.5 * (np.log(2 * np.pi * var_x) + np.square(scores - mu_x) / var_x)
        log_z = -0.5 * (np.log(2 * np.pi * var_z) + np.square(scores - mu_z) / var_z)
        return log_z - log_x
    if model == "common_variance":
        mu_x, mu_z = float(MEANS["x_biased"]), float(MEANS["z_biased"])
        return ((mu_z - mu_x) / POOL_VAR) * (scores - 0.5 * (mu_x + mu_z))
    raise ValueError(model)


def decision(llr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    cumulative = np.cumsum(llr, axis=1)
    crossed = np.abs(cumulative) >= THRESHOLD
    has_crossed = crossed.any(axis=1)
    first = np.argmax(crossed, axis=1)
    consumed = np.where(has_crossed, first + 1, MAX_SHOTS)
    final = np.where(has_crossed, cumulative[np.arange(len(llr)), np.maximum(consumed - 1, 0)], cumulative[:, -1])
    return final < 0, consumed


def validation_scores(profile: str, measurement_p: float, windows: int, seed: int) -> tuple[np.ndarray, float, dict]:
    from noise_model import build_circuit as source_build

    circuit = build("z", profile, 3, 5, bias_ratio=10.0, gate_p=0.003, measurement_p=measurement_p)
    source = source_build("z", profile, distance=3, rounds=5, bias_ratio=10.0, gate_p=0.003, measurement_p=measurement_p)
    if str(circuit) != str(source):
        raise RuntimeError(f"source builder mismatch for {profile}, measurement_p={measurement_p}")
    masks = feature_masks(circuit, 3, 5)
    started = time.perf_counter()
    det = circuit.compile_detector_sampler(seed=seed).sample(shots=windows * SHOTS_PER_WINDOW)
    elapsed = time.perf_counter() - started
    scores = make_features(det, masks) @ np.asarray(LDA["weights"]) + float(LDA["intercept"])
    if not np.isfinite(scores).all():
        raise RuntimeError("non-finite score values")
    return scores.reshape(windows, SHOTS_PER_WINDOW), elapsed, {
        "source_builder_byte_identical": True,
        "detectors": int(circuit.num_detectors),
        "bucket_sizes": [int(mask.sum()) for mask in masks],
    }


def score_windows(scores: np.ndarray, profile: str) -> dict:
    truth_x = profile == "x_biased"
    h_llr = llr_stream(scores, "heteroscedastic")
    c_llr = llr_stream(scores, "common_variance")
    h_choice, h_n = decision(h_llr)
    c_choice, c_n = decision(c_llr)
    cumulative_h, cumulative_c = np.cumsum(h_llr, axis=1), np.cumsum(c_llr, axis=1)
    fixed = {}
    for budget in (25, 100, 500):
        lda = scores[:, :budget].mean(axis=1) < 0
        h_fixed = cumulative_h[:, budget - 1] < 0
        c_fixed = cumulative_c[:, budget - 1] < 0
        fixed[str(budget)] = {
            "lda_errors": int(np.count_nonzero(lda != truth_x)),
            "heteroscedastic_llr_errors": int(np.count_nonzero(h_fixed != truth_x)),
            "common_variance_llr_errors": int(np.count_nonzero(c_fixed != truth_x)),
        }
    common_errors = int(np.count_nonzero(c_choice != truth_x))
    hetero_errors = int(np.count_nonzero(h_choice != truth_x))
    return {
        "windows": len(scores),
        "score_mean": float(scores.mean()),
        "score_variance": float(scores.var(ddof=1)),
        "common_variance_sprt_errors": common_errors,
        "common_variance_sprt_error_rate": common_errors / len(scores),
        "common_variance_sprt_exact_95_ci": exact_ci(common_errors, len(scores)),
        "common_variance_mean_shots": float(c_n.mean()),
        "common_variance_median_shots": float(np.median(c_n)),
        "heteroscedastic_sprt_errors": hetero_errors,
        "heteroscedastic_sprt_error_rate": hetero_errors / len(scores),
        "heteroscedastic_sprt_exact_95_ci": exact_ci(hetero_errors, len(scores)),
        "heteroscedastic_mean_shots": float(h_n.mean()),
        "fixed_budget_baselines": fixed,
    }


def run(preflight: bool) -> dict:
    started = time.perf_counter()
    windows = PRE_WINDOWS if preflight else MAIN_WINDOWS
    seeds = PRE_SEEDS if preflight else MAIN_SEEDS
    condition_rows, elapsed_sampling = [], 0.0
    i = 0
    for regime, measurement_p in REGIMES:
        for profile in PROFILES:
            scores, seconds, resources = validation_scores(profile, measurement_p, windows, seeds[i])
            elapsed_sampling += seconds
            condition_rows.append({"regime": regime, "measurement_p": measurement_p, "profile": profile, "seed": seeds[i], "resources": resources, **score_windows(scores, profile)})
            i += 1
    elapsed = time.perf_counter() - started
    output = {
        "status": "common_variance_preflight" if preflight else "common_variance_validation",
        "nominal_score_means": MEANS,
        "nominal_score_variances": VARS,
        "pooled_variance": POOL_VAR,
        "fixed_wald_threshold": THRESHOLD,
        "regimes": [{"name": name, "gate_p": 0.003, "measurement_p": p} for name, p in REGIMES],
        "conditions": condition_rows,
        "elapsed_seconds": elapsed,
        "new_source_equivalent_samples": len(condition_rows) * windows * SHOTS_PER_WINDOW,
        "scope": "common-vs-class-specific Gaussian SPRT robustness; development-only",
    }
    if preflight:
        output["projected_main_seconds"] = elapsed * MAIN_WINDOWS / PRE_WINDOWS
        output["runtime_cap_seconds"] = 300
        output["runtime_gate_passed"] = output["projected_main_seconds"] <= 300
        path = HERE / "adaptive_basis_sprt_common_variance_preflight.json"
    else:
        passing = all(
            row["common_variance_sprt_exact_95_ci"][1] <= 0.05
            for row in condition_rows
        )
        output["common_variance_advances"] = passing and float(np.mean([r["common_variance_mean_shots"] for r in condition_rows])) < 100
        path = HERE / "adaptive_basis_sprt_common_variance_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "projected_main_seconds": output.get("projected_main_seconds"), "common_errors": [r["common_variance_sprt_errors"] for r in condition_rows], "common_mean_shots": [r["common_variance_mean_shots"] for r in condition_rows], "output": str(path)}, indent=2))
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    result = run(args.preflight)
    if args.preflight and not result["runtime_gate_passed"]:
        raise SystemExit(1)
