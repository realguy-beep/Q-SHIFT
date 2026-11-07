"""Enumerate two tiny categorical toy channels and compare DEM matchers."""
from __future__ import annotations

import json
import math
from pathlib import Path

import stim
import pymatching

from categorical_reference import decoder_risk, exact_posterior
from toy_circuits import (ONE_Q_PROBS, PAULI_PAIRS, TWO_Q_NONIDENTITY_TOTAL,
                          one_qubit_model, two_qubit_model, noisy_stim_circuit,
                          pymatching_decisions, stim_exhaustive_joint, two_qubit_probabilities)

HERE = Path(__file__).resolve().parent


def evaluate(kind, model):
    exact = exact_posterior(model)
    stim_joint, stim_count = stim_exhaustive_joint(model, kind)
    if set(exact.joint) != set(stim_joint):
        raise AssertionError(f"custom and Stim exact enumeration supports differ for {kind}")
    for syndrome in exact.joint:
        if any(not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12)
               for a, b in zip(exact.joint[syndrome], stim_joint[syndrome])):
            raise AssertionError(f"joint P(s,l) mismatch for {kind}, syndrome {syndrome}")
    syndromes = list(range(1 << model.detector_count))
    pm = pymatching_decisions(kind, syndromes)
    decoder_predictions = {
        "exact_categorical_MAP": exact.decisions,
        "pymatching_approx_dem_correlation_disabled": {int(k): int(v) for k, v in pm["decoders"]["correlation_disabled"].items()},
        "pymatching_approx_dem_correlation_enabled": {int(k): int(v) for k, v in pm["decoders"]["correlation_enabled"].items()},
    }
    risks = {name: decoder_risk(exact.joint, decisions) for name, decisions in decoder_predictions.items()}
    syndrome_rows = []
    for s in syndromes:
        probs = exact.joint.get(s, (0.0, 0.0))
        mass = sum(probs)
        post = [p / mass for p in probs] if mass else None
        syndrome_rows.append({
            "syndrome_bits_D0_D1": [(s >> j) & 1 for j in range(2)],
            "syndrome_integer_little_bit_order": s,
            "P_syndrome_L0": probs[0], "P_syndrome_L1": probs[1],
            "P_syndrome": mass, "P_L1_given_syndrome": post[1] if post else None,
            "exact_MAP_decision": exact.decisions.get(s),
            "PyMatching_uncorrelated_decision": decoder_predictions["pymatching_approx_dem_correlation_disabled"].get(s),
            "PyMatching_correlated_decision": decoder_predictions["pymatching_approx_dem_correlation_enabled"].get(s),
            "off_disagrees_with_exact": decoder_predictions["pymatching_approx_dem_correlation_disabled"].get(s) != exact.decisions.get(s),
            "on_disagrees_with_exact": decoder_predictions["pymatching_approx_dem_correlation_enabled"].get(s) != exact.decisions.get(s),
        })
    return {
        "kind": kind,
        "model": {"detectors": model.detector_count, "observables": model.observable_count,
                  "location_count": len(model.locations),
                  "outcomes_per_location": [len(loc.outcomes) for loc in model.locations],
                  "full_fault_configurations": model.configuration_count,
                  "per_location_probability_sums": [sum(o.probability for o in loc.outcomes) for loc in model.locations]},
        "exact_reference": {"method": "Cartesian exhaustive enumeration; one categorical outcome selected per location",
                            "configuration_count_visited": exact.configuration_count,
                            "stim_deterministic_reference_configurations": stim_count,
                            "joint_probability_mass": exact.total_probability,
                            "tie_syndromes": list(exact.tie_syndromes), "tie_policy": exact.tie_policy,
                            "exact_MAP_logical_error_probability": exact.logical_error_probability,
                            "joint_distribution": {str(s): list(v) for s, v in exact.joint.items()},
                            "conditional_distribution": {str(s): list(v) for s, v in exact.conditional.items()},
                            "stim_joint_matches_custom_exact_enumeration": True},
        "approximate_dem_pymatching": pm,
        "logical_error_probability_under_exact_channel": risks,
        "decision_disagreements_vs_exact_by_syndrome": {
            "correlation_disabled": sum(r["off_disagrees_with_exact"] for r in syndrome_rows),
            "correlation_enabled": sum(r["on_disagrees_with_exact"] for r in syndrome_rows),
            "correlation_on_vs_off": sum(decoder_predictions["pymatching_approx_dem_correlation_disabled"][s] !=
                                          decoder_predictions["pymatching_approx_dem_correlation_enabled"][s]
                                          for s in syndromes)},
        "syndrome_decisions": syndrome_rows,
    }


def main():
    one = one_qubit_model()
    two = two_qubit_model()
    out = {
        "status": "PASS_TOY_EXACT_REFERENCE_VALIDATED",
        "software": {"stim": stim.__version__, "pymatching": pymatching.__version__},
        "noise_semantics": "Independent locations; each location is one categorical draw including identity. No Monte Carlo evaluation is used.",
        "toy_circuits": {
            "structure": "three data qubits initialized to |000>; one round of Z-parity checks MZZ(0,1), MZZ(1,2); final Z measurements; logical observable is parity of all three final measurements",
            "detector_masks": "D0=x0 XOR x1, D1=x1 XOR x2",
            "logical_mask": "L0=x0 XOR x1 XOR x2; X and Y flip the computational measurement bit; Z does not",
        },
        "one_qubit": {"categorical_probabilities_I_X_Y_Z": ONE_Q_PROBS,
                      "result": evaluate("one_qubit", one)},
        "two_qubit": {"pauli_pair_order": list(PAULI_PAIRS),
                      "identity_probability_per_location": 1.0 - TWO_Q_NONIDENTITY_TOTAL,
                      "nonidentity_total_probability_per_location": TWO_Q_NONIDENTITY_TOTAL,
                      "probabilities_by_pair": two_qubit_probabilities(),
                      "result": evaluate("two_qubit", two)},
        "execution_accounting": {
            "stochastic_shots_generated": 0,
            "deterministic_forced_fault_configurations_checked_by_stim": 64 + 256,
            "phase2b_evaluation_shots_generated": 0,
            "method": "exhaustive Cartesian enumeration; each Stim check uses one-hot probability-1 channel outcomes, so its detector/observable result is deterministic",
        },
    }
    (HERE / "TOY_RESULTS.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    summary = {}
    for name in ("one_qubit", "two_qubit"):
        r = out[name]["result"]
        summary[name] = {
            "configs": r["exact_reference"]["configuration_count_visited"],
            "risk": r["logical_error_probability_under_exact_channel"],
            "disagreements": r["decision_disagreements_vs_exact_by_syndrome"],
            "by_syndrome": r["syndrome_decisions"],
            "DEM_errors": r["approximate_dem_pymatching"]["dem_error_count"],
            "DEM_separators": r["approximate_dem_pymatching"]["dem_separator_count"],
        }
    print(json.dumps({"status": out["status"], "execution_accounting": out["execution_accounting"], "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
