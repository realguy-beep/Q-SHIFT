"""Extract and exactly infer one deterministic Phase 2B circuit fragment."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import threading
import time
from pathlib import Path
import sys

from factor_graph import make_factor_graph
from phase2b_fragments import extract_model, build_fragment
from structured_inference import direct_xor_dp, map_metrics, xor_walsh_posterior


class _MemorySampler:
    """Sample Windows process working set to record a measured peak."""
    def __init__(self):
        self.peak = 0
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.available = False
    def _working_set(self):
        try:
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            counters = Counters(); counters.cb = ctypes.sizeof(counters)
            psapi = ctypes.WinDLL("Psapi.dll")
            kernel = ctypes.WinDLL("Kernel32.dll")
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return None
            return int(counters.PeakWorkingSetSize)
        except Exception:
            return None
    def _run(self):
        while not self.stop.is_set():
            value = self._working_set()
            if value is not None:
                self.available = True
                self.peak = max(self.peak, value)
            self.stop.wait(0.02)
        value = self._working_set()
        if value is not None:
            self.available = True
            self.peak = max(self.peak, value)
    def start(self): self.thread.start()
    def finish(self):
        self.stop.set(); self.thread.join()
        return {"peak_working_set_bytes": self.peak if self.available else None,
                "measurement_method": "Windows GetProcessMemoryInfo sampled at 20ms" if self.available else "unavailable"}


def _json_model(model):
    return [{"name": loc.name, "outcomes": [
        {"label": o.label, "probability": o.probability,
         "detector_mask": o.detector_mask, "observable_mask": o.observable_mask}
        for o in loc.outcomes]} for loc in model.locations]


def _sha256(data: bytes): return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, required=True)
    parser.add_argument("--max-bytes", type=int, default=2*1024**3)
    args = parser.parse_args()
    started = time.perf_counter()
    memory = _MemorySampler(); memory.start()
    print(f"[rounds={args.rounds}] extracting deterministic fault effects", file=sys.stderr, flush=True)
    circuit, model, extraction = extract_model(rounds=args.rounds, memory_basis="z", regime="x_biased")
    effects_path = Path(__file__).resolve().parent / f"FRAGMENT_R{args.rounds}_EFFECTS.json"
    effects = {"rounds": args.rounds, "memory_basis": "z", "regime": "x_biased",
               "circuit_sha256": _sha256(str(circuit).encode("utf-8")),
               "extraction": extraction, "categorical_locations_and_verified_masks": _json_model(model)}
    effects_path.write_text(json.dumps(effects, separators=(",", ":"))+"\n", encoding="utf-8")
    print(f"[rounds={args.rounds}] effect masks saved; building inference summary", file=sys.stderr, flush=True)
    circuit_hash = _sha256(str(circuit).encode("utf-8"))
    graph = make_factor_graph(model)
    detector_count, observable_count = model.detector_count, model.observable_count
    total_bits = detector_count + observable_count
    state_count = 1 << total_bits
    dense_bytes = state_count * 8
    report = {
        "rounds": args.rounds, "memory_basis": "z", "regime": "x_biased",
        "generation_parameters": {"distance": 3, "gate_probability": 0.003,
                                   "measurement_probability": 0.003, "bias_ratio": 10},
        "extraction": extraction, "circuit_sha256": circuit_hash,
        "circuit_detectors": detector_count, "circuit_observables": observable_count,
        "fault_graph": {"fault_variables": len(model.locations),
                        "output_variables": total_bits,
                        "factor_nodes": len(graph["factor_scopes"]),
                        "factor_incidences": sum(map(len, graph["factor_scopes"])),
                        "parity_factor_scope_sizes": list(map(len, graph["parity_scopes"])),
                        "outcomes_per_location": [len(loc.outcomes) for loc in model.locations],
                        "full_configuration_count": str(model.configuration_count),
                        "configuration_log2": sum(math.log2(len(loc.outcomes)) for loc in model.locations)},
        "structured_elimination": {"representation": "ordered XOR parity frontier; after eliminating a location, retain the accumulated detector/logical parity state",
                                   "frontier_width_bits": total_bits,
                                   "max_intermediate_factor_states": state_count,
                                   "dense_float64_output_bytes": dense_bytes,
                                   "conservative_peak_estimate_bytes": 4*dense_bytes+64*1024**2},
        "stochastic_shots_generated": 0,
        "complete_fault_configurations_enumerated": 0,
    }
    if 4*dense_bytes+64*1024**2 > args.max_bytes:
        report["inference"] = {"status": "SKIPPED_RESOURCE_PREFLIGHT",
                               "reason": "Conservative dense transform working-set estimate exceeds the 2 GiB cap; no posterior array allocated."}
    else:
        print(f"[rounds={args.rounds}] starting structured exact posterior over {state_count} states", file=sys.stderr, flush=True)
        inference_started = time.perf_counter()
        posterior, info = xor_walsh_posterior(model, max_bytes=args.max_bytes)
        print(f"[rounds={args.rounds}] inverse transform complete; summarizing all syndromes", file=sys.stderr, flush=True)
        metrics = map_metrics(posterior, detector_count, observable_count)
        report["inference"] = {"status": "COMPLETED", **info, **metrics}
        report["inference_runtime_seconds_including_MAP_summary"] = time.perf_counter()-inference_started
        if args.rounds <= 1:
            direct = direct_xor_dp(model)
            discrepancy = max(abs(float(posterior[mask])-mass) for mask,mass in direct.items())
            report["inference"]["direct_nonnegative_DP_crosscheck_max_abs_difference"] = discrepancy
            if discrepancy > 1e-10:
                raise AssertionError(f"direct DP disagreement {discrepancy}")
    report["total_runtime_seconds"] = time.perf_counter()-started
    report["memory"] = memory.finish()
    evidence = {"report": report, "categorical_locations_and_verified_masks": _json_model(model)}
    out_path = Path(__file__).resolve().parent / f"FRAGMENT_R{args.rounds}.json"
    out_path.write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"rounds": args.rounds, "detectors": detector_count,
                      "fault_locations": len(model.locations),
                      "forced_fault_checks": extraction["forced_nonidentity_checks"],
                      "inference": report["inference"], "memory": report["memory"],
                      "total_runtime_seconds": report["total_runtime_seconds"],
                      "effects_file": str(effects_path),
                      "output": str(out_path)}, indent=2))


if __name__ == "__main__": main()
