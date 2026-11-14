"""Finite-grid gate-noise mismatch audit for the approximate DEM scalar X mean.

Deterministic model construction and parity expectations only; no sampling.
The finite grid can exhibit counterexamples but cannot certify a continuum envelope.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import stim

from three_parameter_dem_identifiability import build_mechanisms, FEATURES, all_one_moment

HERE = Path(__file__).resolve().parent
LOW_BURST = (0.0, 0.001, 0.002)
HIGH_BURST = (0.010, 0.014, 0.018)
MEASUREMENT = (0.001, 0.003, 0.005)
GATE = (0.002, 0.003, 0.004)


def statistic(pb: float, pm: float, pg: float) -> float:
    mechanisms = build_mechanisms(np.array([pb, pm, pg]))
    return sum(all_one_moment(mechanisms, f) for f in FEATURES[40:45]) / 5


def main() -> None:
    records = []
    for regime, bursts in (("low_null", LOW_BURST), ("high_alternative", HIGH_BURST)):
        for pb in bursts:
            for pm in MEASUREMENT:
                for pg in GATE:
                    records.append({"regime": regime, "burst_p": pb, "measurement_p": pm,
                                    "gate_p": pg, "mean_X": statistic(pb, pm, pg)})
    low_base = max(r["mean_X"] for r in records if r["regime"] == "low_null" and r["gate_p"] == .003)
    low_mismatch = max(r["mean_X"] for r in records if r["regime"] == "low_null" and r["gate_p"] == .004)
    high_base = min(r["mean_X"] for r in records if r["regime"] == "high_alternative" and r["gate_p"] == .003)
    high_mismatch = min(r["mean_X"] for r in records if r["regime"] == "high_alternative" and r["gate_p"] == .002)
    result = {
        "classification": "FINITE_GRID_APPROXIMATE_DEM_GATE_MISMATCH_COUNTEREXAMPLES",
        "dem_conversion": {"decompose_errors": True, "approximate_disjoint_errors": True, "stim_version": stim.__version__},
        "grid": {"low_burst_p": LOW_BURST, "high_burst_p": HIGH_BURST,
                 "measurement_p": MEASUREMENT, "gate_p": GATE, "points": len(records)},
        "baseline_gate_fixed_0_003": {"low_null_grid_max_mean_X": low_base, "high_alternative_grid_min_mean_X": high_base},
        "mismatched_gate": {"low_null_gate_0_004_grid_max_mean_X": low_mismatch,
                            "low_excess_over_baseline": low_mismatch-low_base,
                            "high_alternative_gate_0_002_grid_min_mean_X": high_mismatch,
                            "high_shortfall_below_baseline": high_base-high_mismatch},
        "records": records,
        "limitations": [
            "Finite parameter grid counterexamples only; not a continuous DEM envelope or a process-validity theorem.",
            "Results are exact for each constructed independent-event DEM, not the categorical circuit distribution.",
            "No detector histories, stochastic samples, decoder actions, or protected outcomes were used.",
        ],
    }
    out = HERE / "DEM_GATE_NOISE_MISMATCH_AUDIT.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "points": len(records), "baseline": result["baseline_gate_fixed_0_003"],
                      "mismatch": result["mismatched_gate"]}, indent=2))


if __name__ == "__main__":
    main()
