"""Exact syndrome mass/logical-parity inference for seven final channel layers."""
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

MAX_STATES = 1_100_000
MAX_VECTOR_UPDATES = 1_000_000_000
MAX_WALSH_OPERATIONS = 2_000_000_000
MAX_MEMORY_BYTES = 1 << 30
MAX_RUNTIME_SECONDS = 300
TOL = 1e-12
COMBINED_CHECKS = 512


def fwht(values: np.ndarray) -> np.ndarray:
    out = values.astype(np.float64, copy=True)
    half = 1
    while half < len(out):
        blocks = out.reshape(-1, 2 * half)
        left = blocks[:, :half].copy()
        right = blocks[:, half:2 * half].copy()
        blocks[:, :half] = left + right
        blocks[:, half:2 * half] = left - right
        half *= 2
    return out


def kernels(events):
    result = []
    raw_count = 0
    coalesced_count = 0
    for event in events:
        p, z = {}, {}
        for outcome in event["outcomes"]:
            detector = int(outcome["detector_mask"])
            probability = float(outcome["probability"])
            logical = int(outcome["observable_mask"]) & 1
            p[detector] = p.get(detector, 0.0) + probability
            z[detector] = z.get(detector, 0.0) + probability * (-1.0 if logical else 1.0)
            raw_count += 1
        result.append((p, z))
        coalesced_count += len(p)
    return result, raw_count, coalesced_count


def propagate(kernels_, states):
    p = np.zeros(states, dtype=np.float64)
    z = np.zeros(states, dtype=np.float64)
    p[0] = z[0] = 1.0
    indices = np.arange(states, dtype=np.int32)
    for kp, kz in kernels_:
        next_p = np.zeros(states, dtype=np.float64)
        next_z = np.zeros(states, dtype=np.float64)
        for mask, probability in kp.items():
            next_p += probability * p[np.bitwise_xor(indices, mask)]
        for mask, probability in kz.items():
            next_z += probability * z[np.bitwise_xor(indices, mask)]
        p, z = next_p, next_z
    return p, z


def walsh_infer(kernels_, states):
    spectrum_p = np.ones(states, dtype=np.float64)
    spectrum_z = np.ones(states, dtype=np.float64)
    for kp, kz in kernels_:
        factor_p = np.zeros(states, dtype=np.float64)
        factor_z = np.zeros(states, dtype=np.float64)
        for mask, probability in kp.items():
            factor_p[mask] += probability
        for mask, signed_probability in kz.items():
            factor_z[mask] += signed_probability
        spectrum_p *= fwht(factor_p)
        spectrum_z *= fwht(factor_z)
    return fwht(spectrum_p) / states, fwht(spectrum_z) / states


def joint_six_layer(events, detector_count):
    states_count = 1 << (detector_count + 1)
    joint = np.zeros(states_count, dtype=np.float64)
    joint[0] = 1.0
    indices = np.arange(states_count, dtype=np.int32)
    for event in events:
        local = {}
        for outcome in event["outcomes"]:
            sig = int(outcome["detector_mask"]) | ((int(outcome["observable_mask"]) & 1) << detector_count)
            local[sig] = local.get(sig, 0.0) + float(outcome["probability"])
        nxt = np.zeros(states_count, dtype=np.float64)
        for mask, probability in local.items():
            nxt += probability * joint[np.bitwise_xor(indices, mask)]
        joint = nxt
    syndrome_states = 1 << detector_count
    p = joint[:syndrome_states] + joint[syndrome_states:]
    z = joint[:syndrome_states] - joint[syndrome_states:]
    return p, z


def main() -> None:
    started = time.perf_counter()
    preflight_path = HERE / "categorical_seven_layer_preflight.json"
    preflight = json.loads(preflight_path.read_text())
    if preflight["fault_locations"] != 42 or preflight["compact_detector_count"] != 20:
        raise RuntimeError("stored seven-layer signature map has unexpected shape")
    signature_blob = json.dumps(preflight["events"], sort_keys=True, separators=(",", ":"))
    signature_hash = hashlib.sha256(signature_blob.encode()).hexdigest()
    if signature_hash != preflight["compact_event_signatures_sha256"]:
        raise RuntimeError("stored seven-layer event signature hash mismatch")

    detector_count = int(preflight["compact_detector_count"])
    states = 1 << detector_count
    ks, raw_count, coalesced_count = kernels(preflight["events"])
    vector_updates = 2 * states * coalesced_count
    walsh_ops = 2 * (len(ks) + 1) * states * detector_count
    # Includes two DP generations, two Walsh spectra, transform scratch, and indices.
    memory_estimate = states * (8 * 10 + 4)
    if (states > MAX_STATES or vector_updates > MAX_VECTOR_UPDATES
            or walsh_ops > MAX_WALSH_OPERATIONS or memory_estimate > MAX_MEMORY_BYTES):
        raise RuntimeError("parity inference exceeds fixed resource caps")

    # Independent six-layer reference: aggregate a full joint posterior to P and Z.
    six = json.loads((HERE / "categorical_six_layer_preflight.json").read_text())
    six_p, six_z = propagate(kernels(six["events"])[0], 1 << six["compact_detector_count"])
    joint_p, joint_z = joint_six_layer(six["events"], six["compact_detector_count"])
    six_reference_error = max(float(np.max(np.abs(six_p - joint_p))),
                              float(np.max(np.abs(six_z - joint_z))))
    six_risk_error = abs(float((six_p - np.abs(six_z)).sum() / 2)
                         - float((joint_p - np.abs(joint_z)).sum() / 2))
    if six_reference_error > TOL or six_risk_error > TOL:
        raise RuntimeError("six-layer parity aggregation disagrees with joint inference")

    p, z = propagate(ks, states)
    wp, wz = walsh_infer(ks, states)
    p_walsh_error = float(np.max(np.abs(p - wp)))
    z_walsh_error = float(np.max(np.abs(z - wz)))
    mass_error = abs(float(p.sum()) - 1.0)
    min_mass = float(min(p.min(), wp.min()))
    parity_bound_violation = float(np.max(np.abs(z) - p))
    if (max(p_walsh_error, z_walsh_error, mass_error, six_reference_error,
            six_risk_error) > TOL or min_mass < -TOL or parity_bound_violation > TOL):
        raise RuntimeError("seven-layer parity/Walsh or normalization check failed")

    source = build_circuit("z", "x_biased", distance=3, rounds=5,
                           bias_ratio=10).flattened()
    baseline = sample_det_obs(deterministic_circuit(source, {}))
    touched = preflight["touched_detector_ids"]
    for case in range(COMBINED_CHECKS):
        selected = {}
        expected_d = expected_l = 0
        for i, event in enumerate(preflight["events"]):
            index = (case * (2 * i + 3) + 11 * i) % 16
            outcome = event["outcomes"][index]
            selected[(event["instruction_index"], event["pair_index"])] = outcome["label"]
            expected_d ^= int(outcome["detector_mask"])
            expected_l ^= int(outcome["observable_mask"])
        actual_d, actual_l = sample_det_obs(deterministic_circuit(source, selected))
        compact_d = sum(1 << i for i, detector in enumerate(touched)
                        if (actual_d ^ baseline[0]) >> detector & 1)
        if (compact_d, actual_l ^ baseline[1]) != (expected_d, expected_l):
            raise RuntimeError(f"forced combined-fault check failed at {case}")

    elapsed = time.perf_counter() - started
    if elapsed > MAX_RUNTIME_SECONDS:
        raise RuntimeError("parity inference exceeded fixed 300-second runtime cap")
    risk = float(np.maximum(0.0, (p - np.abs(z)) / 2).sum())
    output = {
        "status": "exact_seven_layer_syndrome_parity_pass",
        "source": "d3 five-round Z-memory, X-biased ratio10; final seven PAULI_CHANNEL_2 layers only",
        "fault_locations": len(ks), "raw_categorical_outcomes": raw_count,
        "coalesced_detector_signatures": coalesced_count,
        "compact_detector_count": detector_count, "syndrome_states": states,
        "vectorized_PZ_updates": vector_updates, "walsh_PZ_operations": walsh_ops,
        "estimated_peak_working_memory_bytes": memory_estimate,
        "P_walsh_max_abs_error": p_walsh_error, "Z_walsh_max_abs_error": z_walsh_error,
        "six_layer_joint_reference_max_abs_error": six_reference_error,
        "six_layer_joint_reference_risk_error": six_risk_error,
        "mass_normalization_error": mass_error, "minimum_mass": min_mass,
        "max_abs_Z_minus_P": parity_bound_violation,
        "reachable_syndromes": int(np.count_nonzero(p > 0)),
        "isolated_seven_layer_MAP_risk": risk,
        "forced_stim_combined_fault_checks": COMBINED_CHECKS,
        "signature_map_sha256": signature_hash, "elapsed_seconds": elapsed,
        "stochastic_samples_generated": 0,
        "scope": "exact posterior for 42 final-layer categorical locations only; not full-circuit LER or a decoder result",
    }
    out_path = HERE / "categorical_seven_layer_parity_results.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "states": states,
                      "updates": vector_updates, "walsh_ops": walsh_ops,
                      "six_layer_reference_error": six_reference_error,
                      "P_error": p_walsh_error, "Z_error": z_walsh_error,
                      "risk": risk, "elapsed_seconds": elapsed,
                      "output": str(out_path)}, indent=2))


if __name__ == "__main__":
    main()
