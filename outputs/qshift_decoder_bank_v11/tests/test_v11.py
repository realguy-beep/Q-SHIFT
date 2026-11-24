"""v11 execution-safety tests. No Stim sampling (synthetic_study blocks every sampler in each process it runs in).

Lifecycle tests use tiny jobs. Integration tests build a throw-away git repository from this checkout's files, freeze it,
and drive the real launch, recovery and analysis through separate processes."""
from __future__ import annotations

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import warnings
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import synthetic_study as SY  # noqa: E402,I001
import lifecycle11 as LC  # noqa: E402
import policy as P  # noqa: E402
import runkit as RK  # noqa: E402
import strict as S  # noqa: E402
import study11 as ST  # noqa: E402
import validate as V10  # noqa: E402

C = SY.C
REPO = SY.V11.parents[1]
SEEDS, TR = V10.db8_seeds(), V10.training()
NAMES = ST.job_names(C.EPISODES)
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


# ------------------------------------------------------------------ tiny jobs (spawned)
def tiny(ep, arg):
    if arg == "infra_once" and len(LC.read_events(ep.log)[0]) == 1:
        raise OSError("before sampling")
    if arg == "infra_always":
        raise OSError("before sampling")
    ep.sampling_intent()
    if arg == "intent_then_infra":
        raise OSError("possible sampling")
    ep.sampling_confirmed({"b00:det": 1})
    if arg == "confirmed_then_infra":
        raise OSError("sampled")
    if arg == "code":
        raise ValueError("code")
    if arg == "die":
        os._exit(7)
    if arg == "sleep":
        time.sleep(120)
    if arg == "no_commit":
        return
    if arg == "partial":
        ep.stage.mkdir()
        (ep.stage / "archive.npz").write_bytes(b"half")
        raise OSError("mid-write")
    if arg == "swallow":                         # a job that catches everything and tries to commit late
        while True:
            try:
                time.sleep(0.05)
                if not LC.supervisor_alive(ep.run):
                    ep.commit({}, b"late")
            except BaseException:      # noqa: BLE001
                pass
    ep.commit({}, b"archive")


def supervisor(run, mode):
    """Subprocess: 'claim' dies right after START.json; otherwise the supervisor dies when job a is done."""
    res = LC.reserve(run, {}, ["a", "b"], 2)
    if mode == "claim":
        LC._claim(res)
        os._exit(9)
    if mode == "reserved":
        os._exit(9)
    LC.execute(res, [("a", None), ("b", mode)], tiny, on_done=lambda n: os._exit(9))


def hold_slot(run, seconds):
    k = LC.Lock(Path(run) / "locks" / "worker000")
    print("held", flush=True)
    time.sleep(float(seconds))
    k.close()


def racer(run, go, out):
    """Subprocess: load a reservation *with* its token and start at the barrier."""
    d = json.loads((Path(run).parent / "res.json").read_text())
    while not Path(go).exists():
        pass
    try:
        LC.execute(LC.Reservation(run, d["body"], d["token"]), [("a", None)], tiny)
        Path(out).write_text("won")
    except LC.StartRefused as ex:
        Path(out).write_text(f"refused {ex}")


def call(fn, *args, wait=True):
    code = (f"import sys\nif __name__ == '__main__':\n sys.path.insert(0, {str(HERE)!r})\n import test_v11 as T\n"
            f" T.{fn}(*{[str(a) for a in args]!r})\n")
    p = subprocess.Popen([sys.executable, "-B", "-c", code], env=ENV, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if wait:
        p.communicate(timeout=100)
    return p


def snapshot(run):
    return {p.relative_to(run).as_posix(): (p.read_bytes() if p.is_file() else None) for p in Path(run).rglob("*")}


def alive(pid):
    if os.name != "nt":
        return subprocess.run(["ps", "-p", str(pid)], capture_output=True).returncode == 0
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return f'"{pid}"' in out and "python" in out.lower()


def retry_recover(run, seconds=20):
    end = time.monotonic() + seconds
    while True:
        try:
            return LC.recover(run)
        except LC.NotQuiescent:
            if time.monotonic() > end:
                raise
            time.sleep(0.2)


class Base(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.tmp = Path(self._d.name)
        self.run_dir = self.tmp / "run"

    def tearDown(self):
        self._d.cleanup()

    def go(self, arg=None, names=("a",), **kw):
        res = LC.reserve(self.run_dir, {}, list(names), 1)
        return LC.execute(res, [(n, arg) for n in names], tiny, **kw)

    def close(self):
        return S.loads((self.run_dir / "CLOSE.json").read_bytes())

    def rejected(self):
        with self.assertRaises(S.Invalid):
            LC.load_success(self.run_dir)


class StartTests(Base):                                                       # blocker 1
    def test_success(self):
        self.assertEqual(self.go(names=("a", "b"))["outcome"], "succeeded")
        self.assertEqual(LC.load_success(self.run_dir)[1]["a"][1], b"archive")

    def test_simultaneous_starts_from_processes(self):
        for k in range(5):
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                run = Path(d) / "run"
                res = LC.reserve(run, {}, ["a"], 1)
                (Path(d) / "res.json").write_text(json.dumps({"body": res.body, "token": res.token}))
                ps = [call("racer", run, Path(d) / "go", Path(d) / f"out{i}", wait=False) for i in range(4)]
                time.sleep(1.5)
                (Path(d) / "go").touch()
                for p in ps:
                    p.communicate(timeout=60)
                outs = [(Path(d) / f"out{i}").read_text() for i in range(4)]
                self.assertEqual(sorted(x.split()[0] for x in outs), ["refused"] * 3 + ["won"], outs)
                ev = LC.read_events(run / "journal.jsonl")[0]
                self.assertEqual([x["event"] for x in ev].count("run_start"), 1)
                LC.load_success(run)

    def test_loser_changes_nothing(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        sup = LC._claim(res)
        before = snapshot(self.run_dir / "events"), {p.name for p in self.run_dir.iterdir()}, (self.run_dir / "START.json").read_bytes()
        with self.assertRaises(LC.StartRefused):
            LC.execute(res, [("a", None)], tiny)
        self.assertEqual(before, (snapshot(self.run_dir / "events"), {p.name for p in self.run_dir.iterdir()},
                                  (self.run_dir / "START.json").read_bytes()))
        sup.close()
        with self.assertRaises(LC.StartRefused):                             # lock free, but already started
            LC.execute(res, [("a", None)], tiny)

    def test_reservation_file_is_not_ownership(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        before = snapshot(self.run_dir)
        for token in (None, "", "0" * 64, res.body["token_sha256"]):
            with self.assertRaises(LC.StartRefused):
                LC.execute(LC.Reservation(self.run_dir, LC.read_reservation(self.run_dir), token), [("a", None)], tiny)
        with self.assertRaises(LC.StartRefused):
            LC.execute(res, [("b", None)], tiny)
        self.assertEqual(before, snapshot(self.run_dir))
        with self.assertRaises(LC.StartRefused):
            LC.reserve(self.run_dir, {}, ["a"], 1)

    def test_one_lifecycle(self):
        for arg in (None, "code"):
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                run = Path(d) / "run"
                res = LC.reserve(run, {}, ["a"], 1)
                try:
                    LC.execute(res, [("a", arg)], tiny)
                except ValueError:
                    pass
                before = snapshot(run)
                with self.assertRaises(LC.StartRefused):
                    LC.execute(res, [("a", None)], tiny)
                self.assertEqual(before, snapshot(run))

    def test_interrupted_startup(self):
        call("supervisor", self.run_dir, "claim")
        self.assertEqual({p.name for p in self.run_dir.iterdir()}, {"RUN.json", "START.json", *LC.DIRS})
        body = LC.read_reservation(self.run_dir)
        self.rejected()
        self.assertEqual(LC.recover(self.run_dir)["inventory"]["jobs"]["a"]["state"], "not_started")
        with self.assertRaises(LC.StartRefused):
            LC.execute(LC.Reservation(self.run_dir, body, "x"), [("a", None), ("b", None)], tiny)
        self.rejected()

    def test_torn_start_marker_never_restarts(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        (self.run_dir / "START.json").write_bytes(b"{")
        with self.assertRaises(LC.StartRefused):
            LC.execute(res, [("a", None)], tiny)

    def test_recovery_then_restart(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        LC.recover(self.run_dir)
        before = snapshot(self.run_dir)
        with self.assertRaises(LC.StartRefused):
            LC.execute(res, [("a", None)], tiny)
        self.assertEqual(before, snapshot(self.run_dir))
        with self.assertRaises(LC.RunStop):
            LC.recover(self.run_dir)

    def test_interrupted_recovery_still_blocks_start(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        real, LC.inventory = LC.inventory, lambda run: (_ for _ in ()).throw(KeyboardInterrupt())
        try:
            with self.assertRaises(KeyboardInterrupt):
                LC.recover(self.run_dir)
        finally:
            LC.inventory = real
        with self.assertRaises(LC.StartRefused):
            LC.execute(res, [("a", None)], tiny)
        self.assertEqual(LC.recover(self.run_dir)["outcome"], "recovered")

    def test_tampered_reservation_and_missing_locks(self):
        res = LC.reserve(self.run_dir, {"head": "x"}, ["a"], 1)
        raw = (self.run_dir / "RUN.json").read_bytes()
        (self.run_dir / "RUN.json").write_bytes(raw.replace(b'"x"', b'"y"'))
        with self.assertRaises(S.Invalid):
            LC.execute(res, [("a", None)], tiny)
        (self.run_dir / "RUN.json").write_bytes(raw)
        (self.run_dir / "locks" / "supervisor").unlink()
        for f in (lambda: LC.execute(res, [("a", None)], tiny), lambda: LC.recover(self.run_dir)):
            with self.assertRaises(S.Invalid):
                f()


class FailureTests(Base):
    def test_failures_close_as_failed(self):
        want = {"infra_always": "started", "intent_then_infra": "possibly_sampled", "confirmed_then_infra": "sampled_no_output",
                "code": "sampled_no_output", "die": "sampled_no_output", "partial": "partial", "no_commit": "sampled_no_output"}
        for arg, st in want.items():
            with self.subTest(arg), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                self.run_dir = Path(d) / "run"
                with self.assertRaises(Exception):
                    self.go(arg)
                c = self.close()
                self.assertEqual((c["outcome"], c["inventory"]["jobs"]["a"]["state"]), ("failed", st))
                n = [x["event"] for x in LC.read_events(self.run_dir / "events/a.jsonl")[0]].count("started")
                self.assertEqual(n, 2 if arg == "infra_always" else 1)        # never retried after possible sampling
                self.rejected()
                with self.assertRaises(LC.RunStop):
                    LC.recover(self.run_dir)

    def test_partial_preserved_in_place(self):
        with self.assertRaises(LC.RunStop):
            self.go("partial")
        self.assertEqual((self.run_dir / "staging/a/archive.npz").read_bytes(), b"half")
        self.assertIn("staging/a/archive.npz", self.close()["inventory"]["files"])

    def test_one_retry_is_accounted(self):
        self.assertEqual(self.go("infra_once")["outcome"], "succeeded")
        LC.load_success(self.run_dir)

    def test_pool_startup_interrupt_stall_and_final_check(self):
        def boom(*a):
            raise RuntimeError("x")

        def intr(*a):
            raise KeyboardInterrupt
        for kw, arg, err in (({"pool": boom}, None, RuntimeError), ({"on_done": intr}, None, KeyboardInterrupt),
                             ({"stall_timeout": 4}, "sleep", LC.RunStop), ({"final_check": boom}, None, RuntimeError)):
            with self.subTest(str(kw)), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                self.run_dir = Path(d) / "run"
                with self.assertRaises(err):
                    self.go(arg, **kw)
                self.assertEqual(self.close()["outcome"], "failed")
                self.rejected()

    def test_unquiesced_failure_is_not_closed(self):
        """A process that still holds a worker slot prevents any terminal record."""
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        p = call("hold_slot", self.run_dir, 60, wait=False)
        p.stdout.readline()
        real = LC._all_slots
        LC._all_slots = lambda run, w, t: real(run, w, 1)
        try:
            with self.assertRaises(LC.NotQuiescent):
                LC.execute(res, [("a", None)], tiny)
            self.assertFalse((self.run_dir / "CLOSE.json").exists())
            with self.assertRaises(LC.NotQuiescent):
                LC.recover(self.run_dir)
            self.assertFalse((self.run_dir / "RECOVER.json").exists())
        finally:
            LC._all_slots = real
            p.kill()
            p.communicate()
        self.assertEqual(retry_recover(self.run_dir)["outcome"], "recovered")


class RecoveryTests(Base):                                                    # blocker 2
    def test_supervisor_death_kills_orphans(self):
        for mode in ("sleep", "swallow"):
            with self.subTest(mode), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                run = Path(d) / "run"
                self.assertEqual(call("supervisor", run, mode).returncode, 9)
                c = retry_recover(run)
                self.assertEqual(c["inventory"]["jobs"]["a"]["state"], "committed")
                self.assertIn(c["inventory"]["jobs"]["b"]["state"], ("not_started", "started", "possibly_sampled", "sampled_no_output"))
                left = [int(x) for f in (run / "events").iterdir() for x in {e["pid"] for e in LC.read_events(f)[0] if "pid" in e}]
                self.assertEqual([p for p in left if alive(p)], [])
                before = snapshot(run)
                time.sleep(3)                                                # a late write would show here
                self.assertEqual(before, snapshot(run))
                with self.assertRaises(S.Invalid):
                    LC.load_success(run)

    def test_recover_waits_for_live_worker(self):
        LC.reserve(self.run_dir, {}, ["a"], 1)
        p = call("hold_slot", self.run_dir, 60, wait=False)
        p.stdout.readline()
        before = snapshot(self.run_dir / "events"), {q.name for q in self.run_dir.iterdir()}
        with self.assertRaises(LC.NotQuiescent):
            LC.recover(self.run_dir)
        self.assertEqual(before, (snapshot(self.run_dir / "events"), {q.name for q in self.run_dir.iterdir()}))
        p.kill()
        p.communicate()
        retry_recover(self.run_dir)

    def test_recover_refuses_live_supervisor(self):
        sup = LC._claim(LC.reserve(self.run_dir, {}, ["a"], 1))
        with self.assertRaises(LC.NotQuiescent):
            LC.recover(self.run_dir)
        sup.close()

    def test_fence_stops_late_worker(self):
        """A task handed to a worker before the supervisor died, but only started after recovery."""
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        LC._claim(res).close()
        args = (str(self.run_dir), res.body["run_id"], 1, "a", 1, tiny, None, None, None)
        with self.assertRaises(LC.RunStop):                                  # supervisor gone, not yet recovered
            LC._guarded(*args)
        LC.recover(self.run_dir)
        with self.assertRaises(LC.RunStop):
            LC._guarded(*args)
        ep = LC.Episode(self.run_dir, res.body["run_id"], "a", None)
        ep._sampled = True
        with self.assertRaises(LC.Fenced):
            ep.commit({}, b"late")
        self.assertEqual((snapshot(self.run_dir / "episodes"), snapshot(self.run_dir / "staging")), ({}, {}))

    def test_commit_needs_confirmation_and_never_replaces(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        sup = LC._claim(res)
        one = LC.Episode(self.run_dir, res.body["run_id"], "a", None)
        with self.assertRaises(S.Invalid):
            one.commit({}, b"x")
        one.sampling_intent()
        with self.assertRaises(S.Invalid):
            one.commit({}, b"x")
        one.sampling_confirmed({})
        one.commit({}, b"1")
        with self.assertRaises(LC.RunStop):
            one.commit({}, b"2")
        sup.close()
        self.assertEqual(LC.recover(self.run_dir)["inventory"]["jobs"]["a"]["state"], "conflict")
        self.assertEqual((self.run_dir / "episodes/a/archive.npz").read_bytes(), b"1")

    def test_classification(self):
        def edit(f):
            def g(d):
                (d / f).write_bytes((d / f).read_bytes()[:-2])
            return g

        def manifest(change):
            def g(d):
                c = json.loads((d / "COMMIT.json").read_bytes())
                change(c)
                (d / "COMMIT.json").write_bytes(S.jbytes(c))
            return g
        cases = {
            "empty": lambda d: [p.unlink() for p in d.iterdir()],
            "no manifest": lambda d: (d / "COMMIT.json").unlink(),
            "no record": lambda d: (d / "record.json").unlink(),
            "extra file": lambda d: (d / "x").write_bytes(b""),
            "extra folder file": lambda d: ((d / "s").mkdir(), (d / "s" / "x").write_bytes(b"")),
            "torn manifest": edit("COMMIT.json"), "torn record": edit("record.json"), "short archive": edit("archive.npz"),
            "flipped byte": lambda d: (d / "archive.npz").write_bytes(b"Xrchive"),
            "other run": manifest(lambda c: c.update(run_id="0")),
            "other job": manifest(lambda c: c.update(job="b")),
            "extra field": manifest(lambda c: c.update(note=1)),
            "size": manifest(lambda c: c["files"]["archive.npz"].update(bytes=8)),
            "duplicate key": lambda d: (d / "COMMIT.json").write_bytes(
                (d / "COMMIT.json").read_bytes().replace(b'"job": "a",', b'"job": "a", "job": "a",')),
        }
        for k, f in cases.items():
            with self.subTest(k), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                run = Path(d) / "run"
                res = LC.reserve(run, {}, ["a"], 1)
                sup = LC._claim(res)
                ep = LC.Episode(run, res.body["run_id"], "a", None)
                ep.sampling_intent()
                ep.sampling_confirmed({})
                ep.commit({}, b"archive")
                sup.close()
                self.assertEqual(LC.inventory(run)["jobs"]["a"]["state"], "committed")
                f(run / "episodes" / "a")
                before = snapshot(run / "episodes")
                c = LC.recover(run)["inventory"]["jobs"]["a"]
                self.assertEqual(c["state"], "corrupt")
                self.assertEqual(before, snapshot(run / "episodes"))

    def test_kill_around_rename(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        sup = LC._claim(res)
        ep = LC.Episode(self.run_dir, res.body["run_id"], "a", None)
        ep.sampling_intent()
        self.assertEqual(LC.inventory(self.run_dir)["jobs"]["a"]["state"], "possibly_sampled")
        ep.sampling_confirmed({})
        self.assertEqual(LC.inventory(self.run_dir)["jobs"]["a"]["state"], "sampled_no_output")
        real, LC.os.rename = os.rename, lambda *a: (_ for _ in ()).throw(OSError("killed"))
        try:
            with self.assertRaises(OSError):
                ep.commit({}, b"z")
        finally:
            LC.os.rename = real
        self.assertEqual(LC.inventory(self.run_dir)["jobs"]["a"]["state"], "partial")
        os.rename(ep.stage, ep.final)
        with open(ep.log, "ab") as f:
            f.write(b'{"event": "comm')
        j = LC.inventory(self.run_dir)["jobs"]["a"]
        self.assertEqual((j["state"], j["events_valid"]), ("committed", False))
        sup.close()
        shutil.rmtree(ep.final)
        with open(ep.log, "r+b") as f:
            f.truncate(0)
        (self.run_dir / "episodes" / "stranger").mkdir()
        c = LC.recover(self.run_dir)["inventory"]
        self.assertEqual((c["jobs"]["a"]["state"], c["unexpected"]), ("not_started", ["episodes/stranger"]))


def rechain(events):
    """Rewrite an event list as a file whose hash chain is valid (an attacker's best edit)."""
    out, prev = b"", LC.GENESIS
    for i, x in enumerate(events):
        d = {k: v for k, v in x.items() if k not in ("hash", "seq", "prev")}
        d.update(seq=i, prev=prev)
        d["hash"] = prev = S.sha(json.dumps(d, sort_keys=True).encode())
        out += json.dumps(d, sort_keys=True).encode() + b"\n"
    return out


def reclose(run, outcome=None):
    """Rewrite CLOSE.json to agree with the (edited) files, so that only the semantic checks can object."""
    c = json.loads((run / "CLOSE.json").read_bytes())
    (run / "CLOSE.json").unlink()
    c["inventory"]["files"] = LC.inventory(run)["files"]
    c["outcome"] = outcome or c["outcome"]
    (run / "CLOSE.json").write_bytes(S.jbytes(c))


class AdmissionLifecycleTests(Base):                                          # blocker 3, lifecycle part
    @classmethod
    def setUpClass(cls):
        cls._c = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.good = Path(cls._c.name) / "good"
        res = LC.reserve(cls.good, {}, ["a", "b"], 2)
        LC.execute(res, [("a", None), ("b", "infra_once")], tiny)
        LC.load_success(cls.good)

    @classmethod
    def tearDownClass(cls):
        cls._c.cleanup()

    def fresh(self):
        shutil.rmtree(self.run_dir, ignore_errors=True)
        shutil.copytree(self.good, self.run_dir)
        return self.run_dir

    def test_journal_rejections(self):
        base = LC.read_events(self.good / "journal.jsonl")[0]
        ix = {x["event"]: i for i, x in enumerate(base)}
        ev = lambda n, **k: {"t": base[-1]["t"], "event": n, **k}   # noqa: E731
        cases = {
            "run_failed inside": lambda e: e.insert(-1, ev("run_failed", error="x")),
            "failed end": lambda e: e[-1].update(state="failed"),
            "no end": lambda e: e.pop(),
            "after end": lambda e: e.append(ev("job_done", job="a", commit_sha256="0")),
            "two starts": lambda e: e.insert(1, copy.deepcopy(e[0])),
            "other run": lambda e: e[0].update(run_id="0"),
            "job count": lambda e: e[0].update(n_jobs=3),
            "submission order": lambda e: e.__setitem__(slice(1, 3), [e[2], e[1]]),
            "missing submission": lambda e: e.pop(1),
            "unknown job": lambda e: e[ix["job_done"]].update(job="z"),
            "done twice": lambda e: e.insert(-1, copy.deepcopy(e[ix["job_done"]])),
            "job not done": lambda e: e.pop(ix["job_done"]),
            "retry missing": lambda e: e.pop(ix["job_retry"]),
            "retry of other job": lambda e: e[ix["job_retry"]].update(job="a"),
            "unknown event": lambda e: e.insert(-1, ev("note")),
            "other commit": lambda e: e[ix["job_done"]].update(commit_sha256="0" * 64),
            "time order": lambda e: e[0].update(t="2999-01-01T00:00:00Z"),
        }
        for k, f in cases.items():
            with self.subTest(k):
                run = self.fresh()
                e = copy.deepcopy(base)
                f(e)
                (run / "journal.jsonl").write_bytes(rechain(e))
                self.rejected()                                              # caught by the closing hashes
                reclose(run)
                self.rejected()                                              # and by the journal rules themselves

    def test_worker_event_rejections(self):
        base = LC.read_events(self.good / "events/b.jsonl")[0]
        cases = {"extra start": lambda e: e.insert(1, copy.deepcopy(e[0])), "one start missing": lambda e: e.pop(0),
                 "no confirmation": lambda e: e.pop(-2), "order": lambda e: e.__setitem__(slice(-2, None), [e[-1], e[-2]]),
                 "no commit": lambda e: e.pop(), "attempt": lambda e: e[1].update(attempt=1),
                 "run id": lambda e: e[0].update(run_id="0")}
        for k, f in cases.items():
            with self.subTest(k):
                run = self.fresh()
                e = copy.deepcopy(base)
                f(e)
                (run / "events/b.jsonl").write_bytes(rechain(e))
                reclose(run)
                self.rejected()

    def test_file_rejections(self):
        cases = {"broken chain": lambda r: (r / "journal.jsonl").write_bytes((r / "journal.jsonl").read_bytes().replace(b'"job": "a"', b'"job": "b"', 1)),
                 "torn journal": lambda r: (r / "journal.jsonl").write_bytes((r / "journal.jsonl").read_bytes()[:-3]),
                 "recover marker": lambda r: (r / "RECOVER.json").write_bytes(b"{}"),
                 "failure file": lambda r: (r / "FAILURE.json").write_bytes(b"{}"),
                 "staging leftover": lambda r: (r / "staging/a").mkdir(),
                 "unknown episode": lambda r: (r / "episodes/z").mkdir(),
                 "missing episode": lambda r: shutil.rmtree(r / "episodes/a"),
                 "swapped archives": lambda r: (r / "episodes/a/archive.npz").write_bytes(b"other"),
                 "start record": lambda r: (r / "START.json").write_bytes(b'{"run_id": "0", "pid": 1, "started": "x"}')}
        for k, f in cases.items():
            for also_close in (False, True):
                with self.subTest(k, reclosed=also_close):
                    run = self.fresh()
                    f(run)
                    if also_close:
                        reclose(run)
                    self.rejected()

    def test_outcomes(self):
        for o in ("failed", "recovered", "ready_for_analysis"):
            run = self.fresh()
            reclose(run, o)
            self.rejected()
        run = self.fresh()
        (run / "CLOSE.json").unlink()
        self.rejected()
        run = self.fresh()
        (run / "CLOSE.json").write_bytes(b'{"outcome": "failed", ' + (self.good / "CLOSE.json").read_bytes()[1:])
        self.rejected()                                                      # duplicate key


# ------------------------------------------------------------------ blocker 3: record policy
class PolicyTests(unittest.TestCase):
    def rec(self, n):
        return S.loads((C.ROOT / f"results/dev/records/{n}.json").read_bytes())

    def test_all_committed_records_replay(self):
        for n in NAMES:
            s, e = n.rsplit("_e", 1)
            P.check_record(self.rec(n), SEEDS, TR, (s, int(e)))

    def test_mutations(self):
        """Every mutated field is one the v10 review found unchecked, or a neighbour of it."""
        base = self.rec("U_NEAR_e2")
        i = next(k for k, b in enumerate(base["blocks"]) if b["block"] == 12)
        blk = lambda f: (lambda r: f(r["blocks"][i]))   # noqa: E731
        est = lambda **k: blk(lambda b: b["estimate"].update(k))   # noqa: E731
        both = lambda **k: blk(lambda b: (b["estimate"].update(k), b["estimate_ad3"].update(k)))   # noqa: E731
        e0 = base["blocks"][i]["estimate"]
        m = {
            "plausible unknown state": blk(lambda b: b.update(plausible=["NOT_A_BANK_STATE"])),
            "plausible wrong": blk(lambda b: b.update(plausible=["C"])),
            "plausible order": blk(lambda b: b.update(plausible=["B", "A"])),
            "estimate not an object": blk(lambda b: b.update(estimate="invalid")),
            "estimate missing field": blk(lambda b: b["estimate"].pop("flip")),
            "estimate extra field": est(note=1),
            "p_hat bool": both(p_hat=True), "p_hat negative": both(p_hat=-0.1), "b_hat text": both(b_hat="1"),
            "class out of range": both(class_index=10 ** 6), "class float": both(class_index=float(e0["class_index"] or 1)),
            "flip 2": both(flip=2), "flip alone": both(class_index=None), "flagged flip": both(flagged=not e0["flagged"]),
            "true class": both(true_class=1), "learned_correct": both(learned_correct=not e0["learned_correct"]),
            "excluded -1": both(excluded=-1), "excluded 121": both(excluded=121),
            "S1 on an accepted estimate": lambda r: (r["blocks"][0]["estimate"].update(S1=True), r["blocks"][0]["estimate_ad3"].update(S1=True)),
            "estimates differ": blk(lambda b: b["estimate_ad3"].update(p_hat=b["estimate"]["p_hat"] * 1.01)),
            "seg0 negative": blk(lambda b: b.update(seg0=-99)), "seg0 wrong": blk(lambda b: b.update(seg0=b["seg0"] + 1)),
            "seg0 float": blk(lambda b: b.update(seg0=float(b["seg0"]))), "L": blk(lambda b: b.update(L=999)),
            "L bool": blk(lambda b: b.update(L=True)),
            "changes": lambda r: r.update(changes_detected=[-1, 999]), "changes empty": lambda r: r.update(changes_detected=[]),
            "changes float": lambda r: r.update(changes_detected=[float(x) for x in r["changes_detected"]]),
            "g removed": lambda r: r["g"].pop("5"), "g extra": lambda r: r["g"].update({"29": 1.0}),
            "g crosses threshold": lambda r: r["g"].update({"20": 500.0}), "g nan": lambda r: r["g"].update({"5": float("nan")}),
            "g_prev": blk(lambda b: b.update(g_prev=0.0)), "alarm": blk(lambda b: b.update(alarm=not b["alarm"])),
            "lookahead g": blk(lambda b: b["lookahead"].update(g=b["lookahead"]["g"] + 1)),
            "lookahead extra": blk(lambda b: b["lookahead"].update(x=1)), "db8 extra": blk(lambda b: b["db8"].update(x=1)),
            "gfit of an implausible state": blk(lambda b: b["gfit"].update(A=0.0)), "gfit text": blk(lambda b: b["gfit"].update(A="1")), "gfit state": blk(lambda b: b["gfit"].update(Z=1.0)),
            "tracker cur": blk(lambda b: b["tracker"].update(cur="D")), "tracker occ": blk(lambda b: b["tracker"]["occ"].update(A=99)),
            "tracker h": blk(lambda b: b["tracker"]["h"].update(A=0.9)), "tracker outs": blk(lambda b: b["tracker"]["outs"].update(A=["B", "B", "B"])),
            "AD3 seg_len": blk(lambda b: b["estimate_ad3"].update(seg_len=7)),
            "AD3 source": blk(lambda b: (b["source"].update(AD3="window"), b["estimate_ad3"].update(source="window"))),
            "AD3 invented recall": blk(lambda b: (b["source"].update(AD3="recall"), b["estimate_ad3"].update(source="recall", recall_g=1.0))),
            "AD3 key": blk(lambda b: b["keys"].update(AD3='["est", 0.003, 1.0, [1, 2, 3]]')),
            "acceptable": blk(lambda b: b["acceptable"].update(W0F=not b["acceptable"]["W0F"])),
            "burst_action": blk(lambda b: b["burst_action"].update(FIX_OFF=True)),
            "seed float": lambda r: r["seeds"].update({"b06:det": float(r["seeds"]["b06:det"])}),
            "episode bool": lambda r: r.update(episode=True), "timing": lambda r: r.update(timing={}),
            "seconds": lambda r: r.update(seconds=-1), "block float": blk(lambda b: b.update(block=12.0)),
        }
        P.check_record(copy.deepcopy(base), SEEDS, TR, ("U_NEAR", 2))
        for k, f in m.items():
            with self.subTest(k):
                r = copy.deepcopy(base)
                f(r)
                with self.assertRaises(S.Invalid):
                    P.check_record(r, SEEDS, TR, ("U_NEAR", 2))

    def test_known_limit_consistent_numbers_pass(self):
        """Documented limit: numbers whose inputs are not saved can change if every dependent field still agrees."""
        base = self.rec("U_NEAR_e2")
        i = next(k for k, b in enumerate(base["blocks"]) if b["block"] == 12)
        self.assertNotIn("A", base["blocks"][i]["plausible"])
        base["blocks"][i]["gfit"]["A"] = 1e9
        P.check_record(base, SEEDS, TR, ("U_NEAR", 2))

    def test_bank_arm_policy(self):
        """Each bank-family arm must follow its own rule, on every block of one multi-switch episode."""
        base, tried = self.rec("RX_e0"), 0
        for i in range(0, len(base["blocks"]), 5):
            for a in V10.BANKLIKE:
                r = copy.deepcopy(base)
                b = r["blocks"][i]
                b["keys"][a] = next(x for x in sorted(V10.BANK_KEYS) if x != b["keys"][a])
                with self.assertRaises(S.Invalid):
                    P.check_record(r, SEEDS, TR, ("RX", 0))
                tried += 1
        self.assertGreater(tried, 20)

    def test_recall_must_come_from_library(self):
        hit = None
        for n in NAMES:
            r = self.rec(n)
            for i, b in enumerate(r["blocks"]):
                if b["source"]["AD3"] == "recall":
                    hit = (n, i)
                    break
            if hit:
                break
        s, e = hit[0].rsplit("_e", 1)
        for k, v in (("p_hat", 0.0031), ("recall_g", 1e6), ("flagged", True)):
            r = self.rec(hit[0])
            r["blocks"][hit[1]]["estimate_ad3"][k] = v
            with self.assertRaises(S.Invalid):
                P.check_record(r, SEEDS, TR, (s, int(e)))


# ------------------------------------------------------------------ blocker 4
class StrictTests(unittest.TestCase):
    def test_seed_types(self):
        for v in (4.9, 4.0, True, False, "4", None, 0, -1, 2 ** 31, [4], np.int64(4)):
            with self.assertRaises(S.Invalid, msg=repr(v)):
                S.check_seed(v)
            with self.assertRaises(S.Invalid, msg=repr(v)):
                S.check_inventory({**SEEDS, "db8:AA:e0:b00:det": v}, C.all_keys())
        for v in (1, 2 ** 31 - 1):
            S.check_seed(v)

    def test_inventory(self):
        S.check_inventory(SEEDS, C.all_keys())
        a, b = "db8:AA:e0:b00:det", "db8:U_NEAR:e7:b29:eval"
        for bad in ({**SEEDS, a: SEEDS[b]}, {k: v for k, v in SEEDS.items() if k != a}, {**SEEDS, "extra": 5}, [], None):
            with self.assertRaises(S.Invalid):
                S.check_inventory(bad, C.all_keys())
        with self.assertRaises(S.Invalid):
            S.check_inventory(SEEDS, C.all_keys(), {SEEDS[a]})
        with self.assertRaises(S.Invalid):
            S.check_inventory(SEEDS, [*C.all_keys(), a])

    def test_plan(self):
        pl = S.SeedPlan(1, (), lambda s, e, t, p: p)
        for bad in ({"det": 4.9, "lab": 4}, {"det": 4, "lab": 4}, {"det": True, "lab": 4}):
            with self.assertRaises(S.Invalid):
                pl.expected(bad, "x", 0)
        u = S.SeedUse(pl.expected({"det": 5, "lab": 4}, "x", 0))
        u.take(0, "det")
        for t, p in ((0, "det"), (0, "eval"), (1, "det")):
            with self.assertRaises(S.Invalid):
                u.take(t, p)
        with self.assertRaises(S.Invalid):
            u.finish()
        with self.assertRaises(S.Invalid):
            S.SeedPlan(1, (1,), None)

    def test_json(self):
        for bad in (b'{"a": 1, "a": 1}', b'{"a": NaN}', b'{"a": Infinity}', b"{", b"", b"\xff", b"[" * 100000):
            with self.assertRaises(S.Invalid):
                S.loads(bad)
        self.assertFalse(S.same({"a": 1}, {"a": True}) or S.same([1], [1.0]) or S.same(1, "1"))

    def test_archives(self):
        names, rows = ["x", "y"], 12
        ok = {n: np.packbits(np.arange(rows) % 2 == 0) for n in names}

        def npz(d, **k):
            f = io.BytesIO()
            np.savez(f, **d)
            return f.getvalue()

        def raw(members, comp=zipfile.ZIP_STORED, comment=b""):
            f = io.BytesIO()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with zipfile.ZipFile(f, "w", comp) as z:
                    z.comment = comment
                    for n, b in members:
                        z.writestr(n, b)
            return f.getvalue()

        def npy(a, **k):
            f = io.BytesIO()
            np.lib.format.write_array(f, a, **k)
            return f.getvalue()
        x, y = npy(ok["x"]), npy(ok["y"])
        self.assertEqual(int(S.read_archive(npz(ok), names, rows)["x"].sum()), 6)
        S.read_archive(raw([("x.npy", x), ("y.npy", y)], zipfile.ZIP_DEFLATED), names, rows)
        bad = {
            "duplicate": raw([("x.npy", x), ("y.npy", y), ("x.npy", x)]), "missing": raw([("x.npy", x)]),
            "extra": raw([("x.npy", x), ("y.npy", y), ("z.npy", x)]), "folder": raw([("x.npy", x), ("y.npy", y), ("d/", b"")]),
            "comment": raw([("x.npy", x), ("y.npy", y)], comment=b"c"), "prefix": b"junk" + npz(ok),
            "trailing member bytes": raw([("x.npy", x + b"0"), ("y.npy", y)]), "short member": raw([("x.npy", x[:-1]), ("y.npy", y)]),
            "shape": npz({**ok, "x": np.zeros(3, np.uint8)}), "2d": npz({**ok, "x": np.zeros((2, 1), np.uint8)}),
            "dtype": npz({**ok, "x": np.zeros(2, np.int8)}), "bool": npz({**ok, "x": np.zeros(2, bool)}),
            "padding": npz({**ok, "x": np.array([0, 1], np.uint8)}), "object": npz({**ok, "x": np.array([{}, {}], object)}),
            "npy v2": raw([("x.npy", npy(ok["x"], version=(2, 0))), ("y.npy", y)]), "not zip": b"abc", "empty": b"",
            "bzip2": raw([("x.npy", x), ("y.npy", y)], zipfile.ZIP_BZIP2),
            "truncated": npz(ok)[:-10], "crc": npz(ok).replace(ok["x"].tobytes(), b"\x00\x00", 1),
            "huge": raw([("x.npy", x + b"\0" * 10 ** 6), ("y.npy", y)], zipfile.ZIP_DEFLATED),
        }
        for k, b in bad.items():
            with self.subTest(k), self.assertRaises(S.Invalid):
                S.read_archive(b, names, rows)
        with self.assertRaises(S.Invalid):
            S.read_archive(npz(ok), ["x", "x"], rows)


# ------------------------------------------------------------------ integration
FREEZE = "outputs/qshift_decoder_bank_v11/SYNTHETIC_FREEZE.json"
SEED_REL, TRAIN_REL = "outputs/qshift_decoder_bank_v9/DB8_SEEDS.json", "outputs/qshift_decoder_bank_v1/TRAINING.json"


def trace_inputs():
    """Repository files that importing and using the pipeline reads (no sampler, no archive)."""
    code = f"""
import sys
from pathlib import Path
repo = Path({str(REPO)!r}).resolve()
seen = set()
def hook(ev, a):
    if ev == 'open' and a and isinstance(a[0], str):
        p = Path(a[0])
        if p.is_absolute() and p.resolve().is_relative_to(repo) and p.suffix != '.pyc':
            seen.add(p.resolve())
sys.addaudithook(hook)
sys.path.insert(0, {str(HERE)!r})
import synthetic_study as SY, policy as P, validate as V, strict as S
r = S.loads((SY.C.ROOT / 'results/dev/records/AA_e0.json').read_bytes())
P.check_record(r, V.db8_seeds(), V.training(), ('AA', 0))
for m in list(sys.modules.values()):
    f = getattr(m, '__file__', None)
    if f and Path(f).resolve().is_relative_to(repo):
        seen.add(Path(f).resolve())
print('\\n'.join(sorted(p.relative_to(repo).as_posix() for p in seen if p.is_file())))
"""
    out = subprocess.run([sys.executable, "-B", "-c", code], env=ENV, capture_output=True, text=True, check=True).stdout.split()
    assert not [f for f in out if any(m in Path(f).name.upper() for m in ("SEALED", "HIDDEN", "R" "6_")) or f.endswith("_seal.py")], out
    return out


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.autocrlf=false", *a],
                   check=True, capture_output=True)


class IntegrationTests(Base):
    @classmethod
    def setUpClass(cls):
        cls._c = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.repo = Path(cls._c.name).resolve() / "repo"
        files = set(trace_inputs()) | {f"outputs/qshift_decoder_bank_v9/results/dev/records/{n}.json" for n in NAMES}
        files |= set(json.loads((REPO / SEED_REL).read_bytes())["screened"]) | {SEED_REL, TRAIN_REL}
        for f in files:
            (cls.repo / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / f, cls.repo / f)
        git(cls.repo, "init", "-q")
        git(cls.repo, "add", "-A", "-f")
        git(cls.repo, "commit", "-qm", "code")
        cls.files = sorted(files)
        cls.commit_freeze(cls.repo, cls.files)
        cls.head = cls.rev(cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls._c.cleanup()

    @staticmethod
    def rev(repo):
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

    @classmethod
    def commit_freeze(cls, repo, names, **change):
        doc = {"schema": ST.SCHEMA, "code_head": cls.rev(repo), "runtime": RK.runtime_identity(),
               "files": {f: ST.norm(f, (repo / f).read_bytes()) for f in names}, "training": TRAIN_REL, "seeds": SEED_REL,
               "reserved_seeds": sorted(json.loads((repo / SEED_REL).read_bytes())["screened"]),
               "episodes": C.EPISODES, "workers": 4, **change}
        (repo / FREEZE).write_bytes(S.jbytes(doc))
        git(repo, "add", "-f", FREEZE)
        git(repo, "commit", "-qm", "freeze")

    def other_repo(self, edit=None, after=None, **change):
        """A copy of the frozen repository whose code commit is `edit`ed before a new freeze."""
        r = self.tmp / "repo2"
        shutil.copytree(self.repo, r)
        git(r, "reset", "-q", "--hard", "HEAD^")
        if edit:
            edit(r)
            git(r, "commit", "-qam", "edit")
        self.commit_freeze(r, self.files, **change)
        if after:
            after(r)
        return r

    def drive(self, cmd, run=None, arg=None, fault="", repo=None, ok=True, wait=True):
        repo = repo or self.repo
        p = subprocess.Popen([sys.executable, "-B", str(repo / "outputs/qshift_decoder_bank_v11/tests/synthetic_study.py"),
                              str(repo), FREEZE, cmd, str(run or self.run_dir), *([arg] if arg else [])],
                             env={**ENV, "QSHIFT_FAULT": fault}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if not wait:
            return p
        out, err = p.communicate(timeout=300)
        if ok is not None:
            self.assertEqual(p.returncode == 0, ok, err[-1500:])
        return p.returncode, err

    def launch(self, **kw):
        return self.drive("launch", arg=kw.pop("head", self.head), **kw)

    def no_analysis(self, repo=None, run=None):
        out = self.tmp / "ANALYSIS.json"
        err = self.drive("analyze", run=run, arg=str(out), repo=repo, ok=False)[1]
        self.assertIn("Invalid", err.strip().splitlines()[-1])
        self.assertFalse(out.exists())
        return err

    # ---- success
    def test_end_to_end(self):
        self.launch()
        a, b = self.tmp / "A.json", self.tmp / "B.json"
        self.drive("analyze", arg=str(a))
        self.drive("analyze", arg=str(b))
        self.assertEqual(a.read_bytes(), b.read_bytes())
        res = S.loads(a.read_bytes())
        self.assertEqual((len(res["episodes"]), res["provenance"]["head"]), (64, self.head))
        self.drive("analyze", arg=str(a), ok=False)                          # never overwrites
        self.drive("launch", arg=self.head, ok=False)                        # folder already used
        before = snapshot(self.run_dir)
        self.drive("recover", ok=False)                                      # closed runs are not recovered
        self.assertEqual(before, snapshot(self.run_dir))
        # same run, other revision: not admitted
        r2 = self.other_repo(lambda r: (r / TRAIN_REL).write_bytes((r / TRAIN_REL).read_bytes() + b"\n"))
        self.assertIn("another revision", self.no_analysis(repo=r2))
        # edited record, commit and close made consistent: still rejected by journal binding
        d = self.run_dir / "episodes/AA_e0"
        rec = json.loads((d / "record.json").read_bytes())
        rec["blocks"][0]["errors"]["LA_R2"] += 1
        (d / "record.json").write_bytes(S.jbytes(rec))
        self.no_analysis()
        c = json.loads((d / "COMMIT.json").read_bytes())
        raw = (d / "record.json").read_bytes()
        c["files"]["record.json"] = {"bytes": len(raw), "sha256": S.sha(raw)}
        (d / "COMMIT.json").write_bytes(S.jbytes(c))
        reclose(self.run_dir)
        self.assertIn("differs from the journal", self.no_analysis())

    def test_retry_then_success(self):
        self.launch(fault="AB_e1:infra_once")
        self.drive("analyze", arg=str(self.tmp / "A.json"))

    # ---- failures inside a run
    def test_failed_runs_are_never_analysed(self):
        for fault, state in (("die", "sampled_no_output"), ("partial", "partial"), ("damage_commit", "corrupt"),
                             ("infra_late", "possibly_sampled"), ("late_fail", "committed"), ("skip_seed", "possibly_sampled"),
                             ("unfrozen_import", "sampled_no_output")):
            with self.subTest(fault):
                run = self.tmp / fault
                self.launch(run=run, fault=f"AA_e0:{fault}", ok=False)
                c = S.loads((run / "CLOSE.json").read_bytes())
                self.assertEqual((c["outcome"], c["inventory"]["jobs"]["AA_e0"]["state"]), ("failed", state))
                self.no_analysis(run=run)
                (self.repo / "intruder.py").unlink(missing_ok=True)

    def test_finished_runs_with_bad_content_are_not_analysed(self):
        for fault, why in (("dup_member", "duplicate archive member"), ("bad_meta", "segment start"), ("wrong_seed_meta", "seeds")):
            with self.subTest(fault):
                run = self.tmp / fault
                self.launch(run=run, fault=f"AA_e0:{fault}")
                self.assertIn(why, self.no_analysis(run=run))

    def test_concurrent_launches(self):
        ps = [self.drive("launch", arg=self.head, wait=False) for _ in range(3)]
        codes = [p.communicate(timeout=300) and p.returncode for p in ps]
        self.assertEqual(sorted(c == 0 for c in codes), [False, False, True])
        self.drive("analyze", arg=str(self.tmp / "A.json"))

    def test_interrupted_supervisor(self):
        self.assertEqual(self.launch(fault=":kill_supervisor", ok=None)[0], 9)
        self.no_analysis()
        self.assertEqual(retry_recover(self.run_dir)["outcome"], "recovered")
        before = snapshot(self.run_dir)
        time.sleep(2)
        self.launch(ok=False)                                                # recovery followed by a restart
        self.assertEqual(before, snapshot(self.run_dir))
        self.no_analysis()

    # ---- refused before any run folder exists
    def refused(self, repo=None, head=None, fault=""):
        repo = repo or self.repo
        err = self.drive("launch", arg=head or self.rev(repo), repo=repo, fault=fault, ok=False)[1]
        self.assertFalse(self.run_dir.exists())
        return err

    def test_wrong_head_and_preflight(self):
        self.assertIn("approved revision", self.refused(head="0" * 40))
        self.assertIn("preflight", self.refused(fault=":preflight"))

    def test_wrong_runtime(self):
        rt = RK.runtime_identity()
        for change in ({**rt, "numpy": "0.0"}, {k: v for k, v in rt.items() if k != "ldpc"}):
            self.assertIn("runtime differs", self.refused(self.other_repo(runtime=change)))
            shutil.rmtree(self.tmp / "repo2", onexc=lambda f, p, e: (os.chmod(p, 0o700), f(p)))

    def test_wrong_freeze(self):
        rel = "outputs/qshift_decoder_bank_v9/db8_core.py"
        src = "outputs/qshift_decoder_bank_v2/db2_core.py"

        def commit_more(r):
            (r / "extra.txt").write_text("x")
            git(r, "add", "-A")
            git(r, "commit", "-qm", "more")
        files = {f: ST.norm(f, (self.repo / f).read_bytes()) for f in self.files}
        cases = [("modified", dict(after=lambda r: (r / src).write_bytes((r / src).read_bytes() + b"# x\n"))),
                 ("code commit|other files", dict(after=commit_more)),
                 ("frozen file differs", dict(files={**files, src: "0" * 64})),
                 ("not frozen", dict(files={k: v for k, v in files.items() if k != src})),
                 ("inputs are not in the freeze", dict(files={k: v for k, v in files.items() if k != SEED_REL})),
                 ("freeze fields", dict(note=1)), ("episodes", dict(episodes={**C.EPISODES, "AA": 3})),
                 ("frozen file missing", dict(files={**files, rel + ".nope": "0" * 64}))]
        for why, kw in cases:
            with self.subTest(why):
                self.assertRegex(self.refused(self.other_repo(**kw)), why)
            shutil.rmtree(self.tmp / "repo2", onexc=lambda f, p, e: (os.chmod(p, 0o700), f(p)))

    def test_bad_seed_inventories(self):
        def put(f):
            def g(r):
                d = json.loads((r / SEED_REL).read_bytes())
                f(d)
                (r / SEED_REL).write_bytes((json.dumps(d, indent=1) + "\n").encode())
            return g
        a, b = "db8:AA:e0:b00:det", "db8:U_NEAR:e7:b29:eval"
        cases = {"used twice": lambda d: d["seeds"].update({a: d["seeds"][b]}), "not an integer": lambda d: d["seeds"].update({a: 4.9}),
                 "inventory keys": lambda d: d["seeds"].pop(a)}
        for why, f in cases.items():
            with self.subTest(why):
                self.assertIn(why, self.refused(self.other_repo(put(f))))
            shutil.rmtree(self.tmp / "repo2", onexc=lambda g, p, e: (os.chmod(p, 0o700), g(p)))

        def earlier(r):
            rel = "outputs/qshift_decoder_bank_v6/DB6_SEEDS.json"
            v = next(iter(json.loads((r / rel).read_bytes())["seeds"].values()))
            put(lambda d: d["seeds"].update({a: v}))(r)
        self.assertIn("earlier study", self.refused(self.other_repo(earlier)))

    def test_launch_requires_approval(self):
        with self.assertRaises(S.Invalid):
            ST.launch(ST.Study(self.repo, FREEZE), self.run_dir, None, SY.job, list)


class SourceTests(unittest.TestCase):
    def test_files(self):
        for p in SY.V11.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                b = p.read_bytes()
                self.assertNotIn(b"\r\n", b, p.name)
                for bad in (b"C:" + b"\\Users", b"C:" + b"/Users", b"LEN" + b"OVO", b"@gm" + b"ail"):
                    self.assertNotIn(bad, b, p.name)


if __name__ == "__main__":
    unittest.main()
