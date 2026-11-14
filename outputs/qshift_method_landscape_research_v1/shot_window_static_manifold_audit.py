"""Check whether deterministic mixed-shot feature means lie on static model grids.

This is a population model-adequacy calculation, not calibration or sampling.
Exact categorical-circuit and approximate-DEM feature families stay separate.
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
BURST_GRID = (0.002, 0.010, 0.015, 0.018)
MEAS_GRID = (0.001, 0.003, 0.005)
SCENARIOS = {
    "measurement_only_at_nominal_burst": [(0.010, 0.001, 0.5), (0.010, 0.005, 0.5)],
    "measurement_only_at_low_burst": [(0.002, 0.001, 0.5), (0.002, 0.005, 0.5)],
    "measurement_only_at_high_burst": [(0.018, 0.001, 0.5), (0.018, 0.005, 0.5)],
    "burst_only_at_nominal_measurement": [(0.002, 0.003, 0.5), (0.018, 0.003, 0.5)],
    "positively_correlated_burst_measurement_steps": [(0.002, 0.001, 0.5), (0.018, 0.005, 0.5)],
    "negatively_correlated_burst_measurement_steps": [(0.002, 0.005, 0.5), (0.018, 0.001, 0.5)],
    "balanced_nine_condition_mixture": [(b, m, 1/9) for b in (0.002, 0.010, 0.018) for m in (0.001, 0.003, 0.005)],
}


def main() -> None:
    base = grid.construct(0.010, 0.003)
    sites_template, _ = grid.categorical_sites(base)
    signature = grid.circuit_signature(base)
    exact_profiles: dict[tuple[float, float], np.ndarray] = {}
    dem_profiles: dict[tuple[float, float], np.ndarray] = {}
    for b in BURST_GRID:
        for m in MEAS_GRID:
            circuit = grid.construct(b, m)
            if grid.circuit_signature(circuit) != signature:
                raise RuntimeError("parameter bank changed circuit structure")
            sites = grid.reweight(sites_template, circuit)
            exact_profiles[(b, m)] = grid.means_from_characters(sites)
            dem_profiles[(b, m)] = dem_feature_means(build_dem(b, m)[1])

    results = []
    for name, components in SCENARIOS.items():
        if abs(sum(w for _, _, w in components) - 1) > 1e-12:
            raise RuntimeError(f"scenario {name} weights do not sum to one")
        mean_b = sum(w * b for b, _, w in components)
        mean_m = sum(w * m for _, m, w in components)
        row = {"scenario": name, "mean_parameters": [mean_b, mean_m], "components": [list(v) for v in components]}
        for family, profiles in (("exact_categorical_circuit", exact_profiles), ("approximate_dem", dem_profiles)):
            pooled = sum(w * profiles[(b, m)] for b, m, w in components)
            scale = np.sqrt(np.maximum(pooled * (1 - pooled), 1e-12))
            candidates = []
            for (b, m), means in sorted(profiles.items()):
                standardized = (pooled - means) / scale
                score = float(np.sqrt(np.mean(standardized ** 2)))
                candidates.append((score, b, m, float(np.max(np.abs(standardized))),
                                   float(np.max(np.abs(pooled - means)))))
            score, b, m, max_z, max_abs = min(candidates)
            target_key = min(profiles, key=lambda x: abs(x[0] - mean_b) + abs(x[1] - mean_m))
            if abs(target_key[0] - mean_b) > 1e-12 or abs(target_key[1] - mean_m) > 1e-12:
                raise RuntimeError("arithmetic mean parameter is missing from static grid")
            target_profile = profiles[target_key]
            target_std = (pooled - target_profile) / scale
            row[family] = {
                "nearest_static_grid_parameters": [b, m],
                "nearest_static_standardized_rms_feature_residual": score,
                "nearest_static_max_abs_marginal_sd_residual": max_z,
                "nearest_static_max_abs_feature_mean_residual": max_abs,
                "at_arithmetic_mean_profile_standardized_rms_residual": float(np.sqrt(np.mean(target_std ** 2))),
                "arithmetic_mean_parameters_present_in_grid": True,
            }
        results.append(row)

    result = {
        "classification": "DETERMINISTIC_MIXTURE_TO_STATIC_POPULATION_MANIFOLD_AUDIT",
        "configuration": {"burst_grid": list(BURST_GRID), "measurement_grid": list(MEAS_GRID),
                          "feature_count": 45, "scale": "pooled feature marginal Bernoulli SD; diagonal score only"},
        "method": "Compare deterministic convex mixtures of population means to a small static grid, separately for exact categorical circuit and approximate DEM.",
        "results": results,
        "limitations": [
            "A coarse deterministic grid only; not the existing estimator's fine p grid and not policy tuning.",
            "Diagonal marginal-SD residual is a descriptive compatibility score, not a calibrated statistical test or full-covariance likelihood.",
            "No finite-history data, sampling, logical outcomes, or decoder calls.",
        ],
        "sampling_calls": 0,
        "decoder_calls": 0,
    }
    out = HERE / "SHOT_WINDOW_STATIC_MANIFOLD_AUDIT.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": out.name, "results": [{
        "scenario": r["scenario"],
        "exact_nearest": r["exact_categorical_circuit"]["nearest_static_grid_parameters"],
        "exact_residual": r["exact_categorical_circuit"]["nearest_static_standardized_rms_feature_residual"],
        "dem_nearest": r["approximate_dem"]["nearest_static_grid_parameters"],
        "dem_residual": r["approximate_dem"]["nearest_static_standardized_rms_feature_residual"]}
        for r in results]}, indent=2))


if __name__ == "__main__":
    main()
