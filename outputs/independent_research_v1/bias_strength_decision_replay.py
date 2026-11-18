"""Replay archived d3/d5 seeds to decompose paired decoder disagreements."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import numpy as np
import pymatching

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from noise_model import build_circuit
import bias_strength_frozen_validation as d3_validation
import bias_strength_distance5_validation as d5_validation

RATIOS = (2, 3.5, 5, 10)
PROFILES = ("x_biased", "z_biased")
BASES = ("x", "z")
CONDITIONS = tuple((r, p, b) for r in RATIOS for p in PROFILES for b in BASES)
SHOTS = 100_000


def wilson(errors: int, n: int) -> list[float]:
    z = 1.959963984540054
    p = errors / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(center - half), float(center + half)]


def build_model(distance: int, profile: str, basis: str, assumed: int):
    if distance == 3:
        circuit = build_circuit(basis, profile, distance=3, rounds=5,
                                gate_p=0.003, measurement_p=0.003,
                                bias_ratio=float(assumed))
    else:
        circuit = d5_validation.make_circuit(basis, profile, float(assumed))
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=0.0018)
    return circuit, pymatching.Matching.from_detector_error_model(
        dem, enable_correlations=True)


def main() -> None:
    start = time.perf_counter()
    rows = []
    aggregate_by_distance_ratio = {}
    aggregate_by_distance_syndrome_bin = {}
    for distance, seed_start, result_name in (
        (3, 2026112421, "bias_strength_frozen_validation_results.json"),
        (5, 2026112521, "bias_strength_distance5_validation_results.json"),
    ):
        saved = json.loads((HERE / result_name).read_text())
        for i, ((actual, profile, basis), seed) in enumerate(zip(
                CONDITIONS, range(seed_start, seed_start + len(CONDITIONS)), strict=True)):
            if distance == 3:
                circuit = build_circuit(basis, profile, distance=3, rounds=5,
                                        gate_p=0.003, measurement_p=0.003,
                                        bias_ratio=float(actual))
            else:
                circuit = d5_validation.make_circuit(basis, profile, float(actual))
            detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
                shots=SHOTS, separate_observables=True)
            pred = {}
            failures = {}
            for assumed in (5, 10):
                _, matching = build_model(distance, profile, basis, assumed)
                pred[str(assumed)] = np.asarray(matching.decode_batch(
                    detectors, enable_correlations=True), dtype=np.bool_).reshape(SHOTS, -1)
                failures[str(assumed)] = np.any(pred[str(assumed)] != observables, axis=1)
            decoded_disagree = np.any(pred["5"] != pred["10"], axis=1)
            syndrome_weight = detectors.sum(axis=1)
            both_correct = int(np.count_nonzero(~failures["5"] & ~failures["10"]))
            both_wrong = int(np.count_nonzero(failures["5"] & failures["10"]))
            ratio10_fixes = int(np.count_nonzero(failures["5"] & ~failures["10"]))
            ratio10_breaks = int(np.count_nonzero(~failures["5"] & failures["10"]))
            disagree_n = int(decoded_disagree.sum())
            expected = saved["conditions"][i]
            got = {"5": int(failures["5"].sum()), "10": int(failures["10"].sum())}
            if got != expected["failures_by_assumed_ratio"]:
                raise RuntimeError(
                    f"replay count mismatch d{distance} {actual}/{profile}/{basis}: "
                    f"replayed={got}, archived={expected['failures_by_assumed_ratio']}")
            row = {
                "distance": distance,
                "actual_ratio": actual,
                "profile": profile,
                "memory_basis": basis,
                "seed": seed,
                "shots": SHOTS,
                "failure_counts": got,
                "both_correct": both_correct,
                "both_wrong": both_wrong,
                "ratio10_fixes_ratio5_failure": ratio10_fixes,
                "ratio10_breaks_ratio5_success": ratio10_breaks,
                "prediction_disagreements": disagree_n,
                "disagreement_rate": disagree_n / SHOTS,
                "ratio10_success_given_disagreement": (
                    (disagree_n - ratio10_breaks) / disagree_n if disagree_n else None),
                "ratio5_success_given_disagreement": (
                    (disagree_n - ratio10_fixes) / disagree_n if disagree_n else None),
                "archived_error_counts_reproduced": True,
            }
            bin_id = np.select(
                [syndrome_weight == 0, syndrome_weight <= 2,
                 syndrome_weight <= 4, syndrome_weight <= 8],
                [0, 1, 2, 3], default=4)
            bin_names = {0: "weight_0", 1: "weight_1_2", 2: "weight_3_4",
                         3: "weight_5_8", 4: "weight_9_plus"}
            by_bin = {}
            for bin_value, bin_name in bin_names.items():
                mask = bin_id == bin_value
                dis = mask & decoded_disagree
                by_bin[bin_name] = {
                    "shots": int(mask.sum()),
                    "prediction_disagreements": int(dis.sum()),
                    "ratio10_fixes_ratio5_failure": int(np.count_nonzero(
                        mask & failures["5"] & ~failures["10"])),
                    "ratio10_breaks_ratio5_success": int(np.count_nonzero(
                        mask & ~failures["5"] & failures["10"])),
                    "both_wrong": int(np.count_nonzero(
                        mask & failures["5"] & failures["10"])),
                }
                key = (distance, bin_name)
                agg = aggregate_by_distance_syndrome_bin.setdefault(key, {
                    "distance": distance, "syndrome_weight_bin": bin_name,
                    "shots": 0, "prediction_disagreements": 0,
                    "ratio10_fixes_ratio5_failure": 0,
                    "ratio10_breaks_ratio5_success": 0, "both_wrong": 0,
                })
                for field in ("shots", "prediction_disagreements",
                              "ratio10_fixes_ratio5_failure",
                              "ratio10_breaks_ratio5_success", "both_wrong"):
                    agg[field] += by_bin[bin_name][field]
            row["paired_outcomes_by_syndrome_weight"] = by_bin
            rows.append(row)
            key = (distance, actual)
            a = aggregate_by_distance_ratio.setdefault(key, {
                "distance": distance, "actual_ratio": actual,
                "shots": 0, "both_correct": 0, "both_wrong": 0,
                "ratio10_fixes_ratio5_failure": 0,
                "ratio10_breaks_ratio5_success": 0,
                "prediction_disagreements": 0,
            })
            for field in ("shots", "both_correct", "both_wrong",
                          "ratio10_fixes_ratio5_failure",
                          "ratio10_breaks_ratio5_success", "prediction_disagreements"):
                a[field] += row[field]
    aggregates = list(aggregate_by_distance_ratio.values())
    for x in aggregates:
        x["disagreement_rate"] = x["prediction_disagreements"] / x["shots"]
        x["net_ratio10_error_change"] = (
            x["ratio10_breaks_ratio5_success"] - x["ratio10_fixes_ratio5_failure"])
        n = x["prediction_disagreements"]
        x["ratio10_success_given_disagreement"] = (
            (n - x["ratio10_breaks_ratio5_success"]) / n if n else None)
    by_distance = []
    for distance in (3, 5):
        group = [r for r in rows if r["distance"] == distance]
        counts = {key: sum(r[key] for r in group) for key in (
            "shots", "both_correct", "both_wrong", "ratio10_fixes_ratio5_failure",
            "ratio10_breaks_ratio5_success", "prediction_disagreements")}
        disagreements = counts["prediction_disagreements"]
        fixes = counts["ratio10_fixes_ratio5_failure"]
        breaks = counts["ratio10_breaks_ratio5_success"]
        by_distance.append({
            "distance": distance,
            **counts,
            "disagreement_rate": disagreements / counts["shots"],
            "ratio10_success_given_disagreement": fixes / disagreements,
            "ratio10_conditional_success_wilson_95": wilson(fixes, disagreements),
            "net_error_rate_change_ratio10_minus_ratio5": (breaks - fixes) / counts["shots"],
        })
    output = {
        "status": "paired_seed_replay_decomposition",
        "distances": [3, 5],
        "actual_ratios": RATIOS,
        "assumed_ratios": [5, 10],
        "profiles": PROFILES,
        "memory_bases": BASES,
        "shots_per_condition": SHOTS,
        "conditions": rows,
        "aggregates_by_distance_and_actual_ratio": aggregates,
        "aggregates_by_distance": by_distance,
        "aggregates_by_distance_and_syndrome_weight": list(
            aggregate_by_distance_syndrome_bin.values()),
        "all_archived_error_counts_reproduced": True,
        "new_independent_samples": 0,
        "elapsed_seconds": time.perf_counter() - start,
        "scope": "replay of archived seeds only; paired outcome decomposition, no new validation",
    }
    out_path = HERE / "bias_strength_decision_replay_results.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(out_path),
                      "conditions": len(rows), "archived_counts_reproduced": True,
                      "elapsed_seconds": output["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
