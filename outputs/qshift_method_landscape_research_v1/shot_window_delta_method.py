"""Independent-shot heteroscedastic delta method for pooled burst-edge moments.

Computes deterministic population gradients and exact per-shot categorical
feature covariance matrices. No sampled histories or Monte Carlo is used.
The reported coefficient is an asymptotic standard-deviation scale divided
by sqrt(window_shots), not finite-sample accuracy or a window recommendation.
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
from edge_moment_delta_method import edge_gradient, edge_p

PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))


def estimate_and_gradient(means: np.ndarray) -> tuple[np.ndarray, float]:
    gradient = np.zeros(45)
    estimates = []
    for k, (i, j) in enumerate(PAIRS):
        ids = np.array([i, j, 40 + k])
        x = means[ids]
        g = edge_gradient(x)
        gradient[ids] += g / len(PAIRS)
        estimates.append(edge_p(x))
    return gradient, float(np.mean(estimates))


def main() -> None:
    template_circuit = grid.construct(0.010, 0.003)
    template, _ = grid.categorical_sites(template_circuit)
    signature = grid.circuit_signature(template_circuit)

    def moments(p: float) -> tuple[np.ndarray, np.ndarray]:
        circuit = grid.construct(p, 0.003)
        if grid.circuit_signature(circuit) != signature:
            raise RuntimeError("circuit structure changed across p")
        sites = grid.reweight(template, circuit)
        means = grid.means_from_characters(sites)
        return means, grid.exact_cov(sites, means)

    profiles = {p: moments(p) for p in (0.002, 0.006, 0.010, 0.014, 0.018)}
    scenarios = []
    for low_p, high_p, fraction_low in (
        (0.002, 0.018, 0.25),
        (0.002, 0.018, 0.50),
        (0.002, 0.018, 0.75),
    ):
        low_mean, low_cov = profiles[low_p]
        high_mean, high_cov = profiles[high_p]
        pooled_mean = fraction_low * low_mean + (1 - fraction_low) * high_mean
        average_cov = fraction_low * low_cov + (1 - fraction_low) * high_cov
        g, estimate = estimate_and_gradient(pooled_mean)
        coefficient = float(np.sqrt(g @ average_cov @ g))

        target_p = fraction_low * low_p + (1 - fraction_low) * high_p
        stationary_key = min(profiles, key=lambda p: abs(p - target_p))
        stationary_mean, stationary_cov = profiles[stationary_key] if abs(stationary_key - target_p) < 1e-12 else (None, None)
        stationary_coefficient = None
        population_profile_mean_gap = None
        if stationary_mean is not None:
            stationary_gradient, stationary_estimate = estimate_and_gradient(stationary_mean)
            stationary_coefficient = float(np.sqrt(stationary_gradient @ stationary_cov @ stationary_gradient))
            population_profile_mean_gap = float(np.max(np.abs(pooled_mean - stationary_mean)))
            if abs(stationary_estimate - target_p) > 2e-12:
                raise RuntimeError("stationary comparison profile failed recovery")
        scenarios.append({
            "low_burst_p": low_p,
            "high_burst_p": high_p,
            "fraction_low_shots_in_window": fraction_low,
            "arithmetic_window_mean_p": target_p,
            "pooled_population_estimate": estimate,
            "asymptotic_sd_coefficient_over_sqrt_window_shots": coefficient,
            "stationary_at_mean_p_coefficient_if_profile_available": stationary_coefficient,
            "pooled_vs_stationary_mean_feature_max_abs_gap_if_available": population_profile_mean_gap,
        })

    result = {
        "classification": "INDEPENDENT_NONIDENTICAL_SHOT_DELTA_METHOD_ASYMPTOTIC_ONLY",
        "model": {
            "features": "45 exact categorical-circuit detector means/cofires",
            "gate_p": 0.003,
            "measurement_p": 0.003,
            "burst_rate_constant_within_shot": True,
            "shots_independent_conditional_on_deterministic_burst_rate_schedule": True,
            "sampling_calls": 0,
        },
        "method": "For a window with fixed fractions of independent shot strata, Cov(mean feature)=average single-shot covariance/window size; delta method evaluates the edge-inversion gradient at pooled population means.",
        "scenarios": scenarios,
        "limitations": [
            "This is an asymptotic covariance calculation, not finite-sample estimator bias, domain-failure probability, interval coverage, or alarm behavior.",
            "The deterministic schedules are two-regime mixtures, not sampled trajectories or a recommendation for window length.",
            "The calculation assumes independent shots, known unchanged gate/readout background, and the exact categorical model.",
            "It does not analyze the approximate DEM estimator, temporal dependence, clipping, or decoder utility.",
        ],
        "decoder_calls": 0,
    }
    out = HERE / "SHOT_WINDOW_DELTA_METHOD.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": out.name, "scenarios": scenarios}, indent=2))


if __name__ == "__main__":
    main()
