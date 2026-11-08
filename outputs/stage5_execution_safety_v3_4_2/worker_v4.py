"""Worker for the safety wrapper; scientific work is delegated to frozen v2."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
import argparse
import threading
from pathlib import Path

from ownership_runtime_v4 import (atomic_json, atomic_npz, ChildOwnership,
                                  start_deadline_watchdog, LockBusyError)
from safety_runner_v4 import verify_safety_sources

ROOT = Path(__file__).resolve().parents[2]
V2_PATH = ROOT / "outputs/stage5_secondary_inference_repair_v1/stage5_sampling_runner_v2.py"


def _benchmark_overrides(m):
    cfg = json.loads(Path(os.environ["QSHIFT_SAFETY_BENCH_CONFIG"]).read_text(encoding="utf-8"))
    probs = tuple(float(x) for x in cfg["probabilities"])
    roots = int(cfg["roots_per_condition"])
    m.PROBS = probs
    m.ROOTS = roots
    m.CAL_SHOTS = int(cfg["calibration_shots_per_root"])
    m.EVAL_SHOTS = int(cfg["evaluation_shots_per_root"])
    m.TOTAL_ROOTS = roots * len(probs)
    m.TOTAL_SHOTS = m.TOTAL_ROOTS * (m.CAL_SHOTS + m.EVAL_SHOTS)
    seed_rows = cfg["streams"]
    seeds = {(x["kind"], float(x["probability"]), int(x["root"])): int(x["seed"]) for x in seed_rows}
    m.seed_map = lambda: (seeds, cfg)
    m.verify_candidate_screen = lambda: "benchmark-only seed inventory; no Stage 5 seed rows read"
    def benchmark_summary(rootdir, _cfg):
        records = []
        for p in probs:
            for r in range(roots):
                with __import__("numpy").load(rootdir / m.filename(p, r), allow_pickle=False) as z:
                    obs = z["observables"].astype("uint8", copy=False)
                    pred = z["predictions"].astype("uint8", copy=False)
                    records.append({"probability": p, "root": r, "shots": m.EVAL_SHOTS,
                                    "errors": [int(__import__("numpy").count_nonzero(pred[k] != obs)) for k in range(3)]})
        atomic_json(rootdir / "RUNNER_SUMMARY.json", {"benchmark_only": True, "roots": m.TOTAL_ROOTS,
                    "calibration_shots": m.TOTAL_ROOTS*m.CAL_SHOTS, "evaluation_shots": m.TOTAL_ROOTS*m.EVAL_SHOTS,
                    "per_root": records})
        return {"benchmark_only": True}
    m.summarize = benchmark_summary
    # Test-only fault point: archive the returned Stim output, then die before
    # the checkpoint writer is entered, reproducing a lost uncommitted batch.
    if os.environ.get("QSHIFT_SAFETY_FAULT") == "after_sample_before_checkpoint" or os.environ.get("QSHIFT_SAFETY_ACTIVE_SAMPLE_MARKER"):
        original_build = m.build_spatial_burst_circuit
        class SamplerProxy:
            def __init__(self, sampler): self.sampler = sampler
            def sample(self, *args, **kwargs):
                active_marker=os.environ.get("QSHIFT_SAFETY_ACTIVE_SAMPLE_MARKER")
                if active_marker:
                    Path(active_marker).write_text("sampler call entering\n",encoding="utf-8")
                out = self.sampler.sample(*args, **kwargs)
                if os.environ.get("QSHIFT_SAFETY_FAULT") == "after_sample_before_checkpoint":
                    Path(os.environ["QSHIFT_SAFETY_SAMPLE_RETURNED_MARKER"]).write_text("returned\n", encoding="utf-8")
                    os._exit(86)
                if active_marker:
                    try: Path(active_marker).unlink()
                    except FileNotFoundError: pass
                return out
        class CircuitProxy:
            def __init__(self, circuit): self.circuit = circuit
            def __getattr__(self, name): return getattr(self.circuit, name)
            def compile_detector_sampler(self, *args, **kwargs): return SamplerProxy(self.circuit.compile_detector_sampler(*args, **kwargs))
        m.build_spatial_burst_circuit = lambda **kw: CircuitProxy(original_build(**kw))


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--qshift-owner-token',required=True)
    parser.add_argument('--qshift-deadline-monotonic',required=True,type=float)
    args=parser.parse_args(argv)
    run_dir=Path(os.environ.get('QSHIFT_STAGE5_RUN_DIR',ROOT/'outputs/stage5_secondary_inference_repair_v1/run')).resolve()
    completed=threading.Event()
    try:
        start_deadline_watchdog(args.qshift_deadline_monotonic,completed,'worker-bootstrap')
        with ChildOwnership(run_dir,'worker',args.qshift_owner_token,args.qshift_deadline_monotonic):
            verify_safety_sources()
            _execute_frozen_worker(run_dir)
    finally:
        completed.set()

def _execute_frozen_worker(run_dir):
    spec = importlib.util.spec_from_file_location("stage5_frozen_v2_worker", V2_PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    m.RUN = Path(run_dir)
    if os.environ.get("QSHIFT_SAFETY_BENCHMARK") == "1":
        _benchmark_overrides(m)

    original_json = m.atomic_json
    def safe_json(path, obj):
        copy = dict(obj)
        if Path(path).name == "status.json" and copy.get("status") == "completed":
            copy["status"] = "finalizing"
            copy["finalization_requested_unix"] = __import__("time").time()
        atomic_json(Path(path), copy)
    def safe_npz(path, **arrays):
        fault = None
        if os.environ.get("QSHIFT_SAFETY_TEST_MODE") == "1":
            point = os.environ.get("QSHIFT_SAFETY_FAULT")
            if point in {"after_npz_temp_fsync", "after_npz_replace_before_commit", "after_npz_commit"}:
                names = {"after_npz_temp_fsync":"after_temp_fsync_before_replace",
                         "after_npz_replace_before_commit":"after_replace_before_commit_marker",
                         "after_npz_commit":"after_commit_marker"}
                def fault(stage):
                    if stage == names[point]: os._exit(87)
        return atomic_npz(Path(path), arrays, fault=fault)
    m.atomic_json = safe_json
    m.atomic_npz = safe_npz
    try:
        m.execute()
    except BaseException as exc:
        if isinstance(exc, LockBusyError):
            # Never write status while another worker may own the run.
            raise
        status_path = m.RUN / "status.json"
        if status_path.exists():
            try: status = json.loads(status_path.read_text(encoding="utf-8"))
            except Exception: status = {}
            status.update({"status": "failed", "failure_type": type(exc).__name__,
                           "failure_message": str(exc), "failure_traceback": traceback.format_exc()})
            safe_json(status_path, status)
        raise


if __name__ == "__main__":
    main()
