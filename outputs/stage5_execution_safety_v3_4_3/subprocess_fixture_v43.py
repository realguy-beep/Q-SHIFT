"""Subprocess-only failure injector for disposable v3.4.3 test fixtures."""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from atomic_safety_v43 import InterProcessFileLock, atomic_write_bytes


def main():
    action = sys.argv[1]
    if action == "crash-npz":
        run_dir = Path(sys.argv[2]); target = Path(sys.argv[3]); stage_to_crash = sys.argv[4]
        import numpy as np
        from atomic_safety_v43 import write_committed_npz
        arrays = {"payload": np.asarray([1, 0, 1], dtype=np.uint8)}
        def fail(stage):
            if stage == stage_to_crash:
                os._exit(71)
        write_committed_npz(target, arrays, run_dir=run_dir,
            expected_archive_sha256=None, expected_marker_sha256=None,
            deadline_monotonic=time.monotonic() + 20, fault=fail)
        return 0
    if action == "crash-update-npz":
        run_dir = Path(sys.argv[2]); target = Path(sys.argv[3]); stage_to_crash = sys.argv[4]
        import numpy as np
        from atomic_safety_v43 import sha256_file, write_committed_npz
        marker = Path(str(target) + ".commit.json")
        arrays = {"payload": np.asarray([1, 0, 1], dtype=np.uint8)}
        def fail(stage):
            if stage == stage_to_crash:
                os._exit(71)
        write_committed_npz(target, arrays, run_dir=run_dir,
            expected_archive_sha256=sha256_file(target), expected_marker_sha256=sha256_file(marker),
            deadline_monotonic=time.monotonic() + 20, fault=fail)
        return 0
    if action == "hold-lock":
        target = Path(sys.argv[2]); ready = Path(sys.argv[3]); release = Path(sys.argv[4])
        lock = target.with_name(f".{target.name}.v43.lock")
        with InterProcessFileLock(lock, deadline_monotonic=time.monotonic() + 10):
            ready.write_text("ready", encoding="utf-8")
            limit = time.monotonic() + 10
            while not release.exists() and time.monotonic() < limit:
                time.sleep(0.005)
            if not release.exists():
                return 3
        return 0
    if action == "write-status":
        target, run_dir, expected, payload, outcome = map(Path, sys.argv[2:])
        expected_hash = expected.read_text(encoding="ascii").strip() or None
        try:
            result = atomic_write_bytes(target, payload.read_bytes(), run_dir=run_dir,
                expected_old_sha256=expected_hash, deadline_monotonic=time.monotonic() + 1,
                backoff=(0.01, 0.02))
            state = {"state": "written", "transaction_id": result["transaction_id"]}
            code = 0
        except Exception as exc:
            state = {"state": type(exc).__name__, "message": str(exc)}
            code = 2
        outcome.write_text(json.dumps(state), encoding="utf-8")
        return code
    raise ValueError(f"unknown fixture action {action}")


if __name__ == "__main__":
    raise SystemExit(main())
