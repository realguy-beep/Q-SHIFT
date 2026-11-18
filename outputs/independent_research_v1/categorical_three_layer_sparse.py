"""Exact sparse-DP and Walsh-XOR posterior for 18 native fault variables."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from categorical_phase2b_fragment import deterministic_circuit, sample_det_obs
from categorical_reference import CategoricalLocation, CategoricalModel, FaultOutcome
from noise_model import PAULI_PAIRS, build_circuit

MAX_STATES = 1_000_000
MAX_SPARSE_OPERATIONS = 100_000_000
COMBINED_CHECKS = 512


def sparse_dp(locations: tuple[CategoricalLocation, ...], state_cap: int):
    states = {(0, 0): 1.0}
    operations = 0
    max_states = 1
    for location in locations:
        nxt = {}
        for (syndrome, logical), mass in states.items():
            for outcome in location.outcomes:
                key = (syndrome ^ outcome.detector_mask,
                       logical ^ (outcome.observable_mask & 1))
                nxt[key] = nxt.get(key, 0.0) + mass * outcome.probability
                operations += 1
        if len(nxt) > state_cap:
            raise RuntimeError(f"sparse DP exceeded state cap: {len(nxt)}")
        states = nxt
        max_states = max(max_states, len(states))
    return states, operations, max_states


def fwht(values: np.ndarray) -> np.ndarray:
    out = values.astype(np.float64, copy=True)
    n = len(out)
    if n == 0 or n & (n - 1):
        raise ValueError("Walsh-Hadamard vector length must be a positive power of two")
    half = 1
    while half < n:
        blocks = out.reshape(-1, 2 * half)
        left = blocks[:, :half].copy()
        right = blocks[:, half:].copy()
        blocks[:, :half] = left + right
        blocks[:, half:] = left - right
        half *= 2
    return out


def walsh_convolution(locations: tuple[CategoricalLocation, ...],
                      detector_count: int) -> tuple[np.ndarray, int]:
    nbits = detector_count + 1
    nstates = 1 << nbits
    spectrum = np.ones(nstates, dtype=np.float64)
    for location in locations:
        factor = np.zeros(nstates, dtype=np.float64)
        for outcome in location.outcomes:
            index = outcome.detector_mask | ((outcome.observable_mask & 1) << detector_count)
            factor[index] += outcome.probability
        spectrum *= fwht(factor)
    # The unnormalized Walsh transform is self-inverse up to a factor N,
    # independent of the number of convolved location distributions.
    distribution = fwht(spectrum) / nstates
    operations = len(locations) * nstates * nbits + nstates * nbits
    return distribution, operations


def main() -> None:
    started = time.perf_counter()
    preflight = json.loads((HERE / "categorical_three_layer_preflight.json").read_text())
    if preflight["status"] != "preflight_passed":
        raise RuntimeError("three-layer preflight did not pass")
    if (preflight["joint_signature_state_upper_bound"] > MAX_STATES
            or preflight["sparse_dp_transition_upper_bound"] > MAX_SPARSE_OPERATIONS):
        raise RuntimeError("preflight exceeds fixed sparse caps")

    source = build_circuit("z", "x_biased", distance=3, rounds=5,
                           bias_ratio=10).flattened()
    baseline = sample_det_obs(deterministic_circuit(source, {}))
    events = preflight["events"]
    locations = []
    raw_effect_lookup = []
    for event in events:
        outcome_records = event["outcomes"]
        outcomes = tuple(FaultOutcome(
            record["label"], float(record["probability"]),
            int(record["detector_mask"]), int(record["observable_mask"]))
            for record in outcome_records)
        locations.append(CategoricalLocation(
            f"layer_{event['instruction_index']}_pair_{event['pair_index']}",
            outcomes, "II"))
        raw_effect_lookup.append(outcome_records)
    model = CategoricalModel(preflight["compact_detector_count"], 1, tuple(locations))
    model.validate()

    combined_checks = 0
    for case in range(COMBINED_CHECKS):
        selected = {}
        expected_d = expected_l = 0
        for i, event in enumerate(events):
            index = (case * (2*i + 3) + 11*i) % 16
            label = raw_effect_lookup[i][index]["label"]
            selected[(event["instruction_index"], event["pair_index"])] = label
            expected_d ^= int(raw_effect_lookup[i][index]["detector_mask"])
            expected_l ^= int(raw_effect_lookup[i][index]["observable_mask"])
        actual_d, actual_l = sample_det_obs(deterministic_circuit(source, selected))
        remap = preflight["touched_detector_ids"]
        compact_actual = sum(1 << i for i, detector_id in enumerate(remap)
                             if (actual_d ^ baseline[0]) >> detector_id & 1)
        compact_expected = expected_d
        if (compact_actual, actual_l ^ baseline[1]) != (compact_expected, expected_l):
            raise RuntimeError(f"three-layer forced-fault XOR check failed at case {case}")
        combined_checks += 1

    sparse, sparse_operations, max_states = sparse_dp(model.locations, MAX_STATES)
    if sparse_operations > MAX_SPARSE_OPERATIONS:
        raise RuntimeError("sparse DP exceeded fixed operation cap")
    walsh, walsh_operations = walsh_convolution(model.locations, model.detector_count)
    dense_sparse = np.zeros_like(walsh)
    for (syndrome, logical), mass in sparse.items():
        dense_sparse[syndrome | (logical << model.detector_count)] = mass
    max_error = float(np.max(np.abs(dense_sparse - walsh)))
    min_walsh_mass = float(np.min(walsh))
    if max_error > 1e-12:
        raise RuntimeError(f"sparse DP / Walsh convolution mismatch: {max_error}")
    if min_walsh_mass < -1e-12:
        raise RuntimeError(f"Walsh convolution has material negative mass: {min_walsh_mass}")
    total = float(sparse and sum(sparse.values()))
    if abs(total - 1.0) > 1e-12:
        raise RuntimeError(f"sparse joint mass does not normalize: {total}")
    joint = {}
    for (syndrome, logical), mass in sparse.items():
        joint.setdefault(syndrome, [0.0, 0.0])[logical] += mass
    map_risk = float(sum(min(pair) for pair in joint.values()))
    ordered_joint = [[s, pair[0], pair[1]] for s, pair in sorted(joint.items())]
    joint_digest = hashlib.sha256(json.dumps(ordered_joint, separators=(",", ":")).encode()).hexdigest()
    output = {
        "status": "exact_three_layer_sparse_and_walsh_pass",
        "source": "d3 five-round Z-memory, X-biased ratio10; final three PAULI_CHANNEL_2 layers only",
        "source_resources": {"qubits": source.num_qubits, "detectors": source.num_detectors,
                             "observables": source.num_observables},
        "selected_instruction_indices": preflight["selected_instruction_indices"],
        "fault_locations": len(locations), "categorical_domain_per_location": 16,
        "configuration_count_if_bruteforced": 16**len(locations),
        "touched_detector_ids": preflight["touched_detector_ids"],
        "compact_detector_count": model.detector_count,
        "reachable_joint_syndrome_logical_states": len(sparse),
        "reachable_syndromes": len(joint),
        "joint_probability_total": total,
        "max_abs_mass_error_sparse_dp_vs_walsh": max_error,
        "min_walsh_mass_before_roundoff_clamp": min_walsh_mass,
        "combined_fault_xor_checks": combined_checks,
        "max_sparse_states": max_states,
        "sparse_dp_transitions": sparse_operations,
        "walsh_transform_operations": walsh_operations,
        "joint_mass_sha256": joint_digest,
        "isolated_three_layer_map_risk": map_risk,
        "reachable_joint_masses_by_syndrome": ordered_joint,
        "elapsed_seconds": time.perf_counter() - started,
        "stochastic_samples_generated": 0,
        "scope": "exact posterior for 18 final-layer categorical locations; all other stochastic circuit locations are identity; not a full-circuit decoder result",
    }
    path = HERE / "categorical_three_layer_sparse_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(path),
                      "states": len(sparse), "syndromes": len(joint),
                      "max_error": max_error, "map_risk": map_risk,
                      "elapsed_seconds": output["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
