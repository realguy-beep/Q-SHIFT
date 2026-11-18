"""Exact coalesced-kernel vectorized/Walsh inference for six final layers."""
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
from noise_model import build_circuit

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
    preflight = json.loads((HERE / "categorical_six_layer_preflight.json").read_text())
    if preflight["fault_locations"] != 36 or preflight["compact_detector_count"] != 18:
        raise RuntimeError("stored six-layer signature map has unexpected shape")
    signature_blob = json.dumps(preflight["events"], sort_keys=True, separators=(",", ":"))
    signature_hash = hashlib.sha256(signature_blob.encode()).hexdigest()
    if signature_hash != preflight["compact_event_signatures_sha256"]:
        raise RuntimeError("stored six-layer event signature hash mismatch")

    detector_count = preflight["compact_detector_count"]
    state_count = 1 << (detector_count + 1)
    coalesced_kernels = []
    raw_outcome_count = 0
    coalesced_outcome_count = 0
    for event in preflight["events"]:
        kernel = {}
        for outcome in event["outcomes"]:
            sig = (int(outcome["detector_mask"]), int(outcome["observable_mask"]) & 1)
            kernel[sig] = kernel.get(sig, 0.0) + float(outcome["probability"])
            raw_outcome_count += 1
        coalesced_kernels.append([
            (det | (logical << detector_count), probability)
            for (det, logical), probability in sorted(kernel.items())])
        coalesced_outcome_count += len(kernel)

    vector_updates = state_count * coalesced_outcome_count
    bits = detector_count + 1
    walsh_operations = (len(coalesced_kernels) + 1) * state_count * bits
    memory_estimate = state_count * (8 * 5 + 4)
    if (state_count > MAX_STATES or vector_updates > MAX_VECTOR_UPDATES
            or walsh_operations > MAX_WALSH_OPERATIONS
            or memory_estimate > MAX_MEMORY_BYTES):
        raise RuntimeError("coalesced six-layer method exceeds its fixed resource caps")

    source = build_circuit("z", "x_biased", distance=3, rounds=5,
                           bias_ratio=10).flattened()
    baseline = sample_det_obs(deterministic_circuit(source, {}))
    touched = preflight["touched_detector_ids"]

    # Coalesced XOR-kernel probability propagation over all signature states.
    states = np.zeros(state_count, dtype=np.float64)
    states[0] = 1.0
    indices = np.arange(state_count, dtype=np.int32)
    for kernel in coalesced_kernels:
        nxt = np.zeros(state_count, dtype=np.float64)
        for mask, probability in kernel:
            nxt += probability * states[np.bitwise_xor(indices, mask)]
        states = nxt

    # Independent Walsh-Hadamard convolution over the binary signature group.
    spectrum = np.ones(state_count, dtype=np.float64)
    for kernel in coalesced_kernels:
        factor = np.zeros(state_count, dtype=np.float64)
        for mask, probability in kernel:
            factor[mask] += probability
        spectrum *= fwht(factor)
    walsh_states = fwht(spectrum) / state_count
    max_error = float(np.max(np.abs(states - walsh_states)))
    min_mass = float(min(states.min(), walsh_states.min()))
    total_mass = float(states.sum())
    if max_error > 1e-12 or abs(total_mass - 1.0) > 1e-12 or min_mass < -1e-12:
        raise RuntimeError(f"coalesced six-layer inference failed: {max_error}/{total_mass}/{min_mass}")

    combined_checks = 0
    for case in range(COMBINED_CHECKS):
        selected = {}
        expected_d = expected_l = 0
        for i, event in enumerate(preflight["events"]):
            index = (case * (2*i + 3) + 11*i) % 16
            outcome = event["outcomes"][index]
            selected[(event["instruction_index"], event["pair_index"])] = outcome["label"]
            expected_d ^= int(outcome["detector_mask"])
            expected_l ^= int(outcome["observable_mask"])
        actual_d, actual_l = sample_det_obs(deterministic_circuit(source, selected))
        compact_d = sum(1 << i for i, detector in enumerate(touched)
                        if (actual_d ^ baseline[0]) >> detector & 1)
        if (compact_d, actual_l ^ baseline[1]) != (expected_d, expected_l):
            raise RuntimeError(f"coalesced combined-fault check failed at {case}")
        combined_checks += 1

    detector_states = 1 << detector_count
    map_risk = float(np.minimum(states[:detector_states], states[detector_states:]).sum())
    reachable = int(np.count_nonzero(
        states[:detector_states] + states[detector_states:] > 0))
    output = {
        "status": "exact_six_layer_coalesced_vectorized_walsh_pass",
        "source": "d3 five-round Z-memory, X-biased ratio10; final six PAULI_CHANNEL_2 layers only",
        "fault_locations": len(preflight["events"]),
        "raw_categorical_outcomes": raw_outcome_count,
        "coalesced_local_signatures": coalesced_outcome_count,
        "coalescing_reduction_fraction": 1 - coalesced_outcome_count / raw_outcome_count,
        "configuration_count_if_bruteforced": 16**len(preflight["events"]),
        "touched_detector_ids": touched,
        "compact_detector_count": detector_count,
        "joint_signature_states": state_count,
        "reachable_syndromes": reachable,
        "joint_probability_total": total_mass,
        "max_abs_mass_error_vectorized_dp_vs_walsh": max_error,
        "minimum_mass": min_mass,
        "combined_fault_xor_checks": combined_checks,
        "vectorized_state_updates": vector_updates,
        "walsh_operation_count": walsh_operations,
        "estimated_peak_working_memory_bytes": memory_estimate,
        "isolated_six_layer_map_risk": map_risk,
        "signature_map_sha256": signature_hash,
        "elapsed_seconds": time.perf_counter() - started,
        "stochastic_samples_generated": 0,
        "scope": "exact posterior for 36 final-layer categorical locations; all other stochastic circuit locations are identity; not a full-circuit decoder result",
    }
    path = HERE / "categorical_six_layer_coalesced_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(path),
                      "states": state_count, "coalesced_outcomes": coalesced_outcome_count,
                      "max_error": max_error, "map_risk": map_risk,
                      "elapsed_seconds": output["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
