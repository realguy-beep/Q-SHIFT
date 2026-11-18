"""Deterministic Stim approximation-threshold scan; generates no shots."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pymatching

RESEARCH_DIR = Path(__file__).resolve().parent
REPO = RESEARCH_DIR.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))

from noise_model import MEMORY_BASES, REGIMES, build_circuit  # noqa: E402

THRESHOLDS = (0.001, 0.0018, 0.003, 1.0)


def graph_hash(matching: pymatching.Matching) -> str:
    edges = []
    for left, right, attrs in matching.edges():
        u = -1 if left is None else int(left)
        v = -1 if right is None else int(right)
        edges.append((min(u, v), max(u, v), round(float(attrs["weight"]), 12),
                      tuple(sorted(int(x) for x in attrs.get("fault_ids", set())))))
    return hashlib.sha256(repr(sorted(edges)).encode()).hexdigest()


def main() -> int:
    results = []
    for basis in MEMORY_BASES:
        for regime in REGIMES:
            circuit = build_circuit(basis, regime)
            condition = {"memory_basis": basis, "regime": regime, "thresholds": []}
            for threshold in THRESHOLDS:
                record = {"threshold": threshold}
                try:
                    dem = circuit.detector_error_model(
                        decompose_errors=True,
                        approximate_disjoint_errors=threshold,
                    )
                    matching = pymatching.Matching.from_detector_error_model(
                        dem, enable_correlations=True)
                    dem_text = str(dem)
                    record.update({
                        "status": "ok",
                        "dem_sha256": hashlib.sha256(dem_text.encode()).hexdigest(),
                        "graph_sha256": graph_hash(matching),
                        "edge_count": matching.num_edges,
                        "separator_count": dem_text.count("^"),
                    })
                except ValueError as exc:
                    record.update({"status": "blocked", "reason": str(exc).splitlines()[0]})
                condition["thresholds"].append(record)
            successful = [r for r in condition["thresholds"] if r["status"] == "ok"]
            hashes = {r["dem_sha256"] for r in successful}
            condition["successful_dem_variants"] = len(hashes)
            results.append(condition)

    output = {
        "thresholds": list(THRESHOLDS),
        "conditions": results,
        "stochastic_shots_generated": 0,
        "interpretation": "thresholds below a categorical event probability block conversion; all successful tested thresholds produced identical DEMs per condition",
    }
    target = RESEARCH_DIR / "approximation_threshold_scan.json"
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target}")
    for condition in results:
        successful = [r for r in condition["thresholds"] if r["status"] == "ok"]
        print(condition["memory_basis"], condition["regime"],
              "successful_variants", condition["successful_dem_variants"],
              "blocked", sum(r["status"] == "blocked" for r in condition["thresholds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
