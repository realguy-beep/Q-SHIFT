"""Deterministic single-fault effect extraction for reduced Phase 2B circuits.

No stochastic Phase 2B shots are generated. Each non-identity categorical
outcome is forced by a one-hot Pauli channel and its deterministic D/L mask is
read from Stim. The original Phase 2B generator is imported read-only.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
import sys

import stim

ROOT = Path(__file__).resolve().parents[2]
QSHIFT_DIR = ROOT / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(ROOT / "outputs" / "categorical_decoder_feasibility"))
spec = importlib.util.spec_from_file_location("phase2b_noise_model", QSHIFT_DIR / "noise_model.py")
noise_model = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(noise_model)

PAULI_PAIRS = noise_model.PAULI_PAIRS
NOISE_NAMES = {"PAULI_CHANNEL_1", "PAULI_CHANNEL_2", "X_ERROR", "Z_ERROR"}


def build_fragment(*, rounds: int, memory_basis: str = "z", regime: str = "x_biased") -> stim.Circuit:
    """Reproduce Phase 2B's generated circuit/noise replacement for any rounds.

    For rounds=5, use the frozen builder itself. For reduced rounds only, use
    the identical Stim-generated structure and channel replacements, omitting
    its fixed-40-detector assertion (which was intended for Phase 2B proper).
    """
    if rounds == 5:
        return noise_model.build_circuit(memory_basis, regime, distance=3, rounds=5)
    if memory_basis not in noise_model.MEMORY_BASES:
        raise ValueError(memory_basis)
    p1 = noise_model.one_qubit_probabilities(regime)
    p2 = noise_model.two_qubit_probabilities(regime)
    generated = stim.Circuit.generated(
        f"surface_code:rotated_memory_{memory_basis}", distance=3, rounds=rounds,
        after_clifford_depolarization=noise_model.DEFAULT_GATE_P,
        before_measure_flip_probability=noise_model.DEFAULT_MEAS_P,
    )
    body = str(generated)
    body, n1 = re.subn(r"DEPOLARIZE1\([^)]*\)",
                       "PAULI_CHANNEL_1(" + ",".join(format(v, ".17g") for v in p1) + ")", body)
    body, n2 = re.subn(r"DEPOLARIZE2\([^)]*\)",
                       "PAULI_CHANNEL_2(" + ",".join(format(v, ".17g") for v in p2) + ")", body)
    if n1 == 0 or n2 == 0:
        raise RuntimeError(f"expected 1Q and 2Q sites; found {(n1, n2)}")
    result = stim.Circuit(body)
    if result.num_detectors == 0 or result.num_observables != 1:
        raise RuntimeError((result.num_detectors, result.num_observables))
    return result


def _target_groups(instruction):
    targets = instruction.targets_copy()
    if instruction.name == "PAULI_CHANNEL_2":
        return [targets[i:i+2] for i in range(0, len(targets), 2)]
    return [[t] for t in targets]


def categorical_locations(circuit):
    """Expand vectorized Stim channel instructions into independent locations."""
    locations = []
    for instruction_index, instruction in enumerate(circuit.flattened()):
        name = instruction.name
        if name not in NOISE_NAMES:
            continue
        args = [float(v) for v in instruction.gate_args_copy()]
        groups = _target_groups(instruction)
        for group_index, group in enumerate(groups):
            if name == "PAULI_CHANNEL_1":
                probs = {"X": args[0], "Y": args[1], "Z": args[2]}
                probs["I"] = 1.0 - sum(probs.values())
                labels = ("I", "X", "Y", "Z")
            elif name == "PAULI_CHANNEL_2":
                probs = dict(zip(PAULI_PAIRS, args))
                probs["II"] = 1.0 - sum(args)
                labels = ("II",) + tuple(PAULI_PAIRS)
            else:
                p = args[0]
                fault_label = name[0]
                probs = {"I": 1.0-p, fault_label: p}
                labels = ("I", fault_label)
            if any(p < -1e-12 or p > 1+1e-12 for p in probs.values()) or abs(sum(probs.values())-1)>1e-10:
                raise ValueError(f"invalid channel probabilities at instruction {instruction_index}")
            locations.append({
                "index": len(locations), "instruction_index": instruction_index,
                "group_index": group_index, "instruction": name,
                "qubits_or_targets": [str(t) for t in group], "probabilities": probs,
                "labels": labels,
            })
    return locations


def force_one_outcome(circuit: stim.Circuit, location: dict, label: str) -> stim.Circuit:
    """Keep ideal gates and exactly one deterministic fault; remove other noise."""
    out = stim.Circuit()
    for instruction_index, instruction in enumerate(circuit.flattened()):
        if instruction.name not in NOISE_NAMES:
            out.append(instruction.name, instruction.targets_copy(), instruction.gate_args_copy())
            continue
        if instruction_index != location["instruction_index"] or label in ("I", "II"):
            continue
        groups = _target_groups(instruction)
        group = groups[location["group_index"]]
        if instruction.name == "PAULI_CHANNEL_1":
            args = [float(label == p) for p in "XYZ"]
        elif instruction.name == "PAULI_CHANNEL_2":
            args = [float(label == pair) for pair in PAULI_PAIRS]
        else:
            args = [1.0]
        out.append(instruction.name, group, args)
    return out


def _integer_bits(row):
    value = 0
    for i, bit in enumerate(row):
        value |= int(bit) << i
    return value


def extract_model(*, rounds: int, memory_basis: str = "z", regime: str = "x_biased"):
    """Return circuit, categorical model, and extraction accounting."""
    from categorical_reference import CategoricalLocation, CategoricalModel, FaultOutcome

    circuit = build_fragment(rounds=rounds, memory_basis=memory_basis, regime=regime)
    locations = categorical_locations(circuit)
    ideal = force_one_outcome(circuit, {"instruction_index": -1, "group_index": 0}, "I")
    d0, o0 = ideal.compile_detector_sampler(seed=101).sample(2, separate_observables=True)
    if d0.any() or o0.any() or not (d0[0] == d0[1]).all() or not (o0[0] == o0[1]).all():
        raise AssertionError("noiseless fragment is not deterministic all-zero")

    categorical = []
    checked = 0
    for loc in locations:
        outcomes = []
        for label in loc["labels"]:
            probability = loc["probabilities"][label]
            if label in ("I", "II"):
                detector_mask = observable_mask = 0
            else:
                forced = force_one_outcome(circuit, loc, label)
                detectors, observables = forced.compile_detector_sampler(seed=107).sample(
                    2, separate_observables=True)
                if not (detectors[0] == detectors[1]).all() or not (observables[0] == observables[1]).all():
                    raise AssertionError(f"forced Pauli outcome is not deterministic: {loc['index']}/{label}")
                detector_mask = _integer_bits(detectors[0])
                observable_mask = _integer_bits(observables[0])
                checked += 1
            outcomes.append(FaultOutcome(label, probability, detector_mask, observable_mask))
        categorical.append(CategoricalLocation(
            f"loc_{loc['index']}_{loc['instruction']}_{loc['group_index']}", tuple(outcomes),
            "I" if "I" in loc["labels"] else "II"))
    model = CategoricalModel(circuit.num_detectors, circuit.num_observables, tuple(categorical))
    model.validate()
    return circuit, model, {"fault_locations": len(locations), "forced_nonidentity_checks": checked,
                            "detectors": circuit.num_detectors, "observables": circuit.num_observables,
                            "rounds": rounds, "memory_basis": memory_basis, "regime": regime}
