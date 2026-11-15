"""Windows process-tree watchdog for the one V1.1 evaluation attempt."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
LIMIT_SECONDS = 600


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--v1-repo", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        return subprocess.run([sys.executable, str(ROOT / "run_eval.py"), "--dry-run",
                               "--expected-head", args.expected_head,
                               "--v1-repo", str(args.v1_repo)], cwd=REPO, check=False).returncode
    if os.name != "nt":
        raise SystemExit("V1.1 execution watchdog is Windows-only")
    started = time.monotonic()
    env = os.environ.copy()
    env["QSHIFT_V1_1_WATCHDOG_ACTIVE"] = "1"
    child = subprocess.Popen([sys.executable, str(ROOT / "run_eval.py"), "--execute",
                              "--expected-head", args.expected_head,
                              "--v1-repo", str(args.v1_repo)], cwd=REPO, env=env)
    try:
        code = child.wait(timeout=LIMIT_SECONDS)
        lifetime = time.monotonic() - started
        if lifetime >= LIMIT_SECONDS:
            print(json.dumps({"status": "deadline_boundary_failure", "returncode": code,
                              "lifetime_seconds": lifetime, "success": False}))
            return 124
        print(json.dumps({"status": "child_exited", "returncode": code,
                          "lifetime_seconds": lifetime, "success": code == 0}))
        return code
    except subprocess.TimeoutExpired:
        stop = subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                              capture_output=True, text=True, check=False)
        try:
            child.wait(timeout=15)
            reaped = True
        except subprocess.TimeoutExpired:
            reaped = False
        status = {"schema": "qshift-correlated-decoder-v1.1-watchdog-status-v1",
                  "status": "deadline_terminated" if reaped else "termination_unconfirmed",
                  "success": False, "pid": child.pid,
                  "taskkill_returncode": stop.returncode,
                  "taskkill_output": (stop.stdout + stop.stderr)[-3000:],
                  "reaped": reaped, "lifetime_seconds": time.monotonic() - started}
        run_dir = ROOT / "pilot_runs/attempt_001"
        run_dir.mkdir(parents=True, exist_ok=True)
        target = run_dir / "watchdog_status.json"
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, target)
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
