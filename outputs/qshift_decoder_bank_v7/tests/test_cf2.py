"""CF2 tests: config, the job is DB6's (imported, unchanged), mocked truth invariance (truth metadata, current-block
labels, evaluation labels), the analysis (Holm, onset table, DB6 dev reproduction), strict archives, typed retries,
seeds, LF-only files and no seal."""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
import tempfile
import unittest
from multiprocessing import get_context
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import cf2_config as C  # noqa: E402
import cf2_analyze as A  # noqa: E402
import cf2_run as R  # noqa: E402
import db6_config as C6  # noqa: E402
import db6_run as R6  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_config(self):
        self.assertEqual(sum(C.EPISODES.values()), 48)
        self.assertEqual(set(C.EPISODES), set(C6.EPISODES))
        self.assertEqual(C.ARMS, C6.ARMS)
        self.assertTrue(all(k.startswith("cf2:") for k in C.all_keys()))
        self.assertEqual([h[0] for h in C.HYPOTHESES], ["C1", "C2", "C3"])
        self.assertEqual(C.HYPOTHESES[0][1:], ("W0F", C.SCHEDULES))
        for _, comp, panels in C.HYPOTHESES:
            self.assertIn(comp, C.ARMS)
            self.assertTrue(set(panels) <= set(C.SCHEDULES))
        self.assertNotIn("BB", C.HYPOTHESES[2][2])          # BANK beats LA_W0F on BB/S4/N_OFF in dev: excluded


class JobTests(unittest.TestCase):
    def test_job_is_db6(self):
        src = (PKG / "cf2_run.py").read_text(encoding="utf-8")
        self.assertNotIn("def episode_job", src)
        self.assertIn("return R6.episode_job(args)", inspect.getsource(R.job))
        self.assertIs(R6._setup, R._setup)

    def test_fidelity_la_rule(self):
        self.assertEqual(R.FID_REQUIRE_LA, (("BB", 0),))
        self.assertTrue(set(R.FID_REQUIRE_LA) <= set(R.FID_EPISODES))
        self.assertIn("(s, e) not in FID_REQUIRE_LA", inspect.getsource(R.cmd_fidelity))

    def test_db6_code_unchanged_since_db6_freeze(self):
        fz = json.loads((C.DB6 / "DB6_FREEZE.json").read_text(encoding="utf-8"))["files"]
        for rel in ("outputs/qshift_decoder_bank_v6/db6_run.py", "outputs/qshift_decoder_bank_v6/db6_core.py",
                    "outputs/qshift_decoder_bank_v6/db6_config.py"):
            p = PKG.parents[1] / rel
            self.assertEqual(R._norm_sha(rel, p.read_bytes()), fz[rel], rel)

    def test_setup_modes(self):
        if not (PKG / "CF2_SEEDS.json").exists():
            self.skipTest("seeds not written yet")
        sd = json.loads((PKG / "CF2_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
        truth, seed, n, prm, ch = R._setup("cf2", "RX", 1)
        self.assertEqual(seed(7, "det"), int(sd["cf2:RX:e1:b07:det"]))
        self.assertEqual(n, C.EVAL_PER_BLOCK)
        self.assertEqual(ch, C.changes("RX", prm))
        d6 = json.loads((C.DB6 / "DB6_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
        self.assertEqual(R._setup("dev", "RX", 1)[1](7, "det"), int(d6["db6:RX:e1:b07:det"]))


# ------------------------------------------------------------------ mocked truth invariance (erratum item 4)
MINI_STATES = ["OFF"] * 6 + ["B", "B"]
MINI_SEED = lambda t, p: 10_007 * t + {"det": 1, "lab": 2, "eval": 3}[p] + 900_000   # noqa: E731


def _mini(args):
    """An 8-block episode (scored blocks 6, 7; B onset at 6) through DB6's unchanged job, with one perturbation."""
    perturb, out = args
    import ad2
    import db_core as D
    import cf2_run as RR
    import db6_config as CC
    import db6_run as RD
    CC.BLOCKS = len(MINI_STATES)
    RD._setup = lambda mode, s, e: ((lambda t: MINI_STATES[t]), MINI_SEED, CC.EVAL_PER_BLOCK, {}, [6])
    sample, estimate = D.sample, ad2.estimate
    if perturb == "eval":                               # evaluation labels flipped
        D.sample = lambda st, n, sd: (lambda x, y: (x, 1 - y) if n == CC.EVAL_PER_BLOCK else (x, y))(*sample(st, n, sd))
    elif perturb == "lab_current":                      # the last block's own labelled rows flipped (used from t+1)
        last = MINI_SEED(len(MINI_STATES) - 1, "lab")
        D.sample = lambda st, n, sd: (lambda x, y: (x, 1 - y) if sd == last else (x, y))(*sample(st, n, sd))
    elif perturb == "truth_meta":                       # the truth support handed to the estimator's bookkeeping
        ad2.estimate = lambda dets, labx, laby, classes, truth_sup: estimate(dets, labx, laby, classes, CC.support("A"))
    Path(out, "records").mkdir(parents=True, exist_ok=True)
    RR.job(("mini", "MINI", 0, out))
    return json.loads(Path(out, "records", "MINI_e0.json").read_text(encoding="utf-8"))


def _decisions(rec):
    return [({a: k for a, k in b["keys"].items() if a != "ORACLE"}, b["source"], b["lookahead"], b["plausible"],
             b["alarm"], b["seg0"]) for b in rec["blocks"]]


class TruthInvarianceTests(unittest.TestCase):
    def test_decisions_ignore_truth_labels_and_eval(self):
        d = Path(tempfile.mkdtemp())
        modes = ("base", "eval", "lab_current", "truth_meta")
        with get_context("spawn").Pool(len(modes)) as pool:
            recs = dict(zip(modes, pool.map(_mini, [(m, str(d / m)) for m in modes])))
        base = recs["base"]
        self.assertEqual([b["block"] for b in base["blocks"]], [6, 7])
        self.assertEqual(base["blocks"][0]["source"]["LA_W0F"], "lookahead")     # the overlay is exercised
        self.assertEqual(base["blocks"][0]["keys"]["LA_W0F"], "bank:B")
        for m in modes[1:]:
            self.assertEqual(_decisions(recs[m]), _decisions(base), m)
        self.assertNotEqual([b["errors"] for b in recs["eval"]["blocks"]], [b["errors"] for b in base["blocks"]])


# ------------------------------------------------------------------ analysis
class AnalysisTests(unittest.TestCase):
    def test_holm(self):
        self.assertEqual(A.holm({"a": 0.01, "b": 0.04, "c": 0.03}, 0.05), {"a": True, "b": False, "c": False})
        self.assertEqual(A.holm({"a": 0.01, "b": 0.02, "c": 0.04}, 0.05), {"a": True, "b": True, "c": True})
        self.assertEqual(A.holm({"a": 0.02, "b": 0.001}, 0.05), {"a": True, "b": True})
        self.assertEqual(A.holm({"a": 0.06, "b": 0.001}, 0.05), {"a": False, "b": True})

    def test_stats(self):
        self.assertEqual(A.sign_test_p([-1, -2, -3, 0, 0]), 1 / 8)
        self.assertAlmostEqual(A.cp_upper(0, 48), 1 - 0.05 ** (1 / 48), places=6)
        lo, hi = A.boot_ci([-1, -2, -3, -4], 2000, 1)
        self.assertTrue(-4 <= lo <= hi <= -1)

    def test_onset_table(self):
        mk = lambda t, st, src, key, ew, el: {"block": t, "state": st, "source": {"LA_W0F": src},   # noqa: E731
                                              "keys": {"LA_W0F": key}, "errors": {"W0F": ew, "LA_W0F": el}}
        rec = {"states": ["OFF"] * 6 + ["B", "B", "A", "A"],
               "blocks": [mk(6, "B", "lookahead", "bank:B", 30, 5), mk(7, "B", "base", "bank:B", 4, 4),
                          mk(8, "A", "base", "bank:OFF", 40, 40), mk(9, "A", "lookahead", "bank:B", 2, 3)]}
        o = A.onset_table([rec])
        self.assertEqual(o["by_destination"]["B"], {"opportunities": 1, "triggers": 1, "correct": 1, "saved_vs_W0F": 25})
        self.assertEqual(o["by_destination"]["A"], {"opportunities": 1, "triggers": 0, "correct": 0, "saved_vs_W0F": 0})
        self.assertEqual(o["non_opportunity_triggers"], {"triggers": 1, "correct": 0, "saved_vs_W0F": -1})

    def test_reproduces_db6_dev(self):
        run = C.DB6 / "work" / "dev"
        if not (run / "RUN_STATUS.json").exists():
            self.skipTest("DB6 dev archives are local only")
        ref = json.loads((C.DB6 / "results" / "dev" / "ANALYSIS.json").read_text(encoding="utf-8"))["criteria"]["values"]
        res, _ = A.analyze(run, C6.EPISODES, C6.ARMS, (("C1", "W0F", C6.SCHEDULES),))
        h = res["hypotheses"]["C1"]
        self.assertEqual(h["d"], ref["E1_d"])
        self.assertEqual(h["mean"], ref["E1_mean_LA_W0F_minus_W0F"])
        self.assertEqual(h["sign_p"], ref["E1_sign_p"])
        self.assertEqual((res["gates"]["G4_uses"], res["gates"]["G4_wrong"]), (ref["S3_uses"], ref["S3_wrong"]))
        self.assertEqual(res["gates"]["G2_max_block_harm"], ref["S2_max_block_harm"])
        self.assertEqual(res["gates"]["G5_RX_d"], ref["S4_RX_d"])
        self.assertEqual(res["pooled_errors"], ref["pooled_errors"])


class ArchiveTests(unittest.TestCase):
    def _run(self, mutate):
        d = Path(tempfile.mkdtemp())
        (d / "records").mkdir()
        (d / "archives").mkdir()
        bits, blocks = {}, []
        for t in C.SCORED:
            e = np.zeros(C.EVAL_PER_BLOCK, bool)
            e[:2] = True
            bits[f"b{t:02d}_W0F"] = np.packbits(e)
            blocks.append({"block": t, "errors": {"W0F": 2}})
        mutate(bits)
        np.savez_compressed(d / "archives" / "X_e0.npz", **bits)
        rec = {"schedule": "X", "episode": 0, "arms": ["W0F"], "eval_per_block": C.EVAL_PER_BLOCK, "blocks": blocks,
               "archive": "archives/X_e0.npz",
               "archive_sha256": hashlib.sha256((d / "archives" / "X_e0.npz").read_bytes()).hexdigest()}
        (d / "records" / "X_e0.json").write_text(json.dumps(rec), encoding="utf-8")
        (d / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "n_jobs": 1}), encoding="utf-8")
        return R6.load_checked(d, {"X": 1}, ("W0F",))

    def test_strict(self):
        self._run(lambda b: None)

        def extra(b):
            b["b06_ZZ"] = b["b06_W0F"]

        def width(b):
            b["b06_W0F"] = np.zeros(126, np.uint8)

        def pad(b):
            v = b["b06_W0F"].copy()
            v[-1] |= 1
            b["b06_W0F"] = v

        def count(b):
            b["b07_W0F"] = np.zeros(125, np.uint8)
        for m in (extra, width, pad, count):
            with self.assertRaises(ValueError, msg=m.__name__):
                self._run(m)
        self.assertIn("R6.load_checked(", inspect.getsource(A.analyze))


class RunTests(unittest.TestCase):
    def test_typed_retry_and_guards(self):
        self.assertIs(R.INFRA, R6.INFRA)
        body = inspect.getsource(R.cmd_run)
        self.assertIn("except INFRA as ex:", body)
        self.assertEqual(body.count("except "), 2)       # the INFRA retry and the final status recorder
        for guard in ("expected_head", "tree_clean", "check_freeze", "all_pass", "single attempt only"):
            self.assertIn(guard, body)


class SourceTests(unittest.TestCase):
    def test_no_seal(self):
        for p in list(PKG.glob("*.py")) + list((PKG / "tests").glob("*.py")):
            s = p.read_text(encoding="utf-8")
            for bad in ("open_" "seal", "_SEA" "LED", "re1_" "seal", "re2_" "seal", "HIDDEN_" "COMMITMENT", "R" "6_*",
                        "cf1/" "records", "results/" "cf1"):
                self.assertNotIn(bad, s, p.name)

    def test_lf_only(self):
        for p in list(PKG.glob("*.py")) + list(PKG.glob("*.md")) + list((PKG / "tests").glob("*.py")):
            self.assertNotIn(b"\r\n", p.read_bytes(), p.name)


def _screened():
    import prepare_cf2
    return prepare_cf2.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        p = PKG / "CF2_SEEDS.json"
        if not p.exists():
            self.skipTest("seeds not written yet")
        s = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys()))
        v = set(s["seeds"].values())
        self.assertEqual(len(v), len(s["seeds"]))
        self.assertIn("outputs/qshift_decoder_bank_v6/DB6_SEEDS.json", s["screened"])
        with get_context("spawn").Pool(1) as pool:
            self.assertFalse(v & pool.apply(_screened))


if __name__ == "__main__":
    unittest.main()
