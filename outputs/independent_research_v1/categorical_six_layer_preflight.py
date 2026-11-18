"""Map six categorical layers and estimate sparse-state resource bounds."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from noise_model import PAULI_PAIRS, build_circuit  # noqa: E402
from categorical_phase2b_fragment import deterministic_circuit, sample_det_obs  # noqa: E402
MAX_STATES = 1_000_000
MAX_SPARSE_OPERATIONS = 300_000_000


def main() -> None:
    start = time.perf_counter()
    source = build_circuit("z", "x_biased", distance=3, rounds=5,
                           bias_ratio=10).flattened()
    channel_layers = [(i, inst) for i, inst in enumerate(source)
                      if inst.name == "PAULI_CHANNEL_2"]
    selected = channel_layers[-6:]
    if len(selected) != 6:
        raise RuntimeError("source circuit does not have six PAULI_CHANNEL_2 layers")
    if any(len(inst.targets_copy()) != 12 for _, inst in selected):
        raise RuntimeError("each selected layer must have six two-qubit pairs")
    events = []
    for instruction_index, instruction in selected:
        targets = instruction.targets_copy()
        probabilities = [float(p) for p in instruction.gate_args_copy()]
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
            effects.append([forced[0] ^ baseline[0], forced[1] ^ baseline[1]])
        raw_effects.append(effects)
    touched = sorted({det for effects in raw_effects for dmask, _ in effects
                      for det in range(source.num_detectors) if (dmask >> det) & 1})
    remap = {old: new for new, old in enumerate(touched)}
    compact_events = []
    for event, effects in zip(events, raw_effects, strict=True):
        compact_outcomes = []
        for label, probability, (raw_dmask, raw_omask) in zip(
                ("II", *PAULI_PAIRS),
                (1.0-sum(event["probabilities"]), *event["probabilities"]),
                effects, strict=True):
            mask = sum(1 << remap[d] for d in touched if (raw_dmask >> d) & 1)
            compact_outcomes.append({
                "label": label, "probability": probability,
                "detector_mask": mask, "observable_mask": raw_omask & 1,
            })
        compact_events.append({**event, "outcomes": compact_outcomes})
    signature_blob = json.dumps(compact_events, sort_keys=True, separators=(",", ":"))
    bits = len(touched) + 1
    states_bound = 1 << bits
    sparse_ops_bound = len(events) * states_bound * 16
    fwht_ops_bound = (len(events) + 1) * states_bound * bits
    passed = states_bound <= MAX_STATES and sparse_ops_bound <= MAX_SPARSE_OPERATIONS
    output = {
        "status": "preflight_passed" if passed else "preflight_runtime_stop",
        "source_profile": "d3 five-round Z-memory, X-biased ratio10",
        "source_resources": {"qubits": source.num_qubits,
                             "detectors": source.num_detectors,
                             "observables": source.num_observables},
        "selected_instruction_indices": [i for i, _ in selected],
        "fault_locations": len(events),
        "categorical_domain_per_location": 16,
        "configuration_count_if_bruteforced": 16**len(events),
        "touched_detector_ids": touched,
        "compact_detector_count": len(touched),
        "joint_signature_state_upper_bound": states_bound,
        "sparse_dp_transition_upper_bound": sparse_ops_bound,
        "walsh_transform_operation_upper_bound": fwht_ops_bound,
        "state_cap": MAX_STATES,
        "sparse_operation_cap": MAX_SPARSE_OPERATIONS,
        "compact_event_signatures_sha256": hashlib.sha256(signature_blob.encode()).hexdigest(),
        "events": compact_events,
        "stochastic_samples_generated": 0,
        "elapsed_seconds": time.perf_counter()-start,
        "inference_started": False,
    }
    path = HERE / "categorical_six_layer_preflight.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(path),
                      "fault_locations": len(events), "touched_detectors": len(touched),
                      "state_bound": states_bound, "sparse_ops_bound": sparse_ops_bound,
                      "elapsed_seconds": output["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
