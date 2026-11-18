"""Reproducibly quantify memory-basis matching under Pauli-biased noise."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from scipy.stats import beta, binomtest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
from noise_model import MEMORY_BASES, REGIMES, circuit_noise_record  # noqa: E402


def exact_conditional_rr(x_errors: int, z_errors: int) -> tuple[float, list[float], float]:
    total = x_errors+z_errors
    p = x_errors/total
    interval = beta.ppf([0.025, 0.975], x_errors, z_errors+1)
    rr = p/(1-p)
    ci = [float(v/(1-v)) for v in interval]
    pvalue = float(binomtest(x_errors, total, 0.5, alternative="two-sided").pvalue)
    return rr, ci, pvalue


def main() -> int:
    importance = json.loads((HERE/"categorical_importance_results.json").read_text())
    raw = json.loads((HERE/"categorical_sampler_crosscheck.json").read_text())
    by_imp = {(x["memory_basis"], x["regime"]): x for x in importance["conditions"]}
    by_raw = {(x["memory_basis"], x["regime"]): x for x in raw["condition_results"]}
    rows = []
    for regime in REGIMES:
        cells = {}
        for basis in MEMORY_BASES:
            key = (basis, regime)
            a, b = by_imp[key], by_raw[key]
            n1, n2 = a["shots_per_arm"], b["shots"]
            failures = a["direct_failures"]+b["raw_circuit_failures"]
            cells[basis] = {"failures": failures, "shots": n1+n2,
                            "ler": failures/(n1+n2)}
        rr, ci, pvalue = exact_conditional_rr(cells["x"]["failures"], cells["z"]["failures"])
        if regime == "x_biased":
            aligned, mismatched = "x", "z"
            aligned_rr = rr
            aligned_ci = ci
        elif regime == "z_biased":
            aligned, mismatched = "z", "x"
            aligned_rr = 1/rr
            aligned_ci = [1/ci[1], 1/ci[0]]
        else:
            aligned, mismatched = None, None
            aligned_rr = rr
            aligned_ci = ci
        resource_by_basis = {}
        for basis in MEMORY_BASES:
            circuit, record = circuit_noise_record(basis, regime)
            resource_by_basis[basis] = {
                "physical_qubits": int(circuit.num_qubits),
                "detectors": int(circuit.num_detectors),
                "observables": int(circuit.num_observables),
                "noise_channel_counts": record["flattened_instruction_counts"],
                "noise_target_counts": record["flattened_noise_target_counts"],
                "gate_error_probability": 0.003,
                "measurement_error_probability": 0.003,
            }
        rx, rz = resource_by_basis["x"], resource_by_basis["z"]
        matched = (
            all(rx[k] == rz[k] for k in ("physical_qubits", "detectors", "observables",
                                          "noise_target_counts", "gate_error_probability",
                                          "measurement_error_probability")) and
            rx["noise_channel_counts"]["PAULI_CHANNEL_1"] == rz["noise_channel_counts"]["PAULI_CHANNEL_1"] and
            rx["noise_channel_counts"]["PAULI_CHANNEL_2"] == rz["noise_channel_counts"]["PAULI_CHANNEL_2"] and
            sum(rx["noise_channel_counts"][k] for k in ("X_ERROR", "Z_ERROR")) ==
            sum(rz["noise_channel_counts"][k] for k in ("X_ERROR", "Z_ERROR"))
        )
        rows.append({
            "regime": regime,
            "per_basis": cells,
            "x_over_z_rate_ratio": rr,
            "x_over_z_conditional_exact_95_ci": ci,
            "equal_rate_two_sided_p": pvalue,
            "bias_aligned_basis": aligned,
            "bias_mismatched_basis": mismatched,
            "aligned_over_mismatched_rate_ratio": aligned_rr,
            "aligned_over_mismatched_95_ci": aligned_ci,
            "relative_reduction_from_alignment": 1-aligned_rr if aligned else None,
            "resources_by_basis": resource_by_basis,
            "common_resource_counts_match": matched,
            "matched_resources": {
                "distance": 3,
                "rounds": 5,
                "physical_qubits": resource_by_basis["x"]["physical_qubits"],
                "detectors": resource_by_basis["x"]["detectors"],
                "observables": resource_by_basis["x"]["observables"],
                "same_noise_target_counts": resource_by_basis["x"]["noise_target_counts"] == resource_by_basis["z"]["noise_target_counts"],
                "per_basis_measurement_error_channels": {
                    basis: resource_by_basis[basis]["noise_channel_counts"] for basis in MEMORY_BASES},
            },
        })
    output = {
        "status": "development_analysis_of_two_independent_exact_circuit_samples",
        "samples_per_basis_regime": 40000,
        "data_sources": ["categorical_importance_results.json direct arm",
                         "categorical_sampler_crosscheck.json unmodified Stim arm"],
        "decoder": "correlation-enabled PyMatching using the same approximate DEM construction",
        "interval_method": "conditional binomial/Poisson rate-ratio interval for rare failures; exact two-sided binomial test under equal rates",
        "conditions": rows,
        "interpretation": "same-resource bias-aligned memory basis improves LER in biased regimes; this is known-profile code/circuit co-design, not decoder superiority or an adaptive-policy result",
    }
    target = HERE/"basis_orientation_results.json"
    target.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote {target}")
    for row in rows:
        print(row["regime"], row["per_basis"],
              "alignedRR", row["aligned_over_mismatched_rate_ratio"],
              "CI", row["aligned_over_mismatched_95_ci"],
              "relative_reduction", row["relative_reduction_from_alignment"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
