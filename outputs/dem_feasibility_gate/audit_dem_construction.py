"""Deterministic DEM conversion feasibility check; generates no shots."""
from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
import traceback
from pathlib import Path

import numpy as np
import pymatching
import stim

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PILOT = ROOT / "outputs" / "correlation_pilot"
CFG = json.loads((PILOT / "config.json").read_text(encoding="utf-8"))
PHASE2B = (PILOT / CFG["phase2b_source_dir"]).resolve()
sys.path.insert(0, str(PHASE2B))
noise_model = importlib.import_module("noise_model")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def graph_signature(m):
    return sorted(((-1 if u is None else int(u)), (-1 if v is None else int(v)),
                   float(a["weight"]).hex(),
                   tuple(sorted(int(x) for x in a.get("fault_ids", set()))))
                  for u, v, a in m.edges())


def summarize_dem(dem) -> dict:
    text = str(dem)
    lines = text.splitlines()
    error_lines = [line.strip() for line in lines if line.lstrip().startswith("error(")]
    probabilities = []
    all_detectors = set()
    all_observables = set()
    separator_records = 0
    separators = 0
    component_counts = []
    malformed_probability_lines = []
    for line in error_lines:
        match = re.match(r"error\(([^)]+)\)", line)
        if not match:
            malformed_probability_lines.append(line)
            continue
        try:
            probabilities.append(float(match.group(1)))
        except ValueError:
            malformed_probability_lines.append(line)
        if "^" in line:
            separator_records += 1
            separators += line.count("^")
            component_counts.append(line.count("^") + 1)
        all_detectors.update(int(v) for v in re.findall(r"\bD(\d+)\b", line))
        all_observables.update(int(v) for v in re.findall(r"\bL(\d+)\b", line))
    try:
        coords = {str(k): list(v) for k, v in dem.get_detector_coordinates().items()}
        coords_status = "available"
    except Exception as e:
        coords = None
        coords_status = f"unavailable: {type(e).__name__}: {e}"
    probs = np.asarray(probabilities, dtype=np.float64)
    return {
        "sha256_text": sha256_text(text),
        "num_detectors": int(dem.num_detectors),
        "num_observables": int(dem.num_observables),
        "num_error_mechanisms": int(dem.num_errors),
        "error_records_text": len(error_lines),
        "separator_records": separator_records,
        "separator_tokens": separators,
        "separator_component_count_min_max": ([min(component_counts), max(component_counts)] if component_counts else None),
        "detector_ids_in_error_records": sorted(all_detectors),
        "observable_ids_in_error_records": sorted(all_observables),
        "probability_summary": {
            "n": int(probs.size), "min": float(probs.min()) if probs.size else None,
            "median": float(np.median(probs)) if probs.size else None,
            "max": float(probs.max()) if probs.size else None,
            "all_finite": bool(np.isfinite(probs).all()),
            "all_between_zero_and_one": bool(((probs >= 0) & (probs <= 1)).all()),
            "sum_of_mechanism_probabilities_not_a_channel_total": float(probs.sum()) if probs.size else None,
        },
        "malformed_probability_lines": malformed_probability_lines,
        "dem_detector_coordinates_status": coords_status,
        "dem_detector_coordinates": coords,
        "text": text,
    }


def main() -> None:
    freeze = json.loads((PILOT / "PRETEST_FREEZE.json").read_text(encoding="utf-8"))
    freeze_checks = []
    for rel, expected in freeze["sha256"].items():
        path = ROOT / rel
        actual = sha256_file(path) if path.is_file() else None
        freeze_checks.append({"path": rel, "expected_sha256": expected,
                             "actual_sha256": actual, "matches": actual == expected})
    mismatches = [x["path"] for x in freeze_checks if not x["matches"]]
    if freeze.get("status") != "FROZEN_BEFORE_FULL_SAMPLING" or mismatches:
        raise RuntimeError(f"Historical pilot freeze verification failed: {mismatches}")
    result = {
        "status": "COMPLETED_NO_SHOTS",
        "software": {"python": sys.version, "numpy": np.__version__,
                     "stim": stim.__version__, "pymatching": pymatching.__version__},
        "phase2b_pretest_freeze_verification": {
            "status": freeze.get("status"), "file_count": len(freeze_checks),
            "all_hashes_match": not mismatches, "files": freeze_checks},
        "circuit_parameters": {k: CFG[k] for k in (
            "distance", "rounds", "gate_fault_probability_1q", "gate_fault_probability_2q",
            "measurement_flip_probability", "bias_ratio", "regimes", "memory_bases")},
        "conversion_settings": {
            "A": {"decompose_errors": True, "approximate_disjoint_errors": True},
            "B": {"decompose_errors": True, "approximate_disjoint_errors": False}},
        "conditions": [],
        "no_simulation_shots_generated": True,
        "notes": ["Circuit generation and DEM conversion are deterministic model construction, not shot sampling.",
                  "A/B are built from the identical generated Stim circuit for each condition."]
    }
    for basis in CFG["memory_bases"]:
        for regime in CFG["regimes"]:
            row = {"basis": basis, "regime": regime}
            try:
                circuit = noise_model.build_circuit(
                    basis, regime, distance=CFG["distance"], rounds=CFG["rounds"],
                    gate_p=CFG["gate_fault_probability_1q"],
                    measurement_p=CFG["measurement_flip_probability"],
                    bias_ratio=CFG["bias_ratio"])
                circuit_text = str(circuit)
                row["circuit"] = {
                    "construction": "PASS", "sha256": sha256_text(circuit_text),
                    "num_detectors": int(circuit.num_detectors),
                    "num_observables": int(circuit.num_observables),
                    "detector_coordinates": {str(k): list(v) for k, v in circuit.get_detector_coordinates().items()},
                    "dem_building_preserved_same_circuit_for_A_B": True,
                }
            except Exception as e:
                row["circuit"] = {"construction": "FAIL", "exception_type": type(e).__name__,
                                   "exception": str(e), "traceback": traceback.format_exc()}
                result["conditions"].append(row)
                continue
            for variant, approximate in (("A", True), ("B", False)):
                entry = {"conversion": "PASS"}
                try:
                    dem = circuit.detector_error_model(
                        decompose_errors=True, approximate_disjoint_errors=approximate)
                    summary = summarize_dem(dem)
                    circuit_coords = {str(k): list(v) for k, v in circuit.get_detector_coordinates().items()}
                    summary["detector_coordinates_match_circuit"] = (
                        summary["dem_detector_coordinates"] == circuit_coords)
                    summary["detector_id_range_valid"] = (
                        summary["detector_ids_in_error_records"] == list(range(circuit.num_detectors)))
                    summary["observable_ids_valid"] = (
                        summary["observable_ids_in_error_records"] == list(range(circuit.num_observables)))
                    matcher_results = {}
                    for enabled in (False, True):
                        key = "correlations_enabled" if enabled else "correlations_disabled"
                        try:
                            matcher = pymatching.Matching.from_detector_error_model(
                                dem, enable_correlations=enabled)
                            signature = graph_signature(matcher)
                            graph_nodes = {x for edge in signature for x in edge[:2] if x >= 0}
                            zero_prediction = np.asarray(matcher.decode(
                                np.zeros(int(dem.num_detectors), dtype=np.uint8),
                                enable_correlations=enabled), dtype=np.uint8)
                            matcher_results[key] = {
                                "status": "PASS", "num_detectors": int(matcher.num_detectors),
                                "num_fault_ids": int(matcher.num_fault_ids),
                                "num_nodes_in_edge_list": len(graph_nodes), "num_edges": len(signature),
                                "zero_syndrome_decode": zero_prediction.tolist(),
                                "graph_signature": signature,
                            }
                        except Exception as e:
                            matcher_results[key] = {"status": "FAIL", "exception_type": type(e).__name__,
                                                    "exception": str(e), "traceback": traceback.format_exc()}
                    matcher_results["on_off_graphs_identical"] = (
                        matcher_results.get("correlations_disabled", {}).get("graph_signature") ==
                        matcher_results.get("correlations_enabled", {}).get("graph_signature"))
                    serialized_dem = summary.pop("text")
                    entry.update(summary)
                    entry["pymatching"] = matcher_results
                    entry["serialized_dem"] = serialized_dem
                except Exception as e:
                    entry = {"conversion": "FAIL", "exception_type": type(e).__name__,
                             "exception": str(e), "traceback": traceback.format_exc()}
                row[variant] = entry
            a = row.get("A", {})
            b = row.get("B", {})
            if a.get("conversion") == b.get("conversion") == "PASS":
                row["A_vs_B"] = {
                    "same_detector_count": a["num_detectors"] == b["num_detectors"],
                    "same_observable_count": a["num_observables"] == b["num_observables"],
                    "same_detector_coordinates": a["dem_detector_coordinates"] == b["dem_detector_coordinates"],
                    "same_error_mechanism_count": a["num_error_mechanisms"] == b["num_error_mechanisms"],
                    "same_serialized_dem": a["sha256_text"] == b["sha256_text"],
                    "same_separator_tokens": a["separator_tokens"] == b["separator_tokens"],
                    "same_probability_summary": a["probability_summary"] == b["probability_summary"],
                    "same_error_record_count": a["error_records_text"] == b["error_records_text"],
                }
            result["conditions"].append(row)

    # Compact conversion log retains complete tracebacks and DEM text in JSON.
    output_path = OUT / "DEM_CONSTRUCTION_RESULTS.json"
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    compact = []
    for row in result["conditions"]:
        compact.append({"condition": f"{row['basis']}-memory/{row['regime']}",
                        "circuit": row.get("circuit", {}).get("construction"),
                        "A": row.get("A", {}).get("conversion"),
                        "B": row.get("B", {}).get("conversion"),
                        "A_det": row.get("A", {}).get("num_detectors"),
                        "B_det": row.get("B", {}).get("num_detectors"),
                        "A_errors": row.get("A", {}).get("num_error_mechanisms"),
                        "B_errors": row.get("B", {}).get("num_error_mechanisms"),
                        "A_sep": row.get("A", {}).get("separator_tokens"),
                        "B_sep": row.get("B", {}).get("separator_tokens"),
                        "A_match_on": row.get("A", {}).get("pymatching", {}).get("correlations_enabled", {}).get("status"),
                        "B_match_on": row.get("B", {}).get("pymatching", {}).get("correlations_enabled", {}).get("status"),
                        "A_vs_B": row.get("A_vs_B")})
    print(json.dumps({"software": result["software"], "no_shots": True, "conditions": compact}, indent=2))


if __name__ == "__main__":
    main()
