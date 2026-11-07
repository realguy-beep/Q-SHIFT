from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
P2B = HERE.parent / "phase2b_pauli_bias"
sys.path.insert(0, str(P2B))
from noise_model import (MEMORY_BASES, REGIMES, PAULI_PAIRS, build_circuit,
                         circuit_noise_record, one_qubit_probabilities,
                         two_qubit_probabilities)  # noqa: E402


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    rows = []
    for basis in MEMORY_BASES:
        for regime in REGIMES:
            base = stim.Circuit.generated(
                f"surface_code:rotated_memory_{basis}", distance=3, rounds=5,
                after_clifford_depolarization=0.003,
                before_measure_flip_probability=0.003,
            )
            circuit, noise = circuit_noise_record(basis, regime)
            normalized = re.sub(r"PAULI_CHANNEL_1\([^)]*\)", "DEPOLARIZE1(0.003)", str(circuit))
            normalized = re.sub(r"PAULI_CHANNEL_2\([^)]*\)", "DEPOLARIZE2(0.003)", normalized)
            structural_match = normalized == str(base)
            if not structural_match:
                raise AssertionError(f"noise replacement changed non-channel circuit structure for {basis}/{regime}")
            p1 = one_qubit_probabilities(regime)
            p2 = two_qubit_probabilities(regime)
            if not np.isclose(sum(p1), 0.003) or not np.isclose(sum(p2), 0.003):
                raise AssertionError("categorical channel mass differs from 0.003")
            if noise["2q_pauli_pair_order"] != list(PAULI_PAIRS):
                raise AssertionError("two-qubit Pauli argument order mismatch")
            dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
            matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
            if (circuit.num_detectors, circuit.num_observables) != (40, 1):
                raise AssertionError("detector or observable convention changed")
            if matching.num_detectors != 40:
                raise AssertionError("matching graph detector count changed")
            flat = list(circuit.flattened())
            rows.append({
                "memory_basis": basis, "regime": regime,
                "source_replacement_preserves_all_other_instructions": structural_match,
                "1q_channel_order": ["X", "Y", "Z"], "1q_probabilities": list(p1),
                "2q_channel_order": list(PAULI_PAIRS), "2q_probability_sum": float(sum(p2)),
                "measurement_flip_instruction_counts": {
                    "X_ERROR": sum(x.name == "X_ERROR" for x in flat),
                    "Z_ERROR": sum(x.name == "Z_ERROR" for x in flat)},
                "measurement_flip_targets": noise["flattened_noise_target_counts"]["measurement_flip_targets"],
                "detectors": circuit.num_detectors, "observables": circuit.num_observables,
                "DEM_flags": {"decompose_errors": True, "approximate_disjoint_errors": True},
                "matching_correlations_enabled": True, "matching_edges": matching.num_edges,
                "logical_fault_ids": sorted({int(x) for _, _, a in matching.edges() for x in a.get("fault_ids", set())}),
            })
    report = {
        "status": "PASS",
        "scope": "read-only structural audit; does not alter Phase 2B",
        "phase2b_source_sha256": {name: digest(P2B / name) for name in ["noise_model.py", "decoder_bank.py", "test_phase2b.py"]},
        "cases": rows,
        "measurement_noise_interpretation": "The custom circuit is text-identical to Stim's generated circuit after restoring only the two gate-noise instruction names/arguments. This independently confirms the generated pre-measurement flips and their basis-specific placement were not changed by Phase 2B replacement.",
        "logical_prediction_convention": "Stim observable id 0 is the single target bit; residual failure is observable XOR decoder prediction."
    }
    (HERE / "SOURCE_VALIDATION.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS: all six Phase 2B circuit variants preserve exact generated structure apart from custom gate channels")


if __name__ == "__main__":
    main()
