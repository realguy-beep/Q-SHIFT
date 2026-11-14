"""Exact-circuit population sensitivity of the bounded e-factor to gate p drift.

Fault supports are mapped deterministically once and channel probabilities are
reweighted. No noisy shots, detector histories, alarms, or decoders are used.
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
from simulator import build_spatial_burst_circuit


GATE_GRID = (0.002, 0.003, 0.004)
PM_GRID = (0.001, 0.003, 0.005)
PB_GRID = (0.002, 0.010, 0.018)
PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
M0_CERTIFIED = 0.00269469102575917
M1_CERTIFIED = 0.00997074427026786


def circuit(gate_p: float, measurement_p: float, burst_p: float):
    return build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=gate_p, measurement_p=measurement_p, bias_ratio=10.0,
        burst_probability=burst_p, burst_pair=(8, 10),
    )


def reweight(mapped_template, template_names, target_circuit):
    raw_target = features.extract_sites(target_circuit)
    names = [inst.name for inst in target_circuit]
    if names != template_names or len(raw_target) != len(mapped_template):
        raise RuntimeError("gate/measurement reweight changed circuit or noise-site topology")
    output = []
    for (ix, identity, alternatives), (_template_identity, mapped_alternatives) in zip(raw_target, mapped_template):
        if len(alternatives) != len(mapped_alternatives):
            raise RuntimeError("categorical alternative count changed under mismatch grid")
        new_alternatives = []
        for (probability, paulis), (_old_p, support, observable, old_paulis) in zip(alternatives, mapped_alternatives):
            if paulis != old_paulis:
                raise RuntimeError("categorical Pauli ordering changed under mismatch grid")
            new_alternatives.append((probability, support, observable, paulis))
        output.append((identity, new_alternatives))
    return output


def main() -> None:
    template_circuit = circuit(0.003, 0.003, 0.010)
    mapped_template, meta = features.categorical_sites(template_circuit)
    template_names = [inst.name for inst in template_circuit]
    rows = []
    for gate_p in GATE_GRID:
        for measurement_p in PM_GRID:
            for burst_p in PB_GRID:
                c = circuit(gate_p, measurement_p, burst_p)
                mapped = reweight(mapped_template, template_names, c)
                means = features.means_from_characters(mapped)
                x_mean = float(np.mean(means[40:45]))
                if burst_p <= 0.002:
                    relevant_bound = M0_CERTIFIED
                    regime = "low_burst_null_upper_bound"
                    within = x_mean <= relevant_bound + 1e-12
                else:
                    relevant_bound = M1_CERTIFIED
                    regime = "high_burst_null_lower_bound"
                    within = x_mean >= relevant_bound - 1e-12
                rows.append({
                    "gate_p": gate_p,
                    "measurement_p": measurement_p,
                    "burst_p": burst_p,
                    "exact_categorical_circuit_pair_cofire_mean": x_mean,
                    "relevant_fixed_gate_boundary": relevant_bound,
                    "regime_tested": regime,
                    "excess_or_gap_from_fixed_gate_boundary": x_mean - relevant_bound,
                    "within_fixed_gate_regime_bound": within,
                })
    low_excess = [r["excess_or_gap_from_fixed_gate_boundary"] for r in rows if r["regime_tested"] == "low_burst_null_upper_bound"]
    high_gap = [r["excess_or_gap_from_fixed_gate_boundary"] for r in rows if r["regime_tested"] == "high_burst_null_lower_bound"]
    result = {
        "classification": "DETERMINISTIC_EXACT_CIRCUIT_GATE_MISMATCH_SENSITIVITY_GRID",
        "fixed_gate_certificate_reference": {"gate_p": 0.003, "continuous_null_mean_max": M0_CERTIFIED, "burst_null": [0.0, 0.002], "measurement_interval": [0.001, 0.005]},
        "tested_gate_grid": list(GATE_GRID),
        "tested_measurement_grid": list(PM_GRID),
        "tested_burst_grid": list(PB_GRID),
        "fault_mapping_metadata": meta,
        "maximum_mean": max(r["exact_categorical_circuit_pair_cofire_mean"] for r in rows),
        "maximum_low_null_excess_over_fixed_gate_certificate": max(low_excess),
        "minimum_high_regime_gap_over_fixed_gate_certificate": min(high_gap),
        "any_point_violates_fixed_gate_regime_bound": any(not r["within_fixed_gate_regime_bound"] for r in rows),
        "rows": rows,
        "limitations": [
            "This is a finite gate/measurement grid, not a continuous gate-nuisance certificate.",
            "A detected mean-bound exceedance demonstrates that the fixed-gate e-factor guarantee does not transfer to that tested gate setting; it does not quantify real-world drift probability.",
            "No detector histories, e-process, alarm, decoder, or logical outcome was evaluated.",
        ],
    }
    out = HERE / "GATE_NOISE_MISMATCH_EVALIDITY_AUDIT.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("max_mean", result["maximum_mean"], "low_null_excess", result["maximum_low_null_excess_over_fixed_gate_certificate"], "high_min_gap", result["minimum_high_regime_gap_over_fixed_gate_certificate"], "violates", result["any_point_violates_fixed_gate_regime_bound"])
    print(f"wrote={out}")


if __name__ == "__main__":
    main()
