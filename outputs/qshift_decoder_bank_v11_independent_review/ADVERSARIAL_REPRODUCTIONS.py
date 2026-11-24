"""Windows sampler-free independent probes against the pinned v11 interfaces."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import warnings
import zipfile

V11 = Path(__file__).resolve().parents[1] / "qshift_decoder_bank_v11"
for root in (V11.parents[1], V11.parent / "qshift_decoder_bank_v9",
             V11.parent / "qshift_decoder_bank_v10", V11):
    sys.path.insert(0, str(root))
import stim

def deny(*args, **kwargs):
    raise AssertionError("Stim sampling forbidden")

stim.Circuit.compile_detector_sampler = deny
stim.Circuit.compile_sampler = deny
stim.DetectorErrorModel.compile_sampler = deny

import lifecycle11 as lc
import policy
import strict
import study11


def job(ep, mode):
    if mode != "omit_intent":
        ep.sampling_intent()
    ep.sampling_confirmed({"synthetic": 1})
    if mode == "die":
        ep.stage.mkdir()
        lc.write_new(ep.stage / "archive.npz", b"partial")
        os._exit(42)
    ep.commit({}, b"test-only archive")


def child():
    mode, folder, *args = sys.argv[2:]
    run = Path(folder)
    if mode == "claim":
        until = time.monotonic() + 12
        while not Path(args[1]).exists():
            if time.monotonic() > until:
                raise TimeoutError("start barrier")
            time.sleep(.01)
        res = lc.Reservation(run, lc.read_reservation(run), args[0])
        try:
            lock = lc._claim(res)
        except lc.StartRefused:
            print("refused")
        else:
            print("claimed")
            lock.close()
    elif mode == "late":
        lc._guarded(str(run), lc.read_reservation(run)["run_id"], 1, "root", 1, job, "normal", None, None)
    elif mode == "recover":
        try:
            lc.recover(run)
        except (lc.RunStop, lc.NotQuiescent):
            print("refused")
        else:
            print("recovered")


class Audit(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="qshift_v11_audit_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.res = lc.reserve(self.root / "run", {"fixture": True}, ["root"], 1)
        self.run_dir = self.res.run

    def execute(self, mode="normal"):
        return lc.execute(self.res, [("root", mode)], job, stall_timeout=12)

    def children(self, mode, n, args=(), gate=None):
        workers = []
        try:
            for _ in range(n):
                workers.append(subprocess.Popen(
                    [sys.executable, "-B", __file__, "--child", mode, str(self.run_dir), *args],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            if gate:
                gate.touch()
            results = []
            for proc in workers:
                out, err = proc.communicate(timeout=20)
                self.assertEqual(proc.returncode, 0, err)
                results.append(out.strip())
            return results
        finally:
            for proc in workers:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate(timeout=5)

    def test_v10_1_empty_commit(self):
        (self.run_dir / "episodes/root").mkdir()
        self.assertEqual(lc.inventory(self.run_dir)["jobs"]["root"]["state"], "corrupt")

    def test_v10_2_recovered_cannot_start(self):
        lc.recover(self.run_dir)
        before = lc._tree(self.run_dir)
        with self.assertRaises(lc.StartRefused):
            self.execute()
        self.assertEqual(lc._tree(self.run_dir), before)

    def test_v10_3_start_race(self):
        before = lc._tree(self.run_dir)
        gate = self.root / "go"
        self.assertCountEqual(self.children("claim", 4, (self.res.token, str(gate)), gate),
                              ["claimed", "refused", "refused", "refused"])
        after = lc._tree(self.run_dir)
        after.pop("START.json")
        self.assertEqual(before, after)

    def record(self):
        c = policy.C
        return (json.loads((c.ROOT / "results/dev/records/AA_e0.json").read_bytes()),
                json.loads((c.ROOT / "DB8_SEEDS.json").read_bytes())["seeds"],
                json.loads((c.DB1 / "TRAINING.json").read_bytes()))

    def test_v10_4_contradictions(self):
        record, seeds, train = self.record()
        policy.check_record(record, seeds, train, ("AA", 0))
        for field, value in (("seg0", -1), ("L", -2), ("plausible", ["impossible"]), ("estimate", [])):
            with self.subTest(field=field):
                bad = copy.deepcopy(record)
                bad["blocks"][0][field] = value
                with self.assertRaises(strict.Invalid):
                    policy.check_record(bad, seeds, train, ("AA", 0))

    def test_v10_5_failed_journal_rehashed(self):
        self.execute()
        lc.load_success(self.run_dir)
        journal = self.run_dir / "journal.jsonl"
        events, _ = lc.read_events(journal)
        events.insert(-1, {"event": "run_failed", "error": "synthetic crash"})
        close_path = self.run_dir / "CLOSE.json"
        for end_state in ("failed", "succeeded"):
            events[-1]["state"] = end_state
            journal.unlink()
            for event in events:
                extras = {k: v for k, v in event.items() if k not in {"hash", "prev", "seq", "t", "event"}}
                lc.append_event(journal, event["event"], **extras)
            self.assertTrue(lc.read_events(journal)[1])
            close = json.loads(close_path.read_bytes())
            close["inventory"] = lc.inventory(self.run_dir)
            close_path.write_bytes(strict.jbytes(close))
            with self.assertRaisesRegex(strict.Invalid, "journal"):
                lc.load_success(self.run_dir)

    def test_v10_6_duplicate_zip(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z, warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            z.writestr("a.npy", b"first")
            z.writestr("a.npy", b"second")
        with self.assertRaisesRegex(strict.Invalid, "duplicate archive member"):
            strict.read_archive(stream.getvalue(), ["a"], 8)

    def test_v10_7_seed_aliases(self):
        for val in (4.9, True, "4", None, float("inf"), -1, 2**80, 4):
            with self.subTest(value=val), self.assertRaises(strict.Invalid):
                strict.check_inventory({"a": 4, "b": val}, ["a", "b"])

    def test_recovery_race(self):
        self.assertCountEqual(self.children("recover", 2), ["recovered", "refused"])

    def test_worker_death_preserves_partial(self):
        with self.assertRaises(Exception):
            self.execute("die")
        self.assertEqual(lc.inventory(self.run_dir)["jobs"]["root"]["state"], "partial")
        self.assertEqual((self.run_dir / "staging/root/archive.npz").read_bytes(), b"partial")
        with self.assertRaises(strict.Invalid):
            lc.load_success(self.run_dir)

    def test_torn_terminal_fail_closed(self):
        path = self.run_dir / "CLOSE.json"
        path.write_bytes(b'{"outcome":')
        with self.assertRaises(lc.RunStop):
            lc.recover(self.run_dir)
        with self.assertRaises(strict.Invalid):
            lc.load_success(self.run_dir)
        self.assertEqual(path.read_bytes(), b'{"outcome":')

    def test_gap_success_without_intent(self):
        self.assertEqual(self.execute("omit_intent")["outcome"], "succeeded")
        with self.assertRaisesRegex(strict.Invalid, "event order"):
            lc.load_success(self.run_dir)

    def test_gap_recovery_owner_passes_worker_fence(self):
        lc._claim(self.res).close()
        recovery_lock = lc.try_lock(lc._sup(self.run_dir))
        self.assertIsNotNone(recovery_lock)
        try:
            # Pause recovery before collecting slots. Deliver a delayed worker at its guard.
            self.children("late", 1)
            self.assertTrue((self.run_dir / "episodes/root/COMMIT.json").is_file())
        finally:
            recovery_lock.close()

    def test_gap_io_error_appears_live(self):
        with patch.object(lc, "Lock", side_effect=PermissionError("synthetic denial")):
            self.assertTrue(lc.supervisor_alive(self.run_dir))

    def test_gap_unbound_launch_callbacks(self):
        rel = Path(__file__).resolve().relative_to(V11.parents[1]).as_posix()
        fz = {"episodes": {"root": 1}, "workers": 1, "files": {rel: "fixture"},
              "training": "train", "seeds": "seeds"}
        class AlreadyVerified:
            repo = V11.parents[1]

            def verify(self, head=None):
                return study11.Binding({"head": "approved"}, fz, {}, {})
        called = []
        def preflight():
            called.append("unbound preflight")
            return []
        def pool():
            called.append("unbound pool")
        def execute_stub(*args, **kwargs):
            kwargs["pool"]()
        with patch.object(lc, "execute", side_effect=execute_stub):
            study11.launch(AlreadyVerified(), self.root / "binding", "approved", job, preflight, pool=pool)
        self.assertEqual(called, ["unbound preflight", "unbound pool"])

    def test_gap_estimates_outside_fitter_grid(self):
        c = policy.C
        seedbook = json.loads((c.ROOT / "DB8_SEEDS.json").read_bytes())["seeds"]
        train = json.loads((c.DB1 / "TRAINING.json").read_bytes())
        for episode in ("AA_e0", "U_NEAR_e2", "U_OUT_e0"):
            record = json.loads((c.ROOT / f"results/dev/records/{episode}.json").read_bytes())
            for block in record["blocks"]:
                if block["estimate"]["flagged"] and block["estimate_ad3"]["source"] != "recall":
                    for field in ("estimate", "estimate_ad3"):
                        block[field].update(p_hat=.25, b_hat=100.)
                    schedule, idx = episode.rsplit("_e", 1)
                    policy.check_record(record, seedbook, train, (schedule, int(idx)))
                    return
        self.fail("no flagged non-recall fixture")

    def test_gap_external_import_ignored(self):
        from types import SimpleNamespace
        external = self.root / "shadow.py"
        external.write_text("# synthetic fixture", encoding="utf-8")
        shadow = SimpleNamespace(__file__=str(external))
        with patch.object(study11, "sys", SimpleNamespace(modules={"dependency": shadow})):
            study11.check_imports({"repo": str(V11.parents[1]), "files": {}})


def integration():
    """Reuse the vendor integration fixture with disposable collision metadata."""
    import shutil
    sys.path.insert(0, str(V11 / "tests"))
    import test_v11 as fixture

    class ScopedIntegration(fixture.IntegrationTests):
        @classmethod
        def setUpClass(cls):
            cls._c = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
            cls.repo = Path(cls._c.name).resolve() / "repo"
            files = set(fixture.trace_inputs()) | {
                f"outputs/qshift_decoder_bank_v9/results/dev/records/{n}.json" for n in fixture.NAMES
            } | {fixture.SEED_REL, fixture.TRAIN_REL}
            for name in files:
                dst = cls.repo / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(fixture.REPO / name, dst)
            book = json.loads((cls.repo / fixture.SEED_REL).read_bytes())
            reserved = "synthetic_reserved.json"
            book["screened"] = {reserved: {"values": 1}}
            (cls.repo / fixture.SEED_REL).write_bytes(fixture.S.jbytes(book))
            seed_values = set(book["seeds"].values())
            sentinel = next(i for i in range(1, 10000) if i not in seed_values)
            (cls.repo / reserved).write_bytes(fixture.S.jbytes({"seeds": {"synthetic": sentinel}}))
            files.add(reserved)
            fixture.git(cls.repo, "init", "-q")
            fixture.git(cls.repo, "add", "-A", "-f")
            fixture.git(cls.repo, "commit", "-qm", "fixture code")
            cls.files = sorted(files)
            cls.commit_freeze(cls.repo, cls.files)
            cls.head = cls.rev(cls.repo)

    selected = ("test_end_to_end", "test_wrong_head_and_preflight", "test_wrong_runtime")
    suite = unittest.TestSuite(ScopedIntegration(name) for name in selected)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


if __name__ == "__main__":
    if sys.argv[1:2] == ["--child"]:
        child()
    elif sys.argv[1:2] == ["--integration"]:
        sys.exit(0 if integration() else 1)
    else:
        unittest.main(verbosity=2)
