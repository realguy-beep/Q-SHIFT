"""Capped d3 Fusion Blossom custom-graph interface screen."""
from __future__ import annotations

import json
import resource
import time
from pathlib import Path

import fusion_blossom as fb
import numpy as np
import pymatching

from xzzx_basis_factorial import make_circuit

HERE = Path(__file__).resolve().parent
CONDITIONS = (("css", "x"), ("css", "z"), ("xzzx", "x"), ("xzzx", "z"))
SEEDS = (2026115201, 2026115202, 2026115203, 2026115204)
SHOTS = 250
DISTANCE = 3
ROUNDS = 5
WEIGHT_SCALE = 1_000_000


def build_decoder(code: str, basis: str):
    circuit = make_circuit(code, basis, DISTANCE, ROUNDS)
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=0.0018
    )
    matching = pymatching.Matching.from_detector_error_model(
        dem, enable_correlations=False
    )
    graph = matching.to_networkx()
    weighted_edges = []
    edge_fault_ids = []
    virtual_vertices = set()
    for a, b, data in graph.edges(data=True):
        a, b = int(a), int(b)
        if a >= matching.num_detectors:
            virtual_vertices.add(a)
        if b >= matching.num_detectors:
            virtual_vertices.add(b)
        weight = max(2, 2 * round(float(data["weight"]) * WEIGHT_SCALE / 2))
        weighted_edges.append((a, b, weight))
        edge_fault_ids.append(tuple(int(fid) for fid in data.get("fault_ids", ())))

    vertex_num = max(
        [matching.num_detectors]
        + [max(a, b) + 1 for a, b, _ in weighted_edges]
    )
    initializer = fb.SolverInitializer.from_json(
        json.dumps(
            {
                "vertex_num": vertex_num,
                "weighted_edges": weighted_edges,
                "virtual_vertices": sorted(virtual_vertices),
            }
        )
    )
    return circuit, matching, fb.SolverSerial(initializer), edge_fault_ids, {
        "detectors": int(matching.num_detectors),
        "vertices": int(vertex_num),
        "edges": len(weighted_edges),
        "virtual_vertices": len(virtual_vertices),
        "observables": int(matching.num_fault_ids),
    }


def run_cell(code: str, basis: str, seed: int) -> dict:
    started = time.perf_counter()
    circuit, matching, solver, edge_fault_ids, graph_resources = build_decoder(code, basis)
    graph_build_seconds = time.perf_counter() - started
    detectors, observed = circuit.compile_detector_sampler(seed=seed).sample(
        shots=SHOTS, separate_observables=True
    )

    t = time.perf_counter()
    expected = np.asarray(matching.decode_batch(detectors), dtype=np.uint8)
    pymatching_decode_seconds = time.perf_counter() - t

    t = time.perf_counter()
    fusion_predictions = np.zeros_like(expected)
    for shot, row in enumerate(detectors):
        defects = np.flatnonzero(row).tolist()
        if not defects:
            continue
        solver.solve(fb.SyndromePattern.new_vertices(defects))
        for edge_index in solver.subgraph():
            for fault_id in edge_fault_ids[edge_index]:
                fusion_predictions[shot, fault_id] ^= 1
        solver.clear()
    fusion_decode_seconds = time.perf_counter() - t
    mismatches = int(np.count_nonzero(fusion_predictions != expected))
    failures = int(np.count_nonzero(fusion_predictions != observed))
    return {
        "code": code,
        "basis": basis,
        "seed": seed,
        "shots": SHOTS,
        "observed_failures": failures,
        "prediction_mismatches_vs_pymatching": mismatches,
        "graph_build_seconds": graph_build_seconds,
        "pymatching_decode_seconds": pymatching_decode_seconds,
        "fusion_blossom_decode_seconds": fusion_decode_seconds,
        "fusion_over_pymatching_speed_ratio": (
            pymatching_decode_seconds / fusion_decode_seconds
            if fusion_decode_seconds
            else None
        ),
        "graph": graph_resources,
    }


def main() -> None:
    started = time.perf_counter()
    rows = [run_cell(code, basis, seed) for (code, basis), seed in zip(CONDITIONS, SEEDS, strict=True)]
    elapsed = time.perf_counter() - started
    mismatches = sum(row["prediction_mismatches_vs_pymatching"] for row in rows)
    output = {
        "status": "feasibility_screen_passed" if mismatches == 0 else "feasibility_screen_mismatch",
        "distance": DISTANCE,
        "rounds": ROUNDS,
        "noise": "X-bias ratio 10:1, p=0.003",
        "decoder_scope": "ordinary PyMatching MWPM and Fusion Blossom serial custom graph; correlations disabled in both",
        "weight_quantization": {"scale": WEIGHT_SCALE, "integer_weights_even": True},
        "conditions": rows,
        "new_source_equivalent_samples": SHOTS * len(rows),
        "prediction_mismatches": mismatches,
        "elapsed_seconds": elapsed,
        "max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "follow_on_samples_authorized_by_protocol": 0,
    }
    target = HERE / "fusion_blossom_d3_screen_results.json"
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "prediction_mismatches": mismatches, "elapsed_seconds": elapsed, "output": str(target)}, indent=2))


if __name__ == "__main__":
    main()
