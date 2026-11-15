"""Windows wall-clock wrapper for the bounded pilot process tree."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN_DIR = ROOT / "pilot_runs" / "attempt_001"
LIMIT_SECONDS = 600


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="run the one frozen pilot under deadline")
    parser.add_argument("--expected-head", help="exact frozen commit SHA")
    args = parser.parse_args()
    if not args.execute:
        command = [sys.executable, str(ROOT / "run_pilot.py"), "--dry-run"]
        return subprocess.run(command, cwd=ROOT.parents[1], check=False).returncode
    if os.name != "nt":
        raise SystemExit("execution wrapper requires Windows process-tree termination")
    if not args.expected_head or len(args.expected_head) != 40:
        raise SystemExit("--execute requires --expected-head <40-character commit SHA>")
    started = time.monotonic()
    child_env = os.environ.copy()
    child_env["QSHIFT_V1_WATCHDOG_ACTIVE"] = "1"
    child = subprocess.Popen([sys.executable, str(ROOT / "run_pilot.py"), "--execute",
                              "--expected-head", args.expected_head], cwd=ROOT.parents[1], env=child_env)
    try:
        code = child.wait(timeout=LIMIT_SECONDS)
        print(json.dumps({"status": "child_exited", "returncode": code,
                          "lifetime_seconds": time.monotonic() - started}))
        return code
    except subprocess.TimeoutExpired:
        stop = subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                              capture_output=True, text=True, check=False)
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            raise SystemExit("deadline exceeded and process-tree termination could not be confirmed")
        status = {"schema": "qshift-correlated-pilot-watchdog-v1", "status": "deadline_terminated",
                  "success": False, "pid": child.pid, "taskkill_returncode": stop.returncode,
                  "taskkill_output": stop.stdout[-2000:] + stop.stderr[-2000:],
                  "lifetime_seconds": time.monotonic() - started,
                  "recorded_utc": datetime.now(timezone.utc).isoformat()}
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        target = RUN_DIR / "watchdog_status.json"
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, target)
        return 124

if __name__ == "__main__":
    raise SystemExit(main())
