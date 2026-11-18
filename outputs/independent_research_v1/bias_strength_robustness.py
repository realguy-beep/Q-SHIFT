"""Paired d3 circuit screen of matching sensitivity to assumed bias ratio."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
import pymatching

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
from noise_model import build_circuit  # noqa: E402

ACTUAL_RATIOS = (2, 5, 10)
ASSUMED_RATIOS = (2, 5, 10)
PROFILES = ("x_biased", "z_biased")
BASES = ("x", "z")
CONDITIONS = tuple((r, p, b) for r in ACTUAL_RATIOS for p in PROFILES for b in BASES)
PREFLIGHT_SEEDS = tuple(range(2026112301, 2026112313))
MAIN_SEEDS = tuple(range(2026112321, 2026112333))
N_PREFLIGHT = 100
N_MAIN = 100_000
MAX_PROJECTED_SECONDS = 300.0
DEM_THRESHOLD = 0.0018


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
                circuit = build_circuit(basis, profile, distance=3, rounds=5,
                                        gate_p=0.003, measurement_p=0.003,
                                        bias_ratio=float(assumed))
                dem = circuit.detector_error_model(
                    decompose_errors=True, approximate_disjoint_errors=DEM_THRESHOLD)
                models[(profile, basis, assumed)] = pymatching.Matching.from_detector_error_model(
                    dem, enable_correlations=True)

    rows = []
    geometry = {}
    seeds = PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
    shots = N_PREFLIGHT if args.preflight else args.shots
    for (actual, profile, basis), seed in zip(CONDITIONS, seeds, strict=True):
        circuit = build_circuit(basis, profile, distance=3, rounds=5,
                                gate_p=0.003, measurement_p=0.003,
                                bias_ratio=float(actual))
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
        out_path = HERE / "bias_strength_robustness_preflight.json"
    else:
        macro = {assumed: float(np.mean([row["ler_by_assumed_ratio"][str(assumed)]
                                         for row in rows])) for assumed in ASSUMED_RATIOS}
        macro_matched = float(np.mean([row["ler_by_assumed_ratio"][str(row["actual_ratio"])]
                                       for row in rows]))
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
        output = {
            "status": "development_bias_strength_robustness_screen",
            "actual_ratios": ACTUAL_RATIOS,
            "assumed_ratios": ASSUMED_RATIOS,
            "profiles": PROFILES,
            "memory_bases": BASES,
            "shots_per_condition": args.shots,
            "conditions": rows,
            "macro_ler_equal_weight_all_12_conditions": macro,
            "correctly_specified_model_macro_ler_reference": macro_matched,
            "macro_pairwise_paired_ler_differences": macro_pairwise,
            "geometry_matched_within_actual_ratio": geometry_match,
            "elapsed_seconds": elapsed,
            "scope": "paired development screen of assumed bias-strength mismatch, not decoder selection or adaptation",
        }
        out_path = HERE / "bias_strength_robustness_results.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(out_path),
                      "elapsed_seconds": elapsed,
                      "projected_main_seconds": output.get("projected_main_seconds"),
                      "macro_ler": output.get("macro_ler_equal_weight_all_12_conditions")}, indent=2))


if __name__ == "__main__":
    main()
