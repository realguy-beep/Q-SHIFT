"""Map one shortest graphlike undetectable error to an exact circuit-pattern bound."""
from __future__ import annotations

import itertools
import json
import math
import re
import sys
import time
from pathlib import Path

import stim

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xzzx_basis_factorial import make_circuit

CONDITIONS = (("css", "x"), ("xzzx", "x"))
DISTANCE = 3
ROUNDS = 5
BIAS_RATIO = 10.0
P = 0.003
DEM_THRESHOLD = 0.0018
REFERENCE = {
    ("css", "x"): {"failures": 656, "shots": 500_000, "source": "xzzx_basis_factorial_scale_results.json"},
    ("xzzx", "x"): {"failures": 2479, "shots": 500_000, "source": "xzzx_basis_factorial_scale_results.json"},
}
PAULI2_ORDER = ("IX", "IY", "IZ", "XI", "XX", "XY", "XZ", "YI", "YX", "YY", "YZ", "ZI", "ZX", "ZY", "ZZ")


def noise_event_table(circuit: stim.Circuit) -> dict[tuple[int, int], dict]:
    table = {}
    for instruction_offset, instruction in enumerate(circuit.flattened()):
        name = instruction.name
        targets = instruction.targets_copy()
        args = [float(x) for x in instruction.gate_args_copy()]
        if name == "PAULI_CHANNEL_2":
            if len(targets) % 2 or len(args) != 15:
                raise RuntimeError("unexpected PAULI_CHANNEL_2 structure")
            probs = dict(zip(PAULI2_ORDER, args, strict=True))
            for start in range(0, len(targets), 2):
                table[(instruction_offset, start)] = {"gate": name, "probabilities": probs, "identity_probability": 1.0 - sum(args)}
        elif name == "PAULI_CHANNEL_1":
            if len(args) != 3:
                raise RuntimeError("unexpected PAULI_CHANNEL_1 structure")
            probs = dict(zip(("X", "Y", "Z"), args, strict=True))
            for start in range(len(targets)):
                table[(instruction_offset, start)] = {"gate": name, "probabilities": probs, "identity_probability": 1.0 - sum(args)}
        elif name in ("X_ERROR", "Y_ERROR", "Z_ERROR", "M_ERROR"):
            if len(args) != 1:
                raise RuntimeError(f"unexpected {name} argument structure")
            outcome = {"X_ERROR": "X", "Y_ERROR": "Y", "Z_ERROR": "Z", "M_ERROR": "M"}[name]
            for start in range(len(targets)):
                table[(instruction_offset, start)] = {"gate": name, "probabilities": {outcome: args[0]}, "identity_probability": 1.0 - args[0]}
    if not table:
        raise RuntimeError("no stochastic circuit events found")
    if any(row["identity_probability"] <= 0 for row in table.values()):
        raise RuntimeError("nonpositive identity probability")
    return table


def location_event(location, event_table: dict[tuple[int, int], dict]) -> dict:
    if len(location.stack_frames) != 1:
        raise RuntimeError("nested repeated circuit locations are unsupported")
    frame = location.stack_frames[0]
    key = (int(frame.instruction_offset), int(location.instruction_targets.target_range_start))
    if key not in event_table:
        raise RuntimeError(f"physical location {key} has no independent noise event")
    row = event_table[key]
    gtcs = list(location.instruction_targets.targets_in_range)
    qubits = [int(x.gate_target.qubit_value) for x in gtcs]
    if not qubits:
        raise RuntimeError(f"noise location {key} has no qubit target")
    pauli_by_qubit = {}
    for factor in location.flipped_pauli_product:
        target = factor.gate_target
        pauli_by_qubit[int(target.qubit_value)] = str(target.pauli_type) or "I"
    if row["gate"] == "PAULI_CHANNEL_2":
        outcome = "".join(pauli_by_qubit.get(q, "I") for q in qubits)
    elif row["gate"] == "PAULI_CHANNEL_1":
        outcome = pauli_by_qubit.get(qubits[0], "I")
    elif row["gate"] == "M_ERROR":
        outcome = "M"
    else:
        outcome = row["gate"][0]
    probability = float(row["probabilities"].get(outcome, 0.0))
    if probability <= 0:
        raise RuntimeError(f"zero/unmapped channel probability for {key}: {outcome}")
    return {
        "key": key,
        "gate": row["gate"],
        "outcome": outcome,
        "probability": probability,
        "tick_offset": int(location.tick_offset),
        "instruction_targets": str(location.instruction_targets),
        "flipped_pauli_product": str(location.flipped_pauli_product),
    }


def parity_of_graphlike_path(explained_errors) -> tuple[set[int], set[int]]:
    detectors, observables = set(), set()
    for error in explained_errors:
        for target_with_coords in error.dem_error_terms:
            target = target_with_coords.dem_target
            if target.is_separator():
                continue
            if target.is_relative_detector_id():
                value = int(target.val)
                detectors.symmetric_difference_update((value,))
            elif target.is_logical_observable_id():
                value = int(target.val)
                observables.symmetric_difference_update((value,))
    return detectors, observables


def best_physical_pattern(explained_errors, event_table) -> list[dict]:
    options = []
    for error in explained_errors:
        candidates = {}
        for location in error.circuit_error_locations:
            event = location_event(location, event_table)
            candidates[(event["key"], event["outcome"])] = event
        if not candidates:
            raise RuntimeError("a graphlike event has no physical circuit realization")
        options.append(list(candidates.values()))

    best, best_log_probability = None, -math.inf

    def visit(i: int, used: set, chosen: list[dict]) -> None:
        nonlocal best, best_log_probability
        if i == len(options):
            if len({row["key"] for row in chosen}) != len(chosen):
                return
            value = sum(math.log(row["probability"]) - math.log(event_table[row["key"]]["identity_probability"]) for row in chosen)
            if value > best_log_probability:
                best, best_log_probability = list(chosen), value
            return
        for candidate in options[i]:
            if candidate["key"] in used:
                continue
            used.add(candidate["key"])
            chosen.append(candidate)
            visit(i + 1, used, chosen)
            chosen.pop()
            used.remove(candidate["key"])

    visit(0, set(), [])
    if best is None:
        raise RuntimeError("no nonconflicting physical realization of shortest graphlike path")
    return best


def analyze(code: str) -> dict:
    circuit = make_circuit(code, "x", DISTANCE, ROUNDS, BIAS_RATIO)
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=DEM_THRESHOLD)
    event_table = noise_event_table(circuit)
    errors = circuit.shortest_graphlike_error(ignore_ungraphlike_errors=True)
    if not errors:
        raise RuntimeError(f"no graphlike logical error found for {code}")
    det, obs = parity_of_graphlike_path(errors)
    if det or obs != {0}:
        raise RuntimeError(f"shortest path parity is not undetectable L0: detectors={det}, logical={obs}")
    selected = best_physical_pattern(errors, event_table)
    keys = [tuple(row["key"]) for row in selected]
    if len(set(keys)) != len(keys):
        raise RuntimeError("physical pattern reuses a mutually-exclusive noise event")
    log_identity = sum(math.log(row["identity_probability"]) for row in event_table.values())
    log_pattern = log_identity + sum(
        math.log(row["probability"]) - math.log(event_table[row["key"]]["identity_probability"])
        for row in selected
    )
    lower_log = min(log_identity, log_pattern)
    lower_bound = math.exp(lower_log)
    ref = REFERENCE[(code, "x")]
    reference_ler = ref["failures"] / ref["shots"]
    return {
        "code": code,
        "memory_basis": "x",
        "distance": DISTANCE,
        "rounds": ROUNDS,
        "physical_qubits": int(circuit.num_qubits),
        "detectors": int(circuit.num_detectors),
        "dem_threshold": DEM_THRESHOLD,
        "dem_mechanisms": len([i for i in dem.flattened() if i.type == "error"]),
        "independent_physical_noise_events": len(event_table),
        "shortest_graphlike_fault_count": len(errors),
        "shortest_path_detector_parity": sorted(det),
        "shortest_path_logical_parity": sorted(obs),
        "selected_physical_faults": selected,
        "all_identity_pattern_probability": math.exp(log_identity),
        "selected_undetectable_pattern_probability": math.exp(log_pattern),
        "decoder_independent_logical_error_lower_bound": lower_bound,
        "development_reference_ler": reference_ler,
        "lower_bound_over_reference_ler": lower_bound / reference_ler,
        "reference_source": ref["source"],
        "scope": "one exact circuit fault pattern and identity ambiguity; shortest graphlike path ignores ungraphlike mechanisms; not full error floor",
    }


def main() -> None:
    started = time.perf_counter()
    rows = [analyze(code) for code, _ in CONDITIONS]
    output = {
        "status": "graphlike_exact_pattern_lower_bound",
        "conditions": rows,
        "elapsed_seconds": time.perf_counter() - started,
        "stochastic_samples_generated": 0,
        "scope": "deterministic decoder-independent lower bound from one exact physical pattern per circuit",
    }
    path = HERE / "graphlike_fault_floor_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "rows": [{"code":r['code'],"fault_count":r['shortest_graphlike_fault_count'],"lower_bound":r['decoder_independent_logical_error_lower_bound'],"ratio_to_reference":r['lower_bound_over_reference_ler']} for r in rows],"elapsed_seconds":output['elapsed_seconds'],"output":str(path)},indent=2))


if __name__ == "__main__":
    main()
