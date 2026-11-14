"""Local Fisher-information audit for the ten burst-pair detector bits.

Compares their full 2^10 joint likelihood with optimally weighted means of the
same ten bits plus five cofire features. Exact categorical circuit and
approximate DEM are calculated separately. No samples or histories are made.
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

import burst_step_information_audit as info
import categorical_circuit_parameter_grid_audit as grid
from categorical_circuit_feature_expectations import direct_xor
from dem_feature_expectations import build_dem, direct_xor_convolution

P_VALUES = (0.002, 0.010, 0.018)
PM = 0.003
H_STEPS = (1e-5, 5e-6, 2.5e-6)
STATES = np.arange(2 ** len(info.SELECTED), dtype=np.uint16)
BITS = ((STATES[:, None] >> np.arange(len(info.SELECTED))) & 1).astype(np.float64)
PAIR_FEATURES = np.column_stack([BITS, np.column_stack([
    BITS[:, 2*i] * BITS[:, 2*i+1] for i in range(5)])])


def distribution(model: str, p: float, pm: float, template: list) -> np.ndarray:
    if model == "exact_categorical_circuit":
        circuit = grid.construct(p, pm)
        return direct_xor(grid.reweight(template, circuit), info.SELECTED)
    _, mechanisms = build_dem(p, pm)
    return direct_xor_convolution(mechanisms, info.SELECTED)


def feature_moments(prob: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = prob @ PAIR_FEATURES
    centered = PAIR_FEATURES - mean
    cov = (centered * prob[:, None]).T @ centered
    return mean, cov


def information(prob: np.ndarray, dprob: np.ndarray) -> dict:
    if np.any(prob <= 0):
        raise RuntimeError("all selected-outcome states must have positive mass for this Fisher calculation")
    full = dprob.T @ (dprob / prob[:, None])
    jac = np.zeros((PAIR_FEATURES.shape[1], 2))
    for j in range(2):
        jac[:, j] = dprob[:, j] @ PAIR_FEATURES
    mean, cov = feature_moments(prob)
    eig = np.linalg.eigvalsh(cov)
    if eig[0] <= 1e-14:
        raise RuntimeError(f"15-feature covariance is singular: eigenmin={eig[0]}")
    moment = jac.T @ np.linalg.solve(cov, jac)
    def profile(mat: np.ndarray) -> float:
        return float(mat[0, 0] - mat[0, 1] ** 2 / mat[1, 1])
    vals = {
        "full_joint_fisher": full,
        "15_feature_optimal_gmm_information": moment,
        "mean": mean,
        "feature_covariance_eigenvalues_min_max": [float(eig[0]), float(eig[-1])],
        "profile_burst_information_full": profile(full),
        "profile_burst_information_15_feature_gmm": profile(moment),
        "burst_sd_coefficient_full_unknown_measurement": float(1 / np.sqrt(profile(full))),
        "burst_sd_coefficient_15_feature_unknown_measurement": float(1 / np.sqrt(profile(moment))),
        "burst_sd_coefficient_full_known_measurement": float(1 / np.sqrt(full[0, 0])),
        "burst_sd_coefficient_15_feature_known_measurement": float(1 / np.sqrt(moment[0, 0])),
        "full_fisher_eigenvalues": np.linalg.eigvalsh(full).tolist(),
        "full_fisher_condition_number": float(np.linalg.cond(full)),
        "burst_measurement_score_correlation_full": float(full[0, 1] / np.sqrt(full[0, 0]*full[1, 1])),
        "burst_measurement_score_correlation_15_feature": float(moment[0, 1] / np.sqrt(moment[0, 0]*moment[1, 1])),
    }
    return vals


def main() -> None:
    base = grid.construct(0.010, PM)
    template, _ = grid.categorical_sites(base)
    rows = []
    validation = {"maximum_distribution_normalization_error": 0.0,
        "maximum_derivative_mass_error_by_step": {}, "fisher_psd": True,
        "moment_information_not_above_joint_fisher": True,
        "maximum_step_halving_relative_change": 0.0}
    for model in ("exact_categorical_circuit", "approximate_dem"):
        for p in P_VALUES:
            base_prob = distribution(model, p, PM, template)
            validation["maximum_distribution_normalization_error"] = max(
                validation["maximum_distribution_normalization_error"], abs(float(base_prob.sum())-1))
            step_results = []
            for h in H_STEPS:
                dprob = np.column_stack([
                    (distribution(model, p+h, PM, template) - distribution(model, p-h, PM, template))/(2*h),
                    (distribution(model, p, PM+h, template) - distribution(model, p, PM-h, template))/(2*h),
                ])
                validation["maximum_derivative_mass_error_by_step"][str(h)] = max(
                    validation["maximum_derivative_mass_error_by_step"].get(str(h), 0.0),
                    float(np.max(np.abs(dprob.sum(axis=0)))))
                res = information(base_prob, dprob)
                validation["fisher_psd"] &= min(res["full_fisher_eigenvalues"]) > 0
                gap = res["profile_burst_information_full"] - res["profile_burst_information_15_feature_gmm"]
                validation["moment_information_not_above_joint_fisher"] &= gap >= -2e-7
                step_results.append((h, res))
            base_res = step_results[0][1]
            for (h0, r0), (h1, r1) in zip(step_results, step_results[1:]):
                for key in ("profile_burst_information_full", "profile_burst_information_15_feature_gmm"):
                    rel = abs(r0[key]-r1[key])/max(abs(r1[key]), 1e-15)
                    validation["maximum_step_halving_relative_change"] = max(
                        validation["maximum_step_halving_relative_change"], rel)
            rows.append({"model": model, "burst_p": p, "measurement_p": PM,
                "finite_difference_results_by_step": [
                    {"step": h, **{k:v for k,v in r.items() if k not in ("full_joint_fisher", "15_feature_optimal_gmm_information", "mean")}}
                    for h,r in step_results],
                "reported_primary_step": H_STEPS[-1]})
    if validation["maximum_distribution_normalization_error"] > 2e-12:
        raise RuntimeError("joint distribution normalization failed")
    if any(v > 2e-8 for v in validation["maximum_derivative_mass_error_by_step"].values()):
        raise RuntimeError("derivative does not sum to zero")
    if not validation["fisher_psd"] or not validation["moment_information_not_above_joint_fisher"]:
        raise RuntimeError("Fisher/GMM information sanity check failed")
    result = {
        "classification": "DETERMINISTIC_LOCAL_FISHER_INFORMATION_NOT_FINITE_SAMPLE_ACCURACY",
        "configuration": {"selected_detectors": list(info.SELECTED), "outcome_states": len(STATES),
            "moment_features": "10 detector bits plus five within-pair cofire bits",
            "burst_values": list(P_VALUES), "measurement_p": PM,
            "finite_difference_steps": list(H_STEPS)},
        "method": "Compute per-shot Fisher information from the full 2^10 joint likelihood and optimal-covariance GMM information from the same 15 feature means; profile out measurement p by the Schur complement; check central-difference step halving.",
        "rows": rows, "validation": validation,
        "interpretation": [
            "The full multinomial Fisher calculation uses the complete selected 10-bit outcome, while the 15-feature GMM uses only its ten first moments and five pair cofires. The comparison isolates information discarded by these moments on this detector subset.",
            "Reported SD coefficients are local asymptotic Cramer-Rao/GMM coefficients per square root of independent shot count under the exactly specified static model. They are not observed or finite-history estimator RMSEs, interval coverage, change-detection delay, or logical decoder utility.",
            "Unknown measurement probability is profiled locally; this does not cover gate uncertainty, arbitrary readout correlations, burst support changes, or time-dependent within-shot noise.",
            "Exact categorical circuit and approximate DEM are separate calculations; no sampling, fitting to generated outcomes, or decoder evaluation occurs."
        ], "sampling_calls": 0, "decoder_calls": 0}
    (HERE / "BURST_PAIR_JOINT_FISHER_AUDIT.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"rows": rows, "validation": validation}, indent=2))


if __name__ == "__main__":
    main()
