"""Explicit Pauli-biased circuit-level Stim noise models for Phase 2B."""
from __future__ import annotations

import re
from itertools import product

import numpy as np
import stim

REGIMES = ("x_biased", "balanced", "z_biased")
MEMORY_BASES = ("z", "x")
PAULI_PAIRS = ("IX", "IY", "IZ", "XI", "XX", "XY", "XZ", "YI", "YX", "YY", "YZ", "ZI", "ZX", "ZY", "ZZ")
DEFAULT_GATE_P = 0.003
DEFAULT_MEAS_P = 0.003
DEFAULT_BIAS_RATIO = 10.0


def axis_weights(regime: str, bias_ratio: float = DEFAULT_BIAS_RATIO) -> dict[str, float]:
    if regime == "balanced":
        return {"I": 1.0, "X": 1.0, "Y": 1.0, "Z": 1.0}
    if regime == "x_biased":
        return {"I": 1.0, "X": float(bias_ratio), "Y": 1.0, "Z": 1.0}
    if regime == "z_biased":
        return {"I": 1.0, "X": 1.0, "Y": 1.0, "Z": float(bias_ratio)}
    raise ValueError(f"unknown Pauli bias regime: {regime}")


def one_qubit_probabilities(regime: str, total_p: float = DEFAULT_GATE_P,
                            bias_ratio: float = DEFAULT_BIAS_RATIO) -> tuple[float, float, float]:
    weights = axis_weights(regime, bias_ratio)
    denominator = weights["X"] + weights["Y"] + weights["Z"]
    return tuple(float(total_p * weights[p] / denominator) for p in "XYZ")


def two_qubit_probabilities(regime: str, total_p: float = DEFAULT_GATE_P,
                            bias_ratio: float = DEFAULT_BIAS_RATIO) -> tuple[float, ...]:
    """Disjoint non-II probabilities; sum is exactly total_p up to float roundoff."""
    weights = axis_weights(regime, bias_ratio)
    raw = np.asarray([weights[a] * weights[b] for a, b in PAULI_PAIRS], dtype=np.float64)
    probs = total_p * raw / raw.sum()
    # Correct the final rounding residual without changing the intended ratio materially.
    probs[-1] += total_p - float(probs.sum())
    return tuple(float(v) for v in probs)


def two_qubit_marginals(probabilities: tuple[float, ...]) -> dict[str, dict[str, float]]:
    by_pair = dict(zip(PAULI_PAIRS, probabilities))
    return {
        "first_qubit": {p: float(sum(v for pair, v in by_pair.items() if pair[0] == p)) for p in "IXYZ"},
        "second_qubit": {p: float(sum(v for pair, v in by_pair.items() if pair[1] == p)) for p in "IXYZ"},
    }


def build_circuit(memory_basis: str, regime: str, *, distance: int = 3, rounds: int = 5,
                  gate_p: float = DEFAULT_GATE_P, measurement_p: float = DEFAULT_MEAS_P,
                  bias_ratio: float = DEFAULT_BIAS_RATIO) -> stim.Circuit:
    if memory_basis not in MEMORY_BASES:
        raise ValueError(f"memory_basis must be one of {MEMORY_BASES}")
    p1 = one_qubit_probabilities(regime, gate_p, bias_ratio)
    p2 = two_qubit_probabilities(regime, gate_p, bias_ratio)
    generated = stim.Circuit.generated(
        f"surface_code:rotated_memory_{memory_basis}", distance=distance, rounds=rounds,
        # A nonzero placeholder makes Stim emit all post-Clifford injection sites;
        # every placeholder depolarizing instruction is replaced immediately below.
        after_clifford_depolarization=DEFAULT_GATE_P,
        before_measure_flip_probability=measurement_p,
    )
    body = str(generated)
    p1_text = "PAULI_CHANNEL_1(" + ",".join(format(v, ".17g") for v in p1) + ")"
    p2_text = "PAULI_CHANNEL_2(" + ",".join(format(v, ".17g") for v in p2) + ")"
    body, n1 = re.subn(r"DEPOLARIZE1\([^)]*\)", p1_text, body)
    body, n2 = re.subn(r"DEPOLARIZE2\([^)]*\)", p2_text, body)
    if n1 == 0 or n2 == 0:
        raise RuntimeError(f"expected generated 1Q and 2Q depolarizing locations; found compact counts {(n1, n2)}")
    circuit = stim.Circuit(body)
    if circuit.num_detectors != 40 or circuit.num_observables != 1:
        raise RuntimeError(f"unexpected circuit shape: detectors={circuit.num_detectors}, observables={circuit.num_observables}")
    return circuit


def circuit_noise_record(memory_basis: str, regime: str, *, distance: int = 3, rounds: int = 5,
                         gate_p: float = DEFAULT_GATE_P, measurement_p: float = DEFAULT_MEAS_P,
                         bias_ratio: float = DEFAULT_BIAS_RATIO) -> tuple[stim.Circuit, dict]:
    circuit = build_circuit(memory_basis, regime, distance=distance, rounds=rounds,
                            gate_p=gate_p, measurement_p=measurement_p, bias_ratio=bias_ratio)
    p1 = one_qubit_probabilities(regime, gate_p, bias_ratio)
    p2 = two_qubit_probabilities(regime, gate_p, bias_ratio)
    flat = circuit.flattened()
    counts = {"PAULI_CHANNEL_1": 0, "PAULI_CHANNEL_2": 0, "X_ERROR": 0, "Z_ERROR": 0}
    targets = {"one_qubit_channel_targets": 0, "two_qubit_channel_pairs": 0,
               "measurement_flip_targets": 0}
    for instruction in flat:
        name = instruction.name
        instruction_targets = instruction.targets_copy()
        if name in counts:
            counts[name] += 1
        if name == "PAULI_CHANNEL_1":
            targets["one_qubit_channel_targets"] += len(instruction_targets)
        elif name == "PAULI_CHANNEL_2":
            targets["two_qubit_channel_pairs"] += len(instruction_targets) // 2
        elif name in ("X_ERROR", "Z_ERROR"):
            targets["measurement_flip_targets"] += len(instruction_targets)
    record = {
        "memory_basis": memory_basis, "regime": regime, "distance": distance, "rounds": rounds,
        "total_fault_probability_per_1q_instruction": gate_p,
        "1q_pauli_probabilities_X_Y_Z": list(p1), "1q_pauli_probability_sum": float(sum(p1)),
        "total_fault_probability_per_2q_instruction": gate_p,
        "2q_pauli_pair_order": list(PAULI_PAIRS), "2q_pauli_pair_probabilities": list(p2),
        "2q_pauli_probability_sum": float(sum(p2)), "2q_pauli_marginals": two_qubit_marginals(p2),
        "measurement_flip_probability": measurement_p,
        "flattened_instruction_counts": counts, "flattened_noise_target_counts": targets,
        "detectors": circuit.num_detectors, "observables": circuit.num_observables,
        "noise_semantics": "Each PAULI_CHANNEL_2 draw is a categorical Pauli-pair fault, so two-qubit Pauli components are correlated within that gate. Independent gate locations have no cross-location correlation.",
    }
    return circuit, record
