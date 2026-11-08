"""Owned recovery worker: reconcile saved arrays, then delegate frozen v2 work."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V42 = ROOT / "outputs/stage5_execution_safety_v3_4_2"
sys.path.insert(0, str(V42))
sys.path.insert(0, str(HERE))

from ownership_runtime_v4 import ChildOwnership, start_deadline_watchdog  # noqa: E402
from atomic_safety_v44 import (atomic_write_json, sha256_file, write_committed_npz)  # noqa: E402
from recovery_service_v44 import load_frozen_context, reconcile_recovery_copy  # noqa: E402

V2_PATH = ROOT / "outputs/stage5_secondary_inference_repair_v1/stage5_sampling_runner_v2.py"


def _inside(path: Path, run_dir: Path) -> None:
    try:
        Path(path).resolve().relative_to(Path(run_dir).resolve())
    except ValueError as exc:
        raise ValueError("recovery worker write escaped its recovery directory") from exc


def _execute_frozen_worker(run_dir: Path, deadline: float) -> dict:
    run_dir = Path(run_dir).resolve()
    context = load_frozen_context()
    reconciliation = reconcile_recovery_copy(
        run_dir, context, deadline_monotonic=deadline)
    spec = importlib.util.spec_from_file_location("stage5_frozen_v2_recovery_worker", V2_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import frozen Stage 5 worker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.RUN = run_dir

    def safe_json(path, value):
        path = Path(path)
        _inside(path, run_dir)
        payload = dict(value)
        if path.name == "status.json" and payload.get("status") == "completed":
            payload["status"] = "finalizing"
            payload["finalization_requested_unix"] = time.time()
        return atomic_write_json(path, payload, run_dir=run_dir,
                                 expected_old_sha256=sha256_file(path),
                                 deadline_monotonic=deadline)

    def safe_npz(path, **arrays):
        path = Path(path)
        _inside(path, run_dir)
        marker = Path(str(path) + ".commit.json")
        return write_committed_npz(
            path, arrays, run_dir=run_dir,
            expected_archive_sha256=sha256_file(path),
            expected_marker_sha256=sha256_file(marker),
            deadline_monotonic=deadline,
        )

    module.atomic_json = safe_json
    module.atomic_npz = safe_npz
    module.execute()
    return reconciliation


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--qshift-owner-token", required=True)
    parser.add_argument("--qshift-deadline-monotonic", required=True, type=float)
    args = parser.parse_args(argv)
    run_dir = Path(os.environ["QSHIFT_STAGE5_RUN_DIR"]).resolve()
    deadline = float(args.qshift_deadline_monotonic)
    completed = threading.Event()
    try:
        start_deadline_watchdog(deadline, completed, "recovery-worker-bootstrap")
        with ChildOwnership(run_dir, "worker", args.qshift_owner_token, deadline):
            from recovery_runner_v44 import verify_v44_freeze
            verify_v44_freeze()
            result = _execute_frozen_worker(run_dir, deadline)
            print(json.dumps({"status": "worker_returned", "reconciliation": result,
                              "new_samples_generated_by_reconciliation": 0}, default=str))
            return 0
    except BaseException as exc:
        # Failure status is best effort and only ever written inside the copy.
        try:
            status_path = run_dir / "status.json"
            if status_path.is_file() and time.monotonic() < deadline:
                status = json.loads(status_path.read_text(encoding="utf-8"))
                status.update({"status": "worker_failed", "failure_type": type(exc).__name__,
                               "failure_message": str(exc),
                               "failure_traceback": traceback.format_exc()})
                atomic_write_json(status_path, status, run_dir=run_dir,
                                  expected_old_sha256=sha256_file(status_path),
                                  deadline_monotonic=deadline)
        except Exception:
            pass
        raise
    finally:
        completed.set()


if __name__ == "__main__":
    raise SystemExit(main())
