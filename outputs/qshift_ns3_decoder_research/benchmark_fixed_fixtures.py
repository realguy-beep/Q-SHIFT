"""Deterministic fixed-syndrome comparison; this is not an LER experiment."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import tracemalloc

import numpy as np
import pymatching
import stim

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "outputs" / "phase2b_pauli_bias"))
sys.path.insert(0, str(ROOT / "outputs" / "phase3a_correlated_noise_preflight"))
from decoder_prototypes import DetectorModel, FactorGraphBP
import simulator


def deterministic_fixtures(model: DetectorModel) -> np.ndarray:
    """Zero row plus selected single-event syndromes, with no sampled labels."""
    rows = [np.zeros(model.n_detectors, dtype=np.uint8)]
    selected = []
    predicates = (
        lambda f: len(f.detectors) == 1 and f.logical == 0,
        lambda f: len(f.detectors) == 2 and f.logical == 0,
        lambda f: f.logical == 1 and len(f.detectors) > 0,
        lambda f: set(f.detectors) == {8, 10},
    )
    for predicate in predicates:
        hit = next((f for f in model.mechanisms if predicate(f)), None)
        if hit is not None and hit not in selected:
            selected.append(hit)
    for fault in selected:
        row = np.zeros(model.n_detectors, dtype=np.uint8)
        for d in fault.detectors:
            row[d] ^= 1
        rows.append(row)
    return np.stack(rows)


def mean_seconds(fn, repeats: int) -> float:
    start = time.perf_counter()
    for _ in range(repeats):
        fn()
    return (time.perf_counter() - start) / repeats


def compare_models(pm_dem, bp_dem=None, *, pm_repeats=3, bp_repeats=1,
                   bp_iterations=50) -> dict:
    """Compare identical fixed syndromes; identify different DEM representations."""
    bp_dem = pm_dem if bp_dem is None else bp_dem
    t0 = time.perf_counter()
    bp_model = DetectorModel.from_stim_dem(bp_dem)
    bp_model_build_s = time.perf_counter() - t0
    x = deterministic_fixtures(bp_model)
    pm_results, timing = {}, {"bp_model_parse_s": bp_model_build_s}
    matchers = {}
    for enabled in (False, True):
        t0 = time.perf_counter()
        matcher = pymatching.Matching.from_detector_error_model(pm_dem, enable_correlations=enabled)
        timing[f"pymatching_corr_{enabled}_construction_s"] = time.perf_counter() - t0
        matchers[enabled] = matcher
        pm_results[str(enabled)] = np.asarray(
            matcher.decode_batch(x, enable_correlations=enabled), dtype=np.uint8
        ).tolist()
        timing[f"pymatching_corr_{enabled}_batch_s"] = mean_seconds(
            lambda: matcher.decode_batch(x, enable_correlations=enabled), pm_repeats
        )
    bp = FactorGraphBP(bp_model, iterations=bp_iterations, damping=.25)
    bp_result, bp_diagnostics = bp.decode_batch_with_diagnostics(x)
    timing["bp_batch_s"] = mean_seconds(
        lambda: bp.decode_batch_with_diagnostics(x), bp_repeats
    )
    ordinary = np.asarray(pm_results["False"], dtype=np.uint8)
    correlated = np.asarray(pm_results["True"], dtype=np.uint8)
    return {
        "detectors": bp_model.n_detectors,
        "observables": 1,
        "bp_dem_mechanisms": bp_model.n_mechanisms,
        "pm_dem_error_instructions": sum(i.type == "error" for i in pm_dem.flattened()),
        "fixed_syndrome_rows": len(x),
        "fixed_syndromes": x.tolist(),
        "pymatching_predictions": pm_results,
        "bp_predictions": bp_result.tolist(),
        "bp_diagnostics": [d.__dict__ for d in bp_diagnostics],
        "disagreement_counts_on_fixed_rows": {
            "ordinary_vs_correlated_matching": int(np.count_nonzero(np.any(ordinary != correlated, axis=1))),
            "bp_vs_ordinary_matching": int(np.count_nonzero(np.any(bp_result != ordinary, axis=1))),
            "bp_vs_correlated_matching": int(np.count_nonzero(np.any(bp_result != correlated, axis=1))),
        },
        "timings": timing,
        "timing_method": f"perf_counter; means over fixed batch repeats (PM={pm_repeats}, BP={bp_repeats})",
        "interpretation": "Prediction differences only; no logical labels, stochastic shots, or LER scoring.",
    }


def synthetic_graphlike_dem(n_detectors: int) -> stim.DetectorErrorModel:
    """Fixed cycle graph DEM used only for algorithmic scaling measurements."""
    # DEM detector declarations are optional and Stim's text syntax does not
    # take a detector index as an argument. Every ID is introduced below.
    lines = []
    for i in range(n_detectors):
        lines.append(f"error(0.002) D{i}")
        lines.append(f"error(0.001) D{i} D{(i + 1) % n_detectors}")
    lines.append("error(0.0005) D0 L0")
    return stim.DetectorErrorModel("\n".join(lines))


def main() -> None:
    q_result: dict
    t0 = time.perf_counter()
    qshift = simulator.build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=.003, measurement_p=.003, bias_ratio=10.0,
        burst_probability=.01, burst_pair=(8, 10),
    )
    circuit_build_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    raw = qshift.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
    raw_dem_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    graph = qshift.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    decomposed_dem_s = time.perf_counter() - t0
    q_result = compare_models(graph, raw)
    # Measure Python allocation peak separately so tracing does not distort
    # the latency measurements (native C++ allocations remain invisible).
    bp_model = DetectorModel.from_stim_dem(raw)
    bp_fixtures = deterministic_fixtures(bp_model)
    tracemalloc.start()
    FactorGraphBP(bp_model, iterations=12, damping=.25).decode_batch_with_diagnostics(bp_fixtures)
    _, python_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    q_result["construction_timings_s"] = {
        "stim_circuit": circuit_build_s,
        "hamld_style_undecomposed_approximate_dem": raw_dem_s,
        "pymatching_decomposed_approximate_dem": decomposed_dem_s,
    }
    q_result["python_tracemalloc_peak_bytes"] = python_peak
    q_result["memory_limit"] = "Python allocations only; native C++ extension allocations are not captured."
    q_result["representation_note"] = (
        "BP consumes the undecomposed approximate DEM; PyMatching consumes the decomposed approximate DEM. "
        "These are not identical model representations, so differences are algorithm-plus-representation."
    )
    q_result["correlation_flags"] = {
        "construct": "Matching.from_detector_error_model(dem, enable_correlations=flag)",
        "decode": "matching.decode_batch(syndromes, enable_correlations=the_same_flag)",
        "true_arm": "flag=True at both construction and decode; false arm uses False at both.",
    }
    scaling = []
    for n_det in (10, 20, 40, 80):
        dem = synthetic_graphlike_dem(n_det)
        result = compare_models(dem, pm_repeats=5, bp_repeats=1, bp_iterations=50)
        result["fixture_kind"] = "deterministically constructed cycle DEM; no sampled shots"
        scaling.append(result)
    print(json.dumps({
        "python": sys.version,
        "stim": stim.__version__,
        "numpy": np.__version__,
        "pymatching": pymatching.__version__,
        "logical_cpu_count": os.cpu_count(),
        "qshift_fixed_model": q_result,
        "synthetic_scaling": scaling,
        "sampling_called": False,
        "logical_labels_used": False,
    }, indent=2))


if __name__ == "__main__":
    main()
