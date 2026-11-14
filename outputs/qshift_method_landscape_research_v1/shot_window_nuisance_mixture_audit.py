"""Deterministic window-mixture sensitivity to measurement-noise drift.

Mixes exact per-shot population feature profiles across burst/measurement
conditions, then applies the published edge-moment inversion. Exact circuit
and approximate DEM results are kept separate; no shots are sampled.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import categorical_circuit_parameter_grid_audit as grid
from dem_feature_expectations import build_dem, feature_means as dem_feature_means

PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
BURST_PS = (0.002, 0.010, 0.018)
MEAS_PS = (0.001, 0.003, 0.005)


def invert_profile(mean: np.ndarray) -> list[float]:
    estimates = []
    for k, (i, j) in enumerate(PAIRS):
        pair = float(mean[40 + k])
        covariance = pair - float(mean[i]) * float(mean[j])
        denominator = 1 - 2 * (float(mean[i]) + float(mean[j])) + 4 * pair
        radicand = 0.25 - covariance / denominator
        if denominator == 0 or radicand < 0:
            estimates.append(float('nan'))
        else:
            estimates.append(float(0.5 - np.sqrt(radicand)))
    return estimates


def main() -> None:
    base = grid.construct(0.010, 0.003)
    template, _ = grid.categorical_sites(base)
    signature = grid.circuit_signature(base)
    profiles: dict[tuple[str, float, float], np.ndarray] = {}
    for burst_p in BURST_PS:
        for meas_p in MEAS_PS:
            circuit = grid.construct(burst_p, meas_p)
            if grid.circuit_signature(circuit) != signature:
                raise RuntimeError("noise probabilities changed circuit structure")
            sites = grid.reweight(template, circuit)
            exact = grid.means_from_characters(sites)
            dem = dem_feature_means(build_dem(burst_p, meas_p)[1])
            profiles[('exact_categorical_circuit', burst_p, meas_p)] = exact
            profiles[('approximate_dem', burst_p, meas_p)] = dem

    scenarios = {
        "measurement_only_at_nominal_burst": [(0.010, 0.001, 0.5), (0.010, 0.005, 0.5)],
        "measurement_only_at_low_burst": [(0.002, 0.001, 0.5), (0.002, 0.005, 0.5)],
        "measurement_only_at_high_burst": [(0.018, 0.001, 0.5), (0.018, 0.005, 0.5)],
        "burst_only_at_nominal_measurement": [(0.002, 0.003, 0.5), (0.018, 0.003, 0.5)],
        "positively_correlated_burst_measurement_steps": [(0.002, 0.001, 0.5), (0.018, 0.005, 0.5)],
        "negatively_correlated_burst_measurement_steps": [(0.002, 0.005, 0.5), (0.018, 0.001, 0.5)],
        "balanced_nine_condition_mixture": [(b, m, 1/9) for b in BURST_PS for m in MEAS_PS],
    }
    rows = []
    for name, components in scenarios.items():
        if abs(sum(w for _, _, w in components) - 1) > 1e-12:
            raise RuntimeError(f"scenario {name} weights do not sum to one")
        target_b = sum(w * b for b, _, w in components)
        target_m = sum(w * m for _, m, w in components)
        row = {"scenario": name, "components": [list(x) for x in components],
               "arithmetic_window_mean_burst_p": target_b,
               "arithmetic_window_mean_measurement_p": target_m}
        for model in ('exact_categorical_circuit', 'approximate_dem'):
            pooled = sum(w * profiles[(model, b, m)] for b, m, w in components)
            estimates = invert_profile(pooled)
            row[model] = {
                "edge_estimates": estimates,
                "equal_edge_mean_estimate": float(np.mean(estimates)) if np.isfinite(estimates).all() else None,
                "bias_vs_mean_burst_p": float(np.mean(estimates) - target_b) if np.isfinite(estimates).all() else None,
                "edge_spread": float(max(estimates) - min(estimates)) if np.isfinite(estimates).all() else None,
            }
        rows.append(row)

    result = {
        "classification": "DETERMINISTIC_POPULATION_MIXTURE_UNDER_MEASUREMENT_DRIFT",
        "configuration": {
            "circuit": "Q-SHIFT distance-3 five-round balanced Z-memory",
            "gate_p": 0.003,
            "burst_p_grid": list(BURST_PS),
            "measurement_p_grid": list(MEAS_PS),
            "features": 45,
            "models_separate": ["exact categorical circuit", "approximate DEM"],
        },
        "method": "Take convex mixtures of per-shot deterministic population means; invert pooled pair moments. No samples or outcomes.",
        "scenarios": rows,
        "limitations": [
            "Population mixtures only; no finite-history estimator distribution, alarm behavior, or decoder utility.",
            "Components are deterministic scenario weights, not generated shot sequences.",
            "Exact categorical-circuit means and approximate-DEM means are reported separately.",
            "Measurement probabilities are stationary within each shot; the script does not model within-shot boundary-specific readout drift.",
        ],
        "sampling_calls": 0,
        "decoder_calls": 0,
    }
    out = HERE / "SHOT_WINDOW_NUISANCE_MIXTURE_AUDIT.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": out.name, "scenarios": [{
        "name": r["scenario"], "target_burst_p": r["arithmetic_window_mean_burst_p"],
        "exact_bias": r["exact_categorical_circuit"]["bias_vs_mean_burst_p"],
        "dem_bias": r["approximate_dem"]["bias_vs_mean_burst_p"]} for r in rows]}, indent=2))


if __name__ == "__main__":
    main()
