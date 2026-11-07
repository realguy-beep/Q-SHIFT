"""Subprocess manager for run isolation, bounded live telemetry, and safe controls."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import storage

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = storage.DATA_DIR / "runs"
ACTIVE_STATES = {"queued", "running", "pausing"}


class WorkerManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.processes: dict[str, subprocess.Popen] = {}
        self.threads: dict[str, threading.Thread] = {}
        self.subscribers: dict[str, set[queue.Queue]] = {}

    def active_run(self):
        for run in storage.list_runs(limit=100):
            if run["status"] in ACTIVE_STATES:
                return run
        return None

    @staticmethod
    def worker_script_for_config(config: dict) -> Path:
        """Keep the historical worker intact while routing structured runs."""
        kind = config.get("worker_kind", "legacy")
        if kind == "legacy":
            name = "worker.py"
        elif kind == "structured_3d_cnn":
            name = "structured_worker.py"
        else:
            raise RuntimeError(f"Unsupported worker kind: {kind}")
        return Path(__file__).with_name(name)

    def allocations(self, exclude_run_id: str | None = None):
        found = []
        if not RUNS_DIR.exists():
            return found
        for p in RUNS_DIR.glob("*/seed_inventory.json"):
            if exclude_run_id and p.parent.name == exclude_run_id:
                continue
            try:
                found.append(json.loads(p.read_text(encoding="utf-8"))["plan"])
            except Exception:
                continue
        return found

    def start(self, run_id: str, config_path: Path, resume: bool = False):
        with self.lock:
            active = self.active_run()
            if active is not None and active["id"] != run_id:
                raise RuntimeError("Another training run is already active.")
            if run_id in self.processes and self.processes[run_id].poll() is None:
                raise RuntimeError("This run already has a live worker process.")
            run_dir = RUNS_DIR / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "control.request").unlink(missing_ok=True)
            (run_dir / "checkpoint.request").unlink(missing_ok=True)
            saved_config = json.loads(config_path.read_text(encoding="utf-8"))
            worker_script = self.worker_script_for_config(saved_config)
            cmd = [sys.executable, "-u", str(worker_script),
                   "--config", str(config_path.resolve()), "--run-dir", str(run_dir.resolve())]
            if resume:
                cmd.append("--resume")
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["QSHIFT_RUN_ID"] = run_id
            proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                    errors="replace", bufsize=1, shell=False, env=env)
            self.processes[run_id] = proc
            storage.set_pid(run_id, proc.pid)
            storage.update_run(run_id, status="running")
            th = threading.Thread(target=self._drain, args=(run_id, proc), daemon=True,
                                  name=f"qshift-worker-{run_id[:8]}")
            self.threads[run_id] = th
            th.start()
            return proc.pid

    def _publish(self, run_id: str, event: dict):
        for q in list(self.subscribers.get(run_id, set())):
            try:
                q.put_nowait(event)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except (queue.Empty, queue.Full):
                    pass

    def _drain(self, run_id: str, proc: subprocess.Popen):
        last_log = None
        terminal_seen = False
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict) or "type" not in event:
                        raise ValueError("worker event is not an object with a type")
                except Exception:
                    last_log = line[-2000:]
                    continue
                storage.append_event(run_id, event)
                self._publish(run_id, event)
                terminal_seen |= event.get("type") in {"completed", "failed", "paused", "stopped", "interrupted"}
        except Exception as exc:
            last_log = f"Worker event reader failed: {exc}"
        finally:
            code = proc.wait()
            if not terminal_seen:
                run = storage.get_run(run_id)
                if run and run["status"] in ACTIVE_STATES:
                    event = {"type": "interrupted", "status": "interrupted",
                             "error": last_log or f"Worker exited without a terminal event (exit code {code}).",
                             "summary": {"exit_code": code, "last_log_line": last_log}}
                    storage.append_event(run_id, event)
                    self._publish(run_id, event)
            with self.lock:
                self.processes.pop(run_id, None)

    def subscribe(self, run_id: str) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=64)
        self.subscribers.setdefault(run_id, set()).add(q)
        return q

    def unsubscribe(self, run_id: str, q: queue.Queue):
        self.subscribers.get(run_id, set()).discard(q)

    def control(self, run_id: str, action: str):
        run = storage.get_run(run_id)
        if not run:
            raise KeyError("Run not found.")
        run_dir = RUNS_DIR / run_id
        proc = self.processes.get(run_id)
        if action == "resume":
            if run["status"] not in {"paused", "stopped", "interrupted", "failed"}:
                raise RuntimeError("Only paused, stopped, interrupted, or failed runs can resume.")
            config_path = run_dir / "config.json"
            if not config_path.is_file():
                raise RuntimeError("Saved run configuration is missing.")
            cfg = run.get("config") or {}
            has_checkpoint = ((run_dir / "checkpoint.pt").is_file() if cfg.get("worker_kind") != "structured_3d_cnn"
                              else any((run_dir / "checkpoints").glob("*.pt")))
            if not has_checkpoint:
                raise RuntimeError("No safe checkpoint exists; this run cannot resume.")
            return self.start(run_id, config_path, resume=True)
        if action in {"pause", "stop"}:
            if proc is None or proc.poll() is not None:
                raise RuntimeError("No active worker is running for this run.")
            (run_dir / "control.request").write_text(action, encoding="utf-8")
            storage.update_run(run_id, status="pausing")
            return {"requested": action, "at": "next completed mini-batch boundary"}
        if action == "checkpoint":
            if proc is None or proc.poll() is not None:
                if run.get("config", {}).get("worker_kind") == "structured_3d_cnn":
                    has_checkpoint = any((run_dir / "checkpoints").glob("*.pt"))
                else:
                    has_checkpoint = (run_dir / "checkpoint.pt").is_file()
                if has_checkpoint:
                    return {"checkpoint": "already available"}
                raise RuntimeError("No active worker and no checkpoint available.")
            (run_dir / "checkpoint.request").write_text("checkpoint", encoding="utf-8")
            return {"requested": "checkpoint", "at": "next completed mini-batch boundary"}
        raise ValueError("Unsupported run action.")

    def shutdown(self, timeout: float = 15.0):
        with self.lock:
            active = list(self.processes.items())
        for run_id, proc in active:
            if proc.poll() is None:
                try:
                    (RUNS_DIR / run_id / "control.request").write_text("pause", encoding="utf-8")
                except Exception:
                    pass
        deadline = time.time() + timeout
        for _, proc in active:
            remaining = max(0.0, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.terminate()

