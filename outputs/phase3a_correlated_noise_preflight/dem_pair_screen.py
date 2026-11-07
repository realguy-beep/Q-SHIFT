"""No-shot scan of data-qubit burst-pair DEM/graph compatibility."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import stim
import pymatching

from simulator import build_spatial_burst_circuit

OUT = Path(__file__).resolve().parent


def main():
    base = build_spatial_burst_circuit(gate_p=0, measurement_p=0,
                                      burst_probability=0, burst_pair=(8, 10))
    data = sorted({int(t.value) for inst in base if inst.name == "M"
                   for t in inst.targets_copy() if t.is_qubit_target})
    coords = {}
    for inst in base:
        if inst.name == "QUBIT_COORDS":
            for t in inst.targets_copy():
                coords[int(t.value)] = list(inst.gate_args_copy())
    results = []
    for pair in itertools.combinations(data, 2):
        c = build_spatial_burst_circuit(gate_p=0, measurement_p=0,
            burst_probability=0.1, burst_pair=pair)
        row = {"pair": list(pair), "coordinates": [coords.get(pair[0]), coords.get(pair[1])],
               "detectors": c.num_detectors, "observables": c.num_observables,
               "decompose_true": "pass", "dem_errors": None,
               "py_matching_graph": "not_attempted", "dem_error_records": [],
               "decomposition_exception": None, "nondecomposed_dem": "not_attempted",
               "nondecomposed_py_matching": "not_attempted"}
        try:
            dem = c.detector_error_model(decompose_errors=True,
                approximate_disjoint_errors=True)
            row["dem_errors"] = dem.num_errors
            row["dem_error_records"] = [line for line in str(dem).splitlines()
                if line.startswith("error(")]
            try:
                pm = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
                row["py_matching_graph"] = "pass"
                row["graph_edges"] = len(pm.edges())
            except Exception as exc:
                row["py_matching_graph"] = "fail"
                row["py_matching_exception"] = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            row["decompose_true"] = "fail"
            row["decomposition_exception"] = f"{type(exc).__name__}: {exc}"
            try:
                dem = c.detector_error_model(decompose_errors=False,
                    approximate_disjoint_errors=True)
                row["nondecomposed_dem"] = "pass"
                row["nondecomposed_error_records"] = [line for line in str(dem).splitlines()
                    if line.startswith("error(")]
                try:
                    pm = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
                    row["nondecomposed_py_matching"] = "pass"
                    row["nondecomposed_graph_edges"] = len(pm.edges())
                except Exception as pm_exc:
                    row["nondecomposed_py_matching"] = "fail"
                    row["nondecomposed_py_matching_exception"] = f"{type(pm_exc).__name__}: {pm_exc}"
            except Exception as dem_exc:
                row["nondecomposed_dem"] = "fail"
                row["nondecomposed_dem_exception"] = f"{type(dem_exc).__name__}: {dem_exc}"
        results.append(row)
    selected = next(x for x in results if x["pair"] == [8, 10])
    payload = {
        "status": "NO_SHOT_STRUCTURAL_SCREEN_COMPLETE",
        "purpose": "Select/report DEM graph-compatibility properties only; no outcomes or decoder performance were sampled.",
        "fault": "single CORRELATED_ERROR X on a data pair after the first MR boundary",
        "probability": 0.1,
        "data_qubits": data,
        "selected_pair": selected,
        "pair_count": len(results),
        "decomposition_pass_count": sum(x["decompose_true"] == "pass" for x in results),
        "decomposition_fail_count": sum(x["decompose_true"] == "fail" for x in results),
        "results": results,
    }
    (OUT / "DEM_PAIR_SCREEN.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("status", "pair_count", "decomposition_pass_count",
        "decomposition_fail_count", "selected_pair")}, indent=2))


if __name__ == "__main__":
    main()
