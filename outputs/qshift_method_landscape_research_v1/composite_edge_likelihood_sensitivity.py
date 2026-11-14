"""Exact asymptotic sensitivity of a five-edge composite likelihood.

Builds the joint distribution of the ten burst-pair detector bits by exact
categorical parity recursion, then computes Godambe score variance. No samples
or decoder outputs are generated. This is an asymptotic model calculation.
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

PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
P_PROBES = (0.002, 0.010, 0.018)
PM = 0.003
SELECTED = tuple(d for pair in PAIRS for d in pair)


def pair_cells_from_joint(joint: np.ndarray) -> list[np.ndarray]:
    out = []
    for k in range(len(PAIRS)):
        counts = np.zeros(4)
        i, j = 2 * k, 2 * k + 1
        for mask, mass in enumerate(joint):
            di, dj = (mask >> i) & 1, (mask >> j) & 1
            category = 0 if (di, dj) == (1, 1) else 1 if di else 2 if dj else 3
            counts[category] += mass
        out.append(counts)
    return out


def compute_probe(p: float, template: list) -> dict:
    circuit = grid.construct(p, PM)
    sites = grid.reweight(template, circuit)
    joint = direct_xor(sites, SELECTED)
    if joint.shape != (1 << len(SELECTED),) or abs(float(joint.sum()) - 1) > 2e-12:
        raise RuntimeError("invalid exact ten-detector joint distribution")
    q = pair_cells_from_joint(joint)
    no_pair_cofire = np.ones(joint.size, dtype=bool)
    states = np.arange(joint.size)
    for edge in range(len(PAIRS)):
        i, j = 2 * edge, 2 * edge + 1
        both = (((states >> i) & 1) == 1) & (((states >> j) & 1) == 1)
        no_pair_cofire &= ~both
    p_no_pair_cofire_one_shot = float(joint[no_pair_cofire].sum())
    score_by_state = np.zeros(joint.size)
    hessian_by_state = np.zeros(joint.size)
    per_edge_score = np.zeros((len(PAIRS), joint.size))
    for edge, cells in enumerate(q):
        i, j = 2 * edge, 2 * edge + 1
        for mask, mass in enumerate(joint):
            di, dj = (mask >> i) & 1, (mask >> j) & 1
            category = 0 if (di, dj) == (1, 1) else 1 if di else 2 if dj else 3
            if mass and cells[category] <= 0:
                raise RuntimeError("positive joint mass has zero pair marginal")
            # The pair response is affine in p. Its derivative is obtained
            # from two exact categorical profiles at p=.002 and p=.018.
            score_by_state[mask] += DERIVATIVES[edge][category] / cells[category]
            hessian_by_state[mask] += (DERIVATIVES[edge][category] / cells[category]) ** 2
            per_edge_score[edge, mask] = DERIVATIVES[edge][category] / cells[category]
    score_mean = float(joint @ score_by_state)
    h = float(joint @ hessian_by_state)
    j = float(joint @ (score_by_state ** 2) - score_mean ** 2)
    edge_variances = []
    for edge in range(len(PAIRS)):
        mean = float(joint @ per_edge_score[edge])
        edge_variances.append(float(joint @ (per_edge_score[edge] ** 2) - mean ** 2))
    naive_j = float(sum(edge_variances))
    cross_cov = j - naive_j
    return {
        "burst_p": p,
        "joint_states": int(joint.size),
        "joint_probability_mass_sum": float(joint.sum()),
        "pair_marginals_max_abs_error_vs_exact_45_feature_means": marginal_crosscheck(p, q),
        "probability_no_cofire_on_any_of_five_pairs_one_shot": p_no_pair_cofire_one_shot,
        "probability_no_cofire_on_any_pair_in_iid_windows": {
            str(n): p_no_pair_cofire_one_shot ** n for n in (25, 50, 100, 200)
        },
        "composite_score_mean": score_mean,
        "sensitivity_hessian_H": h,
        "score_variance_J_exact_joint": j,
        "score_variance_J_if_pair_scores_were_independent": naive_j,
        "sum_pair_score_cross_covariance": cross_cov,
        "dependence_correction_ratio_J_over_naive": j / naive_j if naive_j else None,
        "godambe_asymptotic_sd_coefficient_per_sqrt_shots": float(np.sqrt(j) / h),
        "naive_independent_pair_sd_coefficient_per_sqrt_shots": float(np.sqrt(naive_j) / h),
        "pair_cell_marginals": [x.tolist() for x in q],
    }


def marginal_crosscheck(p: float, q_joint: list[np.ndarray]) -> float:
    c = grid.construct(p, PM)
    sites = grid.reweight(TEMPLATE, c)
    means = grid.means_from_characters(sites)
    errors = []
    for edge, (i, j) in enumerate(PAIRS):
        p11 = q_joint[edge][0]
        p10, p01 = q_joint[edge][1], q_joint[edge][2]
        errors.extend([abs((p11 + p10) - means[i]), abs((p11 + p01) - means[j]),
                       abs(p11 - means[40 + edge])])
    return float(max(errors))


def main() -> None:
    global TEMPLATE, DERIVATIVES
    base = grid.construct(0.010, PM)
    TEMPLATE, _ = grid.categorical_sites(base)
    q_lo = pair_cells_from_joint(direct_xor(grid.reweight(TEMPLATE, grid.construct(0.002, PM)), SELECTED))
    q_hi = pair_cells_from_joint(direct_xor(grid.reweight(TEMPLATE, grid.construct(0.018, PM)), SELECTED))
    DERIVATIVES = [(hi - lo) / (0.018 - 0.002) for lo, hi in zip(q_lo, q_hi)]
    probes = [compute_probe(p, TEMPLATE) for p in P_PROBES]
    result = {
        "classification": "DETERMINISTIC_EXACT_JOINT_SCORE_COVARIANCE_ASYMPTOTIC_AUDIT",
        "model": {
            "categorical_circuit": "distance-3, five-round balanced Z-memory",
            "gate_p": 0.003,
            "measurement_p": PM,
            "burst_rate_constant_within_shot": True,
            "detector_bits_jointly_enumerated": list(SELECTED),
            "edge_pairs": [list(x) for x in PAIRS],
            "probability_supports": "exact categorical model; independent burst Bernoulli event on each specified detector pair",
        },
        "estimator": "Sum of five marginal multinomial log-likelihood scores (composite likelihood); exact joint-score sandwich variance J/H^2, compared with a false edge-score independence assumption.",
        "probes": probes,
        "limitations": [
            "Asymptotic variance only; no finite-history bias, boundary mass, interval coverage, or alarm characteristics are calculated.",
            "The composite likelihood uses exact categorical pair marginals; it is not the approximate-DEM estimator and assumes fixed gate/readout nuisance parameters.",
            "The result does not show that composite likelihood beats the 45-feature profile, the five-edge moment average, or any decoder.",
            "No optimization over policy/window or model-generated training grid is performed.",
        ],
        "sampling_calls": 0,
        "decoder_calls": 0,
    }
    out = HERE / "COMPOSITE_EDGE_LIKELIHOOD_SENSITIVITY.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": out.name, "probes": [
        {k: x[k] for k in ("burst_p", "score_variance_J_exact_joint",
                           "score_variance_J_if_pair_scores_were_independent",
                           "dependence_correction_ratio_J_over_naive",
                           "godambe_asymptotic_sd_coefficient_per_sqrt_shots",
                           "naive_independent_pair_sd_coefficient_per_sqrt_shots",
                           "pair_marginals_max_abs_error_vs_exact_45_feature_means")}
        for x in probes]}, indent=2))


if __name__ == "__main__":
    main()
