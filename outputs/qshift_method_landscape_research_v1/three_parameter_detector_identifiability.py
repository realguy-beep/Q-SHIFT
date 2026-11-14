"""Exact-circuit local and grid identifiability for burst, measurement, gate p.

Uses deterministic categorical fault supports and population feature/covariance
algebra only. No Stim shots, decoder calls, or observed histories are produced.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for path in (ROOT, ROOT / "outputs" / "phase3a_correlated_noise_preflight", ROOT / "outputs" / "stage4_noise_adaptive_feasibility_v1"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import categorical_circuit_feature_expectations as features
import categorical_circuit_parameter_grid_audit as covariance_audit
from simulator import build_spatial_burst_circuit


NOMINAL = np.array([0.010, 0.003, 0.003])  # burst, measurement, gate
SCALES = np.array([0.008, 0.004, 0.001])
PAIR_SUPPORTS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))


def build(params: np.ndarray):
    pb, pm, pg = map(float, params)
    return build_spatial_burst_circuit(memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=pg, measurement_p=pm, bias_ratio=10.0, burst_probability=pb, burst_pair=(8, 10))


def map_probabilities(params: np.ndarray, mapped_template: list, instruction_names: list[str]) -> list:
    c = build(params)
    names = [inst.name for inst in c]
    raw = features.extract_sites(c)
    if names != instruction_names or len(raw) != len(mapped_template):
        raise RuntimeError("parameter change altered circuit/noise-site structure")
    mapped = []
    for (ix, identity, alternatives), (_old_identity, old_alts) in zip(raw, mapped_template):
        if len(alternatives) != len(old_alts):
            raise RuntimeError("parameter change altered categorical alternative count")
        alts = []
        for (probability, paulis), (_old_p, support, obs, old_paulis) in zip(alternatives, old_alts):
            if paulis != old_paulis:
                raise RuntimeError("parameter change altered Pauli alternative ordering")
            alts.append((probability, support, obs, paulis))
        mapped.append((identity, alts))
    return mapped


def mean_at(params: np.ndarray, mapped_template: list, instruction_names: list[str]) -> np.ndarray:
    return features.means_from_characters(map_probabilities(params, mapped_template, instruction_names))


def whitened_jacobian(jac: np.ndarray, covariance: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    eig, vec = np.linalg.eigh(covariance)
    if eig[0] <= 0:
        raise RuntimeError(f"feature covariance not positive definite: min eigenvalue {eig[0]}")
    invsqrt = (vec / np.sqrt(eig)) @ vec.T
    matrix = invsqrt @ (jac * SCALES[None, :])
    return np.linalg.svd(matrix, compute_uv=False), eig


def main() -> None:
    template_circuit = build(NOMINAL)
    mapped_template, meta = features.categorical_sites(template_circuit)
    instruction_names = [inst.name for inst in template_circuit]
    mean = features.means_from_characters(mapped_template)
    covariance = covariance_audit.exact_cov(mapped_template, mean)
    if covariance.shape != (45, 45) or not np.isfinite(covariance).all():
        raise RuntimeError("invalid exact single-shot feature covariance")

    step_sizes = (1e-4, 5e-5, 2.5e-5)
    derivative_columns = []
    derivative_stability = []
    for i, name in enumerate(("burst_p", "measurement_p", "gate_p")):
        col_rows = []
        for h in step_sizes:
            plus, minus = NOMINAL.copy(), NOMINAL.copy()
            plus[i] += h
            minus[i] -= h
            col_rows.append((mean_at(plus, mapped_template, instruction_names) - mean_at(minus, mapped_template, instruction_names)) / (2 * h))
        derivative_columns.append(col_rows[0])
        derivative_stability.append({
            "parameter": name,
            "steps": list(step_sizes),
            "relative_change_h_to_h2": float(np.linalg.norm(col_rows[0] - col_rows[1]) / np.linalg.norm(col_rows[1])),
            "relative_change_h2_to_h4": float(np.linalg.norm(col_rows[1] - col_rows[2]) / np.linalg.norm(col_rows[2])),
        })
    jac = np.column_stack(derivative_columns)
    singular_values, covariance_eigenvalues = whitened_jacobian(jac, covariance)
    rank = int(np.sum(singular_values > singular_values[0] * 1e-8))
    column_norms = np.linalg.norm(jac * SCALES[None, :], axis=0)
    cosines = (jac * SCALES[None, :]).T @ (jac * SCALES[None, :]) / np.outer(column_norms, column_norms)
    feature_labels = [f"D[{i}]" for i in range(40)] + [f"D[{a}]D[{b}]" for a, b in PAIR_SUPPORTS]
    marginal_sd = np.sqrt(np.diag(covariance))
    marginal_sensitivities = jac * SCALES[None, :] / marginal_sd[:, None]
    top_features = {}
    for column, parameter in enumerate(("burst_p", "measurement_p", "gate_p")):
        order = np.argsort(-np.abs(marginal_sensitivities[:, column]))[:8]
        top_features[parameter] = [
            {"feature_index": int(i), "feature": feature_labels[i],
             "scaled_derivative_over_nominal_sd": float(marginal_sensitivities[i, column])}
            for i in order
        ]

    pb_grid = np.linspace(0.002, 0.018, 5)
    pm_grid = np.linspace(0.001, 0.005, 5)
    pg_grid = np.linspace(0.002, 0.004, 3)
    profiles = {}
    for pb in pb_grid:
        for pm in pm_grid:
            for pg in pg_grid:
                key = (float(pb), float(pm), float(pg))
                profiles[key] = mean_at(np.array(key), mapped_template, instruction_names)
    feature_scale = np.sqrt(np.maximum(np.diag(covariance), 1e-12))
    keys = sorted(profiles)
    nearest = {"distance": float("inf"), "left": None, "right": None}
    nearest_cross_burst_gate = {"distance": float("inf"), "left": None, "right": None}
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            distance = float(np.linalg.norm((profiles[left] - profiles[right]) / feature_scale) / np.sqrt(45))
            if distance < nearest["distance"]:
                nearest = {"distance": distance, "left": left, "right": right}
            if left[0] != right[0] and left[2] != right[2] and distance < nearest_cross_burst_gate["distance"]:
                nearest_cross_burst_gate = {"distance": distance, "left": left, "right": right}

    result = {
        "classification": "DETERMINISTIC_EXACT_CIRCUIT_LOCAL_AND_GRID_MEAN_IDENTIFIABILITY",
        "configuration": {"distance": 3, "rounds": 5, "memory_basis": "z", "regime": "balanced", "bias_ratio": 10.0},
        "parameters": ["burst_p", "measurement_p", "gate_p"],
        "nominal": NOMINAL.tolist(),
        "declared_scales": SCALES.tolist(),
        "features": 45,
        "burst_pair_supports": meta["burst_detector_supports"],
        "local_sensitivity": {
            "jacobian_shape": list(jac.shape),
            "relative_finite_difference_step_changes": derivative_stability,
            "whitened_scaled_singular_values": singular_values.tolist(),
            "numerical_rank_relative_1e-8": rank,
            "column_cosines_scaled_parameters": cosines.tolist(),
            "feature_covariance_eigenvalue_min_max": [float(covariance_eigenvalues[0]), float(covariance_eigenvalues[-1])],
            "top_marginally_standardized_features": top_features,
        },
        "mean_profile_grid": {"shape": [len(pb_grid), len(pm_grid), len(pg_grid)], "burst_p": pb_grid.tolist(), "measurement_p": pm_grid.tolist(), "gate_p": pg_grid.tolist(), "nearest_distinct_profile": nearest, "nearest_profile_changing_burst_and_gate": nearest_cross_burst_gate},
        "limitations": [
            "Local rank and finite mean-grid distances are not finite-history estimation accuracy or global identifiability.",
            "The declared parameter scales are design scales, not policy margins.",
            "No joint estimator, gate-noise guard, e-process, detector history, or decoder action was implemented or run.",
            "Exact categorical circuit only; the approximate DEM has not received this three-parameter audit.",
        ],
    }
    out = HERE / "THREE_PARAMETER_DETECTOR_IDENTIFIABILITY.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("rank", rank, "singular", singular_values.tolist())
    print("burst_gate_near_collision", nearest_cross_burst_gate)
    print(f"wrote={out}")


if __name__ == "__main__":
    main()
