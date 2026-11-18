"""Compare ratio-5/10 matching graph structure and weights at d3 and d5."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import time

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from noise_model import (DEFAULT_GATE_P, DEFAULT_MEAS_P, build_circuit,
                         one_qubit_probabilities, two_qubit_probabilities)
from code_distance_scaling import build_scaled_circuit

RATIOS = (5, 10)
PROFILES = ("x_biased", "z_biased")
BASES = ("x", "z")
SPECS = ((3, 5), (5, 9))
DEM_THRESHOLD = 0.0018


def make_d5(memory_basis: str, regime: str, ratio: float) -> stim.Circuit:
    p1 = one_qubit_probabilities(regime, DEFAULT_GATE_P, ratio)
    p2 = two_qubit_probabilities(regime, DEFAULT_GATE_P, ratio)
    generated = stim.Circuit.generated(
        f"surface_code:rotated_memory_{memory_basis}", distance=5, rounds=9,
        after_clifford_depolarization=DEFAULT_GATE_P,
        before_measure_flip_probability=DEFAULT_MEAS_P)
    body = str(generated)
    p1_text = "PAULI_CHANNEL_1(" + ",".join(format(x, ".17g") for x in p1) + ")"
    p2_text = "PAULI_CHANNEL_2(" + ",".join(format(x, ".17g") for x in p2) + ")"
    body, n1 = re.subn(r"DEPOLARIZE1\([^)]*\)", p1_text, body)
    body, n2 = re.subn(r"DEPOLARIZE2\([^)]*\)", p2_text, body)
    if not n1 or not n2:
        raise RuntimeError(f"d5 channel substitution failed: {n1}/{n2}")
    return stim.Circuit(body)


def edge_map(matching) -> dict:
    result = {}
    for u, v, data in matching.edges():
        a, b = (u, v) if v is not None and u <= v else (v, u)
        key = f"{a}:{b}:{','.join(map(str, sorted(data['fault_ids'])))}"
        result[key] = {
            "weight": float(data["weight"]),
            "error_probability": float(data["error_probability"]),
        }
    return result


def graph_summary(matching) -> dict:
    edges = edge_map(matching)
    topology = sorted(edges)
    return {
        "nodes": int(matching.num_nodes),
        "edges": len(edges),
        "boundary_edges": sum(":None:" in k for k in edges),
        "topology_sha256": hashlib.sha256("\n".join(topology).encode()).hexdigest(),
        "edges_by_signature": edges,
    }


def main() -> None:
    start = time.perf_counter()
    rows = []
    builder_checks = {}
    for distance, rounds in SPECS:
        for profile in PROFILES:
            for basis in BASES:
                models = {}
                for ratio in RATIOS:
                    if distance == 3:
                        circuit = build_circuit(
                            basis, profile, distance=3, rounds=5,
                            bias_ratio=float(ratio))
                        if ratio == 10:
                            rebuilt = build_scaled_circuit(basis, profile, 3, 5)
                            source = build_circuit(basis, profile, distance=3, rounds=5)
                            builder_checks[f"d3_{profile}_{basis}_ratio10"] = (
                                str(rebuilt) == str(source))
                            if str(rebuilt) != str(source):
                                raise RuntimeError("d3 builder mismatch")
                    else:
                        circuit = make_d5(basis, profile, float(ratio))
                        if ratio == 10:
                            scaled = build_scaled_circuit(basis, profile, 5, 9)
                            builder_checks[f"d5_{profile}_{basis}_ratio10"] = (
                                str(circuit) == str(scaled))
                            if str(circuit) != str(scaled):
                                raise RuntimeError("d5 ratio10 builder mismatch")
                    dem = circuit.detector_error_model(
                        decompose_errors=True,
                        approximate_disjoint_errors=DEM_THRESHOLD)
                    models[ratio] = pymatching.Matching.from_detector_error_model(
                        dem, enable_correlations=True)
                left, right = (graph_summary(models[r]) for r in RATIOS)
                keys_left, keys_right = set(left["edges_by_signature"]), set(right["edges_by_signature"])
                common = sorted(keys_left & keys_right)
                weight_diffs = np.asarray([
                    right["edges_by_signature"][k]["weight"]
                    - left["edges_by_signature"][k]["weight"] for k in common])
                prob_diffs = np.asarray([
                    right["edges_by_signature"][k]["error_probability"]
                    - left["edges_by_signature"][k]["error_probability"] for k in common])
                rows.append({
                    "distance": distance,
                    "rounds": rounds,
                    "profile": profile,
                    "memory_basis": basis,
                    "assumed_ratio5_graph": {k: v for k, v in left.items()
                                               if k != "edges_by_signature"},
                    "assumed_ratio10_graph": {k: v for k, v in right.items()
                                                if k != "edges_by_signature"},
                    "topology_identical": keys_left == keys_right,
                    "common_edges": len(common),
                    "edges_only_ratio5": len(keys_left - keys_right),
                    "edges_only_ratio10": len(keys_right - keys_left),
                    "mean_abs_common_edge_weight_delta": float(np.mean(np.abs(weight_diffs))),
                    "median_abs_common_edge_weight_delta": float(np.median(np.abs(weight_diffs))),
                    "max_abs_common_edge_weight_delta": float(np.max(np.abs(weight_diffs))),
                    "fraction_common_weights_increased_at_ratio10": float(np.mean(weight_diffs > 0)),
                    "median_abs_common_edge_probability_delta": float(np.median(np.abs(prob_diffs))),
                })
    output = {
        "status": "deterministic_matching_graph_mechanism_audit",
        "assumed_ratios": RATIOS,
        "distance_round_pairs": SPECS,
        "profiles": PROFILES,
        "memory_bases": BASES,
        "dem_approximation_threshold": DEM_THRESHOLD,
        "ratio10_builder_checks": builder_checks,
        "conditions": rows,
        "stochastic_samples_generated": 0,
        "elapsed_seconds": time.perf_counter() - start,
        "scope": "descriptive graph topology and edge-weight audit; no causal or LER claim",
    }
    out_path = HERE / "bias_graph_mechanism_results.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "output": str(out_path),
                      "conditions": len(rows), "elapsed_seconds": output["elapsed_seconds"],
                      "topology_identical_count": sum(r["topology_identical"] for r in rows)}, indent=2))


if __name__ == "__main__":
    main()
