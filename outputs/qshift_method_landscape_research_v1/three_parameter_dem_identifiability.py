"""Deterministic three-parameter identifiability in the approximate DEM.

This is deliberately separate from the exact-categorical-circuit audit. The
DEM is rebuilt at each parameter point using Stim's declared decomposition and
disjoint-error approximation, then treated as its resulting independent-event
model. No shots, detector histories, or decoder calls are made.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for directory in (ROOT, ROOT / "outputs" / "phase3a_correlated_noise_preflight", ROOT / "outputs" / "stage4_noise_adaptive_feasibility_v1"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from simulator import build_spatial_burst_circuit
from prototype import BURST_DETECTOR_PAIRS, DETECTOR_COUNT

NOMINAL = np.array([0.010, 0.003, 0.003])  # burst, measurement, gate
SCALES = np.array([0.008, 0.004, 0.001])
FEATURES = [(d,) for d in range(DETECTOR_COUNT)] + [tuple(p) for p in BURST_DETECTOR_PAIRS]
STEP_SIZES = (1e-4, 5e-5, 2.5e-5)


def build_mechanisms(params: np.ndarray) -> list[tuple[float, frozenset[int]]]:
    pb, pm, pg = map(float, params)
    circuit = build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=pg, measurement_p=pm, bias_ratio=10.0,
        burst_probability=pb, burst_pair=(8, 10),
    )
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    mechanisms = []
    for instruction in dem:
        if instruction.type != "error":
            continue
        support = frozenset(t.val for t in instruction.targets_copy() if t.is_relative_detector_id())
        mechanisms.append((float(instruction.args_copy()[0]), support))
    return mechanisms


def parity_character(mechanisms: list[tuple[float, frozenset[int]]], selected: frozenset[int]) -> float:
    value = 1.0
    for probability, support in mechanisms:
        if len(support & selected) % 2:
            value *= 1.0 - 2.0 * probability
    return value


def all_one_moment(mechanisms: list[tuple[float, frozenset[int]]], selected: tuple[int, ...]) -> float:
    # Fourier/inclusion-exclusion identity, exact for the independent DEM event law.
    total = 0.0
    for mask in range(1 << len(selected)):
        subset = frozenset(selected[i] for i in range(len(selected)) if (mask >> i) & 1)
        total += (-1.0 if len(subset) % 2 else 1.0) * parity_character(mechanisms, subset)
    return total / (1 << len(selected))


def means_covariance(mechanisms: list[tuple[float, frozenset[int]]]) -> tuple[np.ndarray, np.ndarray]:
    means = np.asarray([all_one_moment(mechanisms, feature) for feature in FEATURES])
    covariance = np.empty((len(FEATURES), len(FEATURES)), dtype=np.float64)
    for i, left in enumerate(FEATURES):
        for j in range(i, len(FEATURES)):
            right = FEATURES[j]
            joint = tuple(sorted(set(left) | set(right)))
            value = all_one_moment(mechanisms, joint) - means[i] * means[j]
            covariance[i, j] = covariance[j, i] = value
    return means, covariance


def direct_xor_all_one(mechanisms: list[tuple[float, frozenset[int]]], selected: tuple[int, ...]) -> float:
    """Independent finite-state Bernoulli-XOR recursion for an all-one event."""
    n = len(selected)
    state_count = 1 << n
    probabilities = np.zeros(state_count, dtype=np.float64)
    probabilities[0] = 1.0
    detector_bit = {detector: bit for bit, detector in enumerate(selected)}
    states = np.arange(state_count)
    for probability, support in mechanisms:
        mask = 0
        for detector in support:
            if detector in detector_bit:
                mask ^= 1 << detector_bit[detector]
        if mask:
            previous = probabilities
            probabilities = (1.0 - probability) * previous + probability * previous[states ^ mask]
    return float(probabilities[-1])


def mean_at(params: np.ndarray) -> np.ndarray:
    return means_covariance(build_mechanisms(params))[0]


def main() -> None:
    mechanisms = build_mechanisms(NOMINAL)
    mean, covariance = means_covariance(mechanisms)
    if mean.shape != (45,) or covariance.shape != (45, 45) or not np.isfinite(covariance).all():
        raise RuntimeError("invalid approximate-DEM feature moments")
    covariance = (covariance + covariance.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    if eigenvalues[0] <= 0:
        raise RuntimeError(f"approximate DEM feature covariance is not positive definite: {eigenvalues[0]}")

    # Independently reproduce every feature mean and covariance entry by XOR-state recursion.
    subset_cache: dict[tuple[int, ...], float] = {}
    def direct(subset: tuple[int, ...]) -> float:
        key = tuple(sorted(set(subset)))
        if key not in subset_cache:
            subset_cache[key] = direct_xor_all_one(mechanisms, key)
        return subset_cache[key]
    direct_means = np.asarray([direct(feature) for feature in FEATURES])
    direct_cov = np.empty_like(covariance)
    for i, left in enumerate(FEATURES):
        for j, right in enumerate(FEATURES):
            direct_cov[i, j] = direct(tuple(set(left) | set(right))) - direct_means[i] * direct_means[j]
    mean_crosscheck = float(np.max(np.abs(mean - direct_means)))
    covariance_crosscheck = float(np.max(np.abs(covariance - direct_cov)))
    if mean_crosscheck > 5e-12 or covariance_crosscheck > 5e-12:
        raise RuntimeError(f"independent XOR cross-check failed: mean={mean_crosscheck}, cov={covariance_crosscheck}")
    invsqrt = (eigenvectors / np.sqrt(eigenvalues)) @ eigenvectors.T

    columns, stability = [], []
    for column, parameter in enumerate(("burst_p", "measurement_p", "gate_p")):
        derivatives = []
        for step in STEP_SIZES:
            plus, minus = NOMINAL.copy(), NOMINAL.copy()
            plus[column] += step
            minus[column] -= step
            derivatives.append((mean_at(plus) - mean_at(minus)) / (2 * step))
        columns.append(derivatives[0])
        stability.append({
            "parameter": parameter,
            "steps": list(STEP_SIZES),
            "relative_change_h_to_h2": float(np.linalg.norm(derivatives[0] - derivatives[1]) / np.linalg.norm(derivatives[1])),
            "relative_change_h2_to_h4": float(np.linalg.norm(derivatives[1] - derivatives[2]) / np.linalg.norm(derivatives[2])),
        })
    jac = np.column_stack(columns)
    singular = np.linalg.svd(invsqrt @ (jac * SCALES[None, :]), compute_uv=False)
    rank = int(np.sum(singular > singular[0] * 1e-8))

    # Finite parameter profile grid, standardized by nominal DEM marginal SD.
    pb_grid, pm_grid, pg_grid = np.linspace(.002, .018, 5), np.linspace(.001, .005, 5), np.linspace(.002, .004, 3)
    profiles = {}
    for pb in pb_grid:
        for pm in pm_grid:
            for pg in pg_grid:
                key = (float(pb), float(pm), float(pg))
                profiles[key] = mean_at(np.asarray(key))
    sd = np.sqrt(np.diag(covariance))
    keys = sorted(profiles)
    nearest = {"distance": float("inf"), "left": None, "right": None}
    cross = {"distance": float("inf"), "left": None, "right": None}
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            distance = float(np.linalg.norm((profiles[left] - profiles[right]) / sd) / np.sqrt(45))
            if distance < nearest["distance"]:
                nearest = {"distance": distance, "left": left, "right": right}
            if left[0] != right[0] and left[2] != right[2] and distance < cross["distance"]:
                cross = {"distance": distance, "left": left, "right": right}

    result = {
        "classification": "DETERMINISTIC_APPROXIMATE_DEM_LOCAL_AND_GRID_MEAN_IDENTIFIABILITY",
        "dem_conversion": {"decompose_errors": True, "approximate_disjoint_errors": True, "stim_version": stim.__version__},
        "nominal": NOMINAL.tolist(), "declared_scales": SCALES.tolist(),
        "feature_count": 45, "dem_mechanisms_at_nominal": len(mechanisms),
        "independent_xor_crosscheck": {"distinct_subsets": len(subset_cache), "max_abs_mean_error": mean_crosscheck, "max_abs_covariance_error": covariance_crosscheck},
        "local_sensitivity": {
            "jacobian_shape": list(jac.shape),
            "relative_finite_difference_step_changes": stability,
            "covariance_eigenvalue_min_max": [float(eigenvalues[0]), float(eigenvalues[-1])],
            "covariance_whitened_scaled_singular_values": singular.tolist(),
            "numerical_rank_relative_1e-8": rank,
        },
        "profile_grid": {"shape": [5, 5, 3], "burst_p": pb_grid.tolist(), "measurement_p": pm_grid.tolist(), "gate_p": pg_grid.tolist(), "nearest_distinct_profile": nearest, "nearest_profile_changing_burst_and_gate": cross},
        "limitations": [
            "All moments are exact for the resulting independent-event approximate DEM, not for the categorical circuit distribution.",
            "Stim decomposed the model and approximated disjoint circuit errors; this transformation can change feature means and covariance.",
            "Local rank/profile distances do not establish global identifiability or finite-history estimator accuracy.",
            "No detector histories, decoder outputs, sampling, or protected data were used.",
        ],
    }
    out = HERE / "THREE_PARAMETER_DEM_IDENTIFIABILITY.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "dem_mechanisms": len(mechanisms), "rank": rank, "singular_values": singular.tolist(), "nearest": nearest, "cross_burst_gate": cross}, indent=2))


if __name__ == "__main__":
    main()
