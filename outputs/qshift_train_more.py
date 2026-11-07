"""Larger-sample, paired ML vs PyMatching benchmark for Q-SHIFT v0.1."""
import json
from pathlib import Path

import numpy as np
import pymatching
import stim
from sklearn.ensemble import RandomForestClassifier

OUT = Path(__file__).with_name("qshift_train_more_results.json")
LEVELS = (0.001, 0.003, 0.006)
TRAIN_SHOTS = 500_000
VALIDATION_SHOTS = 100_000
TEST_SHOTS = 200_000
SEED = 20261104


def sample(circuit, n, seed):
    d, o = circuit.compile_detector_sampler(seed=seed).sample(
        shots=n, separate_observables=True
    )
    return d.astype(np.uint8), o[:, 0].astype(np.uint8)


def interval(errors, shots):
    z = 1.959963984540054
    p = errors / shots
    den = 1 + z * z / shots
    mid = (p + z * z / (2 * shots)) / den
    half = z * np.sqrt(p * (1 - p) / shots + z * z / (4 * shots**2)) / den
    return [float(mid - half), float(mid + half)]


def main():
    results = {
        "protocol": "independent train, validation, and shared held-out test Stim shots; fixed matching DEM; detector-only RF; validation threshold minimizes XOR residual",
        "seed": SEED,
        "shots_per_level": {"train": TRAIN_SHOTS, "validation": VALIDATION_SHOTS, "shared_test": TEST_SHOTS},
        "levels": {},
    }
    for i, noise in enumerate(LEVELS):
        circuit = stim.Circuit.generated(
            "repetition_code:memory", distance=3, rounds=3,
            after_clifford_depolarization=noise,
        )
        train_d, train_y = sample(circuit, TRAIN_SHOTS, SEED + 100 * i)
        val_d, val_y = sample(circuit, VALIDATION_SHOTS, SEED + 100 * i + 1)
        test_d, test_y = sample(circuit, TEST_SHOTS, SEED + 100 * i + 2)

        model = RandomForestClassifier(
            n_estimators=300, max_depth=10, min_samples_leaf=2,
            random_state=SEED + i, n_jobs=-1,
        )
        model.fit(train_d, train_y)
        val_p = model.predict_proba(val_d)[:, 1]
        thresholds = np.r_[-np.inf, np.unique(val_p), np.inf]
        val_rate, threshold = min(
            ((float(np.mean(val_y ^ (val_p >= t))), float(t)) for t in thresholds),
            key=lambda pair: (pair[0], pair[1]),
        )
        ml_pred = (model.predict_proba(test_d)[:, 1] >= threshold).astype(np.uint8)
        dem = circuit.detector_error_model(decompose_errors=True)
        matching = pymatching.Matching.from_detector_error_model(dem)
        match_pred = np.asarray(matching.decode_batch(test_d), dtype=np.uint8).reshape(-1)
        ml_residual, match_residual = test_y ^ ml_pred, test_y ^ match_pred
        ml_errors, match_errors = int(ml_residual.sum()), int(match_residual.sum())
        results["levels"][str(noise)] = {
            "detectors": circuit.num_detectors,
            "threshold_selected_on_validation": threshold,
            "validation_residual_rate": val_rate,
            "shared_test_before_errors": int(test_y.sum()),
            "shared_test_before_rate": float(test_y.mean()),
            "matching": {
                "errors": match_errors, "rate": float(match_residual.mean()),
                "wilson_95": interval(match_errors, TEST_SHOTS),
            },
            "ml": {
                "errors": ml_errors, "rate": float(ml_residual.mean()),
                "wilson_95": interval(ml_errors, TEST_SHOTS),
            },
            "paired_test": {
                "both_correct": int(np.sum((ml_residual == 0) & (match_residual == 0))),
                "ml_only_wrong": int(np.sum((ml_residual != 0) & (match_residual == 0))),
                "matching_only_wrong": int(np.sum((ml_residual == 0) & (match_residual != 0))),
                "both_wrong": int(np.sum((ml_residual != 0) & (match_residual != 0))),
                "ml_minus_matching_errors": ml_errors - match_errors,
            },
        }
        print(noise, json.dumps(results["levels"][str(noise)], indent=2), flush=True)
    OUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
