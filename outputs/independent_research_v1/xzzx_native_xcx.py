"""Native-XCX realization of the fixed checkerboard XZZX transform."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO/"outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
import xzzx_codesign as base  # fixed checkerboard and source builder
from basis_alignment_distance7 import build as source_build

DISTS = (3, 5)
ROUNDS = {3: 5, 5: 9}
PROFILES = ("x_biased", "z_biased")
CONDITIONS = tuple((d, profile, code) for d in DISTS for profile in PROFILES
                   for code in ("css", "xzzx"))
PREFLIGHT_SEEDS = tuple(range(2026112701, 2026112709))
MAIN_SEEDS = tuple(range(2026112711, 2026112719))


def native_transform(circuit: stim.Circuit):
    """Apply fixed local-H transform, then compile H-CX-H to native XCX."""
    transformed, data, marked = base.transform_xzzx(circuit)
    items = list(transformed.flattened())
    out = stim.Circuit()
    i = 0
    compiled_control = 0
    removed_oneq_targets = 0
    while i < len(items):
        if i+4 < len(items):
            a, na, cx, b, nb = items[i:i+5]
            matched = (
                a.name == "H" and na.name == "PAULI_CHANNEL_1"
                and cx.name == "CX" and b.name == "H" and nb.name == "PAULI_CHANNEL_1"
                and len(a.targets_copy()) == len(na.targets_copy()) == 1
                and len(b.targets_copy()) == len(nb.targets_copy()) == 1
                and a.targets_copy()[0].value == na.targets_copy()[0].value
                == b.targets_copy()[0].value == nb.targets_copy()[0].value
                and len(cx.targets_copy()) == 2
                and cx.targets_copy()[0].value == a.targets_copy()[0].value
                and list(na.gate_args_copy()) == list(nb.gate_args_copy())
            )
            if matched:
                out.append("XCX", cx.targets_copy())
                compiled_control += 1
                removed_oneq_targets += 2
                i += 5
                continue
        inst = items[i]
        out.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
        i += 1

    if not compiled_control:
        raise RuntimeError("no marked-control H-CX-H interactions compiled")
    return out, data, marked, {"native_xcx_interactions": compiled_control,
                               "removed_added_pauli_channel_1_targets": removed_oneq_targets}


def noiseless(circuit: stim.Circuit):
    out = stim.Circuit()
    for inst in circuit.flattened():
        if inst.name in ("PAULI_CHANNEL_1", "PAULI_CHANNEL_2", "X_ERROR", "Z_ERROR"):
            continue
        out.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
    return out


def validate_ideal_conjugations():
    cases = (
        ("CX", [0, 1], stim.Circuit("H 0\nCX 0 1\nH 0"), stim.Circuit("XCX 0 1")),
        ("CZ", [0, 1], stim.Circuit("H 1\nCX 0 1\nH 1"), stim.Circuit("CZ 0 1")),
        ("reverse CX", [0, 1], stim.Circuit("H 0 1\nCX 0 1\nH 0 1"), stim.Circuit("CX 1 0")),
    )
    for name, _, left, right in cases:
        if stim.Tableau.from_circuit(left) != stim.Tableau.from_circuit(right):
            raise RuntimeError(f"native Clifford conjugation mismatch for {name}")
    return len(cases)


def resources(circuit):
    counts = {name: 0 for name in ("CX", "XCX", "CZ", "PAULI_CHANNEL_1", "PAULI_CHANNEL_2")}
    twoq_pairs = oneq_targets = ticks = htargets = 0
    for inst in circuit.flattened():
        if inst.name in counts:
            counts[inst.name] += 1
        if inst.name in ("CX", "XCX", "CZ"):
            twoq_pairs += len(inst.targets_copy())//2
        elif inst.name == "PAULI_CHANNEL_1":
            oneq_targets += len(inst.targets_copy())
        elif inst.name == "PAULI_CHANNEL_2":
            if len(inst.targets_copy())%2:
                raise RuntimeError("odd PAULI_CHANNEL_2 target count")
            # Counts physical pair locations once, independently of gate name.
            pass
        elif inst.name == "TICK":
            ticks += 1
        if inst.name == "H":
            htargets += len(inst.targets_copy())
    return {"qubits": circuit.num_qubits, "detectors": circuit.num_detectors,
            "observables": circuit.num_observables, "two_qubit_interactions": twoq_pairs,
            "one_qubit_noise_targets": oneq_targets, "ticks": ticks,
            "hadamard_targets": htargets, "gate_counts": counts}


def run(distance, profile, code, shots, seed):
    circuit = source_build("z", profile, distance=distance, rounds=ROUNDS[distance], bias_ratio=10.)
    native = circuit
    compile_stats = {"native_xcx_interactions": 0,
                     "removed_added_pauli_channel_1_targets": 0}
    if code == "xzzx":
        native, _, _, compile_stats = native_transform(circuit)
    dem = native.detector_error_model(decompose_errors=True,
                                      approximate_disjoint_errors=.0018)
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    begin = time.perf_counter()
    detector_samples, observable_samples = native.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True)
    sample_seconds = time.perf_counter()-begin
    begin = time.perf_counter()
    predictions = np.asarray(matching.decode_batch(detector_samples), dtype=np.bool_).reshape(shots, -1)
    decode_seconds = time.perf_counter()-begin
    if predictions.shape != observable_samples.shape:
        raise RuntimeError("native decoder prediction shape mismatch")
    failures = int(np.count_nonzero(np.any(predictions != observable_samples, axis=1)))
    scalar = np.asarray([matching.decode(detector_samples[i]) for i in range(min(100, shots))],
                        dtype=np.bool_).reshape(min(100, shots), -1)
    if not np.array_equal(scalar, predictions[:len(scalar)]):
        raise RuntimeError("native batch and scalar decoders disagree")
    return {"distance": distance, "profile": profile, "code": code, "seed": seed,
            "shots": shots, "failures": failures, "ler": failures/shots,
            "wilson_95": base.wilson(failures, shots),
            "conditional_ratio_to_css_helper": None,
            "sampling_seconds": sample_seconds, "decode_seconds": decode_seconds,
            "resources": resources(native), "transform": compile_stats}


def verify_fixed_circuits():
    ideal_checks = validate_ideal_conjugations()
    details = {}
    for d in DISTS:
        for profile in PROFILES:
            css = source_build("z", profile, distance=d, rounds=ROUNDS[d], bias_ratio=10.)
            xzzx, data, marked, transform = native_transform(css)
            rc, rx = resources(css), resources(xzzx)
            core = (rc["qubits"], rc["detectors"], rc["observables"],
                    rc["two_qubit_interactions"], rc["ticks"])
            xcore = (rx["qubits"], rx["detectors"], rx["observables"],
                     rx["two_qubit_interactions"], rx["ticks"])
            if core != xcore:
                raise RuntimeError(f"resource mismatch at d={d}/{profile}: {core}/{xcore}")
            if rx["hadamard_targets"] != rc["hadamard_targets"]:
                raise RuntimeError("native transform left an added physical H gate")
            if rx["one_qubit_noise_targets"] != rc["one_qubit_noise_targets"]:
                raise RuntimeError("native transform changed one-qubit noise-target count")
            if sum(len(i.targets_copy())//2 for i in xzzx.flattened() if i.name == "XCX") != transform["native_xcx_interactions"]:
                raise RuntimeError("XCX resource accounting mismatch")
            for candidate in (css, xzzx):
                clean = noiseless(candidate)
                sampled = clean.compile_detector_sampler(seed=2026112699).sample(
                    shots=64, separate_observables=True)
                if np.any(sampled[0]) or np.any(sampled[1]):
                    raise RuntimeError("native circuit has nondeterministic noiseless detectors/observable")
                candidate.detector_error_model(decompose_errors=True,
                                               approximate_disjoint_errors=.0018)
            css_p2 = [list(i.gate_args_copy()) for i in css.flattened()
                      if i.name == "PAULI_CHANNEL_2"]
            x_p2 = [list(i.gate_args_copy()) for i in xzzx.flattened()
                    if i.name == "PAULI_CHANNEL_2"]
            css_p2_targets = [[t.value for t in i.targets_copy()] for i in css.flattened()
                              if i.name == "PAULI_CHANNEL_2"]
            x_p2_targets = [[t.value for t in i.targets_copy()] for i in xzzx.flattened()
                            if i.name == "PAULI_CHANNEL_2"]
            if css_p2 != x_p2 or css_p2_targets != x_p2_targets:
                raise RuntimeError("native transform changed two-qubit noise probabilities")
            details[f"{d}_{profile}"] = {
                "marked_data_qubits": len(marked), "data_qubits": len(data),
                "transform": transform, "css_resources": rc, "xzzx_resources": rx,
                "two_qubit_noise_unchanged": True, "noiseless_determinism": True}
    return ideal_checks, details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=500_000)
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    ideal_checks, details = verify_fixed_circuits()
    shots = 100 if args.preflight else args.shots
    seeds = PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
    begin = time.perf_counter()
    rows = [run(*condition, shots, seed)
            for condition, seed in zip(CONDITIONS, seeds, strict=True)]
    elapsed = time.perf_counter()-begin
    comparisons = []
    for d in DISTS:
        for profile in PROFILES:
            css = next(x for x in rows if x["distance"] == d and x["profile"] == profile and x["code"] == "css")
            xzzx = next(x for x in rows if x["distance"] == d and x["profile"] == profile and x["code"] == "xzzx")
            comparisons.append({"distance": d, "profile": profile,
                                "css_failures": css["failures"], "xzzx_failures": xzzx["failures"],
                                "css_ler": css["ler"], "xzzx_ler": xzzx["ler"],
                                "xzzx_over_css_rate_ratio": base.rr(xzzx["failures"], css["failures"])})
    projected = (sum((x["sampling_seconds"]+x["decode_seconds"])*args.shots/shots for x in rows)
                 if args.preflight else None)
    output = {"status": "native_xcx_preflight" if args.preflight else "native_xcx_codesign_development",
              "hardware_assumption": "native CX/XCX/CZ equal duration and same source PAULI_CHANNEL_2 distribution",
              "ideal_conjugation_checks": ideal_checks, "preflight_circuit_details": details,
              "distance_rounds": ROUNDS, "bias_ratio": 10., "gate_meas_p": .003,
              "shots_per_condition": shots, "conditions": rows,
              "xzzx_vs_css": comparisons, "elapsed_seconds": elapsed,
              "projected_main_seconds": projected,
              "stochastic_circuit_shots": shots*len(rows),
              "scope": "finite d3/d5 code/circuit co-design under an explicit native-gate noise assumption; not a threshold or arbitrary-state claim"}
    target = HERE/("xzzx_native_xcx_preflight.json" if args.preflight
                   else "xzzx_native_xcx_results.json")
    target.write_text(json.dumps(output, indent=2)+"\n")
    print(json.dumps({"status": output["status"], "elapsed_seconds": elapsed,
                      "projected_main_seconds": projected, "comparisons": comparisons,
                      "output": str(target)}, indent=2))
    return int(args.preflight and projected > 300)


if __name__ == "__main__":
    raise SystemExit(main())
