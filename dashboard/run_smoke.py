"""Run one authorized 10,000-sample end-to-end smoke test through the worker manager.

This is a console fallback for environments where localhost browser access is
blocked. It uses the same run configuration, seed screening, SQLite store, and
subprocess worker as the dashboard, without starting a second HTTP server.
"""
from __future__ import annotations

import json
import argparse
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for entry in (str(ROOT), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import app as dashboard_app  # noqa: E402
import storage  # noqa: E402
from configuration import DEFAULT_CONFIG  # noqa: E402
from seed_protocol import screen_plan, seed_plan  # noqa: E402


def sync_route(coroutine):
    """Run the no-await FastAPI handler body without a Windows asyncio loop."""
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    raise RuntimeError("start route unexpectedly awaited an asynchronous operation")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=DEFAULT_CONFIG["seed"],
                        help="Fresh seed root; the default is already used by the saved smoke and will be rejected on rerun.")
    args = parser.parse_args()
    storage.init_db()
    storage.mark_orphaned_runs_interrupted()
    active = dashboard_app.manager.active_run()
    if active:
        raise SystemExit(f"Refusing to start another run while {active['id']} is {active['status']}.")
    cfg = dict(DEFAULT_CONFIG)
    cfg["seed"] = int(args.seed)
    plan = seed_plan(cfg["seed"], cfg["training_shots"], cfg["validation_shots"],
                     cfg["test_shots"], cfg["batch_size"])
    screening = screen_plan(plan, dashboard_app.manager.allocations())
    if not screening["passed"]:
        raise SystemExit(f"Seed collision check failed: {screening['collisions']}")
    result = sync_route(dashboard_app.start_run(dashboard_app.StartRequest(config=cfg)))
    run_id = result["run_id"]
    print(json.dumps({"event": "started", "run_id": run_id, "run_directory": result["run_directory"],
                      "training_shots": cfg["training_shots"], "validation_shots": cfg["validation_shots"],
                      "test_shots": cfg["test_shots"], "seed_screen": result["seed_screen"]}, indent=2), flush=True)
    worker = dashboard_app.manager.processes[run_id]
    try:
        code = worker.wait(timeout=900)
        thread = dashboard_app.manager.threads.get(run_id)
        if thread is not None:
            thread.join(timeout=10)
        run = storage.get_run(run_id)
        print(json.dumps({"event": "finished", "worker_exit_code": code, "run": run,
                          "metrics": storage.get_metrics(run_id, limit=2000)}, indent=2, allow_nan=False), flush=True)
        if code != 0 or not run or run["status"] != "completed":
            raise SystemExit(1)
    except subprocess.TimeoutExpired as exc:
        dashboard_app.manager.control(run_id, "pause")
        raise SystemExit(f"Smoke run exceeded 900 seconds and was asked to pause: {exc}") from exc
    finally:
        dashboard_app.manager.shutdown(timeout=15)


if __name__ == "__main__":
    main()
