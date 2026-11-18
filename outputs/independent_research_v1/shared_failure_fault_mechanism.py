"""Track categorical two-qubit Pauli outcomes in a bounded mismatch screen."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
sys.path.insert(0, str(HERE))
from noise_model import PAULI_PAIRS, build_circuit  # noqa: E402
from categorical_importance_sampler import instrument_circuit  # noqa: E402
import bias_strength_distance5_validation as d5_validation  # noqa: E402

CONDITIONS = ((3, "x_biased", "z"), (3, "z_biased", "x"),
              (5, "x_biased", "z"), (5, "z_biased", "x"))
PREFLIGHT_ORIGINAL_SEEDS = (2026112611, 2026112612, 2026112613, 2026112614)
PREFLIGHT_INSTRUMENTED_SEEDS = (2026112601, 2026112602, 2026112603, 2026112604)
MAIN_SEEDS = (2026112621, 2026112622, 2026112623, 2026112624)
N_PREFLIGHT = 5_000
N_MAIN = 100_000
MAX_PROJECTED_SECONDS = 300.0
GROUPS = ("both_correct", "both_wrong", "ratio10_fixes_ratio5", "ratio10_breaks_ratio5")


def source_circuit(distance: int, profile: str, basis: str) -> stim.Circuit:
    if distance == 3:
        return build_circuit(basis, profile, distance=3, rounds=5,
                             gate_p=0.003, measurement_p=0.003,
                             bias_ratio=10.0)
    return d5_validation.make_circuit(basis, profile, 10.0)


def matching_for(distance: int, profile: str, basis: str, assumed: int):
    if distance == 3:
        circuit = build_circuit(basis, profile, distance=3, rounds=5,
                                gate_p=0.003, measurement_p=0.003,
                                bias_ratio=float(assumed))
    else:
        circuit = d5_validation.make_circuit(basis, profile, float(assumed))
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=0.0018)
    return pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)


def instrumented_sample(circuit, seed: int, shots: int):
    inst, events = instrument_circuit(circuit, alpha=1.0)
    detectors, observables = inst.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True)
    expected = 1 + 4 * len(events)
    if observables.shape[1] != expected:
        raise RuntimeError(f"flag observable shape {observables.shape[1]} != {expected}")
    codes = (observables[:, 1:].reshape(shots, len(events), 4).astype(np.uint8)
             @ np.asarray([1, 2, 4, 8], dtype=np.uint8)).astype(np.uint8)
    if np.any(codes > 15):
        raise RuntimeError("invalid categorical Pauli outcome code")
    return detectors, observables[:, :1], codes, events, inst


def counts_for(matching, detectors, observables) -> tuple[np.ndarray, np.ndarray]:
    prediction = np.asarray(matching.decode_batch(
        detectors, enable_correlations=True), dtype=np.bool_).reshape(len(detectors), -1)
    if prediction.shape != observables.shape:
        raise RuntimeError("matcher output shape differs from source observable")
    failures = np.any(prediction != observables, axis=1)
    return prediction, failures


def summarize_groups(codes: np.ndarray, failures5: np.ndarray,
                     failures10: np.ndarray, save_fault_detail: bool) -> dict:
    names = {0: "both_correct", 1: "both_wrong",
             2: "ratio10_fixes_ratio5", 3: "ratio10_breaks_ratio5"}
    group_code = np.select(
        [~failures5 & ~failures10, failures5 & failures10,
         failures5 & ~failures10, ~failures5 & failures10],
        [0, 1, 2, 3], default=-1)
    result = {}
    for code, name in names.items():
        rows = codes[group_code == code]
        fault_mask = rows > 0
        count = int(rows.shape[0])
        fault_counts = fault_mask.sum(axis=1) if count else np.asarray([], dtype=np.int64)
        outcome_counts = np.bincount(rows.ravel(), minlength=16)[1:] if count else np.zeros(15, dtype=np.int64)
        result[name] = {
            "shots": count,
            "mean_two_qubit_pair_faults_per_shot": float(fault_counts.mean()) if count else None,
            "median_two_qubit_pair_faults_per_shot": float(np.median(fault_counts)) if count else None,
            "zero_two_qubit_pair_fault_fraction": float(np.mean(fault_counts == 0)) if count else None,
            "pauli_pair_fault_events_by_type": {
                pair: int(n) for pair, n in zip(PAULI_PAIRS, outcome_counts, strict=True)},
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=N_MAIN)
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    start = time.perf_counter()
    rows = []
    seeds = PREFLIGHT_INSTRUMENTED_SEEDS if args.preflight else MAIN_SEEDS
    n = N_PREFLIGHT if args.preflight else args.shots
    projected_total = 0.0

    for i, ((distance, profile, basis), seed) in enumerate(zip(CONDITIONS, seeds, strict=True)):
        source = source_circuit(distance, profile, basis)
        matching5 = matching_for(distance, profile, basis, 5)
        matching10 = matching_for(distance, profile, basis, 10)
        t = time.perf_counter()
        detectors, observables, codes, events, inst = instrumented_sample(source, seed, n)
        instrument_seconds = time.perf_counter() - t
        pred5, failures5 = counts_for(matching5, detectors, observables)
        pred10, failures10 = counts_for(matching10, detectors, observables)
        disagreement = np.any(pred5 != pred10, axis=1)
        row = {
            "distance": distance,
            "rounds": 5 if distance == 3 else 9,
            "actual_ratio": 10,
            "profile": profile,
            "memory_basis": basis,
            "seed": seed,
            "shots": n,
            "source_detectors": source.num_detectors,
            "source_observables": source.num_observables,
            "instrumented_qubits": inst.num_qubits,
            "categorical_two_qubit_pair_locations": len(events),
            "failures_by_assumed_ratio": {"5": int(failures5.sum()), "10": int(failures10.sum())},
            "prediction_disagreements": int(disagreement.sum()),
            "instrument_seconds": instrument_seconds,
        }
        if args.preflight:
            original_seed = PREFLIGHT_ORIGINAL_SEEDS[i]
            t = time.perf_counter()
            d_orig, o_orig = source.compile_detector_sampler(seed=original_seed).sample(
                shots=n, separate_observables=True)
            _, f_orig = counts_for(matching10, d_orig, o_orig)
            original_seconds = time.perf_counter() - t
            raw_rate, inst_rate = float(f_orig.mean()), float(failures10.mean())
            denom = np.sqrt(raw_rate*(1-raw_rate)/n + inst_rate*(1-inst_rate)/n)
            z = (inst_rate-raw_rate)/denom if denom else 0.0
            row.update({
                "original_seed": original_seed,
                "original_failures": int(f_orig.sum()),
                "instrumented_failures_ratio10": int(failures10.sum()),
                "independent_binomial_z_instrumented_minus_original": float(z),
                "original_sample_decode_seconds": original_seconds,
                "scalar_batch_check": "correlation-enabled batch decoder output shape checked",
            })
            projected_total += (instrument_seconds + original_seconds) * N_MAIN / n
        else:
            row["fault_group_summaries"] = summarize_groups(
                codes, failures5, failures10, save_fault_detail=True)
        rows.append(row)

    elapsed = time.perf_counter() - start
    if args.preflight:
        passed = all(row["source_detectors"] == (40 if row["distance"] == 3 else 216)
                     and row["source_observables"] == 1
                     and abs(row["independent_binomial_z_instrumented_minus_original"]) < 4
                     for row in rows)
        projected_total += elapsed
        output = {
            "status": "preflight_passed" if passed and projected_total <= MAX_PROJECTED_SECONDS
                      else "preflight_stopped",
            "conditions": rows,
            "preflight_shots_per_arm_condition": n,
            "projected_main_seconds": projected_total,
            "max_projected_seconds": MAX_PROJECTED_SECONDS,
            "elapsed_preflight_seconds": elapsed,
        }
        path = HERE / "shared_failure_fault_mechanism_preflight.json"
    else:
        output = {
            "status": "development_two_qubit_fault_composition_screen",
            "conditions": rows,
            "shots_per_condition": args.shots,
            "new_source_equivalent_samples": int(args.shots * len(rows)),
            "elapsed_seconds": elapsed,
            "limitation": "one-qubit channels and measurement flips are preserved but not fault-instrumented",
        }
        path = HERE / "shared_failure_fault_mechanism_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(path),
                      "elapsed_seconds": elapsed,
                      "projected_main_seconds": output.get("projected_main_seconds")}, indent=2))


if __name__ == "__main__":
    main()
