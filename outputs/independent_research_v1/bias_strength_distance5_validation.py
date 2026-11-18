"""Fresh d5 paired validation of frozen ratio10 versus ratio5 matching decoders."""
from __future__ import annotations

import argparse
import json
import re

import stim
from pathlib import Path
import sys
import time

import numpy as np
import pymatching

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
from noise_model import one_qubit_probabilities, two_qubit_probabilities  # noqa: E402
from code_distance_scaling import build_scaled_circuit  # noqa: E402

DISTANCE = 5
ROUNDS = 9
ACTUAL_RATIOS = (2, 3.5, 5, 10)
ASSUMED_RATIOS = (5, 10)
PROFILES = ("x_biased", "z_biased")
BASES = ("x", "z")
CONDITIONS = tuple((r, p, b) for r in ACTUAL_RATIOS for p in PROFILES for b in BASES)
PREFLIGHT_SEEDS = tuple(range(2026112501, 2026112517))
MAIN_SEEDS = tuple(range(2026112521, 2026112537))
N_PREFLIGHT = 100
N_MAIN = 100_000
MAX_PROJECTED_SECONDS = 300.0
DEM_THRESHOLD = 0.0018


def make_circuit(memory_basis: str, regime: str, bias_ratio: float) -> stim.Circuit:
    p1 = one_qubit_probabilities(regime, 0.003, bias_ratio)
    p2 = two_qubit_probabilities(regime, 0.003, bias_ratio)
    circuit = stim.Circuit.generated(
        f"surface_code:rotated_memory_{memory_basis}", distance=DISTANCE, rounds=ROUNDS,
        after_clifford_depolarization=0.003, before_measure_flip_probability=0.003)
    body = str(circuit)
    p1_text = "PAULI_CHANNEL_1(" + ",".join(format(x, ".17g") for x in p1) + ")"
    p2_text = "PAULI_CHANNEL_2(" + ",".join(format(x, ".17g") for x in p2) + ")"
    body, n1 = re.subn(r"DEPOLARIZE1\([^)]*\)", p1_text, body)
    body, n2 = re.subn(r"DEPOLARIZE2\([^)]*\)", p2_text, body)
    if not n1 or not n2:
        raise RuntimeError(f"failed to substitute channels: {n1}/{n2}")
    return stim.Circuit(body)


def resources(circuit) -> dict:
    flat = circuit.flattened()
    return {
        "physical_qubits": int(circuit.num_qubits),
        "detectors": int(circuit.num_detectors),
        "observables": int(circuit.num_observables),
        "two_qubit_channel_pairs": sum(
            len(i.targets_copy()) // 2 for i in flat if i.name == "PAULI_CHANNEL_2"),
        "one_qubit_pauli_targets": sum(
            len(i.targets_copy()) for i in flat if i.name == "PAULI_CHANNEL_1"),
    }


def batch_decode(matching, detectors) -> np.ndarray:
    return np.asarray(matching.decode_batch(detectors, enable_correlations=True),
                      dtype=np.bool_).reshape(len(detectors), -1)


def paired_difference(candidate: np.ndarray, oracle: np.ndarray) -> dict:
    d = candidate.astype(np.float64) - oracle.astype(np.float64)
    mean = float(d.mean())
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    return {"difference_candidate_minus_reference": mean,
            "paired_se": se,
            "normal_95_ci": [mean - 1.959963984540054 * se,
                             mean + 1.959963984540054 * se]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=N_MAIN)
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    start = time.perf_counter()

    # Build once per assumed profile/basis/ratio; detector and observable geometry is shared.
    models = {}
    for profile in PROFILES:
        for basis in BASES:
            for assumed in ASSUMED_RATIOS:
                circuit = make_circuit(basis, profile, float(assumed))
                if assumed == 10:
                    reference = build_scaled_circuit(basis, profile, DISTANCE, ROUNDS)
                    if str(circuit) != str(reference):
                        raise RuntimeError("ratio10 custom builder differs from scaled source builder")
                dem = circuit.detector_error_model(
                    decompose_errors=True, approximate_disjoint_errors=DEM_THRESHOLD)
                models[(profile, basis, assumed)] = pymatching.Matching.from_detector_error_model(
                    dem, enable_correlations=True)

    rows = []
    geometry = {}
    seeds = PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
    shots = N_PREFLIGHT if args.preflight else args.shots
    for (actual, profile, basis), seed in zip(CONDITIONS, seeds, strict=True):
        circuit = make_circuit(basis, profile, float(actual))
        if circuit.num_detectors != 216 or circuit.num_observables != 1:
            raise RuntimeError(f"unexpected d5 circuit shape: {circuit.num_detectors}/{circuit.num_observables}")
        res = resources(circuit)
        geometry.setdefault(str(actual), []).append(res)
        t = time.perf_counter()
        detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
            shots=shots, separate_observables=True)
        sample_seconds = time.perf_counter() - t
        decoded = {}
        decode_seconds = {}
        for assumed in ASSUMED_RATIOS:
            matching = models[(profile, basis, assumed)]
            t = time.perf_counter()
            pred = batch_decode(matching, detectors)
            decode_seconds[str(assumed)] = time.perf_counter() - t
            if pred.shape != observables.shape:
                raise RuntimeError("decoder observable shape mismatch")
            scalar = np.asarray([matching.decode(s, enable_correlations=True)
                                 for s in detectors[:min(100, shots)]],
                                dtype=np.bool_).reshape(min(100, shots), -1)
            if not np.array_equal(scalar, pred[:len(scalar)]):
                raise RuntimeError(f"batch/scalar mismatch for assumed ratio {assumed}")
            decoded[str(assumed)] = np.any(pred != observables, axis=1)
        rates = {r: float(np.mean(v)) for r, v in decoded.items()}
        paired = {r: {str(reference): paired_difference(v, decoded[str(reference)])
                       for reference in ASSUMED_RATIOS}
                  for r, v in decoded.items()}
        rows.append({
            "actual_ratio": actual,
            "profile": profile,
            "memory_basis": basis,
            "seed": seed,
            "shots": shots,
            "resources": res,
            "failures_by_assumed_ratio": {r: int(v.sum()) for r, v in decoded.items()},
            "ler_by_assumed_ratio": rates,
            "paired_ler_differences_candidate_vs_reference_ratio": paired,
            "sample_seconds": sample_seconds,
            "decode_seconds_by_assumed_ratio": decode_seconds,
            "scalar_batch_checked_shots_per_decoder": min(100, shots),
        })

    geometry_match = {ratio: len({tuple(sorted(x.items())) for x in group}) == 1
                      for ratio, group in geometry.items()}
    elapsed = time.perf_counter() - start
    if args.preflight:
        projected = elapsed
        for row in rows:
            projected += N_MAIN * (row["sample_seconds"]
                                    + sum(row["decode_seconds_by_assumed_ratio"].values())) / shots
        status = "preflight_passed" if projected <= MAX_PROJECTED_SECONDS else "preflight_runtime_stop"
        output = {
            "status": status,
            "distance": DISTANCE,
            "rounds": ROUNDS,
            "actual_ratios": ACTUAL_RATIOS,
            "assumed_ratios": ASSUMED_RATIOS,
            "profiles": PROFILES,
            "memory_bases": BASES,
            "preflight_shots_per_condition": N_PREFLIGHT,
            "conditions": rows,
            "geometry_matched_within_actual_ratio": geometry_match,
            "projected_main_seconds": projected,
            "max_projected_seconds": MAX_PROJECTED_SECONDS,
            "elapsed_preflight_seconds": elapsed,
        }
        out_path = HERE / "bias_strength_distance5_validation_preflight.json"
    else:
        macro = {assumed: float(np.mean([row["ler_by_assumed_ratio"][str(assumed)]
                                         for row in rows])) for assumed in ASSUMED_RATIOS}
        macro_pairwise = {}
        for candidate in ASSUMED_RATIOS:
            for reference in ASSUMED_RATIOS:
                diffs = [row["paired_ler_differences_candidate_vs_reference_ratio"][str(candidate)][str(reference)]
                         for row in rows]
                mean = float(np.mean([x["difference_candidate_minus_reference"] for x in diffs]))
                se = float(np.sqrt(np.sum([x["paired_se"]**2 for x in diffs])) / len(diffs))
                macro_pairwise[f"{candidate}_vs_{reference}"] = {
                    "mean_paired_ler_difference": mean,
                    "conditional_mc_se": se,
                    "normal_95_ci": [mean - 1.959963984540054 * se,
                                     mean + 1.959963984540054 * se],
                }
        by_actual_ratio = {}
        for actual in ACTUAL_RATIOS:
            actual_rows = [row for row in rows if row["actual_ratio"] == actual]
            actual_delta_rows = [
                row["paired_ler_differences_candidate_vs_reference_ratio"]["10"]["5"]
                for row in actual_rows
            ]
            actual_mean = float(np.mean([x["difference_candidate_minus_reference"]
                                         for x in actual_delta_rows]))
            actual_se = float(np.sqrt(np.sum([x["paired_se"]**2
                                              for x in actual_delta_rows]))
                              / len(actual_delta_rows))
            by_actual_ratio[str(actual)] = {
                "macro_ler_by_assumed_ratio": {
                    str(assumed): float(np.mean([
                        row["ler_by_assumed_ratio"][str(assumed)]
                        for row in actual_rows])) for assumed in ASSUMED_RATIOS
                },
                "paired_ratio10_minus_ratio5": {
                    "mean_paired_ler_difference": actual_mean,
                    "conditional_mc_se": actual_se,
                    "normal_95_ci": [actual_mean - 1.959963984540054 * actual_se,
                                     actual_mean + 1.959963984540054 * actual_se],
                    "cells_favoring_ratio10": int(sum(
                        x["difference_candidate_minus_reference"] < 0
                        for x in actual_delta_rows)),
                    "cells": len(actual_delta_rows),
                },
            }
        output = {
            "status": "development_d5_frozen_bias_strength_validation",
            "distance": DISTANCE,
            "rounds": ROUNDS,
            "actual_ratios": ACTUAL_RATIOS,
            "assumed_ratios": ASSUMED_RATIOS,
            "profiles": PROFILES,
            "memory_bases": BASES,
            "shots_per_condition": args.shots,
            "conditions": rows,
            "macro_ler_equal_weight_all_16_conditions": macro,
            "macro_pairwise_paired_ler_differences": macro_pairwise,
            "macro_summary_by_actual_ratio": by_actual_ratio,
            "geometry_matched_within_actual_ratio": geometry_match,
            "elapsed_seconds": elapsed,
            "scope": "fresh-seed d5 validation of frozen ratio10 versus ratio5; actual ratio 3.5 adds an interpolation point; no selection or adaptation",
        }
        out_path = HERE / "bias_strength_distance5_validation_results.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(out_path),
                      "elapsed_seconds": elapsed,
                      "projected_main_seconds": output.get("projected_main_seconds"),
                      "macro_ler": output.get("macro_ler_equal_weight_all_16_conditions")}, indent=2))


if __name__ == "__main__":
    main()
