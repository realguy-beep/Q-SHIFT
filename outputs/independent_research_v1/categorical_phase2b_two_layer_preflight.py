"""Scope-only min-fill growth estimate for the last two channel layers."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from categorical_elimination import estimate_factor_growth  # noqa: E402
from categorical_phase2b_fragment import deterministic_circuit, sample_det_obs  # noqa: E402
from categorical_reference import CategoricalLocation, CategoricalModel, FaultOutcome  # noqa: E402
from noise_model import PAULI_PAIRS, build_circuit  # noqa: E402

CAP = 1_000_000


def main() -> None:
    started = time.perf_counter()
    source = build_circuit("z", "x_biased", distance=3, rounds=5, bias_ratio=10).flattened()
    channel_layers = [(i, ins) for i, ins in enumerate(source) if ins.name == "PAULI_CHANNEL_2"]
    selected_layers = channel_layers[-2:]
    if len(selected_layers) != 2 or any(len(ins.targets_copy()) != 12 for _, ins in selected_layers):
        raise RuntimeError("expected two final six-pair PAULI_CHANNEL_2 layers")
    events = []
    for instruction_index, instruction in selected_layers:
        targets = instruction.targets_copy()
        probabilities = [float(p) for p in instruction.gate_args_copy()]
        for pair_index in range(6):
            events.append({
                "instruction_index": instruction_index,
                "pair_index": pair_index,
                "qubits": [int(targets[2*pair_index].value), int(targets[2*pair_index+1].value)],
                "probabilities": probabilities,
            })

    baseline = sample_det_obs(deterministic_circuit(source, {}))
    raw_effects = []
    for event in events:
        outcomes = []
        key = (event["instruction_index"], event["pair_index"])
        for label in ("II", *PAULI_PAIRS):
            forced = baseline if label == "II" else sample_det_obs(deterministic_circuit(source, {key: label}))
            outcomes.append((forced[0] ^ baseline[0], forced[1] ^ baseline[1]))
        raw_effects.append(outcomes)

    touched = sorted({det for outcomes in raw_effects for dmask, _ in outcomes
                      for det in range(source.num_detectors) if (dmask >> det) & 1})
    if not touched:
        raise RuntimeError("two-layer fragment has no detector support")
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
    strategies = ("weighted_min_fill", "weighted_min_product", "min_fill", "min_degree",
                  "natural", "reverse_natural", "location_carry_interleaved",
                  "carry_location_interleaved")
    ordering_estimates = [estimate_factor_growth(model, strategy) for strategy in strategies]
    growth = ordering_estimates[0]
    best = min(ordering_estimates,
               key=lambda item: (item["max_intermediate_factor_entries"], item["induced_width"]))
    result = {
        "status": "two_layer_width_preflight_complete",
        "profile": "source d3 five-round Z-memory; X-biased ratio10",
        "selected_instruction_indices": [i for i, _ in selected_layers],
        "selected_channel_pairs": events,
        "fault_locations": len(locations),
        "categorical_domain_per_location": 16,
        "configuration_count_if_bruteforced": model.configuration_count,
        "source_detectors": source.num_detectors,
        "touched_detector_ids": touched,
        "compact_detector_count": len(touched),
        "factor_growth_estimate": growth,
        "alternate_ordering_scope_audit": ordering_estimates[1:],
        "best_tested_ordering": {"strategy": best["strategy"],
                                  "induced_width": best["induced_width"],
                                  "max_intermediate_factor_entries": best["max_intermediate_factor_entries"]},
        "factor_entry_cap": CAP,
        "cap_passed": growth["max_intermediate_factor_entries"] <= CAP,
        "any_tested_ordering_passed_cap": any(
            item["max_intermediate_factor_entries"] <= CAP for item in ordering_estimates),
        "stochastic_qshift_shots_generated": 0,
        "elapsed_seconds": time.perf_counter() - started,
        "scope": "last two adjacent PAULI_CHANNEL_2 layers only; factor scopes and weighted min-fill; no inference tables allocated",
    }
    path = HERE / "categorical_phase2b_two_layer_preflight.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {path}; width={growth['induced_width']}, "
          f"largest factor={growth['max_intermediate_factor_entries']}, cap passed={result['cap_passed']}")


if __name__ == "__main__":
    main()
