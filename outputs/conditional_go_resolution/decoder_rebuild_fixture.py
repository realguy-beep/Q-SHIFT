"""Small deterministic PyMatching rebuild and causal-swap feasibility fixture.

This is a feasibility artifact, not a Q-SHIFT performance experiment.  It uses
Stim's native depolarizing circuit and constructs immutable Matching instances
from independently generated DEM objects.
"""
from __future__ import annotations

import threading
import time
import os
import ctypes
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pymatching
import stim


@dataclass(frozen=True)
class DecoderVersion:
    name: str
    gate_p: float
    meas_p: float
    dem: stim.DetectorErrorModel
    matching: pymatching.Matching


def build_version(name: str, gate_p: float, meas_p: float, rounds: int = 5) -> DecoderVersion:
    """Build a valid rotated Z-memory DEM/matcher for the supplied probabilities."""
    if not (0 <= gate_p < 1 and 0 <= meas_p < 1):
        raise ValueError("noise probabilities must be in [0, 1)")
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=3,
        rounds=rounds,
        after_clifford_depolarization=gate_p,
        before_measure_flip_probability=meas_p,
    )
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    if circuit.num_observables != 1:
        raise AssertionError(f"expected one logical observable, found {circuit.num_observables}")
    if matching.num_detectors != circuit.num_detectors:
        raise AssertionError("DEM/matching detector count mismatch")
    if matching.num_fault_ids != circuit.num_observables:
        raise AssertionError("DEM/matching observable count mismatch")
    return DecoderVersion(name, gate_p, meas_p, dem, matching)


def decode(version: DecoderVersion, detectors: np.ndarray) -> np.ndarray:
    d = np.asarray(detectors, dtype=np.uint8)
    if d.ndim != 2 or d.shape[1] != version.matching.num_detectors:
        raise ValueError("detector matrix shape does not match decoder")
    if not np.isin(d, (0, 1)).all():
        raise ValueError("detectors must be binary")
    pred = np.asarray(version.matching.decode_batch(d), dtype=np.uint8)
    if pred.ndim == 2:
        if pred.shape != (len(d), 1):
            raise ValueError("expected one predicted observable per shot")
        pred = pred[:, 0]
    if pred.shape != (len(d),) or not np.isin(pred, (0, 1)).all():
        raise ValueError("invalid prediction shape or values")
    return pred


class BoundaryDecoder:
    """Pins a decoder for a block; publishes a new immutable version only at a boundary."""

    def __init__(self, initial: DecoderVersion):
        self._lock = threading.RLock()
        self._active = initial
        self._active_block: int | None = None
        self._last_completed = -1

    def begin_block(self, block_index: int) -> DecoderVersion:
        with self._lock:
            if self._active_block is not None:
                raise RuntimeError("a block is already active")
            if block_index != self._last_completed + 1:
                raise RuntimeError("blocks must be processed in order")
            self._active_block = block_index
            return self._active  # local immutable snapshot for the complete block

    def complete_block(self, block_index: int) -> None:
        with self._lock:
            if self._active_block != block_index:
                raise RuntimeError("completion does not match active block")
            self._last_completed = block_index
            self._active_block = None

    def publish_after(self, completed_block: int, new_version: DecoderVersion) -> None:
        """Atomically make a ready model active for the next block, never mid-block."""
        with self._lock:
            if self._active_block is not None:
                raise RuntimeError("decoder replacement is forbidden during a block")
            if completed_block != self._last_completed:
                raise RuntimeError("update must use the latest completed block only")
            if new_version.matching.num_detectors != self._active.matching.num_detectors:
                raise RuntimeError("new decoder graph schema differs")
            if new_version.matching.num_fault_ids != self._active.matching.num_fault_ids:
                raise RuntimeError("new decoder observable schema differs")
            self._active = new_version


def noiseless_check(rounds: int = 5, shots: int = 32) -> dict:
    c = stim.Circuit.generated("surface_code:rotated_memory_z", distance=3, rounds=rounds)
    d, o = c.compile_detector_sampler(seed=99870001).sample(
        shots, separate_observables=True
    )
    assert c.num_detectors == 8 * rounds
    assert c.num_observables == 1
    assert not d.any() and not o.any()
    return {"detectors": int(c.num_detectors), "observables": int(c.num_observables), "shots": shots}


def process_memory_bytes() -> dict:
    """Return process working-set and peak values, including native allocations, on Windows."""
    if os.name != "nt":
        return {"available": False, "reason": "Windows process memory API not available"}
    class PMC(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]
    try:
        from ctypes import wintypes
        psapi = ctypes.WinDLL("Psapi.dll")
        kernel32 = ctypes.WinDLL("Kernel32.dll")
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        proc = kernel32.GetCurrentProcess()
        counters = PMC()
        counters.cb = ctypes.sizeof(PMC)
        ok = psapi.GetProcessMemoryInfo(proc, ctypes.byref(counters), counters.cb)
        if not ok:
            return {"available": False, "reason": "GetProcessMemoryInfo returned false"}
        return {"available": True, "working_set_bytes": int(counters.WorkingSetSize),
                "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
                "pagefile_bytes": int(counters.PagefileUsage)}
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}


def run_fixture(seed: int = 99870002) -> dict:
    memory_before = process_memory_bytes()
    started = time.perf_counter()
    old = build_version("nominal", 0.003, 0.003)
    build_old_s = time.perf_counter() - started
    update_started = time.perf_counter()
    updated = build_version("measurement_heavy", 0.001, 0.006)
    rebuild_s = time.perf_counter() - update_started
    independently_built = build_version("measurement_heavy_reference", 0.001, 0.006)
    rebuild_samples = []
    for _ in range(25):
        t0 = time.perf_counter()
        _ = build_version("timing_probe", 0.001, 0.006)
        rebuild_samples.append(time.perf_counter() - t0)
    def weight_map(version):
        found = {}
        for u, v, attrs in version.matching.edges():
            key = tuple(sorted((-1 if u is None else int(u), -1 if v is None else int(v))))
            found[key] = float(attrs["weight"])
        return found
    old_weights, new_weights = weight_map(old), weight_map(updated)
    common_edge_keys = sorted(set(old_weights) & set(new_weights))
    changed_weight_edges = sum(
        not np.isclose(old_weights[k], new_weights[k], rtol=0, atol=1e-12)
        for k in common_edge_keys
    )

    gen = stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=3, rounds=5,
        after_clifford_depolarization=0.001,
        before_measure_flip_probability=0.006,
    )
    detectors, observables = gen.compile_detector_sampler(seed=seed).sample(
        2048, separate_observables=True
    )
    decode_start = time.perf_counter()
    old_pred = decode(old, detectors)
    old_decode_s = time.perf_counter() - decode_start
    decode_start = time.perf_counter()
    new_pred = decode(updated, detectors)
    new_decode_s = time.perf_counter() - decode_start
    reference_pred = decode(independently_built, detectors)
    assert np.array_equal(new_pred, reference_pred)
    assert len(new_pred) == len(observables) == 2048

    # Causality fixture: block 0 is completed under the old model; the update
    # then becomes available for block 1. Block-1 samples never choose its model.
    boundary = BoundaryDecoder(old)
    used0 = boundary.begin_block(0)
    pred0 = decode(used0, detectors[:64])
    boundary.complete_block(0)
    boundary.publish_after(0, updated)
    used1 = boundary.begin_block(1)
    pred1 = decode(used1, detectors[64:128])
    boundary.complete_block(1)
    assert used0 is old and used1 is updated
    assert pred0.shape == pred1.shape == (64,)

    # An attempted swap while a block is active must fail, preserving its pin.
    boundary.begin_block(2)
    try:
        boundary.publish_after(1, old)
    except RuntimeError as e:
        assert "during a block" in str(e)
        active_swap_rejected = True
    else:
        raise AssertionError("mid-block replacement was not rejected")
    boundary.complete_block(2)

    return {
        "fixture": "rotated_memory_z_d3_r5",
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "noiseless": noiseless_check(),
        "schema": {
            "detectors": old.matching.num_detectors,
            "observables": old.matching.num_fault_ids,
            "old_edges": old.matching.num_edges,
            "new_edges": updated.matching.num_edges,
            "common_edge_keys": len(common_edge_keys),
            "changed_weights_on_common_edges": changed_weight_edges,
            "old_dem_error_terms": sum(1 for x in str(old.dem).splitlines() if x.startswith("error(")),
            "new_dem_error_terms": sum(1 for x in str(updated.dem).splitlines() if x.startswith("error(")),
        },
        "paired_samples": int(len(detectors)),
        "prediction_shape": list(new_pred.shape),
        "reference_predictions_exact_match": bool(np.array_equal(new_pred, reference_pred)),
        "old_vs_new_prediction_disagreements": int(np.count_nonzero(old_pred != new_pred)),
        "old_vs_new_prediction_disagreement_rate": float(np.mean(old_pred != new_pred)),
        "old_vs_new_residual_errors": {
            "old": int(np.count_nonzero(old_pred != observables[:, 0])),
            "new": int(np.count_nonzero(new_pred != observables[:, 0])),
        },
        "causal_block_versions": [used0.name, used1.name],
        "active_swap_rejected": active_swap_rejected,
        "build_nominal_seconds": build_old_s,
        "rebuild_candidate_seconds": rebuild_s,
        "rebuild_timing_probe_count": len(rebuild_samples),
        "rebuild_seconds_median": float(np.median(rebuild_samples)),
        "rebuild_seconds_p95": float(np.quantile(rebuild_samples, 0.95)),
        "pymatching_public_set_edge_available": hasattr(updated.matching, "set_edge"),
        "pymatching_edge_related_methods": sorted(x for x in dir(updated.matching) if "edge" in x.lower()),
        "sample_decode_seconds_old": old_decode_s,
        "sample_decode_seconds_new": new_decode_s,
        "process_memory_before": memory_before,
        "process_memory_after_models": process_memory_bytes(),
    }


if __name__ == "__main__":
    import json
    result = run_fixture()
    print(json.dumps(result, indent=2, sort_keys=True))
    from pathlib import Path
    Path(__file__).with_name("FIXTURE_RESULTS.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
