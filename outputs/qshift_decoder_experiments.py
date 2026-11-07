"""Compare simple and model-based decoders on shared independent test shots.

The circuit has only 8 detector bits (at most 256 input patterns). The exact
pattern decoder estimates P(observable flip | detector pattern) from training
counts and selects its threshold on validation. A separate matched DEM decoder
and a deliberately mismatched fixed DEM decoder provide useful references.
"""
import json
from pathlib import Path

import numpy as np
import pymatching
import stim

OUT = Path(__file__).with_name("qshift_decoder_experiments_results.json")
LEVELS = (0.001, 0.003, 0.006)
TRAIN_SHOTS = 2_000_000
VALIDATION_SHOTS = 200_000
TEST_SHOTS = 1_000_000
SEED = 20261105


def sample(circuit, n, seed):
    d, o = circuit.compile_detector_sampler(seed=seed).sample(shots=n, separate_observables=True)
    # Pack detector bits into an integer key (safe here: exactly 8 detectors).
    keys = np.packbits(d.astype(np.uint8), axis=1, bitorder="little")[:, 0].astype(np.uint8)
    return keys, o[:, 0].astype(np.uint8)


def wilson(errors, n):
    z = 1.959963984540054
    p = errors / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(mid - half), float(mid + half)]


def paired_difference_interval(only_ml, only_matching, n):
    """Approximate 95% CI for paired rate difference using discordant shots."""
    delta = (only_ml - only_matching) / n
    se = np.sqrt(max(0, only_ml + only_matching - (only_ml - only_matching) ** 2 / n)) / n
    return [float(delta - 1.96 * se), float(delta + 1.96 * se)]


def main():
    results = {
        "protocol": "per-noise independent train/validation/shared-test batches; exact 256-pattern lookup with Laplace smoothing and validation threshold; same test samples for all decoders",
        "seed": SEED,
        "shots_per_level": {"train": TRAIN_SHOTS, "validation": VALIDATION_SHOTS, "shared_test": TEST_SHOTS},
        "levels": {},
    }
    for i, noise in enumerate(LEVELS):
        circuit = stim.Circuit.generated("repetition_code:memory", distance=3, rounds=3,
                                         after_clifford_depolarization=noise)
        tr_x, tr_y = sample(circuit, TRAIN_SHOTS, SEED + i * 10)
        va_x, va_y = sample(circuit, VALIDATION_SHOTS, SEED + i * 10 + 1)
        te_x, te_y = sample(circuit, TEST_SHOTS, SEED + i * 10 + 2)

        # Estimate P(L0=1 | detector pattern) with weak Beta(1,1) smoothing.
        n_by_pattern = np.bincount(tr_x, minlength=256).astype(float)
        errors_by_pattern = np.bincount(tr_x, weights=tr_y, minlength=256)
        p_error = (errors_by_pattern + 1.0) / (n_by_pattern + 2.0)
        val_scores = p_error[va_x]
        thresholds = np.r_[-np.inf, np.unique(val_scores), np.inf]
        val_rate, threshold = min(
            ((float(np.mean(va_y ^ (val_scores >= t))), float(t)) for t in thresholds),
            key=lambda v: (v[0], v[1]),
        )
        lookup_pred = (p_error[te_x] >= threshold).astype(np.uint8)

        matched = pymatching.Matching.from_detector_error_model(
            circuit.detector_error_model(decompose_errors=True)
        )
        fixed_circuit = stim.Circuit.generated("repetition_code:memory", distance=3, rounds=3,
                                                after_clifford_depolarization=0.003)
        fixed = pymatching.Matching.from_detector_error_model(
            fixed_circuit.detector_error_model(decompose_errors=True)
        )
        te_d, te_obs = circuit.compile_detector_sampler(seed=SEED + i * 10 + 2).sample(
            shots=TEST_SHOTS, separate_observables=True
        )
        matched_pred = np.asarray(matched.decode_batch(te_d), dtype=np.uint8).reshape(-1)
        fixed_pred = np.asarray(fixed.decode_batch(te_d), dtype=np.uint8).reshape(-1)
        actual = te_obs[:, 0].astype(np.uint8)
        predictions = {"pattern_lookup": lookup_pred, "matched_dem": matched_pred, "fixed_dem_at_0.003": fixed_pred}
        entry = {
            "train_observable_errors": int(tr_y.sum()),
            "unique_training_patterns": int(np.unique(tr_x).size),
            "validation_selected_threshold": threshold,
            "validation_residual_rate": val_rate,
            "test_before_errors": int(actual.sum()),
            "test_before_rate": float(actual.mean()),
            "decoders": {},
        }
        residuals = {}
        for name, prediction in predictions.items():
            residual = actual ^ prediction
            errors = int(residual.sum())
            residuals[name] = residual
            entry["decoders"][name] = {"errors": errors, "rate": float(residual.mean()),
                                        "wilson_95": wilson(errors, TEST_SHOTS)}
        entry["paired_vs_matched_dem"] = {
            name: {
                "only_this_decoder_wrong": int(np.sum((residual != 0) & (residuals["matched_dem"] == 0))),
                "only_matched_dem_wrong": int(np.sum((residual == 0) & (residuals["matched_dem"] != 0))),
                "net_error_difference": int(np.sum(residual, dtype=np.int64) - np.sum(residuals["matched_dem"], dtype=np.int64)),
                "paired_rate_difference_wilson_approx_95": paired_difference_interval(
                    int(np.sum((residual != 0) & (residuals["matched_dem"] == 0))),
                    int(np.sum((residual == 0) & (residuals["matched_dem"] != 0))), TEST_SHOTS
                ),
            }
            for name, residual in residuals.items() if name != "matched_dem"
        }
        results["levels"][str(noise)] = entry
        print(noise, json.dumps(entry, indent=2), flush=True)
    OUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
