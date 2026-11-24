"""v10 tests. No stim sampling: module setup blocks every sampler, in this process and in synthetic workers.

Optional, read-only: set QSHIFT_DB8_EVIDENCE to a v9 folder that holds work/dev_a3 to check all 64 final archives."""
from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
for _p in (PKG.parents[1], PKG.parent / "qshift_decoder_bank_v9", PKG):
    sys.path.insert(0, str(_p))
import db8_config as C  # noqa: E402,I001
import analyze10 as A10  # noqa: E402
import controller as CT  # noqa: E402
import db8_addendum as AD  # noqa: E402
import decoder_factory as DF  # noqa: E402
import runkit2 as R2  # noqa: E402
import seed_spec as SS  # noqa: E402
import validate as V  # noqa: E402

HEAD, FZ = "a" * 40, "b" * 64
SEEDS, TR = V.db8_seeds(), V.training()
JOBS = [f"{s}_e{e}" for s, n in C.EPISODES.items() for e in range(n)]
RECS = C.ROOT / "results" / "dev" / "records"


def block_samplers():
    import stim

    def no(*a, **k):
        raise AssertionError("stim sampler used")
    stim.Circuit.compile_detector_sampler = no
    stim.Circuit.compile_sampler = no
    stim.DetectorErrorModel.compile_sampler = no


def setUpModule():
    block_samplers()


def committed(name):
    return json.loads((RECS / f"{name}.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ jobs (top level: spawned)
def ok_job(run, rid, name, args):
    ep = R2.Episode(run, rid, name)
    ep.sampling()
    return ep.commit({"x": args}, b"archive")


def bad_job(run, rid, name, args):
    ep = R2.Episode(run, rid, name)
    if args == "infra_once":
        if sum(x["event"] == "started" for x in R2.read_events(ep.log)[0]) == 1:
            raise OSError("pre-sampling")
    elif args == "infra_always":
        raise OSError("pre-sampling")
    ep.sampling()
    if args == "infra_late":
        raise OSError("after sampling")
    if args == "code":
        raise ValueError("code error")
    if args == "die":
        os._exit(7)
    if args == "partial":
        ep.stage.mkdir(parents=True)
        (ep.stage / "archive.npz").write_bytes(b"half")
        raise OSError("mid-write")
    if args == "sleep":
        time.sleep(60)
    return ep.commit({"x": args}, b"archive")


def killed_parent(run):
    """Run in a subprocess: the parent dies while one job sleeps and after one job committed."""
    res = R2.reserve(run, HEAD, FZ, ["a", "b"], 2)
    R2.run_jobs([("a", None), ("b", "sleep")], bad_job, run, res, on_done=lambda n: os._exit(9))


def synthetic_job(run, rid, name, args):
    """A full-shape episode: committed DB8 metadata, with synthetic error bits that are equal for equal keys."""
    block_samplers()
    ep = R2.Episode(run, rid, name)
    r = committed(name)
    s, e = name.rsplit("_e", 1)
    use = SS.SeedUse(V.spec(), SEEDS, s, int(e))
    ep.sampling()
    bits, rng = {}, np.random.default_rng(12345)
    for t in range(C.BLOCKS):
        for p in ("det", "lab") + (("eval",) if t in C.SCORED else ()):
            use.take(t, p)
    for b in r["blocks"]:
        bykey = {}
        for a in C.ARMS:
            k = b["keys"].get(a, "nominal-plain")
            if k not in bykey:
                bykey[k] = rng.random(C.EVAL_PER_BLOCK) < 0.01
            bits[f"b{b['block']:02d}_{a}"] = np.packbits(bykey[k])
            b["errors"][a] = int(bykey[k].sum())
    buf = io.BytesIO()
    np.savez_compressed(buf, **bits)
    r.update(seeds=use.finish(), archive="archive.npz")
    return ep.commit(r, buf.getvalue())


class Tmp(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.run_dir = Path(self._d.name) / "run"

    def tearDown(self):
        self._d.cleanup()

    def launch(self, jobs, fn=bad_job, workers=2, **kw):
        res = R2.reserve(self.run_dir, HEAD, FZ, [n for n, _ in jobs], workers)
        return R2.run_jobs(jobs, fn, self.run_dir, res, **kw)

    def failure(self):
        return json.loads((self.run_dir / "FAILURE.json").read_bytes())

    def state(self):
        return json.loads((self.run_dir / "RUN_STATUS.json").read_bytes())["state"]


class DecoderTests(unittest.TestCase):
    def test_every_fixed_key_builds(self):                                   # F1
        self.assertEqual(DF.preflight(DF.db8_required()), [])

    def test_x03_fails_only_in_matching(self):                               # F1: attempt 2's cause
        p0, sup = C.spec(gate_p=C.P0, measurement_p=C.P0), (3, 25, 34)
        bad = DF.preflight([("X03", DF.L2, p0, sup), ("X03", DF.MATCHING, p0, sup)])
        self.assertEqual([x[:2] for x in bad], [("X03", DF.MATCHING)])
        self.assertIn("undetectable component", bad[0][2])

    def test_same_models_as_re1(self):
        import re1
        import outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd as LB
        from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
        old = LB.LdpcBPOSD, m.build_matching
        LB.LdpcBPOSD, m.build_matching = (lambda dem, cfg: (str(dem), repr(cfg))), str
        try:
            p0 = C.spec(gate_p=C.P0, measurement_p=C.P0)
            for sup in (None, C.support("B"), C.support("UO")):
                self.assertEqual(re1.decoders(p0, sup), (DF.build_l2(p0, sup), DF.build_matching(p0, sup)))
            self.assertEqual(DF.build_plain(p0, None), str(m.build_decomposed_dem(m.build_base_circuit(p0))))
        finally:
            LB.LdpcBPOSD, m.build_matching = old

    def test_preflight_reports_all(self):
        def boom(sp, sup):
            raise ValueError(sup)
        bad = DF.preflight([("a", "l2", 0, 1), ("b", "l2", 0, 2)], {"l2": boom})
        self.assertEqual([x[0] for x in bad], ["a", "b"])


class SeedTests(unittest.TestCase):
    def test_matches_all_committed_records(self):                            # F4
        for n in JOBS:
            s, e = n.rsplit("_e", 1)
            self.assertEqual(committed(n)["seeds"], V.spec().expected(SEEDS, s, int(e)), n)

    def test_use(self):
        u = SS.SeedUse(V.spec(), SEEDS, "AA", 0)
        with self.assertRaises(ValueError):
            u.take(0, "eval")                                                # warm-up evaluation seed
        u.take(0, "det")
        with self.assertRaises(ValueError):
            u.take(0, "det")
        with self.assertRaises(ValueError):
            u.finish()


class ControllerTests(unittest.TestCase):
    RISK = {"A": {"OFF": .9, "A": .01, "B": .02, "C": .9, "D": .9}, "B": {"OFF": .9, "A": .02, "B": .01, "C": .9, "D": .9},
            **{s: {k: .5 for k in C.STATES} for s in ("OFF", "C", "D")}}
    BOTH = {"OFF": 999, "A": 100, "B": 100, "C": 999, "D": 999}
    NONE = {k: 999 for k in C.STATES}

    def seq(self, memory):
        k1, s1, prev = CT.cb_key({**self.BOTH, "A": 999}, TR["tau_fit"], self.RISK, "A", "bank:A", memory=memory)
        k2, s2, prev = CT.cb_key(self.NONE, TR["tau_fit"], self.RISK, prev, "bank:A", memory=memory)
        k3, s3, _ = CT.cb_key(self.BOTH, TR["tau_fit"], self.RISK, prev, "bank:B", memory=memory)
        return [k1, k2, k3], [s1, s2, s3]

    def test_fallback_then_tie(self):                                        # F6
        self.assertEqual(self.seq(CT.LAST_BANK), (["bank:B", "bank:A", "bank:B"], ["cb", "w0f", "cb"]))
        self.assertEqual(self.seq(CT.LAST_EMITTED), (["bank:B", "bank:A", "bank:A"], ["cb", "w0f", "cb"]))

    def test_non_bank_fallback_and_no_default(self):
        self.assertIsNone(CT.cb_key(self.NONE, TR["tau_fit"], self.RISK, "A", "nominal", memory=CT.LAST_EMITTED)[2])
        with self.assertRaises(TypeError):
            CT.cb_key(self.NONE, TR["tau_fit"], self.RISK, "A", "nominal")
        with self.assertRaises(ValueError):
            CT.cb_key(self.NONE, TR["tau_fit"], self.RISK, "A", "nominal", memory="x")

    def test_selector(self):                                                 # F9
        for ranked in ([], ["X03", "V01"]):
            with self.assertRaises(CT.NoEligibleCandidate):
                CT.first_eligible(ranked, lambda lab: "no")
        self.assertEqual(CT.first_eligible(["a", "b"], lambda x: "r" if x == "a" else None), ("b", [{"label": "a", "reason": "r"}]))

    def test_selector_reproduces_a3(self):
        sel = json.loads((C.ROOT / "SELECTION_A3.json").read_text(encoding="utf-8"))["states"]["UF"]
        why = {x["label"]: x["reason"] for x in sel["skipped_A3"]}
        self.assertEqual(CT.first_eligible(["X03", "V01", "V06"], why.get), (sel["label"], sel["skipped_A3"]))


class RunnerTests(Tmp):                                                      # F7
    def test_success(self):
        st = self.launch([("a", 1), ("b", 2)], ok_job)
        self.assertEqual(st["state"], "ready_for_analysis")
        rec, raw = R2.read_committed(self.run_dir, st["run_id"], "a")
        self.assertEqual((rec["x"], raw), (1, b"archive"))

    def test_second_reservation_and_second_start(self):
        st = self.launch([("a", 1)], ok_job)
        with self.assertRaises(R2.ReservationError):
            R2.reserve(self.run_dir, HEAD, FZ, ["a"], 1)
        with self.assertRaises(R2.RunStop):
            R2.run_jobs([("a", 1)], ok_job, self.run_dir, R2.read_reservation(self.run_dir))
        self.assertEqual(json.loads((self.run_dir / "RUN_STATUS.json").read_bytes()), st)      # untouched
        self.assertFalse((self.run_dir / "FAILURE.json").exists())

    def test_tampered_reservation(self):
        res = R2.reserve(self.run_dir, HEAD, FZ, ["a"], 1)
        p = self.run_dir / "RUN.json"
        p.write_bytes(p.read_bytes().replace(HEAD.encode(), b"c" * 40))
        with self.assertRaises(ValueError):
            R2.run_jobs([("a", 1)], ok_job, self.run_dir, res)

    def test_pool_startup_failure_is_recorded(self):
        def boom():
            raise RuntimeError("no pool")
        with self.assertRaises(RuntimeError):
            self.launch([("a", 1)], executor=boom)
        self.assertEqual((self.state(), self.failure()["jobs"]["a"]["state"]), ("failed", "not_started"))

    def test_retry_before_sampling_once(self):
        st = self.launch([("a", "infra_once")])
        self.assertEqual((st["state"], set(st["reruns"])), ("ready_for_analysis", {"a"}))

    def test_stops(self):
        want = {"infra_always": "started", "infra_late": "sampled_no_output", "code": "sampled_no_output",
                "partial": "partial", "die": "sampled_no_output"}
        for mode, state in want.items():
            with self.subTest(mode), tempfile.TemporaryDirectory() as d:
                self.run_dir = Path(d) / "run"
                with self.assertRaises(Exception):
                    self.launch([("a", mode)], workers=1)
                self.assertEqual((self.state(), self.failure()["jobs"]["a"]["state"]), ("failed", state))

    def test_partial_preserved(self):
        with self.assertRaises(R2.RunStop):
            self.launch([("a", "partial")], workers=1)
        self.assertEqual((self.run_dir / "partial/a/archive.npz").read_bytes(), b"half")
        self.assertIn("partial/a/archive.npz", self.failure()["files"])
        self.assertFalse((self.run_dir / "episodes/a").exists())

    def test_stall(self):
        t = time.time()
        with self.assertRaises(R2.RunStop):
            self.launch([("a", "sleep")], workers=1, stall_timeout=5)
        self.assertLess(time.time() - t, 45)
        self.assertEqual(self.state(), "failed")

    def test_interrupt(self):
        def stop(n):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.launch([("a", 1)], on_done=stop)
        self.assertEqual((self.state(), self.failure()["jobs"]["a"]["state"]), ("failed", "committed"))

    def test_killed_parent_then_recover(self):
        code = f"import sys; sys.path.insert(0, {str(PKG / 'tests')!r}); import test_v10 as T; T.killed_parent({str(self.run_dir)!r})"
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        p = subprocess.run([sys.executable, "-c", "if __name__ == '__main__':\n " + code.replace("; ", "\n ")],
                           env=env, timeout=110, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 9)
        self.assertEqual(self.state(), "running")
        before = {q: q.read_bytes() for q in self.run_dir.rglob("*") if q.is_file()}
        inv = R2.recover(self.run_dir)
        self.assertEqual(inv["jobs"]["a"]["state"], "committed")
        self.assertIn(inv["jobs"]["b"]["state"], ("not_started", "started", "sampled_no_output"))
        self.assertTrue(all(q.read_bytes() == b for q, b in before.items() if "events" not in q.parts))
        with self.assertRaises(FileExistsError):
            R2.recover(self.run_dir)
        with self.assertRaises(R2.RunStop):
            R2.run_jobs([("a", None), ("b", "sleep")], bad_job, self.run_dir, R2.read_reservation(self.run_dir))
        time.sleep(0.5)

    def test_killed_around_commit(self):
        res = R2.reserve(self.run_dir, HEAD, FZ, ["a"], 1)
        (self.run_dir / "events").mkdir()
        ep = R2.Episode(self.run_dir, res["run_id"], "a")
        ep.sampling()
        (self.run_dir / "episodes").mkdir()
        real = os.rename
        R2.os.rename = lambda *a: (_ for _ in ()).throw(OSError("killed before rename"))
        try:
            with self.assertRaises(OSError):
                ep.commit({}, b"z")
        finally:
            R2.os.rename = real
        self.assertEqual(R2.inventory(self.run_dir)["jobs"]["a"]["state"], "partial")
        os.rename(ep.stage, ep.final)                                        # renamed, then killed before its event
        with open(ep.log, "ab") as f:
            f.write(b'{"event": "comm')                                      # torn line
        j = R2.inventory(self.run_dir)["jobs"]["a"]
        self.assertEqual((j["state"], j["torn_event_line"]), ("committed", True))
        with self.assertRaises(R2.RunStop):
            R2.Episode(self.run_dir, res["run_id"], "a")

    def test_commit_never_replaces(self):
        res = R2.reserve(self.run_dir, HEAD, FZ, ["a"], 1)
        for k in ("events", "episodes"):
            (self.run_dir / k).mkdir()
        one, two = (R2.Episode(self.run_dir, res["run_id"], "a") for _ in range(2))
        one.commit({}, b"1")
        with self.assertRaises(OSError):
            two.commit({}, b"2")
        self.assertEqual(R2.read_committed(self.run_dir, res["run_id"], "a")[1], b"1")

    def test_recover_refuses_closed_run(self):
        self.launch([("a", 1)], ok_job)
        with self.assertRaises(R2.RunStop):
            R2.recover(self.run_dir)


class ValidatorTests(unittest.TestCase):                                     # F5
    def check(self, r):
        V.validate_record(r, SEEDS, TR, ("U_NEAR", 2))

    def test_all_committed_pass(self):
        self.assertEqual(len(AD.load()), 64)

    def test_mutations_fail(self):
        base = committed("U_NEAR_e2")
        i = next(k for k, b in enumerate(base["blocks"]) if b["block"] == 10)

        def blk(f):
            return lambda r: f(r["blocks"][i])
        muts = {
            "block state": blk(lambda b: b.update(state="C")),
            "episode state": lambda r: r["states"].__setitem__(10, "OFF"),
            "both states": lambda r: (r["states"].__setitem__(10, "C"), r["blocks"][i].update(state="C")),
            "mode": lambda r: r.update(mode="fidelity"),
            "params": lambda r: r.update(params={"onset": 11}),
            "true changes": lambda r: r.update(true_changes=[]),
            "static": lambda r: r.update(static_key="B"),
            "arms": lambda r: r["arms"].reverse(),
            "seed": lambda r: r["seeds"].update({"b06:eval": 1}),
            "extra seed": lambda r: r["seeds"].update({"b00:eval": 1}),
            "unknown field": lambda r: r.update(note=1),
            "missing block": lambda r: r["blocks"].pop(),
            "invalid key": blk(lambda b: b["keys"].update(LA_R2="bank:Z")),
            "junk learned key": blk(lambda b: b["keys"].update(AD3="[1]")),
            "oracle": blk(lambda b: b["keys"].update(ORACLE="bank:B")),
            "fix": blk(lambda b: b["keys"].update(FIX_A="bank:B")),
            "rule key": blk(lambda b: b["keys"].update(LA_R2="bank:A")),
            "rule source": blk(lambda b: b["source"].update(LA_R2="base")),
            "cap ignored": blk(lambda b: (b["keys"].update(LA_R2_170="bank:B"), b["source"].update(LA_R2_170="lookahead"))),
            "source word": blk(lambda b: b["source"].update(W0F="hold")),
            "missing source": blk(lambda b: b["source"].pop("CB")),
            "bank/learn": blk(lambda b: b["source"].update(BANK="learn")),
            "cb": blk(lambda b: b["keys"].update(CB="bank:C")),
            "alarm": blk(lambda b: b["lookahead"].update(alarm=False)),
            "P1": blk(lambda b: b["lookahead"].update(P1=["A"])),
            "gf1 nan": blk(lambda b: b["db8"]["gf1"].update(B=float("nan"))),
            "negative errors": blk(lambda b: b["errors"].update(CB=-1)),
            "arm key missing": blk(lambda b: b["keys"].pop("DB2")),
        }
        self.check(copy.deepcopy(base))
        for name, f in muts.items():
            with self.subTest(name):
                r = copy.deepcopy(base)
                f(r)
                with self.assertRaises(ValueError):
                    self.check(r)


class PreflightTests(Tmp):                                                   # F4, F5, F7 end to end
    def test_launch_to_analysis(self):
        st = self.launch([(n, None) for n in JOBS], synthetic_job, workers=4)
        self.assertEqual(len(st["jobs"]), 64)
        status, pairs = V.load_bound(self.run_dir, HEAD, FZ)
        self.assertEqual(status["run_id"], st["run_id"])
        out = A10.analyze(pairs)
        self.assertEqual(len(out["episodes"]), 64)
        self.assertEqual(out["episodes"][0]["errors"]["LA_R2"], sum(b["errors"]["LA_R2"] for b in pairs[0][0]["blocks"]))
        self.assertEqual(out, A10.analyze(V.load_bound(self.run_dir, HEAD, FZ)[1]))      # repeatable
        # identity and integrity mutations on the same run
        for h, z in (("c" * 40, FZ), (HEAD, "d" * 64)):
            with self.assertRaises(ValueError):
                V.load_bound(self.run_dir, h, z)
        ep = self.run_dir / "episodes"

        def mutated(path, data):
            old = path.read_bytes()
            path.write_bytes(data)
            try:
                with self.assertRaises(ValueError, msg=path.name):
                    V.load_bound(self.run_dir, HEAD, FZ)
            finally:
                path.write_bytes(old)
        rp = ep / "AA_e0" / "record.json"
        mutated(rp, rp.read_bytes().replace(b'"mode": "db8"', b'"mode": "dbX"'))
        ar = ep / "AA_e0" / "archive.npz"
        mutated(ar, (ep / "AA_e1" / "archive.npz").read_bytes())
        j = self.run_dir / "journal.jsonl"
        mutated(j, b"".join(x for x in j.read_bytes().splitlines(True) if b'"AA_e0"' not in x))
        mutated(j, j.read_bytes()[:-5])
        ev = self.run_dir / "events" / "AA_e0.jsonl"
        mutated(ev, ev.read_bytes().splitlines(True)[0])
        s = self.run_dir / "RUN_STATUS.json"
        mutated(s, s.read_bytes().replace(b"ready_for_analysis", b"failed"))
        (ep / "ZZ_e0").mkdir()
        with self.assertRaises(ValueError):
            V.load_bound(self.run_dir, HEAD, FZ)
        (ep / "ZZ_e0").rmdir()
        (self.run_dir / "staging" / "x").mkdir()
        with self.assertRaises(ValueError):
            V.load_bound(self.run_dir, HEAD, FZ)
        (self.run_dir / "staging" / "x").rmdir()
        V.load_bound(self.run_dir, HEAD, FZ)

    def test_bits_must_agree_with_keys_and_counts(self):
        r = committed("AA_e0")
        with self.assertRaises(ValueError):
            V.arrays(r, b"not the archive")


class AddendumTests(unittest.TestCase):
    def test_reproduces_and_matches_frozen_totals(self):                     # F6, F10, F11
        res = AD.build(AD.load())
        saved = (PKG / "DB8_ADDENDUM.json").read_bytes()
        self.assertEqual((json.dumps(res, indent=1, sort_keys=True) + "\n").encode(), saved)
        an = json.loads((C.ROOT / "results/dev/ANALYSIS.json").read_text(encoding="utf-8"))
        self.assertEqual(res["cb_memory_sensitivity"], {
            "last_bank": {"pooled_errors": an["pooled_errors"]["CB"], "keys_different_from_frozen": 0},
            "last_emitted": {"pooled_errors": 10069, "keys_different_from_frozen": 16}})
        for a in AD.ARMS:
            boxes = list(res["onset_table"][a]["by_destination"].values()) + [res["onset_table"][a]["non_onset"]]
            cells = [c for b in boxes for c in b.values()]
            self.assertEqual(sum(c["firings"] for c in cells), an["reported"]["fires"][a])
            self.assertEqual(sum(c["saved_vs_W0F"] for c in cells), an["pooled_errors"]["W0F"] - an["pooled_errors"][a])
        u = res["unknown_panels"]["LA_W0F"].values()
        self.assertEqual((sum(x["wrong_by_block_truth"] for x in u), sum(x["wrong_by_panel_wording"] for x in u)), (20, 21))
        self.assertEqual([sum(x["excess_vs_W0F"][a] for x in res["U_NEAR_onsets"]) for a in ("LA_R2", "LA_R2_170")], [375, 327])


@unittest.skipUnless(os.environ.get("QSHIFT_DB8_EVIDENCE"), "QSHIFT_DB8_EVIDENCE not set")
class SavedEvidenceTests(unittest.TestCase):
    def test_final_archives(self):
        run = Path(os.environ["QSHIFT_DB8_EVIDENCE"]) / "work" / "dev_a3"
        pairs = []
        for n in JOBS:
            r = committed(n)
            pairs.append((r, V.arrays(r, (run / r["archive"]).read_bytes())))
        out = A10.analyze(pairs)
        an = json.loads((C.ROOT / "results/dev/ANALYSIS.json").read_text(encoding="utf-8"))
        for k in out:
            self.assertEqual(json.loads(json.dumps(out[k])), an[k], k)


class SourceTests(unittest.TestCase):
    def test_lf_and_no_local_paths(self):
        for p in PKG.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                b = p.read_bytes()
                self.assertNotIn(b"\r\n", b, p.name)
                for bad in (b"C:" + b"\\Users", b"C:" + b"/Users", b"LEN" + b"OVO", b"@gm" + b"ail"):
                    self.assertNotIn(bad, b, p.name)


if __name__ == "__main__":
    unittest.main()
