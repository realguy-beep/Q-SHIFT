"""Single fixed complementary checkerboard XZZX orientation screen."""
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
import xzzx_codesign as original
from xzzx_native_xcx import native_transform, resources, noiseless, validate_ideal_conjugations
from basis_alignment_distance7 import build as source_build

VARIANTS = ("css", "xzzx_original", "xzzx_complement")
DISTS = (3, 5)
ROUNDS = {3: 5, 5: 9}
CONDITIONS = tuple((d, v) for d in DISTS for v in VARIANTS)
PREFLIGHT_SEEDS = tuple(range(2026112801, 2026112807))
MAIN_SEEDS = tuple(range(2026112811, 2026112817))


def complement_transform(circuit):
    """Use (x+y) mod 4 == 0, the one fixed complement of original's == 2."""
    saved = original.xy_sum
    try:
        original.xy_sum = lambda xy: saved(xy)+2
        return native_transform(circuit)
    finally:
        original.xy_sum = saved


def make_circuit(distance, variant):
    source = source_build("z", "z_biased", distance=distance,
                          rounds=ROUNDS[distance], bias_ratio=10.)
    if variant == "css":
        return source, source, {"marked_data_qubits": 0, "native_xcx_interactions": 0}
    if variant == "xzzx_original":
        transformed, data, marked, detail = native_transform(source)
    elif variant == "xzzx_complement":
        transformed, data, marked, detail = complement_transform(source)
    else:
        raise ValueError(variant)
    detail = {**detail, "data_qubits": len(data), "marked_data_qubits": len(marked)}
    return source, transformed, detail


def verify_fixed_variants():
    tableau_checks = validate_ideal_conjugations()
    details = {}
    for d in DISTS:
        source, css, _ = make_circuit(d, "css")
        source_p2 = [(tuple(t.value for t in i.targets_copy()), tuple(i.gate_args_copy()))
                     for i in source.flattened() if i.name == "PAULI_CHANNEL_2"]
        cssres = resources(css)
        for variant in VARIANTS[1:]:
            _, circuit, transform = make_circuit(d, variant)
            res = resources(circuit)
            if (res["qubits"], res["detectors"], res["observables"],
                res["two_qubit_interactions"], res["ticks"]) != (
                cssres["qubits"], cssres["detectors"], cssres["observables"],
                cssres["two_qubit_interactions"], cssres["ticks"]):
                raise RuntimeError(f"core resource mismatch: d={d}, {variant}")
            if res["hadamard_targets"] != cssres["hadamard_targets"]:
                raise RuntimeError(f"added H targets: d={d}, {variant}")
            if res["one_qubit_noise_targets"] != cssres["one_qubit_noise_targets"]:
                raise RuntimeError(f"one-qubit noise target mismatch: d={d}, {variant}")
            target_p2 = [(tuple(t.value for t in i.targets_copy()), tuple(i.gate_args_copy()))
                         for i in circuit.flattened() if i.name == "PAULI_CHANNEL_2"]
            if target_p2 != source_p2:
                raise RuntimeError(f"two-qubit channel mismatch: d={d}, {variant}")
            clean = noiseless(circuit)
            sample = clean.compile_detector_sampler(seed=2026112899).sample(
                shots=64, separate_observables=True)
            if np.any(sample[0]) or np.any(sample[1]):
                raise RuntimeError(f"noiseless detector/observable failure: d={d}, {variant}")
            circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=.0018)
            details[f"d{d}_{variant}"] = {"resources": res, "transform": transform,
                                          "noiseless_determinism": True,
                                          "p2_targets_and_probabilities_unchanged": True}
    return tableau_checks, details


def run(distance, variant, shots, seed):
    _, circuit, transform = make_circuit(distance, variant)
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=.0018)
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    start = time.perf_counter()
    detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True)
    sample_seconds = time.perf_counter()-start
    start = time.perf_counter()
    predictions = np.asarray(matching.decode_batch(detectors), dtype=np.bool_).reshape(shots, -1)
    decode_seconds = time.perf_counter()-start
    failures = int(np.count_nonzero(np.any(predictions != observables, axis=1)))
    scalar = np.asarray([matching.decode(detectors[i]) for i in range(min(100, shots))],
                        dtype=np.bool_).reshape(min(100, shots), -1)
    if not np.array_equal(scalar, predictions[:len(scalar)]):
        raise RuntimeError("scalar and batch decoding differ")
    return {"distance": distance, "variant": variant, "shots": shots,
            "seed": seed, "failures": failures, "ler": failures/shots,
            "wilson_95": original.wilson(failures, shots),
            "sampling_seconds": sample_seconds, "decode_seconds": decode_seconds,
            "resources": resources(circuit), "transform": transform}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=500_000)
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    tableau_checks, details = verify_fixed_variants()
    shots = 100 if args.preflight else args.shots
    seeds = PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
    start = time.perf_counter()
    rows = [run(*condition, shots, seed)
            for condition, seed in zip(CONDITIONS, seeds, strict=True)]
    elapsed = time.perf_counter()-start
    projected = (sum((row["sampling_seconds"]+row["decode_seconds"])*args.shots/shots
                     for row in rows) if args.preflight else None)
    comparisons = []
    for d in DISTS:
        css = next(r for r in rows if r["distance"] == d and r["variant"] == "css")
        orig = next(r for r in rows if r["distance"] == d and r["variant"] == "xzzx_original")
        comp = next(r for r in rows if r["distance"] == d and r["variant"] == "xzzx_complement")
        comparisons.append({"distance": d,
                            "primary_complement_vs_css": original.rr(comp["failures"], css["failures"]),
                            "secondary_original_vs_css": original.rr(orig["failures"], css["failures"]),
                            "secondary_complement_vs_original": original.rr(comp["failures"], orig["failures"]),
                            "failures": {"css": css["failures"], "original": orig["failures"],
                                         "complement": comp["failures"]},
                            "ler": {"css": css["ler"], "original": orig["ler"],
                                    "complement": comp["ler"]}})
    output = {"status": "native_xzzx_orientation_preflight" if args.preflight
              else "native_xzzx_orientation_development",
              "hardware_assumption": "native CX/XCX/CZ equal duration and same source PAULI_CHANNEL_2 noise",
              "bias": "z_biased, ratio 10, p=.003, Z-memory",
              "tableau_conjugation_checks": tableau_checks, "resource_checks": details,
              "distance_rounds": ROUNDS, "shots_per_cell": shots,
              "conditions": rows, "comparisons": comparisons,
              "elapsed_seconds": elapsed, "projected_main_seconds": projected,
              "stochastic_circuit_shots": shots*len(rows),
              "scope": "one complementary checkerboard orientation at d3/d5; finite-size, simulator-specific, not a pattern sweep or hardware result"}
    target = HERE/("xzzx_native_orientation_preflight.json" if args.preflight
                   else "xzzx_native_orientation_results.json")
    target.write_text(json.dumps(output, indent=2)+"\n")
    print(json.dumps({"status": output["status"], "elapsed_seconds": elapsed,
                      "projected_main_seconds": projected, "comparisons": comparisons,
                      "output": str(target)}, indent=2))
    return int(args.preflight and projected > 300)


if __name__ == "__main__":
    raise SystemExit(main())
