"""Deterministic information-per-shot audit for burst-rate step changes.

Computes exact joint distributions of the ten detectors in five burst pairs
for the categorical circuit and independent approximate DEM, then evaluates
KL/TV distances. No detector histories or random outcomes are generated.
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
from categorical_circuit_feature_expectations import direct_xor
from dem_feature_expectations import build_dem, direct_xor_convolution

PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
SELECTED = tuple(d for pair in PAIRS for d in pair)
TRANSITIONS = ((0.002, 0.010), (0.010, 0.018), (0.002, 0.018))
MEASUREMENT_PS = (0.001, 0.003, 0.005)


def kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    if abs(float(p.sum()) - 1) > 2e-12 or abs(float(q.sum()) - 1) > 2e-12:
        raise ValueError("joint distribution does not sum to one")
    mask = p > 0
    if np.any(q[mask] == 0):
        return float("inf")
    return float(np.sum(p[mask] * np.log(p[mask] / q[mask])))


def distances(p_old: np.ndarray, p_new: np.ndarray) -> dict:
    tv = float(0.5 * np.abs(p_new - p_old).sum())
    midpoint = (p_old + p_new) / 2
    jsd = 0.5 * kl_divergence(p_old, midpoint) + 0.5 * kl_divergence(p_new, midpoint)
    return {
        "KL_new_given_old_nats_per_shot": kl_divergence(p_new, p_old),
        "KL_old_given_new_nats_per_shot": kl_divergence(p_old, p_new),
        "jensen_shannon_nats_per_shot": jsd,
        "total_variation_per_shot": tv,
        "hellinger_squared_per_shot": float(1 - np.sqrt(p_old * p_new).sum()),
    }


def exact_circuit_distribution(template: list, p: float, pm: float) -> np.ndarray:
    circuit = grid.construct(p, pm)
    sites = grid.reweight(template, circuit)
    distribution = direct_xor(sites, SELECTED)
    if abs(float(distribution.sum()) - 1) > 2e-12:
        raise RuntimeError("exact circuit ten-detector distribution failed normalization")
    return distribution


def dem_distribution(p: float, pm: float) -> np.ndarray:
    _, mechanisms = build_dem(p, pm)
    distribution = direct_xor_convolution(mechanisms, SELECTED)
    if abs(float(distribution.sum()) - 1) > 2e-12:
        raise RuntimeError("approximate DEM ten-detector distribution failed normalization")
    return distribution


def main() -> None:
    base = grid.construct(0.010, 0.003)
    template, _ = grid.categorical_sites(base)
    burst_values = sorted({p for transition in TRANSITIONS for p in transition})
    exact_cache = {(p, pm): exact_circuit_distribution(template, p, pm)
                   for p in burst_values for pm in MEASUREMENT_PS}
    dem_cache = {(p, pm): dem_distribution(p, pm)
                 for p in burst_values for pm in MEASUREMENT_PS}
    rows = []
    for pm in MEASUREMENT_PS:
        for old_p, new_p in TRANSITIONS:
            exact_old = exact_cache[(old_p, pm)]
            exact_new = exact_cache[(new_p, pm)]
            dem_old = dem_cache[(old_p, pm)]
            dem_new = dem_cache[(new_p, pm)]
            rows.append({
                "old_burst_p": old_p,
                "new_burst_p": new_p,
                "measurement_p": pm,
                "exact_categorical_circuit": distances(exact_old, exact_new),
                "approximate_dem": distances(dem_old, dem_new),
                "support_states_exact_old_new": [int(np.count_nonzero(exact_old)), int(np.count_nonzero(exact_new))],
                "support_states_dem_old_new": [int(np.count_nonzero(dem_old)), int(np.count_nonzero(dem_new))],
            })
    nuisance_rows = []
    for old_p, new_p in TRANSITIONS:
        for model, cache in (("exact_categorical_circuit", exact_cache), ("approximate_dem", dem_cache)):
            candidates = []
            for old_pm in MEASUREMENT_PS:
                for new_pm in MEASUREMENT_PS:
                    d = distances(cache[(old_p, old_pm)], cache[(new_p, new_pm)])
                    candidates.append((d["KL_new_given_old_nats_per_shot"], old_pm, new_pm,
                                       d["total_variation_per_shot"], d["jensen_shannon_nats_per_shot"]))
            min_row = min(candidates, key=lambda x: x[0])
            nuisance_rows.append({
                "model": model,
                "old_burst_p": old_p,
                "new_burst_p": new_p,
                "min_KL_new_given_old_over_independent_old_new_measurement_p_grid": min_row[0],
                "measurement_p_old_new_attaining_minimum": [min_row[1], min_row[2]],
                "total_variation_at_minimum_KL": min_row[3],
                "jensen_shannon_at_minimum_KL": min_row[4],
                "measurement_grid": list(MEASUREMENT_PS),
            })
    identity_error = 0.0
    for cache in (exact_cache, dem_cache):
        for distribution in cache.values():
            self_distance = distances(distribution, distribution)
            identity_error = max(identity_error, abs(self_distance["KL_new_given_old_nats_per_shot"]))
    if identity_error > 2e-12:
        raise RuntimeError("information-distance identity check failed")
    if any(r["exact_categorical_circuit"]["KL_new_given_old_nats_per_shot"] < -1e-12
           or r["approximate_dem"]["KL_new_given_old_nats_per_shot"] < -1e-12 for r in rows):
        raise RuntimeError("KL divergence became negative beyond numerical tolerance")
    result = {
        "classification": "DETERMINISTIC_PER_SHOT_INFORMATION_DISTANCE_NOT_CHANGE_DETECTOR_EVALUATION",
        "configuration": {
            "circuit": "Q-SHIFT distance-3, five-round balanced Z-memory",
            "gate_p": 0.003,
            "detectors": list(SELECTED),
            "features": "joint ten-bit distribution for five burst detector pairs",
            "transition_grid": [list(x) for x in TRANSITIONS],
            "measurement_p_grid": list(MEASUREMENT_PS),
        },
        "method": "Exact parity-recursion distributions over 2^10 states; KL, Jensen-Shannon, total-variation, and Hellinger distances. Exact categorical circuit and approximate DEM are distinct.",
        "rows": rows,
        "measurement_nuisance_grid_minima": nuisance_rows,
        "deterministic_validation": {
            "self_KL_max_abs_error": identity_error,
            "all_probabilities_normalized": True,
            "all_reported_KL_nonnegative_within_tolerance": True,
        },
        "interpretation": [
            "KL new||old is expected log-likelihood evidence per independent completed shot under the stated model; it is a signal-information quantity, not a false-alarm threshold or actual detection delay.",
            "The ten-detector subset yields a lower bound on information in all 40 detector bits by data processing, but omits other measurements that may help estimate nuisance rates.",
            "Any sequential-delay calculation needs a prespecified error target, causal policy, finite-history calibration, model-mismatch allowance, and suitable stopping-time analysis.",
            "No logical outcomes, decoder utility, sampling, or independent confirmation is assessed.",
        ],
        "sampling_calls": 0,
        "decoder_calls": 0,
    }
    out = HERE / "BURST_STEP_INFORMATION_AUDIT.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": out.name, "rows": [{
        "old_p": r["old_burst_p"], "new_p": r["new_burst_p"], "measurement_p": r["measurement_p"],
        "exact_kl": r["exact_categorical_circuit"]["KL_new_given_old_nats_per_shot"],
        "dem_kl": r["approximate_dem"]["KL_new_given_old_nats_per_shot"],
        "exact_tv": r["exact_categorical_circuit"]["total_variation_per_shot"],
        "dem_tv": r["approximate_dem"]["total_variation_per_shot"]} for r in rows],
        "measurement_nuisance_minima": nuisance_rows}, indent=2))


if __name__ == "__main__":
    main()
