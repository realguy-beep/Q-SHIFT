"""Run protections for any future frozen Q-SHIFT run (CF2 audit F3, F4, F5, F7, F8). No study is wired here.

  check_revision   F3  HEAD is exactly the approved freeze commit: parent = frozen code_head, only the freeze file
                       changed, clean tree, no result files tracked.
  runtime_identity F3  python + numpy, scipy, stim, pymatching, ldpc (the BP+OSD native dependency) + platform.
  check_runtime    F3  every frozen runtime field must match exactly (missing fields fail).
  Reservation      F5  exclusive O_CREAT|O_EXCL run lock; never released, so one directory = one attempt.
  Journal          F5  append-only, fsynced JSONL of every attempt event.
  run_jobs         F5  bounded waits; retry only an infrastructure error raised before the job wrote any output;
                       anything else (code error, timeout, interruption, post-write failure) stops the run, terminates
                       workers and moves partial outputs to partial/<job>/ (preserved, never reused or deleted).
  load_strict      F4  exact expected episode set, record/archive/seed identity, exact evaluation-row count,
                       job status per episode, archive key set, width, zero padding and counts.
  describe         F8  descriptive contrasts carry no p value.
  cp_min_n         F7  smallest n at which k events pass a one-sided Clopper-Pearson bound.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import os
import platform
import shutil
import time
from multiprocessing import TimeoutError as MPTimeout
from multiprocessing import get_context
from pathlib import Path

import numpy as np

RUNTIME_PACKAGES = ("numpy", "scipy", "stim", "pymatching", "ldpc")
INFRA = (OSError, MemoryError, EOFError, ConnectionError)      # retriable only if raised before any output exists


# ------------------------------------------------------------------ F3: revision and runtime identity
class PreflightError(SystemExit):
    pass


def check_revision(expected_head, freeze_rel, code_head, git, result_paths=()):
    """git(args) -> stdout str. Raises PreflightError unless HEAD is exactly the approved freeze commit."""
    head = git(["rev-parse", "HEAD"]).strip()
    if head != expected_head:
        raise PreflightError(f"HEAD {head} != approved {expected_head}")
    parent = git(["rev-parse", "HEAD^"]).strip()
    if parent != code_head:
        raise PreflightError(f"HEAD^ {parent} != frozen code_head {code_head}")
    changed = set(git(["diff", "--name-only", "HEAD^", "HEAD"]).split())
    if changed != {freeze_rel}:
        raise PreflightError(f"freeze commit changes {sorted(changed)}, not only {freeze_rel}")
    if git(["status", "--porcelain", "--untracked-files=no"]).strip():
        raise PreflightError("working tree not clean")
    for rp in result_paths:
        if git(["ls-tree", "-r", "--name-only", "HEAD", rp]).strip():
            raise PreflightError(f"results already tracked at HEAD: {rp}")
    return head


def runtime_identity():
    out = {"python": platform.python_version(), "implementation": platform.python_implementation(),
           "platform": platform.platform()}
    for p in RUNTIME_PACKAGES:
        try:
            out[p] = md.version(p)
        except md.PackageNotFoundError:
            out[p] = None
    return out


def check_runtime(frozen, current=None):
    """-> mismatched fields. Every RUNTIME_PACKAGES field must be frozen; a missing or None field fails."""
    cur = current if current is not None else runtime_identity()
    need = ("python", "implementation", "platform") + RUNTIME_PACKAGES
    return sorted(k for k in need if frozen.get(k) is None or cur.get(k) != frozen.get(k))


# ------------------------------------------------------------------ F5: exclusive reservation and journal
class Reservation:
    """Exclusive run lock. Creating it twice fails; it is never removed (a directory holds one attempt)."""

    def __init__(self, run_dir, info):
        self.path = Path(run_dir) / "RUN.lock"
        Path(run_dir).mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise PreflightError(f"{self.path} exists: this run directory was already reserved") from None
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "reserved": _now(), **info}, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())


class Journal:
    def __init__(self, run_dir):
        self.path = Path(run_dir) / "journal.jsonl"

    def log(self, event, **kw):
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"t": _now(), "event": event, **kw}, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def events(self):
        if not self.path.exists():
            return []
        return [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x]


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _preserve(run_dir, name, outputs, journal, attempt):
    moved = []
    for rel in outputs:
        src = Path(run_dir) / rel
        if src.exists():
            dst = Path(run_dir) / "partial" / name / f"attempt{attempt}" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved.append(dst.relative_to(run_dir).as_posix())
    if moved:
        journal.log("partial_preserved", job=name, attempt=attempt, files=moved)
    return moved


def run_jobs(jobs, job_fn, run_dir, outputs_of, workers=8, timeout=20_000, on_progress=None):
    """jobs: list of (name, args). outputs_of(name) -> relative output paths. Returns the status dict.

    Fail-closed: any failure except a pre-write infrastructure error stops the run (state "failed"), terminates
    the pool and preserves partial outputs. A pre-write infrastructure error gets one bounded retry."""
    run_dir = Path(run_dir)
    journal = Journal(run_dir)
    status = {"state": "running", "started": _now(), "jobs": {}, "reruns": {}, "n_jobs": len(jobs)}
    st = run_dir / "RUN_STATUS.json"
    _dump(st, status)
    journal.log("run_start", n_jobs=len(jobs), workers=workers)
    pool = get_context("spawn").Pool(workers)
    done = set()
    try:
        hs = [(n, a, pool.apply_async(job_fn, (a,))) for n, a in jobs]
        retry = []
        for n, a, h in hs:
            journal.log("job_wait", job=n)
            try:
                h.get(timeout=timeout)
            except INFRA as ex:
                if any((run_dir / o).exists() for o in outputs_of(n)):
                    journal.log("job_failed_after_write", job=n, error=repr(ex))
                    raise RunStop(f"{n}: infrastructure error after output was written") from ex
                journal.log("job_infra_prewrite", job=n, error=repr(ex))
                status["reruns"][n] = {"first_error": repr(ex)}
                retry.append((n, a))
                continue
            except MPTimeout as ex:
                journal.log("job_timeout", job=n)
                raise RunStop(f"{n}: timed out after {timeout}s") from ex
            done.add(n)
            status["jobs"][n] = {"returncode": 0}
            journal.log("job_done", job=n)
            _dump(st, status)
            if on_progress:
                on_progress(n)
        for n, a in retry:
            journal.log("job_retry", job=n)
            pool.apply_async(job_fn, (a,)).get(timeout=timeout)
            done.add(n)
            status["jobs"][n] = {"returncode": 0, "rerun": True}
            journal.log("job_done", job=n, rerun=True)
        status["state"] = "ready_for_analysis"
        pool.close()
    except BaseException as ex:      # noqa: BLE001  (fail closed: code errors, timeouts, interruptions)
        pool.terminate()
        status["state"], status["error"] = "failed", repr(ex)
        for n, _ in jobs:
            if n not in done:
                _preserve(run_dir, n, outputs_of(n), journal, 1)
        journal.log("run_failed", error=repr(ex))
        raise
    finally:
        pool.join()
        status["finished"] = _now()
        _dump(st, status)
    journal.log("run_end", state=status["state"])
    return status


class RunStop(RuntimeError):
    pass


def _dump(p, obj):
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, p)


# ------------------------------------------------------------------ F4: strict archive and identity binding
def load_strict(run_dir, episodes, arms, eval_rows, scored, seeds_for):
    """episodes {schedule: n}; seeds_for(s, e) -> {"bNN:part": int} for every block and part the job samples."""
    run_dir = Path(run_dir)
    st = json.loads((run_dir / "RUN_STATUS.json").read_text(encoding="utf-8"))
    want = {(s, e) for s, n in episodes.items() for e in range(n)}
    names = {f"{s}_e{e}" for s, e in want}
    if st.get("state") != "ready_for_analysis":
        raise ValueError(f"run state {st.get('state')}")
    if st.get("n_jobs") != len(want) or set(st.get("jobs", {})) != names \
            or any(j.get("returncode") != 0 for j in st["jobs"].values()):
        raise ValueError("job status does not match the expected episodes")
    files = sorted((run_dir / "records").glob("*.json"))
    if {p.stem for p in files} != names:
        raise ValueError("record files do not match the expected episodes")
    width = -(-eval_rows // 8)
    recs, seen_arc, seen_id = [], set(), set()
    for p in files:
        r = json.loads(p.read_text(encoding="utf-8"))
        ident = (r.get("schedule"), r.get("episode"))
        if ident not in want or f"{ident[0]}_e{ident[1]}" != p.stem or ident in seen_id:
            raise ValueError(f"record identity {ident} in {p.name}")
        seen_id.add(ident)
        if r.get("archive") != f"archives/{p.stem}.npz" or r["archive"] in seen_arc:
            raise ValueError(f"archive path {r.get('archive')}")
        seen_arc.add(r["archive"])
        if r.get("eval_per_block") != eval_rows:
            raise ValueError(f"eval_per_block {r.get('eval_per_block')} != {eval_rows}")
        if list(r.get("arms", [])) != list(arms):
            raise ValueError("arm list")
        if r.get("seeds") != seeds_for(*ident):
            raise ValueError(f"seed identity {p.stem}")
        arc = run_dir / r["archive"]
        if hashlib.sha256(arc.read_bytes()).hexdigest() != r.get("archive_sha256"):
            raise ValueError("archive hash")
        if [b["block"] for b in r["blocks"]] != list(scored):
            raise ValueError("scored blocks")
        z = np.load(arc)
        if set(z.files) != {f"b{t:02d}_{a}" for t in scored for a in arms}:
            raise ValueError("archive keys")
        for b in r["blocks"]:
            for a in arms:
                v = z[f"b{b['block']:02d}_{a}"]
                if v.dtype != np.uint8 or v.shape != (width,):
                    raise ValueError("archive width")
                bits = np.unpackbits(v)
                if bits[eval_rows:].any() or int(bits.sum()) != b["errors"][a]:
                    raise ValueError("count mismatch")
        recs.append(r)
    return st, recs


# ------------------------------------------------------------------ F7, F8: bounds and descriptive contrasts
def cp_upper(k, n, a=0.05):
    from scipy.stats import beta
    return 1.0 if k >= n else float(beta.ppf(1 - a, k + 1, n - k))


def cp_min_n(k, a=0.05, limit=0.05):
    n = k + 1
    while cp_upper(k, n, a) > limit:
        n += 1
    return n


def describe(d):
    """Descriptive contrast: no p value (F8)."""
    d = list(d)
    return {"n": len(d), "mean": float(np.mean(d)) if d else None, "median": float(np.median(d)) if d else None,
            "better": sum(x < 0 for x in d), "worse": sum(x > 0 for x in d), "tied": sum(x == 0 for x in d)}
