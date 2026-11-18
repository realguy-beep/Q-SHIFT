"""Frozen detector-only sequential X/Z profile calibration screen."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import beta

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bias_identification import FEATURES, feature_masks, make_features
from basis_alignment_distance7 import build

MODEL = json.loads((HERE / "bias_identification_results.json").read_text())["training"]
W = np.asarray(MODEL["weights"], dtype=float)
B = float(MODEL["intercept"])
PROFILES = ("x_biased", "z_biased")
PRE_TRAIN = (2026115301, 2026115302)
PRE_VALIDATION = (2026115303, 2026115304)
MAIN_TRAIN = (2026115311, 2026115312)
MAIN_VALIDATION = (2026115313, 2026115314)
PRE_TRAIN_SHOTS = 10_000
MAIN_TRAIN_SHOTS = 50_000
WINDOWS = 1_000
WINDOWS_PREFLIGHT = 100
MAX_SHOTS = 500
THRESHOLD = float(np.log(19))


def sample_scores(profile: str, count: int, seed: int) -> tuple[np.ndarray, float, dict]:
    circuit = build("z", profile, 3, 5, bias_ratio=10.0)
    masks = feature_masks(circuit, 3, 5)
    t = time.perf_counter()
    detector_samples = circuit.compile_detector_sampler(seed=seed).sample(shots=count)
    elapsed = time.perf_counter() - t
    features = make_features(detector_samples, masks)
    scores = features @ W + B
    if not np.isfinite(scores).all():
        raise RuntimeError(f"non-finite detector-only scores for {profile}")
    return scores, elapsed, {
        "detectors": int(circuit.num_detectors),
        "feature_bucket_sizes": [int(mask.sum()) for mask in masks],
        "feature_count": len(FEATURES),
    }


def exact_ci(errors: int, windows: int) -> list[float]:
    return [
        0.0 if errors == 0 else float(beta.ppf(0.025, errors, windows - errors + 1)),
        1.0 if errors == windows else float(beta.ppf(0.975, errors + 1, windows - errors)),
    ]


def evaluate(
    train_scores: dict[str, np.ndarray] | None,
    validation: dict[str, np.ndarray],
    windows: int,
    frozen_parameters: dict | None = None,
) -> dict:
    if frozen_parameters is None:
        assert train_scores is not None
        means = {profile: float(np.mean(train_scores[profile])) for profile in PROFILES}
        variances = {profile: float(np.var(train_scores[profile], ddof=1)) for profile in PROFILES}
    else:
        means = {profile: float(frozen_parameters["training_score_means"][profile]) for profile in PROFILES}
        variances = {profile: float(frozen_parameters["training_score_variances"][profile]) for profile in PROFILES}
    if min(variances.values()) <= 0:
        raise RuntimeError("non-positive training score variance")

    def log_density(score: np.ndarray, profile: str) -> np.ndarray:
        var = variances[profile]
        return -0.5 * (np.log(2 * np.pi * var) + np.square(score - means[profile]) / var)

    metrics = []
    for profile in PROFILES:
        score_windows = validation[profile].reshape(windows, MAX_SHOTS)
        llr = log_density(score_windows, "z_biased") - log_density(score_windows, "x_biased")
        cumulative = np.cumsum(llr, axis=1)
        crossed = np.abs(cumulative) >= THRESHOLD
        has_crossed = crossed.any(axis=1)
        first_cross = np.argmax(crossed, axis=1)
        consumed = np.where(has_crossed, first_cross + 1, MAX_SHOTS)
        stopped_llr = np.where(
            has_crossed,
            cumulative[np.arange(windows), np.maximum(consumed - 1, 0)],
            cumulative[:, -1],
        )
        sprt_predict_x = stopped_llr < 0
        truth_x = profile == "x_biased"
        sprt_errors = int(np.count_nonzero(sprt_predict_x != truth_x))
        fixed = {}
        fixed_likelihood = {}
        for budget in (25, 100, 500):
            predict_x = score_windows[:, :budget].mean(axis=1) < 0
            errors = int(np.count_nonzero(predict_x != truth_x))
            fixed[str(budget)] = {
                "errors": errors,
                "windows": windows,
                "error_rate": errors / windows,
                "exact_95_ci": exact_ci(errors, windows),
            }
            likelihood_predict_x = cumulative[:, budget - 1] < 0
            likelihood_errors = int(np.count_nonzero(likelihood_predict_x != truth_x))
            fixed_likelihood[str(budget)] = {
                "errors": likelihood_errors,
                "windows": windows,
                "error_rate": likelihood_errors / windows,
                "exact_95_ci": exact_ci(likelihood_errors, windows),
            }
        metrics.append(
            {
                "profile": profile,
                "sprt_errors": sprt_errors,
                "sprt_error_rate": sprt_errors / windows,
                "sprt_exact_95_ci": exact_ci(sprt_errors, windows),
                "mean_shots_consumed": float(consumed.mean()),
                "median_shots_consumed": float(np.median(consumed)),
                "stopped_before_cap": int(np.count_nonzero(has_crossed)),
                "fixed_prefix_baselines": fixed,
                "fixed_prefix_gaussian_likelihood_baselines": fixed_likelihood,
            }
        )
    return {
        "training_score_means": means,
        "training_score_variances": variances,
        "wald_threshold": THRESHOLD,
        "per_profile": metrics,
        "both_profile_error_rates_at_most_5pct": all(row["sprt_error_rate"] <= 0.05 for row in metrics),
        "mean_shots_under_25": float(np.mean([row["mean_shots_consumed"] for row in metrics])) < 25,
    }


def run(preflight: bool) -> dict:
    started = time.perf_counter()
    from noise_model import build_circuit as source_build

    source_matches = {
        profile: str(build("z", profile, 3, 5, bias_ratio=10.0))
        == str(source_build("z", profile, distance=3, rounds=5, bias_ratio=10.0))
        for profile in PROFILES
    }
    if not all(source_matches.values()):
        raise RuntimeError(f"calibration circuit differs from source builder: {source_matches}")
    train_n = PRE_TRAIN_SHOTS if preflight else MAIN_TRAIN_SHOTS
    windows = WINDOWS_PREFLIGHT if preflight else WINDOWS
    train_seeds = PRE_TRAIN if preflight else MAIN_TRAIN
    validation_seeds = PRE_VALIDATION if preflight else MAIN_VALIDATION
    train_scores, validation_scores, sample_rows = {}, {}, []
    for i, profile in enumerate(PROFILES):
        train, train_seconds, info = sample_scores(profile, train_n, train_seeds[i])
        validation, valid_seconds, _ = sample_scores(profile, windows * MAX_SHOTS, validation_seeds[i])
        train_scores[profile] = train
        validation_scores[profile] = validation
        sample_rows.append(
            {
                "profile": profile,
                "train_seed": train_seeds[i],
                "training_shots": train_n,
                "training_sampling_seconds": train_seconds,
                "validation_seed": validation_seeds[i],
                "validation_windows": windows,
                "validation_shots": windows * MAX_SHOTS,
                "validation_sampling_seconds": valid_seconds,
                "resources": info,
            }
        )
    result = evaluate(train_scores, validation_scores, windows)
    elapsed = time.perf_counter() - started
    result.update(
        {
            "status": "sequential_calibration_preflight" if preflight else "sequential_calibration_validation",
            "distance": 3,
            "rounds": 5,
            "bias_ratio": 10,
            "gate_and_measurement_p": 0.003,
            "frozen_lda_source": "bias_identification_results.json; no weights fitted or updated here",
            "source_builder_byte_identical": source_matches,
            "decoder_observables_used": False,
            "sample_rows": sample_rows,
            "elapsed_seconds": elapsed,
            "new_source_equivalent_samples": sum(r["training_shots"] + r["validation_shots"] for r in sample_rows),
            "scope": "detector calibration only; two fixed simulator profiles; no logical LER or change-point claim",
            "matched_fixed_gaussian_likelihood_comparator": "retrospective fairness analysis; not in primary protocol",
        }
    )
    if preflight:
        full_equiv = sum(MAIN_TRAIN_SHOTS + WINDOWS * MAX_SHOTS for _ in PROFILES)
        result["projected_main_seconds"] = elapsed * full_equiv / result["new_source_equivalent_samples"]
        result["main_runtime_cap_seconds"] = 300
        result["runtime_gate_passed"] = result["projected_main_seconds"] <= 300
        target = HERE / "adaptive_basis_sprt_preflight.json"
    else:
        target = HERE / "adaptive_basis_sprt_results.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "projected_main_seconds": result.get("projected_main_seconds"), "profile_error_rates": [r["sprt_error_rate"] for r in result["per_profile"]], "mean_shots": [r["mean_shots_consumed"] for r in result["per_profile"]], "output": str(target)}, indent=2))
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    output = run(args.preflight)
    if args.preflight and not output["runtime_gate_passed"]:
        raise SystemExit(1)
