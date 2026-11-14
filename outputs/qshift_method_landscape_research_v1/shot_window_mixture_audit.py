"""Deterministic population audit of burst-edge inversion across drifting shots.

For each shot, the five-boundary burst probability is constant, and it may
change between independently reset completed shots. This script combines
exact categorical-circuit feature expectations using prespecified mixture
weights; it never samples detector histories.
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

PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
BURST_PS = (0.002, 0.010, 0.018)
OLD_FRACTIONS = (0.10, 0.25, 0.50, 0.75, 0.90)


def invert(means: np.ndarray, pair_index: int, pair: tuple[int, int]) -> float:
    i, j = pair
    pair_mean = float(means[40 + pair_index])
    covariance = pair_mean - float(means[i]) * float(means[j])
    denominator = 1 - 2 * (float(means[i]) + float(means[j])) + 4 * pair_mean
    radicand = 0.25 - covariance / denominator
    if denominator == 0 or radicand < 0:
        raise ValueError("population mixture left real inversion domain")
    return float(0.5 - np.sqrt(radicand))


def main() -> None:
    template_circuit = grid.construct(0.010, 0.003)
    template_sites, _ = grid.categorical_sites(template_circuit)
    signature = grid.circuit_signature(template_circuit)
    profiles: dict[float, np.ndarray] = {}
    for p in BURST_PS:
        circuit = grid.construct(p, 0.003)
        if grid.circuit_signature(circuit) != signature:
            raise RuntimeError("circuit structure changed across burst probabilities")
        profiles[p] = grid.means_from_characters(grid.reweight(template_sites, circuit))
        if profiles[p].shape != (45,) or not np.isfinite(profiles[p]).all():
            raise RuntimeError("invalid 45-dimensional population feature profile")

    rows = []
    for low, high in ((0.002, 0.018), (0.002, 0.010), (0.010, 0.018)):
        for fraction_old in OLD_FRACTIONS:
            pooled = fraction_old * profiles[low] + (1 - fraction_old) * profiles[high]
            estimates = [invert(pooled, k, pair) for k, pair in enumerate(PAIRS)]
            target = fraction_old * low + (1 - fraction_old) * high
            average = float(np.mean(estimates))
            rows.append({
                "old_burst_p": low,
                "new_burst_p": high,
                "fraction_old_population_in_window": fraction_old,
                "pooled_window_target_mean_burst_p": target,
                "five_edge_population_inversion_estimates": estimates,
                "equal_weight_edge_estimate": average,
                "bias_vs_window_mean": average - target,
                "between_edge_spread": max(estimates) - min(estimates),
            })

    max_bias = max(abs(r["bias_vs_window_mean"]) for r in rows)
    max_spread = max(r["between_edge_spread"] for r in rows)
    if max_bias > 2e-12 or max_spread > 2e-12:
        raise RuntimeError("pooled edge inversion failed population-mixture identity")

    result = {
        "classification": "DETERMINISTIC_EXACT_CATEGORICAL_POPULATION_MIXTURE_AUDIT",
        "model": {
            "circuit": "Q-SHIFT distance-3, five-round Z-memory categorical circuit",
            "gate_p": 0.003,
            "measurement_p": 0.003,
            "burst_probability_constant_within_each_shot": True,
            "burst_probability_may_change_between_independently_reset_shots": True,
            "feature_dimension": 45,
            "edge_pairs": [list(p) for p in PAIRS],
        },
        "method": "Convexly mix exact per-shot population feature means, then apply the published edge-moment inverse to the pooled moments.",
        "population_profile_burst_probabilities": list(BURST_PS),
        "mixture_rows": rows,
        "summary": {
            "mixture_cases": len(rows),
            "edge_estimates": len(rows) * len(PAIRS),
            "max_abs_bias_vs_arithmetic_window_mean": max_bias,
            "max_within_case_spread_across_five_edges": max_spread,
            "tolerance": 2e-12,
        },
        "interpretation_limits": [
            "This is a population identity for a static background model and a shotwise changing burst rate; it is not finite-history estimator accuracy.",
            "No detector histories, random draws, shots, decoder outputs, logical outcomes, or seeds are generated.",
            "The published relative-window difference can isolate one new population time point algebraically, but with one Q-SHIFT detector vector per completed shot its empirical differencing removes the averaging and leaves single-shot noise; practical usefulness is undetermined.",
            "The result does not cover within-shot changes across the five syndrome rounds, temporal dependence between shots, or changing gate/readout nuisance parameters.",
        ],
        "sampling_calls": 0,
        "decoder_calls": 0,
    }
    out = HERE / "SHOT_WINDOW_MIXTURE_AUDIT.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": out.name, **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
