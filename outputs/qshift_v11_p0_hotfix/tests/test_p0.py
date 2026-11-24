"""Fresh adversarial tests for the v11 P0 hotfix. Real Windows processes with file barriers; synthetic bytes; no Stim.

Where a test is about the identity fence, the parent-death watchdog is switched off in the worker (`init_no_watch`), so
that the fence itself has to refuse."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
HOT = HERE.parent
for _p in (HOT.parent / "qshift_decoder_bank_v11", HOT, HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import lifecycle11p0 as LC  # noqa: E402,I001
import strict as S  # noqa: E402

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


# ------------------------------------------------------------------ barriers and helpers
def put(p):
    Path(p).touch()


def until(p, seconds=30):
    end = time.monotonic() + seconds
    while not Path(p).exists():
        if time.monotonic() > end:
            raise TimeoutError(str(p))
        time.sleep(0.01)


def call(fn, *args):
    code = (f"import sys\nif __name__ == '__main__':\n sys.path.insert(0, {str(HERE)!r})\n import test_p0 as T\n"
            f" T.{fn}(*{[str(a) for a in args]!r})\n")
    # a file, not a pipe: a grandchild that outlives the process would keep a pipe open
    out = tempfile.TemporaryFile("w+")
    p = subprocess.Popen([sys.executable, "-B", "-c", code], env=ENV, stdout=out, stderr=subprocess.STDOUT, text=True)
    p.out = out
    return p


def output(p):
    p.wait(60)
    p.out.seek(0)
    return p.out.read()


def snap(run):
    return {p.relative_to(run).as_posix(): (p.read_bytes() if p.is_file() else None) for p in Path(run).rglob("*")}


def free(run):
    """Every lock of the run can be taken right now."""
    for p in (Path(run) / "locks").iterdir():
        k = LC.try_lock(p)
        if k is None:
            return False
        k.close()
    return True


def recover_soon(run, seconds=30):
    end = time.monotonic() + seconds
    while True:
        try:
            return LC.recover(run)
        except LC.NotQuiescent:
            if time.monotonic() > end:
                raise


def pid_alive(pid):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return f'"{pid}"' in out and "python" in out.lower()


# ------------------------------------------------------------------ jobs (spawned workers)
def init_no_watch(run, rid, workers, session):
    LC._wait_parent = lambda: None
    LC._worker_init(run, rid, workers, session)


def job(ep, arg):
    if arg == "swallow_no_intent":
        try:
            ep.sampling_confirmed({"x": 1})
        except ValueError:
            pass
        ep.sampling_intent()                                   # must stay broken
    if arg == "no_intent":
        ep.sampling_confirmed({"x": 1})
        ep.commit({}, b"a")
    if arg == "forge_state":
        LC.append_event(ep.log, "sampling_confirmed", seeds_sha256="0" * 64)
        ep._state = LC.CONFIRMED
        ep.commit({}, b"a")
    if arg == "forge_all":                                     # writes a valid-looking commit without the API
        for f, b in (("archive.npz", b"a"), ("record.json", S.jbytes({"run_id": ep.run_id, "archive_sha256": S.sha(b"a")}))):
            ep.stage.mkdir(exist_ok=True)
            LC.write_new(ep.stage / f, b)
        LC.write_new(ep.stage / "COMMIT.json", S.jbytes({"run_id": ep.run_id, "job": ep.name, "files": {
            f: {"bytes": len((ep.stage / f).read_bytes()), "sha256": S.sha((ep.stage / f).read_bytes())} for f in LC.FILES}}))
        os.rename(ep.stage, ep.final)
        LC.append_event(ep.log, "sampling_confirmed", seeds_sha256="0" * 64)
        LC.append_event(ep.log, "committed")
        return
    ep.sampling_intent()
    if arg == "no_confirm":
        ep.commit({}, b"a")
    if arg == "intent_twice":
        ep.sampling_intent()
    ep.sampling_confirmed({"x": 2 if arg == "mismatch" else 1})
    if arg == "confirm_twice":
        ep.sampling_confirmed({"x": 1})
    if arg == "intent_after_confirm":
        ep.sampling_intent()
    if arg == "commit_twice":
        ep.commit({"seeds": {"x": 1}}, b"a")
        ep.commit({"seeds": {"x": 1}}, b"b")
    if isinstance(arg, dict) and "pause_commit" in arg:        # pause after staging, before the gated rename
        d, real, n = Path(arg["pause_commit"]), LC._permit, [0]

        def permit(*a):
            n[0] += 1
            if n[0] == 2:
                raise AssertionError("unreachable")
            real(*a)
        gate = LC._gate
        count = [0]

        def paused_gate(run):
            count[0] += 1
            if count[0] == 2:
                put(d / "staged")
                until(d / "go", 60)
            return gate(run)
        LC._gate = paused_gate
        try:
            ep.commit({}, b"late")
            put(d / "committed")
        except BaseException as ex:
            (d / "refused").write_text(f"{type(ex).__name__}: {ex}")
            raise
    ep.commit({"seeds": {"x": 1}}, b"a")


def seed_admission(body, episodes, used):
    for n, (rec, _) in episodes.items():
        S.need(used[n] == S.sha(S.jbytes(S.loads(rec)["seeds"])), f"{n}: confirmed seeds differ")


# ------------------------------------------------------------------ process entry points
def supervisor(run, mode, d="."):
    d = Path(d)
    res = LC.reserve(run, {}, ["a"], 1)
    arg, kw = None, {}
    if mode == "pause_commit":
        arg = {"pause_commit": str(d)}
    if mode in ("pause_commit", "pause_init"):
        def pool():
            rid = res.body["run_id"]
            return ProcessPoolExecutor(1, mp_context=get_context("spawn"), initializer=init_no_watch if mode == "pause_commit"
                                       else init_paused, initargs=(run, rid, 1, LC._CLAIMS[rid].session))
        kw["pool"] = pool
        threading.Thread(target=lambda: (until(d / ("staged" if mode == "pause_commit" else "in_gate"), 60), os._exit(9)),
                         daemon=True).start()
    if mode == "end_then_die":
        LC._publish = lambda *a: os._exit(9)
    if mode == "torn_closing":
        def torn(path, data):
            if Path(path).name.startswith("CLOSING.succeeded"):
                Path(path).write_bytes(data[:len(data) // 2])
                os._exit(9)
            return write(path, data)
        write, LC.write_new = LC.write_new, torn
    if mode == "before_rename":
        real = os.rename

        def rename(a, b):
            if Path(b).name == "CLOSE.json":
                os._exit(9)
            return real(a, b)
        LC.os.rename = rename
    LC.execute(res, [("a", arg)], job, **kw)


def init_paused(run, rid, workers, session):
    """A worker that stops inside initialisation, holding the gate, and outlives its supervisor."""
    LC._wait_parent = lambda: None
    d = Path(run).parent
    real = LC._permit

    def permit(*a):
        put(d / "in_gate")
        until(d / "go", 60)
        real(*a)
    LC._permit = permit
    try:
        LC._worker_init(run, rid, workers, session)
        put(d / "initialised")
    except BaseException as ex:
        (d / "refused").write_text(f"{type(ex).__name__}: {ex}")
        raise


def claimant(run, d):
    """Claims, spawns a child that holds the true session but has not initialised, then dies."""
    res = LC.reserve(run, {}, ["a"], 1)
    k = LC._claim(res)
    p = get_context("spawn").Process(target=delayed, args=(run, res.body["run_id"], k.session, d))
    p.start()
    until(Path(d) / "spawned")
    os._exit(9)


def delayed(run, rid, session, d):
    d = Path(d)
    LC._wait_parent = lambda: None
    put(d / "spawned")
    until(d / "deliver", 60)
    out = []
    for f in (lambda: LC._worker_init(run, rid, 1, session),
              lambda: (LC._WORKER.update(run=str(run), run_id=rid, session=session, slot=None, index=0),
                       LC._guarded(run, rid, 1, "a", 1, job, None, None, None)),
              lambda: LC.Episode(run, rid, "a", None, session).sampling_intent()):
        try:
            f()
            out.append("PERMITTED")
        except BaseException as ex:      # noqa: BLE001
            out.append(f"{type(ex).__name__}: {ex}")
    (d / "tmp").write_text(json.dumps(out))
    os.rename(d / "tmp", d / "delayed.json")


def paused_recovery(run, d):
    """A real recovery stopped after taking the supervisor lock and before writing its fence."""
    d, real = Path(d), LC._gate

    def gate(r):
        put(d / "recovery_holds")
        until(d / "resume", 60)
        return real(r)
    LC._gate = gate
    LC.recover(run)


def recoverer(run, go):
    until(go)
    try:
        LC.recover(run)
        print("recovered")
    except (LC.RunStop, LC.NotQuiescent) as ex:
        print("refused", type(ex).__name__)


class Base(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.d = Path(self._d.name)
        self.run_dir = self.d / "run"
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
            p.wait()
            p.out.close()
        self._d.cleanup()

    def start(self, *a):
        p = call(*a)
        self.procs.append(p)
        return p

    def go(self, arg=None, **kw):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        return LC.execute(res, [("a", arg)], job, **kw)

    def outcome(self):
        return S.loads((self.run_dir / "CLOSE.json").read_bytes())["outcome"]

    def never_success(self):
        """Repeated validation and recovery change nothing and never yield success."""
        before = snap(self.run_dir)
        for _ in range(3):
            with self.assertRaises(S.Invalid):
                LC.load_success(self.run_dir)
            if (self.run_dir / "CLOSE.json").exists():
                with self.assertRaises(LC.RunStop):
                    LC.recover(self.run_dir)
        self.assertEqual(before, snap(self.run_dir))


class RecoveryIdentity(Base):
    def test_01_recovery_holding_supervisor_lock_permits_no_delayed_worker(self):
        self.start("claimant", self.run_dir, self.d).wait(60)
        rec = self.start("paused_recovery", self.run_dir, self.d)
        until(self.d / "recovery_holds")
        self.assertTrue(LC.supervisor_alive(self.run_dir))      # the v11 test for authority would pass here
        before = snap(self.run_dir)
        put(self.d / "deliver")
        until(self.d / "delayed.json")
        out = json.loads((self.d / "delayed.json").read_text())
        self.assertEqual(len(out), 3)
        for x in out:
            self.assertIn("supervisor is gone", x)
        self.assertEqual(before, snap(self.run_dir))
        put(self.d / "resume")
        self.assertEqual(rec.wait(60), 0, output(rec))
        self.assertEqual(self.outcome(), "recovered")
        self.never_success()

    def test_01b_unrelated_process_and_wrong_session(self):
        sup = LC._claim(LC.reserve(self.run_dir, {}, ["a"], 1))
        rid = sup.run_id
        del LC._CLAIMS[rid]                                      # same process, without the claim
        for session in (None, "", sup.session, "0" * 64):
            with self.assertRaises(LC.Fenced):
                LC._check_authority(self.run_dir, rid, session)  # this process is not a child of the supervisor
        with self.assertRaises(LC.RunStop):
            LC._guarded(str(self.run_dir), rid, 1, "a", 1, job, None, None, None)
        sup.close()
        self.assertEqual(snap(self.run_dir)["events"], None)
        self.assertEqual(list((self.run_dir / "events").iterdir()), [])

    def test_02_recovery_races_worker_initialisation(self):
        """Deterministic: a worker is stopped inside initialisation, holding the gate, when its supervisor dies."""
        self.start("supervisor", self.run_dir, "pause_init", self.d).wait(60)
        with patch.object(LC, "_wait_lock", side_effect=lambda p, t, w, real=LC._wait_lock: real(p, min(t, 1), w)):
            with self.assertRaises(LC.NotQuiescent):             # cannot fence yet: nothing certified
                LC.recover(self.run_dir)
        self.assertFalse((self.run_dir / "CLOSE.json").exists())
        put(self.d / "go")
        until(self.d / "refused")
        self.assertIn("supervisor is gone", (self.d / "refused").read_text())
        self.assertEqual(recover_soon(self.run_dir)["inventory"]["jobs"]["a"]["state"], "not_started")
        self.assertFalse((self.d / "initialised").exists())
        self.never_success()

    def test_02b_supervisor_killed_at_many_startup_moments(self):
        for k in range(12):
            with self.subTest(k), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                run = Path(d) / "run"
                p = self.start("supervisor", run, "plain", d)
                until(run / "START.json")
                time.sleep(k * 0.08)
                p.kill()
                p.wait()
                if (run / "CLOSE.json").exists():               # finished first
                    LC.load_success(run)
                    continue
                recover_soon(run)
                before = snap(run)
                time.sleep(1.5)
                self.assertEqual(before, snap(run))
                ev = LC.read_events(run / "events/a.jsonl")[0]
                self.assertEqual([e["pid"] for e in ev if "pid" in e and pid_alive(e["pid"])], [])
                with self.assertRaises(S.Invalid):
                    LC.load_success(run)

    def test_09_concurrent_recoveries(self):
        for k in range(5):
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                run = Path(d) / "run"
                LC.reserve(run, {}, ["a"], 2)
                ps = [self.start("recoverer", run, Path(d) / "go") for _ in range(4)]
                time.sleep(1.2)
                put(Path(d) / "go")
                outs = [output(p).split()[0] for p in ps]
                self.assertEqual(sorted(outs), ["recovered", "refused", "refused", "refused"])
                self.assertEqual(sorted(p.name for p in run.iterdir() if p.name.startswith("CLOS")), ["CLOSE.json"])
                before = snap(run)
                with self.assertRaises(LC.RunStop):
                    LC.recover(run)
                self.assertEqual(before, snap(run))

    def test_10_late_commit_after_fence(self):
        p = self.start("supervisor", self.run_dir, "pause_commit", self.d)
        self.assertEqual(p.wait(60), 9)
        self.assertTrue((self.run_dir / "staging/a/COMMIT.json").exists())
        with self.assertRaises(LC.NotQuiescent):                 # the worker is alive and holds its slot
            LC.recover(self.run_dir)
        self.assertTrue((self.run_dir / "RECOVER.json").exists())
        self.assertFalse((self.run_dir / "CLOSE.json").exists())
        staged = snap(self.run_dir / "staging")
        put(self.d / "go")
        until(self.d / "refused")
        self.assertIn("Fenced", (self.d / "refused").read_text())
        with self.assertRaises(LC.NotQuiescent):                 # now idle, but still alive: still not certified
            LC.recover(self.run_dir)
        pid = LC.read_events(self.run_dir / "events/a.jsonl")[0][0]["pid"]
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, check=True)
        c = recover_soon(self.run_dir)
        self.assertEqual(c["inventory"]["jobs"]["a"]["state"], "partial")
        self.assertEqual(staged, snap(self.run_dir / "staging"))
        self.assertFalse((self.d / "committed").exists() or (self.run_dir / "episodes/a").exists())
        self.never_success()

    def test_10b_fence_without_supervisor_death(self):
        """The fence alone (live supervisor, valid authority) also refuses start, intent and commit."""
        for fence in ("FAILED.json", "RECOVER.json"):
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                run = Path(d) / "run"
                sup = LC._claim(LC.reserve(run, {}, ["a"], 1))
                ep = LC.Episode(run, sup.run_id, "a", None)
                ep.sampling_intent()
                ep.sampling_confirmed({})
                put(run / fence)
                with self.assertRaises(LC.Fenced):
                    ep.commit({}, b"late")
                with self.assertRaises(LC.Fenced):
                    LC.Episode(run, sup.run_id, "b", None).sampling_intent()
                with self.assertRaises(LC.RunStop):
                    LC._worker_init(run, sup.run_id, 1, sup.session)
                self.assertEqual(list((run / "episodes").iterdir()), [])
                sup.close()

    def test_recovery_refuses_restart_and_preserves(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        LC.recover(self.run_dir)
        before = snap(self.run_dir)
        with self.assertRaises(LC.StartRefused):
            LC.execute(res, [("a", None)], job)
        self.assertEqual(before, snap(self.run_dir))


class LockErrors(Base):
    def test_03_errors_are_not_owners(self):
        res = LC.reserve(self.run_dir, {}, ["a"], 2)
        before = snap(self.run_dir)
        for target, err in (("_os_lock", PermissionError(13, "denied")), ("_os_lock", OSError(5, "io")),
                            ("Lock", PermissionError("denied"))):
            with patch.object(LC, target, side_effect=err):
                for f in (lambda: LC.supervisor_alive(self.run_dir), lambda: LC.recover(self.run_dir),
                          lambda: LC.execute(res, [("a", None)], job), lambda: LC._worker_init(self.run_dir, res.body["run_id"], 2, "x")):
                    with self.assertRaises(LC.LockError):
                        f()
        self.assertEqual(before, snap(self.run_dir))
        k = LC.try_lock(LC._sup(self.run_dir))
        self.assertTrue(LC.supervisor_alive(self.run_dir))        # real contention is still contention
        k.close()

    def test_03b_real_permission_error(self):
        LC.reserve(self.run_dir, {}, ["a"], 1)
        for name in ("supervisor", "gate", "worker000"):
            with self.subTest(name):
                p = self.run_dir / "locks" / name
                os.chmod(p, 0o400)
                try:
                    with self.assertRaises(LC.LockError):
                        LC.recover(self.run_dir)
                    self.assertFalse((self.run_dir / "CLOSE.json").exists())
                finally:
                    os.chmod(p, 0o600)
                self.assertTrue(free(self.run_dir))
        self.assertEqual(LC.recover(self.run_dir)["outcome"], "recovered")

    def test_03c_unreadable_identity(self):
        sup = LC._claim(LC.reserve(self.run_dir, {}, ["a"], 1))
        rid, session = sup.run_id, sup.session
        del LC._CLAIMS[rid]
        with patch.object(Path, "read_bytes", side_effect=PermissionError("denied")):
            with self.assertRaises(LC.Fenced):
                LC._check_authority(self.run_dir, rid, session)
        (self.run_dir / "START.json").write_bytes(b"{")
        with self.assertRaises(LC.Fenced):
            LC._check_authority(self.run_dir, rid, session)
        sup.close()

    def test_04_partial_acquisition_releases_everything(self):
        n = 5
        LC.reserve(self.run_dir, {}, ["a"], n)
        real, kept = LC.try_lock, []
        for pos in range(n):
            for err in (LC.LockError("x"), KeyboardInterrupt(), OSError("x"), MemoryError()):
                with self.subTest(pos=pos, err=repr(err)):
                    def flaky(p, pos=pos, err=err):
                        if Path(p).name == f"worker{pos:03d}":
                            raise err
                        return real(p)
                    with patch.object(LC, "try_lock", side_effect=flaky):
                        for f in (lambda: LC._all_slots(self.run_dir, n, 1), lambda: LC.recover(self.run_dir)):
                            try:
                                f()
                                self.fail("no error")
                            except BaseException as ex:      # noqa: BLE001
                                self.assertIs(type(ex), type(err))
                                kept.append(ex)                   # keep the traceback alive, as a caller might
                    self.assertTrue(free(self.run_dir))
            k = real(self.run_dir / "locks" / f"worker{pos:03d}")  # busy at this position
            try:
                with self.assertRaises(LC.NotQuiescent) as cm:
                    LC._all_slots(self.run_dir, n, 0)
                kept.append(cm.exception)
            finally:
                k.close()
            self.assertTrue(free(self.run_dir))
        self.assertEqual(LC.recover(self.run_dir)["outcome"], "recovered")

    def test_04b_acquisition_failure_while_closing(self):
        """The same failure at the end of a finished run: no success, no lock left, recoverable."""
        real = LC._all_slots
        with patch.object(LC, "_all_slots", side_effect=LC.LockError("x")), self.assertRaises(LC.LockError):
            self.go()
        self.assertFalse((self.run_dir / "CLOSE.json").exists())
        self.assertTrue((self.run_dir / "FAILED.json").exists() and free(self.run_dir))
        self.assertIs(LC._all_slots, real)
        self.never_success()
        self.assertEqual(LC.recover(self.run_dir)["outcome"], "recovered")
        self.never_success()


class SuccessMeansAdmissible(Base):
    def failed(self, arg, **kw):
        with self.assertRaises(Exception):
            self.go(arg, **kw)
        self.assertEqual(self.outcome(), "failed")
        ev = [x["event"] for x in LC.read_events(self.run_dir / "journal.jsonl")[0]]
        self.assertNotIn("run_end", ev)
        self.never_success()

    def test_control(self):
        self.assertEqual(self.go(admission=seed_admission)["outcome"], "succeeded")
        LC.load_success(self.run_dir)
        self.assertEqual(sorted(p.name for p in self.run_dir.iterdir()),
                         sorted(["RUN.json", "START.json", "journal.jsonl", "CLOSE.json", *LC.DIRS]))

    def each(self, args, **kw):
        for a in args:
            with self.subTest(a), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                self.run_dir = Path(d) / "run"
                self.failed(a, **kw)

    def test_05_missing_intent(self):
        self.each(("no_intent", "swallow_no_intent", "forge_state", "forge_all"))

    def test_06_missing_or_mismatched_confirmation(self):
        self.each(("no_confirm", "mismatch"), admission=seed_admission)

    def test_06b_transitions_are_one_way(self):
        self.each(("intent_twice", "confirm_twice", "intent_after_confirm", "commit_twice"))

    def test_07_failed_journal_with_valid_hashes(self):
        for event, kw in (("run_failed", {"error": "x"}), ("run_end", {"state": "failed"}), ("note", {})):
            with self.subTest(event), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                self.run_dir = Path(d) / "run"
                jr = self.run_dir / "journal.jsonl"
                with self.assertRaises(S.Invalid):
                    self.go(on_done=lambda n: LC.append_event(jr, event, **kw))
                self.assertTrue(LC.read_events(jr)[1])           # the chain itself is valid
                self.assertEqual(self.outcome(), "failed")
                self.never_success()

    def test_07b_other_damage_before_closing(self):
        cases = {"extra file": lambda r: (r / "x").write_bytes(b""), "staging": lambda r: (r / "staging/z").mkdir(),
                 "commit": lambda r: (r / "episodes/a/archive.npz").write_bytes(b"zz"),
                 "start": lambda r: (r / "START.json").write_bytes(b"{}"),
                 "events": lambda r: LC.append_event(r / "events/a.jsonl", "started", run_id="x", attempt=2)}
        for k, f in cases.items():
            with self.subTest(k), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                self.run_dir = Path(d) / "run"
                with self.assertRaises(Exception):
                    self.go(final_check=lambda: f(self.run_dir))
                self.assertEqual(self.outcome(), "failed")
                self.never_success()

    def test_admission_rejection_and_error(self):
        for err in (S.Invalid("no"), RuntimeError("bug"), KeyboardInterrupt()):
            with self.subTest(repr(err)), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                self.run_dir = Path(d) / "run"

                def adm(*a):
                    raise err
                with self.assertRaises(type(err)):
                    self.go(admission=adm)
                self.assertEqual(self.outcome(), "failed")
                self.never_success()

    def test_08_terminal_write_killed(self):
        for mode, left in (("end_then_die", []), ("torn_closing", ["CLOSING.succeeded.0.json"]),
                           ("before_rename", ["CLOSING.succeeded.0.json"])):
            with self.subTest(mode), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                self.run_dir = Path(d) / "run"
                self.assertEqual(self.start("supervisor", self.run_dir, mode, d).wait(60), 9)
                self.assertEqual(LC.read_events(self.run_dir / "journal.jsonl")[0][-1]["event"], "run_end")
                self.assertFalse((self.run_dir / "CLOSE.json").exists())
                self.never_success()
                kept = {n: (self.run_dir / n).read_bytes() for n in left}
                self.assertEqual(recover_soon(self.run_dir)["outcome"], "recovered")
                self.assertEqual(kept, {n: (self.run_dir / n).read_bytes() for n in left})
                self.assertEqual(self.outcome(), "recovered")
                self.never_success()

    def test_08b_terminal_write_error(self):
        real = LC.write_new

        def broken(path, data):
            if Path(path).name.startswith("CLOSING.succeeded"):
                Path(path).write_bytes(data[:40])
                raise OSError("disk")
            return real(path, data)
        with patch.object(LC, "write_new", side_effect=broken), self.assertRaises(OSError):
            self.go()
        self.assertEqual(self.outcome(), "failed")
        self.assertEqual((self.run_dir / "CLOSING.succeeded.0.json").stat().st_size, 40)
        self.never_success()

    def test_08c_published_success_is_never_rewritten(self):
        real = LC._publish

        def late(run, data, outcome):
            real(run, data, outcome)
            raise KeyboardInterrupt
        with patch.object(LC, "_publish", side_effect=late), self.assertRaises(KeyboardInterrupt):
            self.go()
        self.assertEqual(self.outcome(), "succeeded")
        LC.load_success(self.run_dir)
        self.assertFalse((self.run_dir / "FAILED.json").exists())

    def test_torn_failure_records_do_not_reopen(self):
        """An interrupted failure or recovery record is kept and the next recovery still ends as recovered."""
        res = LC.reserve(self.run_dir, {}, ["a"], 1)
        real = os.rename
        with patch.object(LC.os, "rename", side_effect=OSError("killed")), self.assertRaises(OSError):
            LC.recover(self.run_dir)
        self.assertIs(os.rename, real)
        self.assertEqual(LC.recover(self.run_dir)["outcome"], "recovered")
        self.assertTrue((self.run_dir / "CLOSING.recovered.0.json").exists())
        with self.assertRaises(LC.StartRefused):
            LC.execute(res, [("a", None)], job)
        self.never_success()


class Source(unittest.TestCase):
    def test_files(self):
        for p in HOT.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                b = p.read_bytes()
                self.assertNotIn(b"\r\n", b, p.name)
                for bad in (b"C:" + b"\\Users", b"C:" + b"/Users", b"LEN" + b"OVO", b"@gm" + b"ail"):
                    self.assertNotIn(bad, b, p.name)

    def test_no_worker_decision_reads_the_supervisor_lock(self):
        src = (HOT / "lifecycle11p0.py").read_text(encoding="utf-8")
        worker = src[src.index("# ---", src.index("def _claim(")):src.index("# ------------------------------------------------------------------ commits")]
        self.assertIn("def _permit", worker)
        for name in ("supervisor_alive", "_sup("):
            self.assertNotIn(name, worker)


if __name__ == "__main__":
    unittest.main()
