"""Recoverable, fail-closed runs (audit F7). Extends v8 runkit's guards; v8 is unchanged. No study is wired here.

A run directory holds one attempt:
  RUN.json                    exclusive reservation: run_id, approved head, freeze hash, workers
  journal.jsonl               the parent's fsynced events
  events/<job>.jsonl          the worker's fsynced events: started, sampling_started, committed
  staging/<job>/              files being written (never read by analysis)
  episodes/<job>/             committed: record.json, archive.npz, COMMIT.json (run_id + sizes + hashes)
  partial/<job>/              staging files preserved after a failure
  RUN_STATUS.json / FAILURE.json / RECOVERY.json

Commit: all three files are written and fsynced in staging/, then the folder is renamed to episodes/ in one step.
Renaming onto an existing folder fails, so a committed episode is never replaced.
Everything after the reservation, pool startup included, is inside the failure handler.
A process kill cannot run that handler: `recover` then records what is on disk. It never resumes or reruns anything;
whether to rerun is a protocol decision.

Limits: directory entries are not fsynced (Windows has no portable call), so power-loss durability is not claimed."""
from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from multiprocessing import get_context
from pathlib import Path

INFRA = (OSError, MemoryError, EOFError)
FILES = ("archive.npz", "record.json")


class RunStop(RuntimeError):
    pass


class ReservationError(SystemExit):
    pass


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write_new(path, data):
    """Create (never overwrite) and fsync."""
    with open(path, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def jbytes(obj):
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode()


def append_event(path, event, **kw):
    with open(path, "ab") as f:
        f.write((json.dumps({"t": now(), "event": event, **kw}, sort_keys=True) + "\n").encode())
        f.flush()
        os.fsync(f.fileno())


def read_events(path):
    """-> (events, torn): a torn last line (killed mid-append) is reported, not fatal. A bad earlier line raises."""
    if not Path(path).exists():
        return [], False
    lines = Path(path).read_bytes().split(b"\n")
    tail, out = lines.pop(), [json.loads(x) for x in lines]
    return out, bool(tail)


def _dump(p, obj):
    tmp = Path(str(p) + ".tmp")
    with open(tmp, "wb") as f:
        f.write(jbytes(obj))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


# ------------------------------------------------------------------ reservation
def reserve(run_dir, head, freeze_sha, job_names, workers):
    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)
    body = {"head": head, "freeze_sha256": freeze_sha, "jobs": sorted(job_names), "workers": workers, "reserved": now(),
            "pid": os.getpid(), "nonce": os.urandom(8).hex()}
    if len(set(job_names)) != len(job_names):
        raise ReservationError("duplicate job names")
    body["run_id"] = sha(json.dumps(body, sort_keys=True).encode())
    try:
        write_new(run / "RUN.json", jbytes(body))
    except FileExistsError:
        raise ReservationError(f"{run} was already reserved") from None
    return body


def read_reservation(run_dir):
    body = json.loads((Path(run_dir) / "RUN.json").read_bytes())
    rest = {k: v for k, v in body.items() if k != "run_id"}
    if body.get("run_id") != sha(json.dumps(rest, sort_keys=True).encode()):
        raise ValueError("RUN.json does not match its run_id")
    return body


# ------------------------------------------------------------------ worker side
class Episode:
    """One job's life in a worker: `started` on creation, `sampling()` before the first draw, `commit()` at the end."""

    def __init__(self, run_dir, run_id, name):
        self.run, self.run_id, self.name = Path(run_dir), run_id, name
        self.log = self.run / "events" / f"{name}.jsonl"
        self.stage, self.final = self.run / "staging" / name, self.run / "episodes" / name
        if self.final.exists():
            raise RunStop(f"{name}: already committed")
        append_event(self.log, "started", run_id=run_id, pid=os.getpid())

    def sampling(self):
        append_event(self.log, "sampling_started")

    def commit(self, record, archive):
        """record: dict (run_id, archive_sha256 are added); archive: npz bytes."""
        rec = {**record, "run_id": self.run_id, "archive_sha256": sha(archive)}
        self.stage.mkdir(parents=True)
        data = {"archive.npz": archive, "record.json": jbytes(rec)}
        for f in FILES:
            write_new(self.stage / f, data[f])
        write_new(self.stage / "COMMIT.json", jbytes(
            {"run_id": self.run_id, "job": self.name,
             "files": {f: {"bytes": len(data[f]), "sha256": sha(data[f])} for f in FILES}}))
        os.rename(self.stage, self.final)
        append_event(self.log, "committed")
        return self.name


def read_committed(run_dir, run_id, name):
    """-> (record, archive bytes), both checked against COMMIT.json. The caller must use these bytes, not re-read."""
    d = Path(run_dir) / "episodes" / name
    if {p.name for p in d.iterdir()} != {*FILES, "COMMIT.json"}:
        raise ValueError(f"{name}: committed files")
    c = json.loads((d / "COMMIT.json").read_bytes())
    if c.get("run_id") != run_id or c.get("job") != name or set(c.get("files", {})) != set(FILES):
        raise ValueError(f"{name}: commit identity")
    data = {f: (d / f).read_bytes() for f in FILES}
    for f, b in data.items():
        if c["files"][f] != {"bytes": len(b), "sha256": sha(b)}:
            raise ValueError(f"{name}: {f} does not match its commit")
    rec = json.loads(data["record.json"])
    if rec.get("run_id") != run_id or rec.get("archive_sha256") != sha(data["archive.npz"]):
        raise ValueError(f"{name}: record identity")
    return rec, data["archive.npz"]


# ------------------------------------------------------------------ inventory and recovery (read-only on run outputs)
def inventory(run_dir):
    """State of every reserved job from disk alone, plus byte hashes. Opens no record or archive content."""
    run, body = Path(run_dir), read_reservation(run_dir)
    out = {"run_id": body["run_id"], "jobs": {}, "files": {}}
    for n in body["jobs"]:
        ev, torn = read_events(run / "events" / f"{n}.jsonl")
        names = [x["event"] for x in ev]
        staged = any((run / k / n).is_dir() and any((run / k / n).iterdir()) for k in ("staging", "partial"))
        if (run / "episodes" / n).is_dir():
            st = "committed"
        elif staged:
            st = "partial"
        elif "sampling_started" in names:
            st = "sampled_no_output"
        else:
            st = "started" if names else "not_started"
        out["jobs"][n] = {"state": st, "events": names, "torn_event_line": torn}
    for k in ("episodes", "staging", "partial"):
        for p in sorted((run / k).rglob("*")):
            if p.is_file():
                b = p.read_bytes()
                out["files"][p.relative_to(run).as_posix()] = {"bytes": len(b), "sha256": sha(b)}
    return out


def recover(run_dir):
    """Record the state of a run whose process died. Refuses a run that closed itself; writes RECOVERY.json once.
    The caller must first make sure that no process of the run is alive."""
    run = Path(run_dir)
    st = json.loads((run / "RUN_STATUS.json").read_bytes()) if (run / "RUN_STATUS.json").exists() else {}
    if st.get("state") in ("ready_for_analysis", "failed"):
        raise RunStop(f"run already closed: {st['state']}")
    inv = {"recovered": now(), "last_status": st.get("state"), "journal_torn": read_events(run / "journal.jsonl")[1],
           **inventory(run)}
    write_new(run / "RECOVERY.json", jbytes(inv))
    return inv


# ------------------------------------------------------------------ parent side
def run_jobs(jobs, job_fn, run_dir, reservation, stall_timeout=20_000, executor=None, on_done=None):
    """jobs: [(name, args)]; job_fn(run_dir, run_id, name, args) -> name, committing through Episode.

    Any failure stops the run as soon as it is seen: workers are killed, staging is preserved under partial/, and
    FAILURE.json records every job's state. One retry, only for an infrastructure error raised before `sampling()`.
    stall_timeout: seconds with no job completing."""
    run, rid = Path(run_dir), reservation["run_id"]
    jr, sp = run / "journal.jsonl", run / "RUN_STATUS.json"
    status = {"state": "starting", "run_id": rid, "head": reservation["head"], "freeze_sha256": reservation["freeze_sha256"],
              "started": now(), "n_jobs": len(jobs), "jobs": {}, "reruns": {}}
    ex, owns = None, False
    try:
        if read_reservation(run) != reservation or sorted(n for n, _ in jobs) != reservation["jobs"]:
            raise RunStop("jobs do not match the reservation")
        if sp.exists():
            raise RunStop("run was already started")
        owns = True
        _dump(sp, status)
        append_event(jr, "run_start", run_id=rid, n_jobs=len(jobs))
        for k in ("events", "staging", "episodes", "partial"):
            (run / k).mkdir()
        ex = (executor or (lambda: ProcessPoolExecutor(reservation["workers"], mp_context=get_context("spawn"))))()
        status["state"] = "running"
        _dump(sp, status)
        args = dict(jobs)
        pend = {ex.submit(job_fn, str(run), rid, n, a): n for n, a in jobs}
        while pend:
            done, _ = wait(pend, timeout=stall_timeout, return_when=FIRST_COMPLETED)
            if not done:
                raise RunStop(f"no job completed in {stall_timeout}s")
            for h in done:
                n = pend.pop(h)
                try:
                    h.result()
                except INFRA as err:
                    seen = {x["event"] for x in read_events(run / "events" / f"{n}.jsonl")[0]}
                    if n in status["reruns"] or "sampling_started" in seen or (run / "staging" / n).exists() \
                            or (run / "episodes" / n).exists():
                        raise RunStop(f"{n}: infrastructure error, not retriable: {err!r}") from err
                    status["reruns"][n] = repr(err)
                    append_event(jr, "job_retry", job=n, error=repr(err))
                    pend[ex.submit(job_fn, str(run), rid, n, args[n])] = n
                    continue
                read_committed(run, rid, n)
                status["jobs"][n] = {"returncode": 0, "rerun": n in status["reruns"]}
                append_event(jr, "job_done", job=n)
                _dump(sp, status)
                if on_done:
                    on_done(n)
        ex.shutdown()
        status.update(state="ready_for_analysis", finished=now())
        append_event(jr, "run_end", state=status["state"])
        _dump(sp, status)
        return status
    except BaseException as err:      # noqa: BLE001  (fail closed: code errors, stalls, interruption)
        if owns:                      # never touch another start's files
            _close_failed(run, ex, status, err, jr, sp)
        raise


def _close_failed(run, ex, status, err, jr, sp):
    if ex is not None:
        procs = list((getattr(ex, "_processes", None) or {}).values())
        ex.shutdown(wait=False, cancel_futures=True)
        for p in procs:
            p.terminate()
        for p in procs:
            p.join(30)
    if status["state"] == "starting" and sp.exists() and json.loads(sp.read_bytes()).get("started") != status["started"]:
        return                                                # another start's status: never overwrite it
    moved = []
    for d in sorted((run / "staging").glob("*")) if (run / "staging").is_dir() else []:
        os.rename(d, run / "partial" / d.name)
        moved.append(d.name)
    status.update(state="failed", error=repr(err), finished=now())
    append_event(jr, "run_failed", error=repr(err), partial=moved)
    _dump(sp, status)
    if not (run / "FAILURE.json").exists():
        write_new(run / "FAILURE.json", jbytes({"error": repr(err), "acknowledged": sorted(status["jobs"]), **inventory(run)}))
