"""Exact vectorized and Walsh inference for the five-layer categorical slice."""
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
from noise_model import PAULI_PAIRS, build_circuit

MAX_STATES = 1_000_000
MAX_VECTOR_UPDATES = 300_000_000
MAX_WALSH_OPERATIONS = 400_000_000
MAX_MEMORY_BYTES = 1 << 30
COMBINED_CHECKS = 512


def fwht(values: np.ndarray) -> np.ndarray:
    out = values.astype(np.float64, copy=True)
    n = len(out)
    half = 1
    while half < n:
        blocks = out.reshape(-1, 2 * half)
        left = blocks[:, :half].copy()
        right = blocks[:, half:2*half].copy()
        blocks[:, :half] = left + right
        blocks[:, half:2*half] = left - right
        half *= 2
    return out


def main() -> None:
    started = time.perf_counter()
    preflight = json.loads((HERE / "categorical_five_layer_preflight.json").read_text())
    if preflight["fault_locations"] != 30 or preflight["compact_detector_count"] != 18:
        raise RuntimeError("stored five-layer signature map has unexpected shape")
    signature_blob = json.dumps(preflight["events"], sort_keys=True, separators=(",", ":"))
    signature_hash = hashlib.sha256(signature_blob.encode()).hexdigest()
    if signature_hash != preflight["compact_event_signatures_sha256"]:
        raise RuntimeError("stored five-layer event signature hash mismatch")

    state_count = int(preflight["joint_signature_state_upper_bound"])
    nbits = preflight["compact_detector_count"] + 1
    vector_updates = len(preflight["events"]) * state_count * 16
    walsh_operations = (len(preflight["events"]) + 1) * state_count * nbits
    # Two state vectors, one work vector, one int32 index vector, and FWHT copies.
    memory_estimate = state_count * (8 * 5 + 4)
    if (state_count > MAX_STATES or vector_updates > MAX_VECTOR_UPDATES
            or walsh_operations > MAX_WALSH_OPERATIONS
            or memory_estimate > MAX_MEMORY_BYTES):
        raise RuntimeError("five-layer vectorized/Walsh preflight exceeds fixed caps")

    source = build_circuit("z", "x_biased", distance=3, rounds=5,
                           bias_ratio=10).flattened()
    baseline = sample_det_obs(deterministic_circuit(source, {}))
    events = preflight["events"]
    outcome_masks = []
    probabilities = []
    for event in events:
        outcome_masks.append([
            int(outcome["detector_mask"])
            | ((int(outcome["observable_mask"]) & 1) << preflight["compact_detector_count"])
            for outcome in event["outcomes"]])
        probabilities.append([float(outcome["probability"]) for outcome in event["outcomes"]])

    # Fixed-size vectorized DP: each local categorical outcome permutes state indices by XOR.
    states = np.zeros(state_count, dtype=np.float64)
    states[0] = 1.0
    indices = np.arange(state_count, dtype=np.int32)
    for masks, probs in zip(outcome_masks, probabilities, strict=True):
        nxt = np.zeros(state_count, dtype=np.float64)
        for mask, probability in zip(masks, probs, strict=True):
            nxt += probability * states[np.bitwise_xor(indices, mask)]
        states = nxt

    # Independent finite-group convolution in the Walsh domain.
    spectrum = np.ones(state_count, dtype=np.float64)
    for masks, probs in zip(outcome_masks, probabilities, strict=True):
        factor = np.zeros(state_count, dtype=np.float64)
        for mask, probability in zip(masks, probs, strict=True):
            factor[mask] += probability
        spectrum *= fwht(factor)
    walsh_states = fwht(spectrum) / state_count
    max_error = float(np.max(np.abs(states - walsh_states)))
    min_mass = float(min(states.min(), walsh_states.min()))
    total_mass = float(states.sum())
    if max_error > 1e-12 or abs(total_mass - 1.0) > 1e-12 or min_mass < -1e-12:
        raise RuntimeError(f"five-layer exact check failed: err={max_error}, total={total_mass}, min={min_mass}")

    # Map detector/logical group coordinates back to physical Stim outcomes.
    touched = preflight["touched_detector_ids"]
    combined_checks = 0
    for case in range(COMBINED_CHECKS):
        selected = {}
        expected_d = expected_l = 0
        for i, event in enumerate(events):
            idx = (case * (2*i + 3) + 11*i) % 16
            outcome = event["outcomes"][idx]
            selected[(event["instruction_index"], event["pair_index"])] = outcome["label"]
            expected_d ^= int(outcome["detector_mask"])
            expected_l ^= int(outcome["observable_mask"])
        actual_d, actual_l = sample_det_obs(deterministic_circuit(source, selected))
        compact_d = sum(1 << i for i, detector in enumerate(touched)
                        if (actual_d ^ baseline[0]) >> detector & 1)
        if (compact_d, actual_l ^ baseline[1]) != (expected_d, expected_l):
            raise RuntimeError(f"combined-fault XOR mismatch at {case}")
        combined_checks += 1

    detector_count = preflight["compact_detector_count"]
    detector_states = 1 << detector_count
    p0 = states[:detector_states]
    p1 = states[detector_states:]
    map_risk = float(np.minimum(p0, p1).sum())
    reachable_syndromes = int(np.count_nonzero(p0 + p1 > 0))
    output = {
        "status": "exact_five_layer_vectorized_walsh_pass",
        "source": "d3 five-round Z-memory, X-biased ratio10; final five PAULI_CHANNEL_2 layers only",
        "fault_locations": len(events),
        "categorical_domain_per_location": 16,
        "configuration_count_if_bruteforced": 16**len(events),
        "touched_detector_ids": touched,
        "compact_detector_count": detector_count,
        "joint_signature_states": state_count,
        "reachable_syndromes": reachable_syndromes,
        "joint_probability_total": total_mass,
        "max_abs_mass_error_vectorized_dp_vs_walsh": max_error,
        "minimum_mass": min_mass,
        "combined_fault_xor_checks": combined_checks,
        "vectorized_state_updates": vector_updates,
        "walsh_operation_count": walsh_operations,
        "estimated_peak_working_memory_bytes": memory_estimate,
        "isolated_five_layer_map_risk": map_risk,
        "signature_map_sha256": signature_hash,
        "elapsed_seconds": time.perf_counter() - started,
        "stochastic_samples_generated": 0,
        "scope": "exact posterior for 30 final-layer categorical locations; all other stochastic circuit locations are identity; not a full-circuit decoder result",
    }
    path = HERE / "categorical_five_layer_vectorized_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(path),
                      "states": state_count, "reachable_syndromes": reachable_syndromes,
                      "max_error": max_error, "map_risk": map_risk,
                      "elapsed_seconds": output["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
