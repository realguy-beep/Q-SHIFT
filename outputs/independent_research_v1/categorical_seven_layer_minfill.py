"""Deterministic min-fill ordering challenge for the exact seven-layer P/Z arrays."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from categorical_seven_layer_parity import kernels, propagate


def min_fill_order(events: list[dict], detector_count: int) -> tuple[list[int], list[dict]]:
    adjacency = [set() for _ in range(detector_count)]
    for event in events:
        for outcome in event["outcomes"]:
            if float(outcome["probability"]) == 0:
                continue
            mask = int(outcome["detector_mask"])
            bits = [bit for bit in range(detector_count) if (mask >> bit) & 1]
            for i, a in enumerate(bits):
                adjacency[a].update(bits[:i])
                adjacency[a].update(bits[i + 1 :])
    remaining = set(range(detector_count))
    order, steps = [], []
    while remaining:
        scored = []
        for vertex in remaining:
            neighbors = sorted(adjacency[vertex] & remaining)
            missing = sum(
                1 for i, a in enumerate(neighbors) for b in neighbors[i + 1 :]
                if b not in adjacency[a]
            )
            scored.append(((missing, len(neighbors), vertex), vertex, neighbors))
        score, vertex, neighbors = min(scored)
        for i, a in enumerate(neighbors):
            adjacency[a].update(neighbors[:i])
            adjacency[a].update(neighbors[i + 1 :])
        remaining.remove(vertex)
        order.append(vertex)
        steps.append({"detector_bit": vertex, "missing_edges": score[0], "degree": score[1]})
    return order, steps


def inspect(values: np.ndarray, order: list[int], name: str) -> dict:
    m = len(order)
    original_bit_axes = [m - 1 - bit for bit in order]
    tensor = values.reshape((2,) * m).transpose(original_bit_axes)
    cuts = []
    for cut in range(1, m):
        matrix = np.ascontiguousarray(tensor.reshape(1 << cut, 1 << (m - cut)))
        singular = np.linalg.svd(matrix, compute_uv=False)
        total = float(np.square(singular).sum())
        tails = np.r_[np.cumsum(np.square(singular)[::-1])[::-1], 0.0]
        rank = lambda tol: int(np.flatnonzero(np.sqrt(tails / total) <= tol)[0])
        cuts.append(
            {
                "cut_after_order_position": cut,
                "matrix_shape": list(matrix.shape),
                "rank_rel_frob_1e-6": rank(1e-6),
                "rank_rel_frob_1e-10": rank(1e-10),
                "machine_rank": int(np.count_nonzero(singular > np.finfo(float).eps * max(matrix.shape) * singular[0])),
            }
        )
    return {
        "array": name,
        "cuts": cuts,
        "max_rank_1e-6": max(x["rank_rel_frob_1e-6"] for x in cuts),
        "max_rank_1e-10": max(x["rank_rel_frob_1e-10"] for x in cuts),
        "max_machine_rank": max(x["machine_rank"] for x in cuts),
    }


def main() -> None:
    started = time.perf_counter()
    pre = json.loads((HERE / "categorical_seven_layer_preflight.json").read_text())
    digest = hashlib.sha256(
        json.dumps(pre["events"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if digest != pre["compact_event_signatures_sha256"]:
        raise RuntimeError("seven-layer signature map hash mismatch")
    m = int(pre["compact_detector_count"])
    p, z = propagate(kernels(pre["events"])[0], 1 << m)
    if abs(float(p.sum()) - 1) > 1e-12 or np.max(np.abs(z) - p) > 1e-12:
        raise RuntimeError("exact P/Z invariant failed")
    order, steps = min_fill_order(pre["events"], m)
    p_result, z_result = inspect(p, order, "P_syndrome_mass"), inspect(z, order, "Z_signed_logical_mass")
    elapsed = time.perf_counter() - started
    result = {
        "status": "minfill_ordering_rank_audit",
        "source_signature_map_sha256": digest,
        "detector_count": m,
        "minfill_elimination_order": order,
        "minfill_steps": steps,
        "P": p_result,
        "Z": z_result,
        "elapsed_seconds": elapsed,
        "stochastic_samples_generated": 0,
        "advances_rank64_exact_fidelity_gate": p_result["max_rank_1e-10"] <= 64 and z_result["max_rank_1e-10"] <= 64,
        "scope": "deterministic order-specific TT rank diagnostic on the same exact seven-layer tail",
    }
    target = HERE / "categorical_seven_layer_minfill_results.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "order": order, "P_rank_1e-10": p_result["max_rank_1e-10"], "Z_rank_1e-10": z_result["max_rank_1e-10"], "elapsed_seconds": elapsed, "output": str(target)}, indent=2))


if __name__ == "__main__":
    main()
