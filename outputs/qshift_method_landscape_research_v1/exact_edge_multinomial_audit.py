"""Exact finite-N multinomial audit for one pooled burst detector pair.

The distribution is enumerated analytically from exact categorical-circuit
population probabilities. No detector history is sampled or materialized.
This is a one-edge diagnostic; it is not the joint five-edge estimator.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import categorical_circuit_parameter_grid_audit as grid

PAIR = (8, 10)
PAIR_INDEX = 0
BURST_PS = (0.002, 0.010, 0.018)
WINDOW_SHOTS = (25, 50, 100, 200)


def multinomial_edge_summary(n: int, q: np.ndarray, true_p: float) -> dict:
    if q.shape != (4,) or np.any(q <= 0) or abs(float(q.sum()) - 1) > 1e-12:
        raise ValueError(f"invalid pair-cell probabilities: {q}")
    log_fact = np.array([math.lgamma(k + 1) for k in range(n + 1)])
    log_q = np.log(q)
    probability_total = invalid_probability = negative_probability = above_half_probability = 0.0
    zero_cofire_probability = 0.0
    estimate_sum = estimate_sq_error_sum = 0.0
    valid_probability = 0.0
    sample_marginal_sums = np.zeros(3)

    # Cell order is n11, n10, n01, n00. Enumerate all count tables using
    # vectorized runs over n01 for each n11/n10 pair.
    for n11 in range(n + 1):
        for n10 in range(n - n11 + 1):
            n01 = np.arange(n - n11 - n10 + 1, dtype=np.int64)
            n00 = n - n11 - n10 - n01
            log_probability = (
                log_fact[n]
                - log_fact[n11]
                - log_fact[n10]
                - log_fact[n01]
                - log_fact[n00]
                + n11 * log_q[0]
                + n10 * log_q[1]
                + n01 * log_q[2]
                + n00 * log_q[3]
            )
            weights = np.exp(log_probability)
            a = (n10 + n11) / n
            b = (n01 + n11) / n
            c = n11 / n
            covariance = c - a * b
            denominator = 1 - 2 * (a + b) + 4 * c
            radicand = np.full_like(covariance, np.nan, dtype=float)
            nonzero = denominator != 0
            radicand[nonzero] = 0.25 - covariance[nonzero] / denominator[nonzero]
            valid = np.isfinite(radicand) & (radicand >= 0)
            probability_total += float(weights.sum())
            sample_marginal_sums += np.array([weights.sum() * a, weights @ b, weights.sum() * c])
            if n11 == 0:
                zero_cofire_probability += float(weights.sum())
            invalid_probability += float(weights[~valid].sum())
            if np.any(valid):
                estimate = 0.5 - np.sqrt(radicand[valid])
                wv = weights[valid]
                valid_probability += float(wv.sum())
                estimate_sum += float(wv @ estimate)
                estimate_sq_error_sum += float(wv @ ((estimate - true_p) ** 2))
                negative_probability += float(wv[estimate < 0].sum())
                above_half_probability += float(wv[estimate > 0.5].sum())

    if abs(probability_total - 1) > 2e-10:
        raise RuntimeError(f"multinomial enumeration sums to {probability_total}, not 1")
    theoretical_means = np.array([q[0] + q[1], q[0] + q[2], q[0]])
    mean_error = float(np.max(np.abs(sample_marginal_sums - theoretical_means)))
    zero_cofire_formula = float((1 - q[0]) ** n)
    zero_cofire_error = abs(zero_cofire_probability - zero_cofire_formula)
    if mean_error > 2e-10 or zero_cofire_error > 2e-10:
        raise RuntimeError("multinomial enumeration failed independent moment check")
    if valid_probability == 0:
        conditional_mean = conditional_bias = conditional_rmse = None
    else:
        conditional_mean = estimate_sum / valid_probability
        conditional_bias = conditional_mean - true_p
        conditional_rmse = math.sqrt(estimate_sq_error_sum / valid_probability)
    return {
        "window_shots": n,
        "total_multinomial_count_tables": math.comb(n + 3, 3),
        "probability_mass_sum": probability_total,
        "enumerated_sample_means_max_abs_error_vs_multinomial_moments": mean_error,
        "probability_zero_pair_cofires": zero_cofire_probability,
        "probability_zero_pair_cofires_binomial_identity": zero_cofire_formula,
        "zero_cofire_probability_identity_abs_error": zero_cofire_error,
        "probability_raw_inverse_outside_real_domain": invalid_probability,
        "probability_raw_inverse_below_zero": negative_probability,
        "probability_raw_inverse_above_half": above_half_probability,
        "probability_inverse_valid": valid_probability,
        "conditional_mean_raw_inverse_given_valid": conditional_mean,
        "conditional_bias_given_valid": conditional_bias,
        "conditional_rmse_given_valid": conditional_rmse,
        "boundary_policy": "none; invalid/negative outputs are reported, not silently clipped",
    }


def main() -> None:
    started = time.perf_counter()
    template_circuit = grid.construct(0.010, 0.003)
    template, _ = grid.categorical_sites(template_circuit)
    signature = grid.circuit_signature(template_circuit)
    cases = []
    for p in BURST_PS:
        circuit = grid.construct(p, 0.003)
        if grid.circuit_signature(circuit) != signature:
            raise RuntimeError("circuit structure changed across p")
        sites = grid.reweight(template, circuit)
        means = grid.means_from_characters(sites)
        i, j = PAIR
        pair_mean = float(means[40 + PAIR_INDEX])
        cells = np.array([
            pair_mean,
            float(means[i]) - pair_mean,
            float(means[j]) - pair_mean,
            1 - float(means[i]) - float(means[j]) + pair_mean,
        ])
        rows = [multinomial_edge_summary(n, cells, p) for n in WINDOW_SHOTS]
        cases.append({"burst_p": p, "measurement_p": 0.003,
                      "pair": list(PAIR), "pair_cell_probabilities_11_10_01_00": cells.tolist(),
                      "window_summaries": rows})

    result = {
        "classification": "EXACT_FINITE_N_MULTINOMIAL_PROBABILITY_ENUMERATION_ONE_EDGE_ONLY",
        "model": {
            "circuit": "Q-SHIFT distance-3, five-round balanced Z-memory categorical circuit",
            "gate_p": 0.003,
            "measurement_p": 0.003,
            "pair": list(PAIR),
            "pair_feature_distribution": "four pair outcomes from exact categorical-circuit population means",
            "shots_iid_at_fixed_burst_p": True,
        },
        "estimator": "Plug-in published edge-moment inverse from sample means of Di, Dj, and DiDj.",
        "cases": cases,
        "enumeration": {
            "method": "Exhaustive multinomial count-table probability sums in log-probability form; no random draws, detector vectors, or histories are generated.",
            "maximum_count_tables": max(math.comb(n + 3, 3) for n in WINDOW_SHOTS),
            "elapsed_wall_seconds": time.perf_counter() - started,
        },
        "limitations": [
            "Only one detector pair is analyzed. The five edge estimates are correlated; this does not give the distribution of their average.",
            "IID fixed-p shots only; no abrupt mixed-rate window, temporal dependence, measurement/gate drift, or nuisance uncertainty.",
            "Conditional mean/bias/RMSE are among real-domain outputs only; invalid and negative probabilities are reported separately.",
            "No boundary correction is selected. Results do not justify clipping, window size, confidence intervals, or controller thresholds.",
            "This is exact under the declared categorical-circuit pair distribution, not under approximate DEM or hardware/model mismatch.",
        ],
        "sampling_calls": 0,
        "decoder_calls": 0,
    }
    out = HERE / "EXACT_EDGE_MULTINOMIAL_AUDIT.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": out.name, "cases": [
        {"burst_p": c["burst_p"], "windows": [
            {"N": r["window_shots"], "invalid": r["probability_raw_inverse_outside_real_domain"],
             "negative": r["probability_raw_inverse_below_zero"],
             "conditional_bias": r["conditional_bias_given_valid"]}
            for r in c["window_summaries"]]} for c in cases]}, indent=2))


if __name__ == "__main__":
    main()
