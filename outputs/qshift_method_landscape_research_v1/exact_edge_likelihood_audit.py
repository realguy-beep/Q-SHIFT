"""Exact multinomial audit of a bounded detector-only pair likelihood.

The pair likelihood uses known exact categorical-circuit endpoint probabilities
and only the observed four pair counts. The resulting estimator distribution is
calculated by exhaustive count-table summation, not by sampling.
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
P_MAX = 0.5


def pair_cells(means: np.ndarray) -> np.ndarray:
    i, j = PAIR
    p11 = float(means[40 + PAIR_INDEX])
    return np.array([p11, float(means[i]) - p11, float(means[j]) - p11,
                     1 - float(means[i]) - float(means[j]) + p11])


def bounded_mle_for_count_vectors(counts: np.ndarray, q0: np.ndarray,
                                  delta: np.ndarray) -> np.ndarray:
    """Vectorized concave multinomial likelihood maximizer on [0,P_MAX]."""
    q_hi = q0 + P_MAX * delta
    if np.any(q0 <= 0) or np.any(q_hi <= 0):
        raise ValueError("likelihood endpoint cell probabilities must be positive")

    def score(p: np.ndarray, counts_use: np.ndarray = counts) -> np.ndarray:
        probs = q0[:, None] + delta[:, None] * p[None, :]
        return np.sum(counts_use * delta[:, None] / probs, axis=0)

    lo = np.zeros(counts.shape[1])
    hi = np.full(counts.shape[1], P_MAX)
    at_lo = score(lo)
    at_hi = score(hi)
    out = np.zeros_like(lo)
    out[at_lo <= 0] = 0.0
    out[at_hi >= 0] = P_MAX
    interior = (at_lo > 0) & (at_hi < 0)
    if np.any(interior):
        left = lo[interior]
        right = hi[interior]
        interior_counts = counts[:, interior]
        for _ in range(48):
            mid = (left + right) / 2
            keep_left = score(mid, interior_counts) > 0
            left = np.where(keep_left, mid, left)
            right = np.where(keep_left, right, mid)
        out[interior] = (left + right) / 2
    return out


def enumerate_case(n: int, q: np.ndarray, q0: np.ndarray,
                   q1: np.ndarray, true_p: float) -> dict:
    log_fact = np.array([math.lgamma(k + 1) for k in range(n + 1)])
    log_q = np.log(q)
    delta = q1 - q0
    mass = mean_hat = sq_error = low_mass = high_mass = 0.0
    moment_sums = np.zeros(3)
    for n11 in range(n + 1):
        for n10 in range(n - n11 + 1):
            n01 = np.arange(n - n11 - n10 + 1, dtype=np.int64)
            n00 = n - n11 - n10 - n01
            log_weight = (
                log_fact[n] - log_fact[n11] - log_fact[n10]
                - log_fact[n01] - log_fact[n00]
                + n11 * log_q[0] + n10 * log_q[1]
                + n01 * log_q[2] + n00 * log_q[3]
            )
            weights = np.exp(log_weight)
            # Batch count columns have categories in the required cell order.
            counts = np.vstack((np.full(n01.size, n11),
                                np.full(n01.size, n10), n01, n00))
            estimates = bounded_mle_for_count_vectors(counts, q0, delta)
            mass += float(weights.sum())
            mean_hat += float(weights @ estimates)
            sq_error += float(weights @ ((estimates - true_p) ** 2))
            low_mass += float(weights[estimates <= 1e-14].sum())
            high_mass += float(weights[estimates >= P_MAX - 1e-14].sum())
            a = (n10 + n11) / n
            b = (n01 + n11) / n
            c = n11 / n
            moment_sums += np.array([weights.sum() * a, weights @ b, weights.sum() * c])
    expected_moments = np.array([q[0] + q[1], q[0] + q[2], q[0]])
    moment_error = float(np.max(np.abs(moment_sums - expected_moments)))
    if abs(mass - 1) > 2e-10 or moment_error > 2e-10:
        raise RuntimeError("exact likelihood count enumeration failed mass/moment check")
    return {
        "window_shots": n,
        "count_tables": math.comb(n + 3, 3),
        "probability_mass_sum": mass,
        "enumerated_sample_moment_max_abs_error": moment_error,
        "mle_mean": mean_hat,
        "mle_bias": mean_hat - true_p,
        "mle_rmse": math.sqrt(sq_error),
        "probability_mle_at_zero_boundary": low_mass,
        "probability_mle_at_upper_half_boundary": high_mass,
    }


def validate_hand_fixtures(q0: np.ndarray, q1: np.ndarray) -> dict:
    """Compare vectorized score roots with a dense deterministic grid oracle."""
    fixtures = np.array([
        [0, 2, 3, 20],
        [1, 3, 4, 92],
        [4, 10, 12, 174],
    ], dtype=float).T
    fitted = bounded_mle_for_count_vectors(fixtures, q0, q1 - q0)
    p_grid = np.linspace(0, P_MAX, 100_001)
    grid_log_likelihoods = []
    fit_log_likelihoods = []
    for column, p_hat in zip(fixtures.T, fitted):
        probs_grid = q0[:, None] + (q1 - q0)[:, None] * p_grid[None, :]
        ll_grid = np.sum(column[:, None] * np.log(probs_grid), axis=0)
        probs_fit = q0 + (q1 - q0) * p_hat
        ll_fit = float(column @ np.log(probs_fit))
        grid_log_likelihoods.append(float(np.max(ll_grid)))
        fit_log_likelihoods.append(ll_fit)
        if ll_fit + 1e-10 < float(np.max(ll_grid)):
            raise RuntimeError("score-root MLE is below dense-grid likelihood oracle")
    shortfall = float(max(reference - actual for reference, actual in zip(grid_log_likelihoods, fit_log_likelihoods)))
    return {
        "hand_count_fixtures": fixtures.T.astype(int).tolist(),
        "vectorized_score_root_estimates": fitted.tolist(),
        "dense_grid_oracle_points": len(p_grid),
        "max_log_likelihood_shortfall_vs_dense_grid": shortfall,
        "status": "passed",
    }


def main() -> None:
    started = time.perf_counter()
    template_circuit = grid.construct(0.010, 0.003)
    template, _ = grid.categorical_sites(template_circuit)

    def profile(p: float) -> np.ndarray:
        circuit = grid.construct(p, 0.003)
        return grid.means_from_characters(grid.reweight(template, circuit))

    # Stim drops the zero-probability CORRELATED_ERROR instructions, changing
    # the physical-site list. Extrapolate the pair's affine Bernoulli response
    # from two positive-p exact circuit profiles, then verify at a third p.
    q_low = pair_cells(profile(0.002))
    q_mid = pair_cells(profile(0.010))
    q0 = q_low - 0.002 * (q_mid - q_low) / (0.010 - 0.002)
    # A forced X8/X10 burst toggles both pair bits, so q1 is the deterministic
    # both-bit complement of the extrapolated p=0 background distribution.
    q1 = np.array([q0[3], q0[2], q0[1], q0[0]])
    endpoint_error = 0.0
    cases = []
    for p in BURST_PS:
        q = pair_cells(profile(p))
        linear_q = (1 - p) * q0 + p * q1
        endpoint_error = max(endpoint_error, float(np.max(np.abs(q - linear_q))))
        if endpoint_error > 2e-12:
            raise RuntimeError("pair-cell model is not affine in burst p")
        rows = [enumerate_case(n, q, q0, q1, p) for n in WINDOW_SHOTS]
        cases.append({"burst_p": p, "measurement_p": 0.003,
                      "pair": list(PAIR), "pair_cell_probabilities": q.tolist(),
                      "bounded_likelihood_results": rows})

    result = {
        "classification": "EXACT_FINITE_N_MULTINOMIAL_LIKELIHOOD_ENUMERATION_ONE_EDGE",
        "model": {
            "circuit": "Q-SHIFT distance-3, five-round balanced Z-memory categorical circuit",
            "gate_p": 0.003,
            "measurement_p": 0.003,
            "pair": list(PAIR),
            "feature_input": "four detector-pair category counts only; no labels or logical observables",
            "likelihood": "multinomial with q(p)=(1-p)q0+p*q1; q0 is extrapolated from two exact positive-p categorical profiles, q1 is the exact both-bit complement under a forced pair burst, and p=.018 validates the affine relation",
            "parameter_bounds": [0.0, P_MAX],
        },
        "endpoint_affine_model_max_abs_error": endpoint_error,
        "deterministic_hand_fixture_validation": validate_hand_fixtures(q0, q1),
        "cases": cases,
        "enumeration": {
            "method": "Exhaustive multinomial count-table probability summation; vectorized bisection maximizes the concave bounded likelihood.",
            "maximum_count_tables": math.comb(max(WINDOW_SHOTS) + 3, 3),
            "elapsed_wall_seconds": time.perf_counter() - started,
        },
        "limitations": [
            "One pair only. Multiplying five pair likelihoods would be a composite likelihood because the pair data share one shot; dependence must be included in uncertainty and checked for estimator behavior.",
            "The estimator assumes exact known detector-pair endpoint distributions, including gate and measurement noise; it is not model-robust.",
            "The [0,.5] interval is the conventional probability range tested here; it is not an owner-approved online guard or model-validity range.",
            "The comparison does not establish superiority over the five-edge average or existing 45-feature profile; no boundary rule is owner-approved.",
            "Exact categorical circuit only; no DEM approximation, detector-history sampling, decoder evaluation, or logical outcome is used.",
        ],
        "sampling_calls": 0,
        "decoder_calls": 0,
    }
    out = HERE / "EXACT_EDGE_LIKELIHOOD_AUDIT.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": out.name, "endpoint_model_error": endpoint_error,
        "cases": [{"p": c["burst_p"], "windows": [
            {"N": r["window_shots"], "bias": r["mle_bias"],
             "rmse": r["mle_rmse"], "at_zero": r["probability_mle_at_zero_boundary"],
             "at_upper_half": r["probability_mle_at_upper_half_boundary"]}
            for r in c["bounded_likelihood_results"]]} for c in cases]}, indent=2))


if __name__ == "__main__":
    main()
