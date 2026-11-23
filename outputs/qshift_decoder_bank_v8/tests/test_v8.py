"""Regression tests for the CF2 audit corrections (F3-F8). No study sampling: the truth-invariance test runs DB6's
unchanged episode job on synthetic detector/label rows with the stim sampler disabled."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
import unittest
from multiprocessing import get_context
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import runkit as K  # noqa: E402


# ------------------------------------------------------------------ F3
def _git(table):
    return lambda args: table[tuple(args)]


GOOD = {("rev-parse", "HEAD"): "f" * 40 + "\n", ("rev-parse", "HEAD^"): "c" * 40 + "\n",
        ("diff", "--name-only", "HEAD^", "HEAD"): "v9/FREEZE.json\n", ("status", "--porcelain", "--untracked-files=no"): "",
        ("ls-tree", "-r", "--name-only", "HEAD", "v9/results"): ""}


class RevisionTests(unittest.TestCase):
    def check(self, over=None):
        t = {**GOOD, **(over or {})}
        return K.check_revision("f" * 40, "v9/FREEZE.json", "c" * 40, _git(t), ("v9/results",))

    def test_exact_freeze_commit_passes(self):
        self.assertEqual(self.check(), "f" * 40)

    def test_rejections(self):
        bad = {"later commit (e.g. the result commit)": {("rev-parse", "HEAD"): "e" * 40},
               "parent is not the frozen code": {("rev-parse", "HEAD^"): "d" * 40},
               "freeze commit also changes code": {("diff", "--name-only", "HEAD^", "HEAD"): "v9/FREEZE.json\nv9/x.py"},
               "dirty tree": {("status", "--porcelain", "--untracked-files=no"): " M v9/x.py"},
               "results already tracked": {("ls-tree", "-r", "--name-only", "HEAD", "v9/results"): "v9/results/a.json"}}
        for why, over in bad.items():
            with self.assertRaises(K.PreflightError, msg=why):
                self.check(over)


class RuntimeTests(unittest.TestCase):
    def test_identity_has_native_deps(self):
        r = K.runtime_identity()
        for k in ("python", "numpy", "scipy", "stim", "pymatching", "ldpc", "platform"):
            self.assertIn(k, r)
        self.assertIsNotNone(r["ldpc"])
        self.assertEqual(K.check_runtime(r, r), [])

    def test_mismatch_and_missing(self):
        r = K.runtime_identity()
        self.assertEqual(K.check_runtime(r, {**r, "ldpc": "0.0"}), ["ldpc"])
        self.assertEqual(K.check_runtime(r, {**r, "scipy": "0.0"}), ["scipy"])
        cf2_style = {k: r[k] for k in ("python", "numpy", "stim", "pymatching", "platform")}   # CF2 froze only these
        self.assertEqual(set(K.check_runtime(cf2_style, r)), {"implementation", "scipy", "ldpc"})


# ------------------------------------------------------------------ F4
SCORED = (6, 7)
EVAL = 1000


def _seeds(s, e):
    return {f"b{t:02d}:{p}": 1000 * e + 10 * t + i for t in range(8) for i, p in enumerate(("det", "lab", "eval"))}


def _write_run(d, eps=(("X", 0), ("X", 1)), mutate=None):
    d = Path(d)
    (d / "records").mkdir(parents=True)
    (d / "archives").mkdir()
    recs = {}
    for s, e in eps:
        bits, blocks = {}, []
        for t in SCORED:
            v = np.zeros(EVAL, bool)
            v[:3 + e] = True
            bits[f"b{t:02d}_W0F"] = np.packbits(v)
            blocks.append({"block": t, "errors": {"W0F": 3 + e}})
        np.savez_compressed(d / "archives" / f"{s}_e{e}.npz", **bits)
        recs[f"{s}_e{e}"] = {"schedule": s, "episode": e, "arms": ["W0F"], "eval_per_block": EVAL, "blocks": blocks,
                             "seeds": _seeds(s, e), "archive": f"archives/{s}_e{e}.npz"}
    st = {"state": "ready_for_analysis", "n_jobs": len(eps), "jobs": {n: {"returncode": 0} for n in recs}}
    if mutate:
        mutate(d, recs, st)
    for n, r in recs.items():
        r.setdefault("archive_sha256", hashlib.sha256((d / r["archive"]).read_bytes()).hexdigest())
        (d / "records" / f"{n}.json").write_text(json.dumps(r), encoding="utf-8")
    (d / "RUN_STATUS.json").write_text(json.dumps(st), encoding="utf-8")
    return d


def _load(d):
    return K.load_strict(d, {"X": 2}, ("W0F",), EVAL, SCORED, _seeds)


class LoadStrictTests(unittest.TestCase):
    def test_good(self):
        st, recs = _load(_write_run(tempfile.mkdtemp()))
        self.assertEqual(len(recs), 2)

    def test_mutations(self):
        def dup_episode(d, recs, st):                  # the audit's probe: two records claiming episode 0
            recs["X_e1"]["episode"] = 0

        def shared_archive(d, recs, st):
            recs["X_e1"]["archive"] = "archives/X_e0.npz"

        def eval_1001(d, recs, st):
            recs["X_e0"]["eval_per_block"] = 1001

        def seed_mismatch(d, recs, st):
            recs["X_e1"]["seeds"]["b07:eval"] += 1

        def missing_job(d, recs, st):
            del st["jobs"]["X_e1"]

        def failed_job(d, recs, st):
            st["jobs"]["X_e1"]["returncode"] = 1

        def wrong_count(d, recs, st):
            st["n_jobs"] = 3
        for m in (dup_episode, shared_archive, eval_1001, seed_mismatch, missing_job, failed_job, wrong_count):
            with self.assertRaises(ValueError, msg=m.__name__):
                _load(_write_run(tempfile.mkdtemp(), mutate=m))

    def test_extra_record_file(self):
        d = _write_run(tempfile.mkdtemp())
        (d / "records" / "X_e2.json").write_text((d / "records" / "X_e0.json").read_text(encoding="utf-8"),
                                                encoding="utf-8")
        with self.assertRaises(ValueError):
            _load(d)


# ------------------------------------------------------------------ F5
def _job(args):
    """Fake job (no sampling). kind: ok | infra_prewrite | infra_postwrite | code | slow."""
    name, kind, run, flag = args
    run = Path(run)
    if kind == "infra_prewrite" and not Path(flag).exists():
        Path(flag).write_text("x")
        raise OSError("transient")
    if kind == "slow":
        time.sleep(30)
    (run / "archives").mkdir(exist_ok=True)
    (run / "archives" / f"{name}.npz").write_bytes(b"partial")
    if kind == "infra_postwrite":
        raise OSError("disk went away after the archive was written")
    if kind == "code":
        raise ValueError("bug")
    (run / "records").mkdir(exist_ok=True)
    (run / "records" / f"{name}.json").write_text("{}")
    return name


def _outs(n):
    return (f"archives/{n}.npz", f"records/{n}.json")


class RunTests(unittest.TestCase):
    def go(self, kinds, timeout=60, on_progress=None):
        d = Path(tempfile.mkdtemp())
        K.Reservation(d, {"head": "test"})
        jobs = [(f"J{i}", (f"J{i}", k, str(d), str(d / f"flag{i}"))) for i, k in enumerate(kinds)]
        try:
            st = K.run_jobs(jobs, _job, d, _outs, workers=2, timeout=timeout, on_progress=on_progress)
            err = None
        except BaseException as ex:      # noqa: BLE001
            st, err = json.loads((d / "RUN_STATUS.json").read_text(encoding="utf-8")), ex
        return d, st, err, [e["event"] for e in K.Journal(d).events()]

    def test_reservation_is_exclusive_and_permanent(self):
        d = tempfile.mkdtemp()
        K.Reservation(d, {"head": "a"})
        with self.assertRaises(K.PreflightError):
            K.Reservation(d, {"head": "a"})
        self.assertTrue((Path(d) / "RUN.lock").exists())

    def test_ok(self):
        d, st, err, ev = self.go(["ok", "ok"])
        self.assertIsNone(err)
        self.assertEqual(st["state"], "ready_for_analysis")
        self.assertEqual(ev[0], "run_start")
        self.assertEqual(ev[-1], "run_end")

    def test_prewrite_infra_retried_once(self):
        d, st, err, ev = self.go(["ok", "infra_prewrite"])
        self.assertIsNone(err)
        self.assertEqual(st["jobs"]["J1"], {"returncode": 0, "rerun": True})
        self.assertIn("job_infra_prewrite", ev)
        self.assertIn("job_retry", ev)

    def test_postwrite_infra_fails_closed_and_preserves(self):
        d, st, err, ev = self.go(["ok", "infra_postwrite"])
        self.assertIsInstance(err, K.RunStop)
        self.assertEqual(st["state"], "failed")
        self.assertNotIn("job_retry", ev)
        self.assertFalse((d / "archives" / "J1.npz").exists())
        self.assertEqual((d / "partial" / "J1" / "attempt1" / "archives" / "J1.npz").read_bytes(), b"partial")
        self.assertTrue((d / "records" / "J0.json").exists())          # completed work is left in place

    def test_code_error_not_retried(self):
        d, st, err, ev = self.go(["code"])
        self.assertIsInstance(err, ValueError)
        self.assertEqual(st["state"], "failed")
        self.assertNotIn("job_retry", ev)
        self.assertTrue((d / "partial" / "J0" / "attempt1" / "archives" / "J0.npz").exists())

    def test_timeout_fails_closed(self):
        d, st, err, ev = self.go(["slow"], timeout=2)
        self.assertIsInstance(err, K.RunStop)
        self.assertIn("job_timeout", ev)
        self.assertEqual(st["state"], "failed")

    def test_interruption_fails_closed(self):
        def stop(n):
            raise KeyboardInterrupt
        d, st, err, ev = self.go(["ok", "ok"], on_progress=stop)
        self.assertIsInstance(err, KeyboardInterrupt)
        self.assertEqual(st["state"], "failed")
        self.assertIn("run_failed", ev)


# ------------------------------------------------------------------ F7, F8
class BoundTests(unittest.TestCase):
    def test_g4_boundary(self):
        self.assertLess(K.cp_upper(1, 93), 0.05)                   # 4.9994%: 1/93 would have passed
        self.assertGreater(K.cp_upper(1, 92), 0.05)
        self.assertAlmostEqual(K.cp_upper(3, 96), 0.0787869, places=6)
        self.assertEqual([K.cp_min_n(k) for k in range(4)], [59, 93, 124, 153])

    def test_describe_has_no_p(self):
        self.assertEqual(set(K.describe([-1, 0, 2])), {"n", "mean", "median", "better", "worse", "tied"})


# ------------------------------------------------------------------ F6: sampler-free truth invariance
STATES9 = ["OFF"] * 6 + ["B", "B", "B"]
PARTS = {"det": 1, "lab": 2, "eval": 3}


def _seed(t, p):
    return 1_000 * t + PARTS[p]


def _synthetic(perturb):
    """Synthetic rows: detectors ~ Bernoulli(DB1 template of the block's state); labels ~ Bernoulli(0.03)."""
    import db6_config as CC
    tpl = {k: np.array(v) for k, v in json.loads((CC.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["templates"].items()}

    def sample(state, n, sd):
        t, part = divmod(sd, 1_000)
        part = {v: k for k, v in PARTS.items()}[part]
        st = state
        if perturb == "future_det" and part == "det" and t == len(STATES9) - 1:
            st = "A"                                                    # the last block's detectors change
        rng = np.random.default_rng(sd)
        x = (rng.random((n, tpl["OFF"].size)) < tpl[st]).astype(np.uint8)
        y = (rng.random(n) < 0.03).astype(np.uint8)
        if (perturb == "eval" and part == "eval") or (perturb == "lab_current" and part == "lab" and t == 7):
            y = 1 - y
        return x, y
    return sample


def _mini(args):
    perturb, out = args
    sys.path.insert(0, str(PKG.parent / "qshift_decoder_bank_v6"))
    import db6_config as CC          # first: puts DB5-DB1 and AD2/AD3 on sys.path
    import ad2
    import db_core as D
    import db6_run as RD
    import stim

    def no_sampler(*a, **k):
        raise AssertionError("stim sampler used")
    stim.Circuit.compile_detector_sampler = no_sampler
    stim.Circuit.compile_sampler = no_sampler
    CC.BLOCKS = len(STATES9)
    RD._setup = lambda mode, s, e: ((lambda t: STATES9[t]), _seed, 64, {}, [6])
    D.sample = _synthetic(perturb)
    if perturb == "truth_meta":
        est = ad2.estimate
        ad2.estimate = lambda dets, labx, laby, classes, truth_sup: est(dets, labx, laby, classes, CC.support("A"))
    Path(out, "records").mkdir(parents=True, exist_ok=True)
    RD.episode_job(("mini", "MINI", 0, out))
    return json.loads(Path(out, "records", "MINI_e0.json").read_text(encoding="utf-8"))


def _decisions(rec, upto):
    return [({a: k for a, k in b["keys"].items() if a != "ORACLE"}, b["source"], b["lookahead"], b["plausible"],
             b["alarm"], b["seg0"]) for b in rec["blocks"] if b["block"] <= upto]


class TruthInvarianceTests(unittest.TestCase):
    def test_synthetic_invariance(self):
        d = Path(tempfile.mkdtemp())
        modes = ("base", "eval", "lab_current", "truth_meta", "future_det")
        with get_context("spawn").Pool(len(modes)) as pool:
            recs = dict(zip(modes, pool.map(_mini, [(m, str(d / m)) for m in modes])))
        base = recs["base"]
        self.assertEqual([b["block"] for b in base["blocks"]], [6, 7, 8])
        self.assertEqual(base["blocks"][0]["source"]["LA_W0F"], "lookahead")      # the overlay is exercised
        self.assertEqual(base["blocks"][0]["keys"]["LA_W0F"], "bank:B")
        for m in ("eval", "truth_meta"):
            self.assertEqual(_decisions(recs[m], 8), _decisions(base, 8), m)
        self.assertEqual(_decisions(recs["lab_current"], 7), _decisions(base, 7))   # block 7 labels: used from 8
        self.assertEqual(_decisions(recs["future_det"], 7), _decisions(base, 7))    # block 8 detectors: from 8
        self.assertNotEqual(recs["future_det"]["blocks"][2]["lookahead"], base["blocks"][2]["lookahead"])
        self.assertNotEqual([b["errors"] for b in recs["eval"]["blocks"]], [b["errors"] for b in base["blocks"]])


class SourceTests(unittest.TestCase):
    def test_phaseb_never_reads_cf2_or_seals(self):
        s = (PKG / "research" / "phaseb.py").read_text(encoding="utf-8")
        lines = s.split('"""', 2)[2].splitlines()
        deny = [ln for ln in lines if ln.startswith("FORBIDDEN = ")]
        self.assertEqual(len(deny), 1)
        self.assertIn("qshift_decoder_bank_v7", deny[0])            # an explicit deny-list on every record path
        body = "\n".join(ln for ln in lines if not ln.startswith("FORBIDDEN = "))
        for bad in ("bank_v7", "bank_v5", "results/" "cf", "work/" "cf", "R" "6_*", "open_" "seal"):
            self.assertNotIn(bad, body, bad)

    def test_lf_only(self):
        for p in list(PKG.rglob("*.py")) + list(PKG.rglob("*.md")) + list(PKG.rglob("*.json")):
            if "__pycache__" not in p.parts:
                self.assertNotIn(b"\r\n", p.read_bytes(), p.name)


if __name__ == "__main__":
    unittest.main()
