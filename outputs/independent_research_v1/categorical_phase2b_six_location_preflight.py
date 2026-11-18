"""Scope-only min-fill preflight for all six pair channels in the final layer."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from categorical_elimination import estimate_factor_growth
from categorical_phase2b_fragment import sample_det_obs, deterministic_circuit
from categorical_reference import CategoricalLocation, CategoricalModel, FaultOutcome
from noise_model import PAULI_PAIRS, build_circuit

CAP = 1_000_000


def main() -> None:
    start = time.perf_counter()
    source = build_circuit("z", "x_biased", distance=3, rounds=5, bias_ratio=10).flattened()
    layers = [(i, ins) for i, ins in enumerate(source) if ins.name == "PAULI_CHANNEL_2"]
    instruction_index, instruction = layers[-1]
    targets = instruction.targets_copy()
    if len(targets) != 12:
        raise RuntimeError(f"expected six independent target pairs, got {len(targets)//2}")
    probabilities = [float(p) for p in instruction.gate_args_copy()]
    identity = 1.0 - sum(probabilities)
    baseline = sample_det_obs(deterministic_circuit(source, {}))
    locations = []
    raw_effects = []
    for pair_index in range(6):
        outcomes = []
        for label in ("II", *PAULI_PAIRS):
            forced = baseline if label == "II" else sample_det_obs(
                deterministic_circuit(source, {(instruction_index, pair_index): label}))
            outcomes.append((forced[0] ^ baseline[0], forced[1] ^ baseline[1]))
        raw_effects.append(outcomes)
    touched = sorted({det for outcomes in raw_effects for dmask, _ in outcomes
                      for det in range(source.num_detectors) if (dmask >> det) & 1})
    if not touched:
        raise RuntimeError("final layer has no detector support; stop preflight")
    remap = {old: new for new, old in enumerate(touched)}
    for pair_index, outcomes in enumerate(raw_effects):
        loc_outcomes = []
        for label, probability, (raw_dmask, raw_omask) in zip(
                ("II", *PAULI_PAIRS), (identity, *probabilities), outcomes, strict=True):
            compact = sum(1 << remap[d] for d in touched if (raw_dmask >> d) & 1)
            loc_outcomes.append(FaultOutcome(label, probability, compact, raw_omask & 1))
        locations.append(CategoricalLocation(f"final_layer_pair_{pair_index}", tuple(loc_outcomes), "II"))
    model = CategoricalModel(len(touched), 1, tuple(locations))
    model.validate()
    growth = estimate_factor_growth(model)
    pair_ids = [{"pair_index": i, "qubits": [int(targets[2*i].value), int(targets[2*i+1].value)]}
                for i in range(6)]
    result = {
        "status": "six_location_width_preflight_complete",
        "selected_instruction_index": instruction_index,
        "selected_target_pairs": pair_ids,
        "categorical_domain_per_location": 16,
        "fault_locations": len(locations),
        "source_detectors": source.num_detectors,
        "touched_detector_ids": touched,
        "compact_detector_count": model.detector_count,
        "exact_assignments_if_bruteforced": model.configuration_count,
        "factor_growth_estimate": growth,
        "factor_entry_cap": CAP,
        "cap_passed": growth["max_intermediate_factor_entries"] <= CAP,
        "stochastic_qshift_shots_generated": 0,
        "elapsed_seconds": time.perf_counter() - start,
        "scope": "all six mutually exclusive PAULI_CHANNEL_2 pairs in one final layer; no inference or sampling",
    }
    path = HERE / "categorical_phase2b_six_location_preflight.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {path}; width={growth['induced_width']}, "
          f"max factor={growth['max_intermediate_factor_entries']}, cap passed={result['cap_passed']}")
    if not result["cap_passed"]:
        raise RuntimeError("six-location layer exceeds the one-million-entry cap; do not infer")


if __name__ == "__main__":
    main()
