"""v11 lifecycle with the P0 fixes of Codex's v11 review (abc1ae474). Derived from lifecycle11.py; v11 is unchanged.

Roles, each with its own proof
  supervisor   holds locks/supervisor and the in-memory session secret whose hash is in START.json
  worker       a direct child of that supervisor process (checked through the OS process handle), given the secret by it,
               holding one slot lock from pool initialisation to process exit
  recovery     holds locks/supervisor after the supervisor's death. That gives it no worker authority: no worker decision
               reads the supervisor lock
Lock contention (LockBusy) and lock failure (LockError) are different. A failure is never read as a live or dead owner.

Files: RUN.json, START.json, journal.jsonl, events/, staging/, episodes/, locks/ as in v11, and
  FAILED.json / RECOVER.json  persistent fences. Written under locks/gate, which every worker start, sampling intent and
                              commit also takes, so none of these can happen after a fence
  CLOSING.*                   a terminal record being written (kept if interrupted)
  CLOSE.json                  the only terminal record, renamed into place complete

Success is published only after the exact bytes to be published passed the same check analysis uses (check_run) and the
study's admission. Anything else ends failed, recovered, or blocked without a terminal record.
Recovery certifies only while holding every slot, so initialising (refused by the fence), idle, active and delayed
workers are all excluded. Nothing is moved, deleted, repaired or reused.

Assumptions: one host, a local filesystem with working OS locks and atomic rename; jobs write only through Episode and
start no processes that outlive them; nobody edits the folder or calls private functions. Hashes are not signatures.
No power-loss or cross-host claim."""
from __future__ import annotations

import contextlib
import ctypes
import hashlib
import importlib
import json
import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from multiprocessing import get_context, parent_process
from pathlib import Path

from strict import Invalid, jbytes, loads, need, sha

if os.name == "nt":
    import msvcrt
    from ctypes import wintypes
else:
    import fcntl

INFRA = (OSError, MemoryError, EOFError)
FILES = ("archive.npz", "record.json")
DIRS = ("locks", "events", "staging", "episodes")
FENCES = ("FAILED.json", "RECOVER.json", "CLOSE.json")
GENESIS = "0" * 64


class StartRefused(RuntimeError):
    pass


class NotQuiescent(RuntimeError):
    pass


class RunStop(RuntimeError):
    pass


class LockBusy(Exception):
    """Another handle holds the lock."""


class LockError(RuntimeError):
    """The lock could not be examined. Says nothing about its owner."""


class Fenced(BaseException):
    """Raised in a worker that may no longer act. Not an Exception, so a job cannot swallow it by accident."""


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_new(path, data):
    with open(path, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


# ------------------------------------------------------------------ OS locks
def _os_lock(f):
    """Lock or raise LockBusy; any other OS failure raises OSError."""
    if os.name != "nt":
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise LockBusy from None
        return

    class Overlapped(ctypes.Structure):
        _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t), ("Offset", wintypes.DWORD),
                    ("OffsetHigh", wintypes.DWORD), ("hEvent", wintypes.HANDLE)]
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.LockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                             ctypes.POINTER(Overlapped)]
    ov = Overlapped(OffsetHigh=1)                        # one byte far past the end, so reads are unaffected
    if not k.LockFileEx(msvcrt.get_osfhandle(f.fileno()), 3, 0, 1, 0, ctypes.byref(ov)):   # exclusive | fail immediately
        err = ctypes.get_last_error()
        if err in (33, 997):                             # ERROR_LOCK_VIOLATION, ERROR_IO_PENDING
            raise LockBusy
        raise ctypes.WinError(err)


class Lock:
    """Non-blocking exclusive lock on an existing file. Released by close() or by the death of the process."""

    def __init__(self, path):
        self.session = self.run_id = None
        self.f = open(path, "r+b")
        try:
            _os_lock(self.f)
        except BaseException:
            self.f.close()
            raise

    def close(self):
        if _CLAIMS.get(self.run_id) is self:
            del _CLAIMS[self.run_id]
        self.f.close()


_CLAIMS = {}                 # run_id -> the claim held by this process


def try_lock(path):
    """Lock, or None if and only if another handle holds it. Everything else raises."""
    need(Path(path).is_file(), f"lock file missing: {Path(path).name}")
    try:
        return Lock(path)
    except LockBusy:
        return None
    except OSError as ex:
        raise LockError(f"{Path(path).name}: {ex!r}") from ex


def _sup(run):
    return Path(run) / "locks" / "supervisor"


def _gate_path(run):
    return Path(run) / "locks" / "gate"


def _slots(run, workers):
    return [Path(run) / "locks" / f"worker{i:03d}" for i in range(workers)]


def supervisor_alive(run):
    """Diagnostic only: whether some handle holds the supervisor lock. Grants nothing; errors raise."""
    k = try_lock(_sup(run))
    if k is None:
        return True
    k.close()
    return False


def _release(held):
    for k in reversed(held):
        k.close()


def _wait_lock(path, timeout, what):
    end = time.monotonic() + timeout
    while True:
        k = try_lock(path)
        if k is not None:
            return k
        if time.monotonic() >= end:
            raise NotQuiescent(what)
        time.sleep(0.01)


@contextlib.contextmanager
def _gate(run):
    """Orders fences against worker starts, sampling intents and commits."""
    k = _wait_lock(_gate_path(run), 60, "the gate is held by another process")
    try:
        yield
    finally:
        k.close()


def _all_slots(run, workers, timeout):
    """Hold every worker slot, or raise holding none, whatever goes wrong."""
    end, held = time.monotonic() + timeout, []
    try:
        for p in _slots(run, workers):
            held.append(_wait_lock(p, max(0.0, end - time.monotonic()), f"{p.name} is still held by a live process"))
    except BaseException:
        _release(held)
        raise
    return held


# ------------------------------------------------------------------ hash-chained event files
def event_line(ev, event, **kw):
    """The next chained line after the valid events `ev`."""
    body = {"t": now(), "event": event, "seq": len(ev), "prev": ev[-1]["hash"] if ev else GENESIS, **kw}
    body["hash"] = sha(json.dumps(body, sort_keys=True).encode())
    return json.dumps(body, sort_keys=True).encode() + b"\n"


def append_line(path, line):
    with open(path, "ab") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def append_event(path, event, **kw):
    ev, ok = read_events(path)
    if not ok:
        raise RunStop(f"{Path(path).name}: damaged event file")
    append_line(path, event_line(ev, event, **kw))


def parse_events(data):
    """-> (valid prefix, whole file is valid)."""
    lines = data.split(b"\n")
    tail, out, prev = lines.pop(), [], GENESIS
    for i, x in enumerate(lines):
        try:
            d = loads(x)
            rest = {k: v for k, v in d.items() if k != "hash"}
            good = d["hash"] == sha(json.dumps(rest, sort_keys=True).encode()) and d["seq"] == i and d["prev"] == prev \
                and type(d["seq"]) is int and type(d["event"]) is str
        except (Invalid, KeyError, TypeError, AttributeError):
            good = False
        if not good:
            return out, False
        out.append(d)
        prev = d["hash"]
    return out, not tail


def read_events(path):
    p = Path(path)
    return parse_events(p.read_bytes()) if p.exists() else ([], True)


# ------------------------------------------------------------------ reservation and start
class Reservation:
    def __init__(self, run, body, token):
        self.run, self.body, self.token = Path(run), body, token


def reserve(run_dir, identity, job_names, workers):
    """Create a new run folder in one rename. -> Reservation, the only holder of the start token."""
    run, names = Path(run_dir), list(job_names)
    need(names and len(set(names)) == len(names) and all(
        type(n) is str and n.replace("_", "").isalnum() and n.isascii() for n in names), "job names")
    need(type(workers) is int and 1 <= workers <= 64, "workers")
    if run.exists():
        raise StartRefused(f"{run.name} already exists")
    token = os.urandom(32).hex()
    body = {"identity": identity, "jobs": names, "workers": workers, "reserved": now(), "nonce": os.urandom(16).hex(),
            "token_sha256": sha(token.encode())}
    body["run_id"] = sha(json.dumps(body, sort_keys=True).encode())
    tmp = run.with_name(f".{run.name}.{body['nonce']}")
    for d in DIRS:
        (tmp / d).mkdir(parents=True)
    for p in (_sup(tmp), _gate_path(tmp), *_slots(tmp, workers)):
        write_new(p, b"")
    write_new(tmp / "RUN.json", jbytes(body))
    try:
        os.rename(tmp, run)
    except OSError:
        raise StartRefused(f"{run.name} was reserved by another process (our unused folder is {tmp.name})") from None
    return Reservation(run, body, token)


def check_reservation(body):
    need(isinstance(body, dict) and set(body) == {"identity", "jobs", "workers", "reserved", "nonce", "token_sha256", "run_id"},
         "reservation fields")
    rest = {k: v for k, v in body.items() if k != "run_id"}
    need(body["run_id"] == sha(json.dumps(rest, sort_keys=True).encode()), "reservation does not match its run_id")
    return body


def read_reservation(run):
    return check_reservation(loads((Path(run) / "RUN.json").read_bytes()))


def _claim(res):
    """-> held supervisor lock. Refuses without writing anything unless this is the first and only start."""
    run = res.run
    body = read_reservation(run)
    if body != res.body or not isinstance(res.token, str) or sha(res.token.encode()) != body["token_sha256"]:
        raise StartRefused("this process does not hold the reservation's start token")
    lock = try_lock(_sup(run))
    if lock is None:
        raise StartRefused("another process holds the run")
    try:
        if {p.name for p in run.iterdir()} != {"RUN.json", *DIRS} or any(any((run / d).iterdir()) for d in DIRS[1:]):
            raise StartRefused("the run was started, recovered or closed before")
        try:
            session = os.urandom(32).hex()
            write_new(run / "START.json", jbytes({"run_id": body["run_id"], "pid": os.getpid(), "started": now(),
                                                  "session_sha256": sha(session.encode())}))
            lock.session, lock.run_id = session, body["run_id"]
            _CLAIMS[body["run_id"]] = lock
        except FileExistsError:
            raise StartRefused("the run was started before") from None
    except BaseException:
        lock.close()
        raise
    return lock


# ------------------------------------------------------------------ worker side
_WORKER = {}                 # this pool process: run, run_id, session, slot


def _fenced(run):
    for f in FENCES:
        if os.path.lexists(Path(run) / f):
            raise Fenced(f"the run is fenced by {f}")


def _check_authority(run, run_id, session):
    """The original supervisor itself, or a live direct child of it that was given its session secret."""
    claim = _CLAIMS.get(run_id)
    if claim is not None and not claim.f.closed:
        return
    try:
        start = loads((Path(run) / "START.json").read_bytes())
        ok = type(session) is str and start["run_id"] == run_id and start["session_sha256"] == sha(session.encode())
        pid = start["pid"]
    except (OSError, Invalid, KeyError, TypeError) as ex:
        raise Fenced(f"the supervisor's identity cannot be read: {ex!r}") from None
    parent = parent_process()
    if not ok or parent is None or parent.pid != pid:
        raise Fenced("not a worker of the original supervisor")
    if not parent.is_alive():
        raise Fenced("the original supervisor is gone")


def _permit(run, run_id, session):
    """Call with the gate held."""
    _fenced(run)
    _check_authority(run, run_id, session)


NEW, INTENT, CONFIRMED, COMMITTING, DONE, BROKEN = "new", "intent", "confirmed", "committing", "committed", "broken"


class Episode:
    """new -> intent -> confirmed -> committing -> committed. Any other call breaks the episode for good."""

    def __init__(self, run, run_id, name, context, session=None):
        self.run, self.run_id, self.name, self.context, self._session = Path(run), run_id, name, context, session
        self.log = self.run / "events" / f"{name}.jsonl"
        self.stage, self.final = self.run / "staging" / name, self.run / "episodes" / name
        self._state = NEW

    def _step(self, want, to):
        have, self._state = self._state, BROKEN
        need(have == want, f"{self.name}: {to} after {have}")

    def _events(self, want):
        ev, ok = read_events(self.log)
        seen = [x["event"] for x in ev if x["event"] != "started"]
        need(ok and seen == want, f"{self.name}: events {seen}")

    def sampling_intent(self):
        """Call before the first draw. From here on the job is never retried."""
        self._step(NEW, INTENT)
        with _gate(self.run):
            _permit(self.run, self.run_id, self._session)
            self._events([])
            append_event(self.log, "sampling_intent")
        self._state = INTENT

    def sampling_confirmed(self, used_seeds):
        """Call after the last draw, with the seeds actually used."""
        self._step(INTENT, CONFIRMED)
        self._events(["sampling_intent"])
        append_event(self.log, "sampling_confirmed", seeds_sha256=sha(jbytes(used_seeds)))
        self._state = CONFIRMED

    def commit(self, record, archive):
        if self.final.exists():
            raise RunStop(f"{self.name}: already committed")
        self._step(CONFIRMED, COMMITTING)
        self._events(["sampling_intent", "sampling_confirmed"])
        with _gate(self.run):
            _permit(self.run, self.run_id, self._session)
        data = {"archive.npz": archive,
                "record.json": jbytes({**record, "run_id": self.run_id, "archive_sha256": sha(archive)})}
        self.stage.mkdir()
        for f in FILES:
            write_new(self.stage / f, data[f])
        write_new(self.stage / "COMMIT.json", jbytes(
            {"run_id": self.run_id, "job": self.name,
             "files": {f: {"bytes": len(data[f]), "sha256": sha(data[f])} for f in FILES}}))
        with _gate(self.run):
            _permit(self.run, self.run_id, self._session)
            if self.final.exists():
                raise RunStop(f"{self.name}: already committed")
            os.rename(self.stage, self.final)
        append_event(self.log, "committed")
        self._state = DONE


def _wait_parent():
    parent_process().join()
    os._exit(86)


def _worker_init(run, run_id, workers, session):
    """Pool initializer. The slot is held until this process exits, so idle workers also block recovery."""
    try:
        with _gate(run):
            _permit(run, run_id, session)
            if parent_process() is None:
                raise Fenced("not a worker process")
            threading.Thread(target=_wait_parent, daemon=True).start()
            for i, p in enumerate(_slots(run, workers)):
                slot = try_lock(p)
                if slot is not None:
                    _WORKER.update(run=str(run), run_id=run_id, session=session, slot=slot, index=i)
                    return
        raise RunStop("no free worker slot")
    except Fenced as ex:
        raise RunStop(str(ex)) from None


def _guarded(run, run_id, workers, name, attempt, job_fn, args, hooks, context):
    if _WORKER.get("run_id") != run_id or _WORKER.get("run") != str(run):
        raise RunStop(f"{name}: this process is not a worker of the run")
    session = _WORKER["session"]
    try:
        ep = Episode(run, run_id, name, context, session)
        with _gate(run):
            _permit(run, run_id, session)
            append_event(ep.log, "started", run_id=run_id, attempt=attempt, pid=os.getpid(), slot=_WORKER["index"])
        if hooks:
            mod, fn = hooks
            real, check = ep.commit, getattr(importlib.import_module(mod), fn)

            def commit(record, archive):
                check(context)
                real(record, archive)
            ep.commit = commit
        job_fn(ep, args)
        return name
    except (Fenced, NotQuiescent) as ex:
        raise RunStop(f"{name}: {ex}") from None


# ------------------------------------------------------------------ commits
def check_commit(files, run_id, name):
    """files: {relative name: bytes} of one episode folder. -> (record bytes, archive bytes) or Invalid."""
    need(set(files) == {*FILES, "COMMIT.json"}, f"{name}: committed files")
    c = loads(files["COMMIT.json"])
    need(isinstance(c, dict) and set(c) == {"run_id", "job", "files"} and c["run_id"] == run_id and c["job"] == name,
         f"{name}: commit identity")
    need(c["files"] == {f: {"bytes": len(files[f]), "sha256": sha(files[f])} for f in FILES}, f"{name}: commit hashes")
    r = loads(files["record.json"])
    need(isinstance(r, dict) and r.get("run_id") == run_id and r.get("archive_sha256") == sha(files["archive.npz"]),
         f"{name}: record identity")
    return files["record.json"], files["archive.npz"]


def _tree(d):
    """{relative name: bytes}. Links and other special entries are refused."""
    out = {}
    for p in sorted(Path(d).rglob("*")):
        need(not p.is_symlink() and not getattr(p, "is_junction", lambda: False)() and (p.is_file() or p.is_dir()),
             f"{p.name}: special file")
        if p.is_file():
            out[p.relative_to(d).as_posix()] = p.read_bytes()
    return out


def _commit_error(run, run_id, name):
    try:
        check_commit(_tree(Path(run) / "episodes" / name), run_id, name)
    except (Invalid, OSError) as ex:
        return str(ex)
    return None


def inventory(run):
    """What the disk proves about every job, plus byte hashes. Decodes no archive."""
    run = Path(run)
    body = read_reservation(run)
    out = {"run_id": body["run_id"], "jobs": {}, "unexpected": [], "files": {}}
    for n in body["jobs"]:
        ev, ok = read_events(run / "events" / f"{n}.jsonl")
        seen = [x["event"] for x in ev]
        final, stage = os.path.lexists(run / "episodes" / n), os.path.lexists(run / "staging" / n)
        why = _commit_error(run, body["run_id"], n) if final else None
        if final and stage:
            st = "conflict"
        elif final:
            st = "corrupt" if why else "committed"
        elif stage:
            st = "partial"
        elif "committed" in seen:
            st = "missing_commit"
        elif "sampling_confirmed" in seen:
            st = "sampled_no_output"
        elif "sampling_intent" in seen:
            st = "possibly_sampled"
        elif not ok:
            st = "unknown"
        else:
            st = "started" if seen else "not_started"
        out["jobs"][n] = {"state": st, "events": seen, "events_valid": ok, **({"why": why} if why else {})}
    for k in ("staging", "episodes"):
        out["unexpected"] += [f"{k}/{p.name}" for p in (run / k).iterdir() if p.name not in body["jobs"]]
    out["unexpected"] += [f"events/{p.name}" for p in (run / "events").iterdir() if p.stem not in body["jobs"]]
    for p in sorted(run.rglob("*")):
        rel = p.relative_to(run).as_posix()
        if p.is_file() and not rel.startswith("locks/") and rel != "CLOSE.json" and not rel.startswith("CLOSING."):
            b = p.read_bytes()
            out["files"][rel] = {"bytes": len(b), "sha256": sha(b)}
    return out


# ------------------------------------------------------------------ supervisor
def execute(res, jobs, job_fn, *, stall_timeout=20_000, context=None, commit_hook=None, final_check=None, pool=None,
            on_done=None, admission=None):
    """Run the reservation's jobs once. jobs: [(name, args)]. -> the CLOSE record.

    Any failure stops the run as soon as it is seen. One retry per job, only for an infrastructure error while the job's
    event file shows nothing but `started` and no output exists.
    commit_hook: (module, function) called with `context` in the worker before each commit.
    final_check: called before the run may close as succeeded.
    admission: called with (reservation, episodes, seed digests) of the exact bytes about to be published as succeeded."""
    run, workers = res.run, res.body["workers"]
    if [n for n, _ in jobs] != res.body["jobs"]:
        raise StartRefused("jobs do not match the reservation")
    sup = _claim(res)
    rid, jr, ex = res.body["run_id"], run / "journal.jsonl", None
    try:
        append_event(jr, "run_start", run_id=rid, n_jobs=len(jobs), workers=workers)
        ex = (pool or (lambda: ProcessPoolExecutor(
            workers, mp_context=get_context("spawn"), initializer=_worker_init,
            initargs=(str(run), rid, workers, sup.session))))()
        args, attempts = dict(jobs), {}

        def submit(n):
            attempts[n] = attempts.get(n, 0) + 1
            append_event(jr, "job_submitted", job=n, attempt=attempts[n])
            return ex.submit(_guarded, str(run), rid, workers, n, attempts[n], job_fn, args[n], commit_hook, context)
        pend = {submit(n): n for n, _ in jobs}
        while pend:
            done, _ = wait(pend, timeout=stall_timeout, return_when=FIRST_COMPLETED)
            if not done:
                raise RunStop(f"no job completed in {stall_timeout}s")
            for h in done:
                n = pend.pop(h)
                try:
                    h.result()
                except INFRA as err:
                    ev, ok = read_events(run / "events" / f"{n}.jsonl")
                    clean = ok and [x["event"] for x in ev] == ["started"] and not os.path.lexists(run / "staging" / n) \
                        and not os.path.lexists(run / "episodes" / n)
                    if attempts[n] > 1 or not clean:
                        raise RunStop(f"{n}: infrastructure error, not retriable: {err!r}") from err
                    append_event(jr, "job_retry", job=n, error=repr(err))
                    pend[submit(n)] = n
                    continue
                why = _commit_error(run, rid, n)
                if why:
                    raise RunStop(f"{n}: returned without a valid commit: {why}")
                append_event(jr, "job_done", job=n, commit_sha256=sha((run / "episodes" / n / "COMMIT.json").read_bytes()))
                if on_done:
                    on_done(n)
        ex.shutdown()
        held = _all_slots(run, workers, 30)
        try:
            _fenced(run)
            if final_check:
                final_check()
            files = _tree(run)
            ev, ok = parse_events(files["journal.jsonl"])
            need(ok, "journal chain")
            line = event_line(ev, "run_end", state="succeeded")
            files["journal.jsonl"] += line
            inv = inventory(run)
            inv["files"]["journal.jsonl"] = {"bytes": len(files["journal.jsonl"]), "sha256": sha(files["journal.jsonl"])}
            close = {"outcome": "succeeded", "run_id": rid, "closed": now(), "inventory": inv}
            files["CLOSE.json"] = jbytes(close)
            body, episodes, seeds, _ = check_run(files, _dirs(run))          # what analysis would check, on these bytes
            need(body == res.body, "reservation")
            if admission:
                admission(body, episodes, seeds)
            append_line(jr, line)
            _publish(run, files["CLOSE.json"], "succeeded")
        finally:
            _release(held)
        return close
    except BaseException as err:      # noqa: BLE001  (fail closed: code errors, stalls, interruption, invalid output)
        _close_failed(run, rid, workers, ex, jr, err)
        raise
    finally:
        sup.close()


def _publish(run, data, outcome):
    """Write a complete terminal record, then rename it into place. Needs every slot and the supervisor lock."""
    n = 0
    while True:
        tmp = run / f"CLOSING.{outcome}.{n}.json"
        try:
            write_new(tmp, data)
            break
        except FileExistsError:                              # left by an interrupted attempt: kept
            n += 1
    if os.path.lexists(run / "CLOSE.json"):
        raise RunStop("the run is already closed")
    os.rename(tmp, run / "CLOSE.json")


def _close_failed(run, rid, workers, ex, jr, err):
    """Fence, kill the workers, prove they are gone, then record the failure. If that cannot be proved, nothing terminal
    is written: the fence stays, and the run is neither startable nor admissible. A published CLOSE is never touched."""
    try:
        with _gate(run):
            if os.path.lexists(run / "CLOSE.json"):
                return
            if not os.path.lexists(run / "FAILED.json"):
                write_new(run / "FAILED.json", jbytes({"run_id": rid, "pid": os.getpid(), "error": repr(err), "failed": now()}))
    finally:
        if ex is not None:
            procs = list((getattr(ex, "_processes", None) or {}).values())
            ex.shutdown(wait=False, cancel_futures=True)
            for p in procs:
                p.kill()
    held = _all_slots(run, workers, 30)
    try:
        if read_events(jr)[1]:
            append_event(jr, "run_failed", error=repr(err))
        _publish(run, jbytes({"outcome": "failed", "run_id": rid, "closed": now(), "error": repr(err),
                              "inventory": inventory(run)}), "failed")
    finally:
        _release(held)


def recover(run_dir):
    """Close a run whose supervisor died: take the supervisor lock, fence, then take every slot and record what is there.

    The fence is permanent even if a worker is still alive (NotQuiescent): the supervisor is dead, so the run can only
    end recovered. Recovery authorises nothing and changes no evidence."""
    run = Path(run_dir)
    body = read_reservation(run)
    sup = try_lock(_sup(run))
    if sup is None:
        raise NotQuiescent("the supervisor lock is held by a live process")
    try:
        with _gate(run):
            if os.path.lexists(run / "CLOSE.json"):
                raise RunStop("the run is already closed")
            if not os.path.lexists(run / "RECOVER.json"):
                write_new(run / "RECOVER.json", jbytes({"run_id": body["run_id"], "pid": os.getpid(), "recovering": now()}))
        held = _all_slots(run, body["workers"], 2)
        try:
            close = {"outcome": "recovered", "run_id": body["run_id"], "closed": now(),
                     "started": os.path.lexists(run / "START.json"), "journal_valid": read_events(run / "journal.jsonl")[1],
                     "inventory": inventory(run)}
            _publish(run, jbytes(close), "recovered")
            return close
        finally:
            _release(held)
    finally:
        sup.close()


# ------------------------------------------------------------------ admission of a finished run
def _dirs(run):
    return {p.relative_to(run).as_posix() for p in Path(run).rglob("*") if p.is_dir()}


def load_success(run_dir):
    """-> (reservation, {job: (record bytes, archive bytes)}, seeds digest per job, CLOSE hash)."""
    run = Path(run_dir)
    return check_run(_tree(run), _dirs(run))


def check_run(files, dirs):
    """One successful lifecycle, complete, ordered, nothing extra. Every byte is checked from `files`, read once."""
    need({"RUN.json", "START.json", "journal.jsonl", "CLOSE.json"} <= set(files), "run files are missing")
    body = check_reservation(loads(files["RUN.json"]))
    rid, names = body["run_id"], body["jobs"]
    lock_files = {"locks/supervisor", "locks/gate", *(f"locks/worker{i:03d}" for i in range(body["workers"]))}
    want = {"RUN.json", "START.json", "journal.jsonl", "CLOSE.json", *lock_files, *(f"events/{n}.jsonl" for n in names),
            *(f"episodes/{n}/{f}" for n in names for f in (*FILES, "COMMIT.json"))}
    need(set(files) == want, "missing or unexpected files in the run")
    need(dirs == {*DIRS, *(f"episodes/{n}" for n in names)}, "missing or unexpected folders in the run")
    close = loads(files["CLOSE.json"])
    need(isinstance(close, dict) and set(close) == {"outcome", "run_id", "closed", "inventory"} and
         close["outcome"] == "succeeded" and close["run_id"] == rid, "the run did not close as succeeded")
    start = loads(files["START.json"])
    need(isinstance(start, dict) and set(start) == {"run_id", "pid", "started", "session_sha256"} and start["run_id"] == rid, "start record")
    inv = close["inventory"]
    need(isinstance(inv, dict) and set(inv) == {"run_id", "jobs", "unexpected", "files"} and inv["run_id"] == rid and
         inv["unexpected"] == [] and set(inv["jobs"]) == set(names) and
         all(j["state"] == "committed" and j["events_valid"] is True for j in inv["jobs"].values()), "closing inventory")
    need(inv["files"] == {k: {"bytes": len(v), "sha256": sha(v)} for k, v in files.items()
                          if k not in lock_files and k != "CLOSE.json"}, "files differ from the closing inventory")
    out, seeds, done = {}, {}, {}
    _check_journal(files, body, done)
    for n in names:
        ev, ok = parse_events(files[f"events/{n}.jsonl"])
        need(ok, f"{n}: event chain")
        starts = done[n]["attempts"]
        need([x["event"] for x in ev] == ["started"] * starts + ["sampling_intent", "sampling_confirmed", "committed"],
             f"{n}: event order")
        need([x.get("attempt") for x in ev[:starts]] == list(range(1, starts + 1)) and
             all(x.get("run_id") == rid for x in ev[:starts]), f"{n}: attempts")
        need(_times(ev), f"{n}: event times")
        out[n] = check_commit({f: files[f"episodes/{n}/{f}"] for f in (*FILES, "COMMIT.json")}, rid, n)
        need(done[n]["commit"] == sha(files[f"episodes/{n}/COMMIT.json"]), f"{n}: commit differs from the journal")
        seeds[n] = ev[starts + 1].get("seeds_sha256")
    return body, out, seeds, hashlib.sha256(files["CLOSE.json"]).hexdigest()


def _times(ev):
    t = [x.get("t") for x in ev]
    return all(type(x) is str for x in t) and t == sorted(t)


def _check_journal(files, body, done):
    ev, ok = parse_events(files["journal.jsonl"])
    need(ok and ev and _times(ev), "journal chain")
    names = body["jobs"]
    n = len(names)
    need(ev[0]["event"] == "run_start" and ev[0].get("run_id") == body["run_id"] and ev[0].get("n_jobs") == n and
         ev[0].get("workers") == body["workers"], "journal start")
    need(ev[-1]["event"] == "run_end" and ev[-1].get("state") == "succeeded", "journal end")
    first = ev[1:n + 1]
    need([(x["event"], x.get("job"), x.get("attempt")) for x in first] == [("job_submitted", k, 1) for k in names],
         "journal submissions")
    state = {k: {"attempts": 1, "commit": None, "retry": False} for k in names}
    for x in ev[n + 1:-1]:
        s = state.get(x.get("job"))
        need(s is not None and s["commit"] is None, "journal names an unknown or finished job")
        if x["event"] == "job_retry":
            need(s["attempts"] == 1 and not s["retry"], "journal retry")
            s["retry"] = True
        elif x["event"] == "job_submitted":
            need(s["retry"] and s["attempts"] == 1 and x.get("attempt") == 2, "journal resubmission")
            s.update(attempts=2, retry=False)
        elif x["event"] == "job_done":
            need(not s["retry"] and type(x.get("commit_sha256")) is str, "journal completion")
            s["commit"] = x["commit_sha256"]
        else:
            need(False, f"journal event {x['event']}")
    need(all(s["commit"] for s in state.values()), "journal: jobs without completion")
    done.update(state)
