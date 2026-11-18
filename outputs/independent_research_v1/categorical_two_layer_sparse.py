"""Exact sparse XOR-state inference for 12 native categorical gate faults."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from categorical_phase2b_fragment import deterministic_circuit, sample_det_obs
from categorical_reference import CategoricalLocation, CategoricalModel, FaultOutcome
from noise_model import PAULI_PAIRS, build_circuit

MAX_STATES = 100_000
MAX_OPERATIONS = 10_000_000
COMBINED_CHECKS = 512


def convolve_maps(a: dict[tuple[int, int], float],
                  b: dict[tuple[int, int], float]) -> tuple[dict[tuple[int, int], float], int]:
    out: dict[tuple[int, int], float] = {}
    operations = 0
    for (sa, la), pa in a.items():
        for (sb, lb), pb in b.items():
            key = (sa ^ sb, la ^ lb)
            out[key] = out.get(key, 0.0) + pa * pb
            operations += 1
    return out, operations


def sparse_dp(locations: tuple[CategoricalLocation, ...],
              state_cap: int) -> tuple[dict[tuple[int, int], float], int, int]:
    states = {(0, 0): 1.0}
    operations = 0
    max_states = 1
    for loc in locations:
        nxt: dict[tuple[int, int], float] = {}
        for (syndrome, logical), mass in states.items():
            for outcome in loc.outcomes:
                key = (syndrome ^ outcome.detector_mask,
                       logical ^ (outcome.observable_mask & 1))
                nxt[key] = nxt.get(key, 0.0) + mass * outcome.probability
                operations += 1
        if len(nxt) > state_cap:
            raise RuntimeError(f"sparse DP exceeded state cap: {len(nxt)} > {state_cap}")
        states = nxt
        max_states = max(max_states, len(states))
    return states, operations, max_states


def main() -> None:
    started = time.perf_counter()
    preflight = json.loads((HERE / "categorical_phase2b_two_layer_preflight.json").read_text())
    if preflight["fault_locations"] != 12 or preflight["compact_detector_count"] != 10:
        raise RuntimeError("two-layer structural preflight differs from the declared fragment")
    if preflight["factor_entry_cap"] != 1_000_000 or preflight["cap_passed"]:
        raise RuntimeError("expected the existing dense-VE two-layer cap to fail")

    source = build_circuit("z", "x_biased", distance=3, rounds=5,
                           bias_ratio=10).flattened()
    channel_layers = [(i, inst) for i, inst in enumerate(source)
                      if inst.name == "PAULI_CHANNEL_2"]
    selected_layers = channel_layers[-2:]
    if len(selected_layers) != 2 or any(len(inst.targets_copy()) != 12
                                        for _, inst in selected_layers):
        raise RuntimeError("expected final two six-pair PAULI_CHANNEL_2 instructions")
    events = []
    for instruction_index, inst in selected_layers:
        targets = inst.targets_copy()
        probabilities = [float(p) for p in inst.gate_args_copy()]
        for pair_index in range(6):
            events.append({
                "instruction_index": instruction_index,
                "pair_index": pair_index,
                "qubits": [int(targets[2*pair_index].value),
                           int(targets[2*pair_index+1].value)],
                "probabilities": probabilities,
            })
    baseline = sample_det_obs(deterministic_circuit(source, {}))
    raw_effects = []
    for event in events:
        effects = []
        key = (event["instruction_index"], event["pair_index"])
        for label in ("II", *PAULI_PAIRS):
            forced = baseline if label == "II" else sample_det_obs(
                deterministic_circuit(source, {key: label}))
            effects.append((forced[0] ^ baseline[0], forced[1] ^ baseline[1]))
        raw_effects.append(effects)

    touched = sorted({det for effects in raw_effects for dmask, _ in effects
                      for det in range(source.num_detectors) if (dmask >> det) & 1})
    remap = {old: new for new, old in enumerate(touched)}
    locations = []
    for event, effects in zip(events, raw_effects, strict=True):
        probabilities = event["probabilities"]
        identity = 1.0 - sum(probabilities)
        outcomes = []
        for label, probability, (raw_dmask, raw_omask) in zip(
                ("II", *PAULI_PAIRS), (identity, *probabilities), effects, strict=True):
            compact = sum(1 << remap[d] for d in touched if (raw_dmask >> d) & 1)
            outcomes.append(FaultOutcome(label, probability, compact, raw_omask & 1))
        locations.append(CategoricalLocation(
            f"channel_{event['instruction_index']}_pair_{event['pair_index']}",
            tuple(outcomes), "II"))
    model = CategoricalModel(len(touched), 1, tuple(locations))
    model.validate()

    state_bound = 1 << (len(touched) + 1)
    operation_bound = len(locations) * state_bound * 16 + state_bound * state_bound
    if state_bound > MAX_STATES or operation_bound > MAX_OPERATIONS:
        output = {
            "status": "sparse_preflight_stopped",
            "fault_locations": len(locations), "touched_detectors": touched,
            "compact_detector_count": len(touched),
            "upper_bound_joint_states": state_bound,
            "upper_bound_operations": operation_bound,
            "max_states_cap": MAX_STATES, "max_operations_cap": MAX_OPERATIONS,
            "inference_attempted": False, "stochastic_samples_generated": 0,
        }
        (HERE / "categorical_two_layer_sparse_results.json").write_text(
            json.dumps(output, indent=2) + "\n")
        print(json.dumps(output, indent=2))
        return

    combined_checks = 0
    for case in range(COMBINED_CHECKS):
        indices = tuple((case * (2*i + 3) + 11*i) % 16 for i in range(len(events)))
        selected = {}
        expected_d = expected_l = 0
        for i, outcome_index in enumerate(indices):
            label = ("II", *PAULI_PAIRS)[outcome_index]
            selected[(events[i]["instruction_index"], events[i]["pair_index"])] = label
            expected_d ^= raw_effects[i][outcome_index][0]
            expected_l ^= raw_effects[i][outcome_index][1]
        actual_d, actual_l = sample_det_obs(deterministic_circuit(source, selected))
        if (actual_d ^ baseline[0], actual_l ^ baseline[1]) != (expected_d, expected_l):
            raise RuntimeError(f"combined-fault XOR map mismatch at case {case}")
        combined_checks += 1

    direct, direct_ops, direct_max_states = sparse_dp(model.locations, MAX_STATES)
    left, left_ops, left_states = sparse_dp(model.locations[:6], MAX_STATES)
    right, right_ops, right_states = sparse_dp(model.locations[6:], MAX_STATES)
    halves, join_ops = convolve_maps(left, right)
    if set(direct) != set(halves):
        raise RuntimeError("direct sparse DP and split-half convolution have different states")
    max_error = max(abs(direct[k] - halves[k]) for k in direct)
    if max_error > 1e-13:
        raise RuntimeError(f"sparse independent constructions disagree: {max_error}")
    if len(direct) > MAX_STATES or direct_ops + join_ops > MAX_OPERATIONS:
        raise RuntimeError("actual sparse computation exceeded fixed operation/state caps")

    joint: dict[int, list[float]] = {}
    for (syndrome, logical), mass in direct.items():
        joint.setdefault(syndrome, [0.0, 0.0])[logical] += mass
    total = sum(sum(v) for v in joint.values())
    map_risk = sum(min(v) for v in joint.values())
    output = {
        "status": "exact_two_layer_sparse_inference_pass",
        "source": "d3 five-round Z-memory, X-biased ratio10; final two PAULI_CHANNEL_2 layers only",
        "source_resources": {"qubits": source.num_qubits, "detectors": source.num_detectors,
                             "observables": source.num_observables},
        "selected_instruction_indices": [i for i, _ in selected_layers],
        "fault_locations": len(locations), "categorical_domain_per_location": 16,
        "configuration_count_if_bruteforced": 16**len(locations),
        "touched_detector_ids": touched, "compact_detector_count": len(touched),
        "reachable_joint_syndrome_logical_states": len(direct),
        "reachable_syndromes": len(joint),
        "joint_probability_total": total,
        "max_abs_mass_error_direct_dp_vs_independent_half_convolution": max_error,
        "combined_fault_xor_checks": combined_checks,
        "max_states_direct_dp": direct_max_states,
        "max_states_half_dp": max(left_states, right_states),
        "direct_dp_transitions": direct_ops,
        "half_convolution_join_operations": join_ops,
        "total_sparse_operations": direct_ops + join_ops,
        "state_cap": MAX_STATES, "operation_cap": MAX_OPERATIONS,
        "dense_ve_comparison": {
            "best_tested_ordering": preflight["best_tested_ordering"],
            "largest_dense_factor_entries": preflight["best_tested_ordering"]["max_intermediate_factor_entries"],
            "dense_cap_passed": False,
        },
        "isolated_two_layer_map_risk": map_risk,
        "elapsed_seconds": time.perf_counter() - started,
        "stochastic_samples_generated": 0,
        "scope": "exact posterior for a 12-location final-two-layer fragment; all other stochastic circuit locations are identity; not a full-circuit decoder result",
    }
    path = HERE / "categorical_two_layer_sparse_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(path),
                      "states": len(direct), "syndromes": len(joint),
                      "max_mass_error": max_error, "operations": direct_ops+join_ops,
                      "map_risk": map_risk, "elapsed_seconds": output["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
