"""SQLite persistence for run metadata and bounded telemetry history."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "run_data"
DB_PATH = DATA_DIR / "qshift_dashboard.sqlite3"
MAX_METRIC_ROWS_PER_RUN = 10_000


def connect(db_path: Path | None = None):
    p = Path(db_path or DB_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


@contextmanager
def connection(db_path: Path | None = None):
    """Transaction context that always closes the SQLite handle (including on Windows)."""
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | None = None):
    with connection(db_path) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, created_at REAL NOT NULL, updated_at REAL NOT NULL,
            status TEXT NOT NULL, config_json TEXT NOT NULL, state_json TEXT NOT NULL,
            error TEXT, worker_pid INTEGER
        );
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
            created_at REAL NOT NULL, event_type TEXT NOT NULL, payload_json TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        );
        CREATE INDEX IF NOT EXISTS metrics_run_id_id ON metrics(run_id, id);
        """)


def create_run(run_id: str, config: dict, seed_plan: dict, db_path: Path | None = None):
    now = time.time()
    state = {"status": "queued", "seed_plan": seed_plan, "progress": {}, "summary": None}
    with connection(db_path) as c:
        c.execute("INSERT INTO runs(id,created_at,updated_at,status,config_json,state_json,error,worker_pid) VALUES(?,?,?,?,?,?,NULL,NULL)",
                  (run_id, now, now, "queued", json.dumps(config), json.dumps(state)))


def update_run(run_id: str, status: str | None = None, state: dict | None = None,
               error: str | None = None, worker_pid: int | None = None, db_path: Path | None = None):
    with connection(db_path) as c:
        old = c.execute("SELECT state_json,status FROM runs WHERE id=?", (run_id,)).fetchone()
        if old is None:
            return
        next_state = state if state is not None else json.loads(old["state_json"])
        next_status = status or old["status"]
        next_state["status"] = next_status
        c.execute("UPDATE runs SET updated_at=?,status=?,state_json=?,error=?,worker_pid=COALESCE(?,worker_pid) WHERE id=?",
                  (time.time(), next_status, json.dumps(next_state), error, worker_pid, run_id))


def set_pid(run_id: str, pid: int, db_path: Path | None = None):
    with connection(db_path) as c:
        c.execute("UPDATE runs SET worker_pid=?,updated_at=? WHERE id=?", (pid, time.time(), run_id))


def append_event(run_id: str, event: dict, db_path: Path | None = None):
    event_type = str(event.get("type", "metric"))
    status = event.get("status")
    with connection(db_path) as c:
        row = c.execute("SELECT state_json,status FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            return
        state = json.loads(row["state_json"])
        if event_type == "progress":
            state["progress"] = event
        if event_type in ("completed", "failed", "paused", "stopped", "cancelled", "interrupted"):
            state["summary"] = event.get("summary", state.get("summary"))
        new_status = status or row["status"]
        if event_type == "progress":
            new_status = "running"
        elif event_type in ("completed", "failed", "paused", "stopped", "cancelled", "interrupted"):
            new_status = event_type
        state["status"] = new_status
        c.execute("UPDATE runs SET updated_at=?,status=?,state_json=?,error=? WHERE id=?",
                  (time.time(), new_status, json.dumps(state), event.get("error"), run_id))
        c.execute("INSERT INTO metrics(run_id,created_at,event_type,payload_json) VALUES(?,?,?,?)",
                  (run_id, time.time(), event_type, json.dumps(event)))
        count = c.execute("SELECT COUNT(*) FROM metrics WHERE run_id=?", (run_id,)).fetchone()[0]
        if count > MAX_METRIC_ROWS_PER_RUN:
            c.execute("DELETE FROM metrics WHERE run_id=? AND id IN (SELECT id FROM metrics WHERE run_id=? ORDER BY id ASC LIMIT ?)",
                      (run_id, run_id, count - MAX_METRIC_ROWS_PER_RUN))


def get_run(run_id: str, db_path: Path | None = None):
    with connection(db_path) as c:
        row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "created_at": row["created_at"], "updated_at": row["updated_at"],
            "status": row["status"], "config": json.loads(row["config_json"]),
            "state": json.loads(row["state_json"]), "error": row["error"], "worker_pid": row["worker_pid"]}


def list_runs(limit: int = 30, db_path: Path | None = None):
    with connection(db_path) as c:
        rows = c.execute("SELECT id,created_at,updated_at,status,config_json,state_json,error FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r["id"], "created_at": r["created_at"], "updated_at": r["updated_at"],
             "status": r["status"], "config": json.loads(r["config_json"]),
             "state": json.loads(r["state_json"]), "error": r["error"]} for r in rows]


def get_metrics(run_id: str, limit: int = 2000, db_path: Path | None = None):
    with connection(db_path) as c:
        rows = c.execute("SELECT id,created_at,event_type,payload_json FROM metrics WHERE run_id=? ORDER BY id DESC LIMIT ?", (run_id, limit)).fetchall()
    rows = list(reversed(rows))
    return [{"id": r["id"], "created_at": r["created_at"], "type": r["event_type"],
             "payload": json.loads(r["payload_json"])} for r in rows]


def mark_orphaned_runs_interrupted(db_path: Path | None = None):
    with connection(db_path) as c:
        rows = c.execute("SELECT id,state_json FROM runs WHERE status IN ('running','queued','pausing')").fetchall()
        for r in rows:
            state = json.loads(r["state_json"])
            state["recovery_note"] = "Backend restarted; run can resume from its last atomic checkpoint."
            state["status"] = "interrupted"
            c.execute("UPDATE runs SET status='interrupted',state_json=?,updated_at=? WHERE id=?",
                      (json.dumps(state), time.time(), r["id"]))
