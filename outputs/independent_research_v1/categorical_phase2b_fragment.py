"""Map three native categorical fault locations from a Phase 2B circuit layer."""
from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import sys
import time

import numpy as np
import stim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs/phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
sys.path.insert(0, str(HERE))
from noise_model import PAULI_PAIRS, build_circuit  # noqa: E402
from categorical_elimination import exact_joint_mass  # noqa: E402
from categorical_reference import (  # noqa: E402
    CategoricalLocation, CategoricalModel, FaultOutcome, exact_posterior,
)

NOISE_NAMES = {
    "PAULI_CHANNEL_1", "PAULI_CHANNEL_2", "X_ERROR", "Y_ERROR", "Z_ERROR",
    "DEPOLARIZE1", "DEPOLARIZE2", "HERALDED_ERASE", "HERALDED_PAULI_CHANNEL_1",
}


def append_pauli(circuit: stim.Circuit, pair: str, q0: int, q1: int) -> None:
    for pauli, qubit in zip(pair, (q0, q1), strict=True):
        if pauli != "I":
            circuit.append(pauli, [qubit])


def deterministic_circuit(source: stim.Circuit, selected: dict[tuple[int, int], str]) -> stim.Circuit:
    out = stim.Circuit()
    for instruction_index, instruction in enumerate(source.flattened()):
        if instruction.name == "PAULI_CHANNEL_2":
            targets = instruction.targets_copy()
            for pair_index in range(len(targets) // 2):
                label = selected.get((instruction_index, pair_index))
                if label is not None:
                    append_pauli(out, label, int(targets[2*pair_index].value),
                                 int(targets[2*pair_index+1].value))
            continue
        if instruction.name in NOISE_NAMES:
            continue
        out.append(instruction.name, instruction.targets_copy(), instruction.gate_args_copy())
    if out.num_detectors != source.num_detectors or out.num_observables != source.num_observables:
        raise RuntimeError("noise removal or fault forcing changed detector/observable dimensions")
    return out


def sample_det_obs(circuit: stim.Circuit) -> tuple[int, int]:
    measurements = circuit.compile_sampler(seed=1).sample(1)[0]
    detector_records = []
    observable_records: dict[int, list[int]] = {}
    record_count = 0
    for instruction in circuit.flattened():
        name = instruction.name
        if name == "DETECTOR":
            detector_records.append([record_count + t.value for t in instruction.targets_copy()])
        elif name == "OBSERVABLE_INCLUDE":
            obs_index = int(instruction.gate_args_copy()[0])
            observable_records.setdefault(obs_index, []).extend(
                record_count + t.value for t in instruction.targets_copy())
        elif name in {"M", "MX", "MY", "MR", "MRX", "MRY"}:
            record_count += len(instruction.targets_copy())
        elif name == "MPP":
            record_count += sum(t.is_combiner for t in instruction.targets_copy()) + 1
    if record_count != len(measurements):
        raise RuntimeError(f"measurement record count mismatch: {record_count} vs {len(measurements)}")
    detector_bits = [sum(int(measurements[index]) for index in records) & 1
                     for records in detector_records]
    observable_bits = [sum(int(measurements[index]) for index in observable_records.get(i, [])) & 1
                       for i in range(circuit.num_observables)]
    dmask = sum(bit << i for i, bit in enumerate(detector_bits))
    omask = sum(bit << i for i, bit in enumerate(observable_bits))
    return dmask, omask


def main() -> None:
    start = time.perf_counter()
    source = build_circuit("z", "x_biased", distance=3, rounds=5, bias_ratio=10).flattened()
    channel_layers = [(i, ins) for i, ins in enumerate(source) if ins.name == "PAULI_CHANNEL_2"]
    instruction_index, instruction = channel_layers[-1]
    targets = instruction.targets_copy()
    probs = [float(p) for p in instruction.gate_args_copy()]
    if len(probs) != 15 or len(targets) < 6:
        raise RuntimeError("selected source layer does not have the expected categorical layout")
    selected_pairs = tuple(range(3))
    source_counts = (source.num_qubits, source.num_detectors, source.num_observables)
    baseline = sample_det_obs(deterministic_circuit(source, {}))

    raw_effects: list[list[tuple[int, int]]] = []
    for pair_index in selected_pairs:
        outcomes = []
        for label in ("II", *PAULI_PAIRS):
            if label == "II":
                forced = baseline
            else:
                forced = sample_det_obs(deterministic_circuit(
                    source, {(instruction_index, pair_index): label}))
            outcomes.append((forced[0] ^ baseline[0], forced[1] ^ baseline[1]))
        raw_effects.append(outcomes)

    touched = sorted({det for outcomes in raw_effects for dmask, _ in outcomes
                      for det in range(source.num_detectors) if (dmask >> det) & 1})
    if not touched and not any(omask for outcomes in raw_effects for _, omask in outcomes):
        raise RuntimeError("selected final-layer fragment has no detector or observable influence")
    remap = {old: new for new, old in enumerate(touched)}
    locations = []
    identity = 1.0 - sum(probs)
    for location_index, pair_index in enumerate(selected_pairs):
        outcomes = []
        for label, probability, (raw_dmask, raw_omask) in zip(
                ("II", *PAULI_PAIRS), (identity, *probs), raw_effects[location_index], strict=True):
            compact_dmask = sum(1 << remap[d] for d in touched if (raw_dmask >> d) & 1)
            outcomes.append(FaultOutcome(label, probability, compact_dmask, raw_omask & 1))
        q0 = int(targets[2*pair_index].value)
        q1 = int(targets[2*pair_index+1].value)
        locations.append(CategoricalLocation(f"pauli_channel_2_{instruction_index}_pair_{pair_index}_{q0}_{q1}",
                                             tuple(outcomes), "II"))
    model = CategoricalModel(len(touched), 1, tuple(locations))
    model.validate()

    # Independently verify simultaneous-fault XOR composition on a fixed
    # coverage set spanning all outcome labels at every selected location.
    combined_checks = 0
    for seed in range(256):
        states = ((seed % 16), ((seed // 7) % 16), ((seed // 31) % 16))
        selected = {}
        expected_d = 0
        expected_l = 0
        for loc, (pair_index, state) in enumerate(zip(selected_pairs, states, strict=True)):
            label = ("II", *PAULI_PAIRS)[state]
            selected[(instruction_index, pair_index)] = label
            dmask, omask = raw_effects[loc][state]
            expected_d ^= dmask
            expected_l ^= omask
        got_d, got_l = sample_det_obs(deterministic_circuit(source, selected))
        if (got_d ^ baseline[0], got_l ^ baseline[1]) != (expected_d, expected_l):
            raise RuntimeError(f"combined Pauli effects failed XOR check for outcomes {states}")
        combined_checks += 1

    reference = exact_posterior(model)
    max_mass_error = 0.0
    max_width = 0
    max_entries = 1
    syndrome_rows = []
    for syndrome in range(1 << model.detector_count):
        exact = reference.joint.get(syndrome, (0.0, 0.0))
        predicted = []
        for logical in range(2):
            value, stats = exact_joint_mass(model, syndrome, logical)
            predicted.append(value)
            max_width = max(max_width, stats.induced_width)
            max_entries = max(max_entries, stats.max_factor_entries)
            if max_entries > 1_000_000:
                raise RuntimeError("Phase 2B fragment exceeded the one-million-entry factor cap")
        delta = max(abs(predicted[l] - exact[l]) for l in range(2))
        max_mass_error = max(max_mass_error, delta)
        if any(exact) or any(predicted):
            syndrome_rows.append({"syndrome": syndrome, "exact_joint": exact,
                                  "elimination_joint": predicted, "abs_error": delta})
    if max_mass_error > 1e-10:
        raise RuntimeError(f"fragment joint mass mismatch: {max_mass_error}")

    result = {
        "status": "exact_bounded_phase2b_fragment_pass",
        "profile": "source d3 five-round Z-memory, X-biased ratio10",
        "source_circuit_resources": {"qubits": source_counts[0], "detectors": source_counts[1],
                                      "observables": source_counts[2]},
        "selected_noise_instruction_index": instruction_index,
        "selected_target_pairs": [{"pair_index": i,
                                   "qubits": [int(targets[2*i].value), int(targets[2*i+1].value)]}
                                  for i in selected_pairs],
        "native_categorical_domain": 16,
        "fragment_fault_locations": len(locations),
        "touched_detector_ids": touched,
        "compact_detector_count": model.detector_count,
        "baseline_detector_observable": baseline,
        "outcome_effects_by_location": [
            {outcome.label: {"probability": outcome.probability,
                             "detector_mask_compact": outcome.detector_mask,
                             "observable_mask": outcome.observable_mask}
             for outcome in loc.outcomes} for loc in locations
        ],
        "combined_fault_xor_checks": combined_checks,
        "enumerated_categorical_assignments": model.configuration_count,
        "reachable_syndromes": len(reference.joint),
        "exact_joint_max_abs_error": max_mass_error,
        "induced_width": max_width,
        "max_intermediate_factor_entries": max_entries,
        "factor_entry_cap": 1_000_000,
        "reachable_syndrome_joint_masses": syndrome_rows,
        "stochastic_qshift_shots_generated": 0,
        "elapsed_seconds": time.perf_counter() - start,
        "scope": "one local layer fragment only; all other stochastic circuit locations are identity; not a full-circuit decoder benchmark",
    }
    path = HERE / "categorical_phase2b_fragment_results.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {path}; {model.configuration_count} configurations, {model.detector_count} touched detectors, "
          f"max error={max_mass_error:.3g}, width={max_width}, entries={max_entries}")


if __name__ == "__main__":
    main()
