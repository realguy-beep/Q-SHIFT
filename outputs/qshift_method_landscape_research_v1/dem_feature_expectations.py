"""Deterministic 45-feature population means for Q-SHIFT approximate DEMs.

Uses parity-characteristic identities for independent DEM error mechanisms.
It constructs Stim DEMs but never samples shots, decodes syndromes, or uses
logical outcomes. Results are exact for each resulting independent-event DEM,
not exact circuit-level expectations.

Run from any directory:

    python outputs/qshift_method_landscape_research_v1/dem_feature_expectations.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import stim

REPO_ROOT = Path(__file__).resolve().parents[2]
SIMULATOR_DIR = REPO_ROOT / "outputs" / "phase3a_correlated_noise_preflight"
PROFILE_DIR = REPO_ROOT / "outputs" / "stage4_noise_adaptive_feasibility_v1"
for directory in (REPO_ROOT, SIMULATOR_DIR, PROFILE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from simulator import build_spatial_burst_circuit  # noqa: E402
from prototype import BURST_DETECTOR_PAIRS, DETECTOR_COUNT  # noqa: E402


GATE_P = 0.003
MEASUREMENT_P = 0.003
BIAS_RATIO = 10.0
BURST_KNOTS = (0.002, 0.010, 0.018)
FINITE_DIFFERENCE_STEP = 0.0001


def build_dem(burst_p: float, measurement_p: float):
    circuit = build_spatial_burst_circuit(
        memory_basis="z",
        regime="balanced",
        distance=3,
        rounds=5,
        gate_p=GATE_P,
        measurement_p=measurement_p,
        bias_ratio=BIAS_RATIO,
        burst_probability=burst_p,
        burst_pair=(8, 10),
    )
    dem = circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
    )
    mechanisms: list[tuple[float, frozenset[int]]] = []
    for instruction in dem:
        if instruction.type != "error":
            continue
        p = float(instruction.args_copy()[0])
        support = frozenset(
            target.val
            for target in instruction.targets_copy()
            if target.is_relative_detector_id()
        )
        mechanisms.append((p, support))
    return dem, mechanisms


def parity_characteristic(mechanisms, selected: frozenset[int]) -> float:
    """Return E[(-1)^(XOR of selected detector bits)] under the DEM."""
    value = 1.0
    for probability, support in mechanisms:
        if len(support.intersection(selected)) % 2:
            value *= 1.0 - 2.0 * probability
    return value


def feature_means(mechanisms) -> np.ndarray:
    detector_means = np.empty(DETECTOR_COUNT, dtype=np.float64)
    detector_chars = np.empty(DETECTOR_COUNT, dtype=np.float64)
    for detector in range(DETECTOR_COUNT):
        char = parity_characteristic(mechanisms, frozenset((detector,)))
        detector_chars[detector] = char
        detector_means[detector] = (1.0 - char) / 2.0
    pair_means = []
    for left, right in BURST_DETECTOR_PAIRS:
        pair_char = parity_characteristic(mechanisms, frozenset((left, right)))
        pair_means.append(
            (1.0 - detector_chars[left] - detector_chars[right] + pair_char) / 4.0
        )
    return np.concatenate((detector_means, np.asarray(pair_means, dtype=np.float64)))


def direct_xor_convolution(mechanisms, selected: tuple[int, ...]) -> np.ndarray:
    """Compute a small detector-subset distribution by direct state recursion."""
    state_count = 1 << len(selected)
    probabilities = np.zeros(state_count, dtype=np.float64)
    probabilities[0] = 1.0
    detector_to_bit = {detector: bit for bit, detector in enumerate(selected)}
    states = np.arange(state_count)
    for event_probability, support in mechanisms:
        mask = 0
        for detector in selected:
            if detector in support:
                mask ^= 1 << detector_to_bit[detector]
        if mask:
            probabilities = (
                (1.0 - event_probability) * probabilities
                + event_probability * probabilities[states ^ mask]
            )
    return probabilities


def direct_feature_means(mechanisms) -> np.ndarray:
    detector_means = np.empty(DETECTOR_COUNT, dtype=np.float64)
    for detector in range(DETECTOR_COUNT):
        distribution = direct_xor_convolution(mechanisms, (detector,))
        detector_means[detector] = distribution[1]
    pair_means = []
    for left, right in BURST_DETECTOR_PAIRS:
        distribution = direct_xor_convolution(mechanisms, (left, right))
        pair_means.append(distribution[3])
    return np.concatenate((detector_means, np.asarray(pair_means, dtype=np.float64)))


def direct_feature_covariance(mechanisms) -> tuple[np.ndarray, np.ndarray]:
    """Compute exact feature covariance under the independent-event DEM."""
    supports = [(detector,) for detector in range(DETECTOR_COUNT)] + [
        tuple(pair) for pair in BURST_DETECTOR_PAIRS
    ]
    means = direct_feature_means(mechanisms)
    covariance = np.empty((len(supports), len(supports)), dtype=np.float64)
    probability_cache: dict[tuple[int, ...], float] = {}
    for left_index, left_support in enumerate(supports):
        for right_index in range(left_index, len(supports)):
            right_support = supports[right_index]
            all_one_support = tuple(sorted(set(left_support).union(right_support)))
            if all_one_support not in probability_cache:
                probability_cache[all_one_support] = float(
                    direct_xor_convolution(mechanisms, all_one_support)[-1]
                )
            product_mean = probability_cache[all_one_support]
            value = product_mean - means[left_index] * means[right_index]
            covariance[left_index, right_index] = value
            covariance[right_index, left_index] = value
    return means, covariance


def labels() -> list[str]:
    return [f"D{i}" for i in range(DETECTOR_COUNT)] + [
        f"D{left}&D{right}" for left, right in BURST_DETECTOR_PAIRS
    ]


def main() -> None:
    profile_results = {}
    dem_mechanism_counts = {}
    validation_errors = []
    for burst_p in BURST_KNOTS:
        dem, mechanisms = build_dem(burst_p, MEASUREMENT_P)
        means = feature_means(mechanisms)
        direct_means = direct_feature_means(mechanisms)
        validation_error = float(np.max(np.abs(means - direct_means)))
        validation_errors.append(validation_error)
        if means.shape != (45,) or np.any((means < 0) | (means > 1)):
            raise RuntimeError("feature mean vector has invalid shape or probabilities")
        if validation_error > 1e-12:
            raise RuntimeError("independent XOR-convolution validation exceeded tolerance")
        profile_results[f"{burst_p:.3f}"] = means.tolist()
        dem_mechanism_counts[f"{burst_p:.3f}"] = sum(
            1 for instruction in dem if instruction.type == "error"
        )

    h = FINITE_DIFFERENCE_STEP

    def mean_at(burst_p: float, measurement_p: float) -> np.ndarray:
        _, mechanisms = build_dem(burst_p, measurement_p)
        return feature_means(mechanisms)

    jac_burst = (mean_at(0.010 + h, 0.003) - mean_at(0.010 - h, 0.003)) / (2 * h)
    jac_measure = (mean_at(0.010, 0.003 + h) - mean_at(0.010, 0.003 - h)) / (2 * h)
    jacobian = np.column_stack((jac_burst, jac_measure))
    singular_values = np.linalg.svd(jacobian, compute_uv=False)
    column_cosine = float(
        np.dot(jac_burst, jac_measure)
        / (np.linalg.norm(jac_burst) * np.linalg.norm(jac_measure))
    )
    p_names = labels()
    order_p = np.argsort(np.abs(jac_burst))[::-1][:10]
    order_m = np.argsort(np.abs(jac_measure))[::-1][:10]
    _, mechanisms_at_point = build_dem(0.010, 0.003)
    covariance_means, feature_covariance = direct_feature_covariance(mechanisms_at_point)
    covariance_eigenvalues = np.linalg.eigvalsh(feature_covariance)
    covariance_diagonal_error = float(
        np.max(np.abs(np.diag(feature_covariance) - covariance_means * (1.0 - covariance_means)))
    )
    if not np.allclose(feature_covariance, feature_covariance.T, atol=1e-14, rtol=0):
        raise RuntimeError("feature covariance is not symmetric")
    if covariance_diagonal_error > 1e-12:
        raise RuntimeError("binary feature variances do not match Bernoulli identities")
    if covariance_eigenvalues[0] <= 0:
        raise RuntimeError("local feature covariance is not positive definite")
    covariance_condition = (
        float(covariance_eigenvalues[-1] / covariance_eigenvalues[0])
        if covariance_eigenvalues[0] > 0
        else None
    )
    covariance_inverse_jacobian = np.linalg.solve(feature_covariance, jacobian)
    optimal_information = jacobian.T @ covariance_inverse_jacobian
    optimal_gmm_covariance_per_shot = np.linalg.inv(optimal_information)
    diagonal_weights = np.diag(1.0 / np.diag(feature_covariance))
    diagonal_information = jacobian.T @ diagonal_weights @ jacobian
    diagonal_information_inverse = np.linalg.inv(diagonal_information)
    diagonal_gmm_covariance_per_shot = (
        diagonal_information_inverse
        @ jacobian.T
        @ diagonal_weights
        @ feature_covariance
        @ diagonal_weights
        @ jacobian
        @ diagonal_information_inverse
    )
    finite_difference_diagnostics = []
    for diagnostic_h in (0.0001, 0.00005, 0.00001):
        diagnostic_burst = (
            mean_at(0.010 + diagnostic_h, 0.003)
            - mean_at(0.010 - diagnostic_h, 0.003)
        ) / (2 * diagnostic_h)
        diagnostic_measure = (
            mean_at(0.010, 0.003 + diagnostic_h)
            - mean_at(0.010, 0.003 - diagnostic_h)
        ) / (2 * diagnostic_h)
        finite_difference_diagnostics.append(
            {
                "step": diagnostic_h,
                "max_absolute_burst_derivative_difference_from_reference": float(
                    np.max(np.abs(diagnostic_burst - jac_burst))
                ),
                "max_absolute_measurement_derivative_difference_from_reference": float(
                    np.max(np.abs(diagnostic_measure - jac_measure))
                ),
            }
        )
    result = {
        "classification": "approximate_DEM_population_expectations_only",
        "assumptions": [
            "Each DEM error instruction is treated as an independent Bernoulli mechanism, as specified by the DEM representation.",
            "For a detector subset A, E[(-1)^(XOR_{i in A} D_i)] is the product of (1-2p_k) over mechanisms with odd support intersection with A.",
            "Pair feature means use P(D_i=1,D_j=1) = (1 - chi_i - chi_j + chi_{i,j})/4.",
            "Stim conversion uses decompose_errors=True and approximate_disjoint_errors=True; outputs are not exact circuit-level expectations.",
        ],
        "configuration": {
            "stim_version": stim.__version__,
            "distance": 3,
            "rounds": 5,
            "memory_basis": "z",
            "regime": "balanced",
            "gate_p": GATE_P,
            "measurement_p": MEASUREMENT_P,
            "bias_ratio": BIAS_RATIO,
            "burst_pair_data_qubits": [8, 10],
            "burst_probability_knots": list(BURST_KNOTS),
            "dem_options": {
                "decompose_errors": True,
                "approximate_disjoint_errors": True,
            },
        },
        "feature_order": p_names,
        "dem_error_mechanism_counts": dem_mechanism_counts,
        "feature_expectations_by_burst_probability": profile_results,
        "independent_algebraic_validation": {
            "method": "direct 2-state/4-state XOR probability recursion over DEM mechanisms",
            "max_absolute_difference_from_parity_characteristic_formulas": max(validation_errors),
            "number_of_burst_knots_checked": len(BURST_KNOTS),
        },
        "local_sensitivity_at": {
            "burst_probability": 0.010,
            "measurement_probability": 0.003,
            "central_difference_step": h,
        },
        "finite_difference_step_sensitivity": finite_difference_diagnostics,
        "local_mean_feature_jacobian_columns": {
            "burst_probability": jac_burst.tolist(),
            "measurement_probability": jac_measure.tolist(),
        },
        "raw_unstandardized_jacobian_singular_values": singular_values.tolist(),
        "raw_unstandardized_jacobian_condition_number": float(
            singular_values[0] / singular_values[-1]
        ),
        "raw_jacobian_column_cosine": column_cosine,
        "raw_unstandardized_jacobian_rank": int(np.linalg.matrix_rank(jacobian)),
        "single_shot_feature_covariance_at_local_point": feature_covariance.tolist(),
        "single_shot_feature_covariance_eigenvalue_range": [
            float(covariance_eigenvalues[0]),
            float(covariance_eigenvalues[-1]),
        ],
        "single_shot_feature_covariance_condition_number": covariance_condition,
        "single_shot_covariance_symmetry_error": float(
            np.max(np.abs(feature_covariance - feature_covariance.T))
        ),
        "single_shot_binary_variance_diagonal_error": covariance_diagonal_error,
        "local_moment_gmm_asymptotic_covariance_per_iid_shot": {
            "full_covariance_weighting_oracle": optimal_gmm_covariance_per_shot.tolist(),
            "diagonal_variance_weighting": diagonal_gmm_covariance_per_shot.tolist(),
            "standard_deviation_per_sqrt_shots_full_covariance": np.sqrt(
                np.diag(optimal_gmm_covariance_per_shot)
            ).tolist(),
            "standard_deviation_per_sqrt_shots_diagonal_weighting": np.sqrt(
                np.diag(diagonal_gmm_covariance_per_shot)
            ).tolist(),
            "assumptions": [
                "Independent identically distributed detector records across shots under the fixed approximate DEM.",
                "Regular interior estimator with the local Jacobian and true single-shot covariance known.",
                "Asymptotic moment-estimator calculation only; not finite-history accuracy or candidate-B evaluation.",
            ],
        },
        "largest_absolute_burst_sensitivities": [
            {"feature": p_names[i], "derivative": float(jac_burst[i])}
            for i in order_p
        ],
        "largest_absolute_measurement_sensitivities": [
            {"feature": p_names[i], "derivative": float(jac_measure[i])}
            for i in order_m
        ],
        "limitations": [
            "Raw Jacobian scaling is coordinate-dependent and is not a finite-sample conditioning or estimator-accuracy result.",
            "No covariance weighting, confidence interval, logical outcome, or decoder performance is evaluated.",
            "Exact categorical-circuit expectations may differ from these approximate-DEM expectations.",
        ],
    }
    output = Path(__file__).with_name("DEM_EXPECTATION_RESULTS.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote={output.relative_to(REPO_ROOT)}")
    print(f"stim_version={stim.__version__}")
    print(f"dem_mechanism_counts={dem_mechanism_counts}")
    print(f"direct_convolution_max_abs_difference={max(validation_errors):.3g}")
    print(f"raw_jacobian_rank={result['raw_unstandardized_jacobian_rank']}")
    print(f"raw_jacobian_singular_values={singular_values.tolist()}")
    print(f"raw_jacobian_condition={result['raw_unstandardized_jacobian_condition_number']:.9g}")
    print(f"raw_jacobian_column_cosine={column_cosine:.9g}")
    print(f"feature_covariance_eigenvalue_range={covariance_eigenvalues[[0,-1]].tolist()}")
    print(f"feature_covariance_condition={covariance_condition:.9g}")
    print(
        "gmm_asymptotic_sd_per_sqrt_shots="
        f"{np.sqrt(np.diag(optimal_gmm_covariance_per_shot)).tolist()}"
    )
    print(f"largest_burst_sensitivities={result['largest_absolute_burst_sensitivities'][:5]}")
    print(f"largest_measurement_sensitivities={result['largest_absolute_measurement_sensitivities'][:5]}")


if __name__ == "__main__":
    main()
