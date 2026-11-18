"""Exact XOR-convolution cross-check for all six categorical pairs in one layer."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from categorical_elimination import exact_joint_mass  # noqa: E402
from categorical_phase2b_fragment import deterministic_circuit, sample_det_obs  # noqa: E402
from categorical_reference import CategoricalLocation, CategoricalModel, FaultOutcome  # noqa: E402
from noise_model import PAULI_PAIRS, build_circuit  # noqa: E402

CAP = 1_000_000


def exact_xor_convolution(model: CategoricalModel) -> dict[int, tuple[float, float]]:
    """Exact sparse DP over aggregate XOR syndrome/logical states."""
    states = {(0, 0): 1.0}
    for location in model.locations:
        next_states: dict[tuple[int, int], float] = {}
        for (syndrome, logical), mass in states.items():
            for outcome in location.outcomes:
                key = (syndrome ^ outcome.detector_mask,
                       logical ^ (outcome.observable_mask & 1))
                next_states[key] = next_states.get(key, 0.0) + mass * outcome.probability
        states = next_states
    joint: dict[int, list[float]] = {}
    for (syndrome, logical), probability in states.items():
        joint.setdefault(syndrome, [0.0, 0.0])[logical] += probability
    return {s: tuple(v) for s, v in joint.items()}


def main() -> None:
    started = time.perf_counter()
    preflight = json.loads((HERE / "categorical_phase2b_six_location_preflight.json").read_text())
    if not preflight["cap_passed"] or preflight["factor_growth_estimate"]["max_intermediate_factor_entries"] > CAP:
        raise RuntimeError("six-location structural preflight did not pass")

    source = build_circuit("z", "x_biased", distance=3, rounds=5, bias_ratio=10).flattened()
    layers = [(i, ins) for i, ins in enumerate(source) if ins.name == "PAULI_CHANNEL_2"]
    instruction_index, instruction = layers[-1]
    targets = instruction.targets_copy()
    probabilities = [float(p) for p in instruction.gate_args_copy()]
    identity = 1.0 - sum(probabilities)
    baseline = sample_det_obs(deterministic_circuit(source, {}))

    raw_effects = []
    locations = []
    for pair_index in range(6):
        effects = []
        for label in ("II", *PAULI_PAIRS):
            forced = baseline if label == "II" else sample_det_obs(
                deterministic_circuit(source, {(instruction_index, pair_index): label}))
            effects.append((forced[0] ^ baseline[0], forced[1] ^ baseline[1]))
        raw_effects.append(effects)

    touched = sorted({det for effects in raw_effects for detector_mask, _ in effects
                      for det in range(source.num_detectors) if (detector_mask >> det) & 1})
    remap = {old: new for new, old in enumerate(touched)}
    for pair_index, effects in enumerate(raw_effects):
        outcomes = []
        for label, probability, (raw_dmask, raw_omask) in zip(
                ("II", *PAULI_PAIRS), (identity, *probabilities), effects, strict=True):
            compact = sum(1 << remap[d] for d in touched if (raw_dmask >> d) & 1)
            outcomes.append(FaultOutcome(label, probability, compact, raw_omask & 1))
        locations.append(CategoricalLocation(f"final_layer_pair_{pair_index}", tuple(outcomes), "II"))
    model = CategoricalModel(len(touched), 1, tuple(locations))
    model.validate()

    combined_checks = 0
    for seed in range(512):
        outcome_indices = tuple((seed * (2*i + 3) + 11*i) % 16 for i in range(6))
        selected = {}
        expected_d = expected_l = 0
        for pair_index, outcome_index in enumerate(outcome_indices):
            label = ("II", *PAULI_PAIRS)[outcome_index]
            selected[(instruction_index, pair_index)] = label
            expected_d ^= raw_effects[pair_index][outcome_index][0]
            expected_l ^= raw_effects[pair_index][outcome_index][1]
        got_d, got_l = sample_det_obs(deterministic_circuit(source, selected))
        if (got_d ^ baseline[0], got_l ^ baseline[1]) != (expected_d, expected_l):
            raise RuntimeError(f"combined-fault XOR check failed at case {seed}")
        combined_checks += 1

    exact = exact_xor_convolution(model)
    ve = {}
    max_error = 0.0
    max_width = 0
    max_entries = 1
    for syndrome, reference_pair in exact.items():
        values = []
        for logical in range(2):
            value, stats = exact_joint_mass(model, syndrome, logical, max_factor_entries=CAP)
            values.append(value)
            max_width = max(max_width, stats.induced_width)
            max_entries = max(max_entries, stats.max_factor_entries)
            if max_entries > CAP:
                raise RuntimeError("actual VE intermediate exceeded the fixed cap")
        error = max(abs(values[l] - reference_pair[l]) for l in range(2))
        max_error = max(max_error, error)
        if error > 1e-10:
            raise RuntimeError(f"XOR-convolution/VE mismatch at syndrome {syndrome}: {error}")
        ve[syndrome] = tuple(values)

    total = sum(sum(pair) for pair in exact.values())
    map_risk = sum(min(pair) for pair in exact.values())
    row = {
        "status": "exact_six_location_phase2b_layer_pass",
        "source_profile": "d3 five-round Z-memory; X-biased ratio10",
        "source_resources": {"qubits": source.num_qubits, "detectors": source.num_detectors,
                              "observables": source.num_observables},
        "instruction_index": instruction_index,
        "pair_qubits": [[int(targets[2*i].value), int(targets[2*i+1].value)] for i in range(6)],
        "categorical_domain": 16,
        "locations": len(locations),
        "configuration_count": model.configuration_count,
        "touched_detector_ids": touched,
        "compact_detector_count": len(touched),
        "combined_fault_xor_checks": combined_checks,
        "reachable_syndromes": len(exact),
        "joint_probability_total": total,
        "joint_mass_max_abs_error_vs_xor_convolution": max_error,
        "max_posterior_abs_error": max(
            abs(ve[s][1] / sum(ve[s]) - exact[s][1] / sum(exact[s]))
            for s in exact if sum(exact[s]) > 0),
        "map_ler_for_isolated_layer": map_risk,
        "induced_width": max_width,
        "max_intermediate_factor_entries": max_entries,
        "preflight_predicted_width": preflight["factor_growth_estimate"]["induced_width"],
        "preflight_predicted_max_entries": preflight["factor_growth_estimate"]["max_intermediate_factor_entries"],
        "elapsed_seconds": time.perf_counter() - started,
        "stochastic_qshift_shots_generated": 0,
        "scope": "all six categorical pairs in one final-round layer; all other stochastic locations are identity",
    }
    path = HERE / "categorical_phase2b_six_location_results.json"
    path.write_text(json.dumps(row, indent=2) + "\n")
    print(f"Wrote {path}; {len(exact)} syndromes, max error={max_error:.3g}, "
          f"width={max_width}, entries={max_entries}, map LER={map_risk:.6g}")


if __name__ == "__main__":
    main()
