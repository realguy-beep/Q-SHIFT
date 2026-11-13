"""Bounded deterministic construction/inference benchmark; no Stim sampling."""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import tracemalloc

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
WORKSPACE = PACKAGE.parents[1]
sys.path.insert(0, str(PACKAGE / ".." / "phase3a_correlated_noise_preflight"))
sys.path.insert(0, str(WORKSPACE / "outputs" / "qshift_ns3_decoder_research"))
import simulator  # noqa: E402
from beliefmatching_adapter import BeliefMatchingAdapter  # noqa: E402
from beliefmatching import BeliefMatching  # noqa: E402


def times(fn, repeats: int):
    values = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn()
        values.append(time.perf_counter() - start)
    return result, values


def chain_dem(n: int) -> stim.DetectorErrorModel:
    lines = []
    for i in range(n - 1):
        lines.append(f"error(0.002) D{i}")
        lines.append(f"error(0.001) D{i} D{i+1}")
    lines.append(f"error(0.002) D{n-1}")
    # The logical-bearing edge has a detector support not used by another
    # event, avoiding the upstream parser's known same-support aliasing.
    lines.append(f"error(0.0005) D0 D{n-1} L0")
    return stim.DetectorErrorModel("\n".join(lines))


def fixture_rows(n: int) -> np.ndarray:
    rows = [np.zeros(n, dtype=np.uint8)]
    for inds in ((0,), (0, 1), (n // 2, (n // 2 + 1) % n)):
        x = np.zeros(n, dtype=np.uint8)
        for i in inds:
            x[i] ^= 1
        rows.append(x)
    return np.stack(rows)


def matching_dimension_circuit(n: int) -> stim.Circuit:
    """Noise-free circuit carrying the same declared D/L dimensions as a case."""
    lines = ["M " + " ".join(str(i) for i in range(n))]
    for i in range(n):
        lines.append(f"DETECTOR rec[-{n-i}]")
    lines.append(f"OBSERVABLE_INCLUDE(0) rec[-{n}]")
    return stim.Circuit("\n".join(lines))


def run_case(name: str, dem: stim.DetectorErrorModel, sampling_circuit: stim.Circuit,
             generating_identity: str, rows: np.ndarray, *, bp_iters: int = 20) -> dict:
    provenance = f"fixed benchmark DEM from {name}; no online fitting"
    # First construction is reported separately as cold. New instances give a
    # construction-only warm mean without carrying decoder state across runs.
    t0 = time.perf_counter()
    adapter = BeliefMatchingAdapter.from_dem(
        decoder_dem=dem, sampling_circuit=sampling_circuit,
        generating_noise_identity=generating_identity,
        assumed_noise_provenance=provenance, enabled=True, max_bp_iters=bp_iters,
    )
    construct_cold_s = time.perf_counter() - t0
    warm_adapters = []
    _, construct_warm = times(lambda: BeliefMatchingAdapter.from_dem(
        decoder_dem=dem, sampling_circuit=sampling_circuit,
        generating_noise_identity=generating_identity,
        assumed_noise_provenance=provenance, enabled=True, max_bp_iters=bp_iters,
    ), 2)
    # Keep and then release warm objects; a fresh construction per repeat is
    # deliberately used to make construction cost measurable.
    # `times` returns only the final value, so earlier objects become collectible.
    warm_construction_mean_s = float(np.mean(construct_warm))

    t0 = time.perf_counter()
    first = adapter.decode_batch(rows[:1])
    inference_cold_one_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    predictions = adapter.decode_batch(rows)
    inference_cold_batch_s = time.perf_counter() - t0
    _, warm_batch = times(lambda: adapter.decode_batch(rows), 3)
    _, warm_one = times(lambda: adapter.decode_batch(rows[:1]), 3)

    # Private upstream BP flag is collected only as a diagnostic after one
    # deterministic sweep, one row at a time; no decoder behavior is changed.
    convergence = []
    for row in rows:
        adapter.decode_batch(row.reshape(1, -1))
        convergence.append(bool(adapter._decoder._bpd.converge))

    pm_t0 = time.perf_counter()
    matcher = pymatching.Matching.from_detector_error_model(dem)
    pm_construct_s = time.perf_counter() - pm_t0
    pm_t0 = time.perf_counter()
    pm_first = matcher.decode(rows[0])
    pm_first_one_s = time.perf_counter() - pm_t0
    pm_t0 = time.perf_counter()
    matcher.decode_batch(rows)
    pm_first_batch_s = time.perf_counter() - pm_t0
    pm_predictions, pm_batch = times(lambda: matcher.decode_batch(rows), 4)
    _, pm_one = times(lambda: matcher.decode(rows[0]), 4)

    pm_corr_t0 = time.perf_counter()
    corr_matcher = pymatching.Matching.from_detector_error_model(
        dem, enable_correlations=True,
    )
    pm_corr_construct_s = time.perf_counter() - pm_corr_t0
    pm_corr_t0 = time.perf_counter()
    corr_matcher.decode(rows[0], enable_correlations=True)
    pm_corr_first_one_s = time.perf_counter() - pm_corr_t0
    pm_corr_t0 = time.perf_counter()
    corr_matcher.decode_batch(rows, enable_correlations=True)
    pm_corr_first_batch_s = time.perf_counter() - pm_corr_t0
    corr_predictions, pm_corr_batch = times(
        lambda: corr_matcher.decode_batch(rows, enable_correlations=True), 4,
    )
    _, pm_corr_one = times(
        lambda: corr_matcher.decode(rows[0], enable_correlations=True), 4,
    )

    # Allocation tracing is separated from latency measurements. This measures
    # Python allocations only; NumPy/LDPC/PyMatching native memory is omitted.
    tracemalloc.start()
    adapter.decode_batch(rows)
    _, python_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    adapter.close()
    return {
        "name": name,
        "detectors": int(dem.num_detectors),
        "observables": int(dem.num_observables),
        "dem_error_instructions": sum(i.type == "error" for i in dem.flattened()),
        "model_identity": {
            "sampling_circuit_sha256": adapter.identity.sampling_circuit_sha256,
            "generating_noise_identity": adapter.identity.generating_noise_identity,
            "decoder_dem_sha256": adapter.identity.decoder_dem_sha256,
            "assumed_noise_provenance": adapter.identity.assumed_noise_provenance,
            "decoder_model_identity": adapter.identity.identity,
            "detector_ids": list(adapter.identity.detector_ids),
            "observable_ids": list(adapter.identity.observable_ids),
            "observable_semantics": adapter.identity.observable_semantics,
        },
        "fixed_rows": int(len(rows)),
        "bp_iterations_limit": bp_iters,
        "bm_bp_converged_each_row_private_upstream_flag": convergence,
        "bm_predictions": np.asarray(predictions, dtype=np.uint8).tolist(),
        "pm_predictions": np.asarray(pm_predictions, dtype=np.uint8).tolist(),
        "pm_correlations_predictions": np.asarray(corr_predictions, dtype=np.uint8).tolist(),
        "bm_pm_disagreements": int(np.count_nonzero(np.any(predictions != pm_predictions, axis=1))),
        "bm_correlated_pm_disagreements": int(np.count_nonzero(np.any(predictions != corr_predictions, axis=1))),
        "ordinary_vs_correlated_pm_disagreements": int(np.count_nonzero(np.any(pm_predictions != corr_predictions, axis=1))),
        "timing_seconds": {
            "bm_first_construction_after_import": construct_cold_s,
            "bm_construction_warm_mean_2": warm_construction_mean_s,
            "bm_first_single_row_after_construction": inference_cold_one_s,
            "bm_first_batch_after_single_row": inference_cold_batch_s,
            "bm_single_row_warm_mean_3": float(np.mean(warm_one)),
            "bm_full_batch_warm_mean_3": float(np.mean(warm_batch)),
            "pm_construction": pm_construct_s,
            "pm_first_single_row_after_construction": pm_first_one_s,
            "pm_first_batch_after_single_row": pm_first_batch_s,
            "pm_single_row_mean_4": float(np.mean(pm_one)),
            "pm_batch_mean_4": float(np.mean(pm_batch)),
            "pm_corr_construction": pm_corr_construct_s,
            "pm_corr_first_single_row_after_construction": pm_corr_first_one_s,
            "pm_corr_first_batch_after_single_row": pm_corr_first_batch_s,
            "pm_corr_single_row_mean_4": float(np.mean(pm_corr_one)),
            "pm_corr_batch_mean_4": float(np.mean(pm_corr_batch)),
        },
        "python_tracemalloc_peak_bytes_bm_batch": int(python_peak),
        "memory_note": "Python allocations only; native allocations from NumPy, LDPC, SciPy, and PyMatching are excluded.",
        "predictive_semantics": "L0..Lk observable flip predictions in Stim order; no logical labels",
        "pymatching_correlation_flags": {
            "ordinary": {"construction": False, "decode": False},
            "correlation_enabled": {"construction": True, "decode": True},
        },
    }


def main() -> None:
    q_circuit = simulator.build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=.003, measurement_p=.003, bias_ratio=10.0,
        burst_probability=.01, burst_pair=(8, 10),
    )
    q_dem = q_circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=True,
    )
    ns3a = json.loads((PACKAGE / "benchmark_results_ns3a.json").read_text(encoding="utf-8"))
    q_rows = np.asarray(ns3a["qshift_fixed_model"]["fixed_syndromes"], dtype=np.uint8)
    cases = [run_case(
        "Q-SHIFT d3 five-round balanced Z memory, fixed p configuration",
        q_dem, q_circuit,
        "balanced-z-d3-r5 gate=.003 meas=.003 burst=.01 pair=(8,10)",
        q_rows,
    )]
    for n in (10, 40, 80):
        dem = chain_dem(n)
        circuit = matching_dimension_circuit(n)
        cases.append(run_case(
            f"synthetic graphlike chain n={n}", dem, circuit,
            f"synthetic-cycle-n{n}", fixture_rows(n),
        ))
    cold_started = time.perf_counter()
    cold = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--cold-child"],
        capture_output=True, text=True, timeout=15, check=True,
    )
    cold_process_wall_s = time.perf_counter() - cold_started
    cold_probe = json.loads(cold.stdout)
    print(json.dumps({
        "upstream_version": "0.2.0",
        "upstream_commit": "4458c278bbec273c8c1a26411dadccc49222f8ef",
        "python": sys.version,
        "platform": platform.platform(),
        "logical_cpu_count": os.cpu_count(),
        "stim": stim.__version__,
        "numpy": np.__version__,
        "pymatching": pymatching.__version__,
        "ldpc": __import__("importlib.metadata", fromlist=["version"]).version("ldpc"),
        "cases": cases,
        "cold_process_probe": {
            **cold_probe,
            "subprocess_wall_seconds_including_python_start": cold_process_wall_s,
            "timeout_seconds": 15,
        },
        "sampling_called": False,
        "logical_labels_used": False,
        "seed_generation": False,
    }, indent=2))


def cold_process_probe() -> dict:
    """One fresh interpreter's import-to-first-prediction bounded probe."""
    start = time.perf_counter()
    circuit = simulator.build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=.003, measurement_p=.003, bias_ratio=10.0,
        burst_probability=.01, burst_pair=(8, 10),
    )
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    decoder = BeliefMatching.from_detector_error_model(dem, max_bp_iters=20)
    row = np.zeros((1, int(dem.num_detectors)), dtype=np.uint8)
    prediction = decoder.decode_batch(row)
    print(json.dumps({
        "fresh_process_import_to_first_prediction_seconds": time.perf_counter() - start,
        "prediction_shape": list(prediction.shape),
        "sampling_called": False,
    }))


if __name__ == "__main__":
    if "--cold-child" in sys.argv:
        cold_process_probe()
    else:
        main()
