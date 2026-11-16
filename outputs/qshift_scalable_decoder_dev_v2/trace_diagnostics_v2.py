"""Residual traces for fixed BP settings; no sampling or parameter sweep."""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np
import stim

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from factor_bp_v2 import FactorBPV2
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as model

OUT = HERE / "CONVERGENCE_DIAGNOSTICS.json"


def trace(decoder: FactorBPV2, syndrome):
    x = np.asarray(syndrome)
    mask = sum(int(bit) << index for index, bit in enumerate(x)) ^ decoder.fixed_detector_mask
    vc = np.asarray([decoder.prior[v] for v, _ in decoder.edges], dtype=float)
    cv = np.zeros(len(decoder.edges), dtype=float)
    residuals = []
    for _ in range(decoder.iterations):
        updated = np.zeros_like(cv)
        for check, edge_ids in enumerate(decoder.by_c):
            if not edge_ids:
                continue
            values = [math.tanh(vc[e] / 2) for e in edge_ids]
            prefix = [1.0]
            for value in values:
                prefix.append(prefix[-1] * value)
            suffix = [1.0] * (len(edge_ids) + 1)
            for i in range(len(edge_ids) - 1, -1, -1):
                suffix[i] = values[i] * suffix[i + 1]
            sign = -1.0 if ((mask >> check) & 1) else 1.0
            for i, edge in enumerate(edge_ids):
                product = sign * prefix[i] * suffix[i + 1]
                raw = 2 * math.atanh(max(-1 + decoder.clip, min(1 - decoder.clip, product)))
                updated[edge] = decoder.damping * cv[edge] + (1 - decoder.damping) * raw
        nxt = np.empty_like(vc)
        for variable, edge_ids in enumerate(decoder.by_v):
            for edge in edge_ids:
                nxt[edge] = decoder.prior[variable] + math.fsum(updated[o] for o in edge_ids if o != edge)
        residuals.append(float(np.max(np.abs(updated - cv))) if len(cv) else 0.0)
        cv, vc = updated, nxt
        if residuals[-1] < decoder.tolerance:
            break
    return residuals


def graph_summary(decoder):
    vertices = len(decoder.p) + decoder.n
    adjacency = [[] for _ in range(vertices)]
    for variable, detector in decoder.edges:
        a, b = variable, len(decoder.p) + detector
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen = set()
    components = 0
    for start in range(vertices):
        if start in seen:
            continue
        components += 1
        seen.add(start)
        stack = [start]
        while stack:
            current = stack.pop()
            for nxt in adjacency[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return {"mechanisms": len(decoder.p), "incidence_edges": len(decoder.edges),
            "components": components,
            "cycle_rank": len(decoder.edges) - vertices + components,
            "max_detector_degree": max(map(len, decoder.by_c), default=0)}


def summarize(label, decoder, syndrome):
    actual = decoder.decode_one(syndrome)
    residuals = trace(decoder, syndrome)
    if len(residuals) != actual["iterations"] or abs(residuals[-1] - actual["message_residual"]) > 1e-12:
        raise AssertionError("trace replay does not match decoder's recorded convergence")
    increasing = sum(b > a for a, b in zip(residuals, residuals[1:]))
    sampled = {str(i): residuals[min(i - 1, len(residuals) - 1)] for i in (1, 2, 5, 10, 20, 50)}
    return {"fixture": label, "iterations": len(residuals), "converged": actual["converged"],
            "initial_residual": residuals[0], "final_residual": residuals[-1],
            "max_residual": max(residuals), "increases_between_iterations": increasing,
            "residual_at_iteration": sampled, "full_residual_trace": residuals}


def main():
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    rows = []
    for q in (0.0, 0.01):
        spec = model.CodeSpec(distance=3, rounds=5)
        support = model.burst_qubits(spec, "scaled_v1")
        circuit = model.build_candidate_circuit(spec, q, support)
        dem = circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
        decoder = FactorBPV2(dem)
        syndromes = [np.zeros(spec.detectors, dtype=np.uint8)]
        for event in model.extract_burst_events(spec, support)[:5]:
            syndrome = np.zeros(spec.detectors, dtype=np.uint8)
            syndrome[list(event.detector_ids)] = 1
            syndromes.append(syndrome)
        rows.append({"distance": 3, "q": q, "graph": graph_summary(decoder),
                     "fixtures": [summarize(f"q={q}:fixture={i}", decoder, syndrome)
                                  for i, syndrome in enumerate(syndromes)]})
    # Minimal 3-check cycle, fixed solver settings; checks whether this toy cycle itself
    # exhibits oscillation or merely approaches a fixed point.
    cycle_dem = stim.DetectorErrorModel(
        "error(0.1) D0 D1\nerror(0.2) D1 D2\nerror(0.3) D0 D2\n"
        "detector D0\ndetector D1\ndetector D2\nlogical_observable L0"
    )
    cycle = FactorBPV2(cycle_dem)
    rows.append({"distance": "toy-3-check-cycle", "q": None,
                 "graph": graph_summary(cycle),
                 "fixtures": [summarize("toy-cycle-syndrome-110", cycle, [1, 1, 0])]})
    OUT.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([
        {"case": row["distance"], "q": row["q"], "graph": row["graph"],
         "converged": sum(f["converged"] for f in row["fixtures"]),
         "count": len(row["fixtures"]),
         "nonconverged_final_residuals": [f["final_residual"] for f in row["fixtures"] if not f["converged"]],
         "nonconverged_residual_increases": [f["increases_between_iterations"] for f in row["fixtures"] if not f["converged"]]}
        for row in rows
    ], indent=2))


if __name__ == "__main__":
    main()

