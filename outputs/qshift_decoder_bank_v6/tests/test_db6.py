"""DB6 tests: loop = DB4 + LA overlay lines, LA inputs (truth/label/eval invariance), the overlay rule, strict
archive validation, typed retries, the portable freeze hash, statistics, seeds, LF-only files and no seal."""
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
import db6_config as C  # noqa: E402
import db6_core as L6  # noqa: E402
import db6_run as R  # noqa: E402

TPL = {k: np.array(v) for k, v in json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["templates"].items()}
TAU = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["tau_fit"]


class ConfigTests(unittest.TestCase):
    def test_config(self):
        self.assertEqual(sum(C.EPISODES.values()), 27)
        self.assertEqual(C.EPISODES["RX"], 4)
        self.assertEqual(C.ARMS[:len(C.C4.ARMS)], C.C4.ARMS)
        self.assertEqual(set(C.LA_ARMS.values()) | set(C.LA2_ARMS.values()), {"W0F", "BANK", "DB2", "STATIC"})
        self.assertEqual(C.changes("RX", {"on1": 6, "dwell": [4, 4, 4, 4, 4]}), [6, 10, 14, 18, 22, 26])
        self.assertTrue(all(k.startswith("db6:") for k in C.all_keys()))


class LoopTests(unittest.TestCase):
    src = (PKG / "db6_run.py").read_text(encoding="utf-8")

    def test_loop_is_db4_plus_overlay(self):
        d4 = (C.DB4 / "db4_run.py").read_text(encoding="utf-8")
        cut = lambda s: s[s.index("def _bank_arm"):s.index("# ------------------------------------------------------------------ ")]  # noqa: E731
        mine = cut(self.src)
        added = [ln for ln in mine.splitlines() if "L6." in ln or "C.LA_ARMS" in ln or "C.LA2_ARMS" in ln
                 or 'blocks[-1]["lookahead"]' in ln]
        self.assertEqual(len(added), 6)
        rest = "\n".join(ln for ln in mine.splitlines() if ln not in added)
        self.assertEqual(rest.rstrip("\n"), cut(d4).rstrip("\n"))

    def test_overlay_after_base_state_and_before_eval(self):
        s = self.src
        i_prev, i_la = s.index("prev.update(keys)"), s.index("la = L6.lookahead(cnt, seg0, t, tpl, tau_fit)")
        self.assertLess(i_prev, i_la)
        self.assertLess(i_la, s.index('x, y = D.sample(st_t, n_eval, seed(t, "eval"))'))
        self.assertLess(s.index("trk.commit(P)"), i_la)

    def test_lookahead_inputs_only(self):
        self.assertEqual(list(inspect.signature(L6.lookahead).parameters), ["cnt", "seg0", "t", "tpl", "tau_fit"])
        body = inspect.getsource(L6.lookahead)
        for bad in ("lab", "eval", "truth", "state(", "y", "st_t"):
            self.assertNotIn(bad, body.split('"""')[-1], bad)


class LookaheadTests(unittest.TestCase):
    def _cnt(self, rng, rates, n=2000):
        return np.minimum(rng.binomial(n, rates), n).astype(np.int64), n

    def test_reads_nothing_after_t(self):
        rng = np.random.default_rng(1)
        cnt = [self._cnt(rng, TPL["OFF"]) for _ in range(10)] + [self._cnt(rng, TPL["B"])]
        a = L6.lookahead(cnt, 0, 10, TPL, TAU)
        b = L6.lookahead(cnt + [self._cnt(rng, TPL["A"]) for _ in range(5)], 0, 10, TPL, TAU)
        self.assertEqual(a, b)
        self.assertTrue(a["alarm"])
        self.assertEqual(a["P1"], ["B"])

    def test_steady_off(self):
        rng = np.random.default_rng(2)
        cnt = [self._cnt(rng, TPL["OFF"]) for _ in range(8)]
        la = L6.lookahead(cnt, 0, 7, TPL, TAU)
        self.assertFalse(la["alarm"])
        self.assertIn("OFF", la["P1"])

    def test_overlay_rule(self):
        self.assertEqual(L6.la_key("bank:A", {"alarm": True, "P1": ["B"]}), ("bank:B", "lookahead"))
        self.assertEqual(L6.la_key("bank:A", {"alarm": False, "P1": ["B"]}), ("bank:A", "base"))
        self.assertEqual(L6.la_key("bank:A", {"alarm": True, "P1": ["A", "OFF"]}), ("bank:A", "base"))
        self.assertEqual(L6.la_key("x", {"alarm": True, "P1": []}), ("x", "base"))
        self.assertEqual(L6.la_key("bank:A", {"alarm": False, "P1": ["OFF"]}, gated=False), ("bank:OFF", "lookahead"))


class FreezeTests(unittest.TestCase):
    def test_norm_sha(self):
        self.assertEqual(R._norm_sha("a.py", b"x\r\ny\r\n"), R._norm_sha("a.py", b"x\ny\n"))
        self.assertEqual(R._norm_sha("a.json", b"{}\r\n"), hashlib.sha256(b"{}\n").hexdigest())
        self.assertNotEqual(R._norm_sha("a.npz", b"x\r\n"), R._norm_sha("a.npz", b"x\n"))

    def test_typed_retry(self):
        self.assertFalse(any(issubclass(e, R.INFRA) for e in (ValueError, KeyError, TypeError, AssertionError,
                                                               ZeroDivisionError, SystemExit)))
        self.assertTrue(issubclass(FileNotFoundError, R.INFRA))
        body = inspect.getsource(R.cmd_dev)
        self.assertIn("except INFRA as ex:", body)
        self.assertEqual(body.count("except "), 2)       # the INFRA retry and the final status recorder


class ArchiveTests(unittest.TestCase):
    def _run(self, mutate):
        d = Path(tempfile.mkdtemp())
        (d / "records").mkdir()
        (d / "archives").mkdir()
        arms = ("W0F",)
        bits, blocks = {}, []
        for t in C.SCORED:
            e = np.zeros(C.EVAL_PER_BLOCK, bool)
            e[:3] = True
            bits[f"b{t:02d}_W0F"] = np.packbits(e)
            blocks.append({"block": t, "errors": {"W0F": 3}})
        mutate(bits)
        np.savez_compressed(d / "archives" / "X_e0.npz", **bits)
        rec = {"schedule": "X", "episode": 0, "arms": list(arms), "eval_per_block": C.EVAL_PER_BLOCK,
               "blocks": blocks, "archive": "archives/X_e0.npz",
               "archive_sha256": hashlib.sha256((d / "archives" / "X_e0.npz").read_bytes()).hexdigest()}
        (d / "records" / "X_e0.json").write_text(json.dumps(rec), encoding="utf-8")
        (d / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "n_jobs": 1}), encoding="utf-8")
        return R.load_checked(d, {"X": 1}, arms)

    def test_good(self):
        self._run(lambda b: None)

    def test_bad(self):
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


class StatsTests(unittest.TestCase):
    def test_sign(self):
        self.assertEqual(R.sign_test_p([-1, -2, -3, 0, 0]), 1 / 8)
        self.assertEqual(R.sign_test_p([-1, 1]), 3 / 4)
        self.assertEqual(R.sign_test_p([0, 0]), 1.0)

    def test_cp(self):
        self.assertAlmostEqual(R.cp_upper(0, 48), 1 - 0.05 ** (1 / 48), places=6)
        self.assertGreater(R.cp_upper(1, 48), R.cp_upper(0, 48))


class SourceTests(unittest.TestCase):
    def test_no_seal(self):
        for p in PKG.glob("*.py"):
            s = p.read_text(encoding="utf-8")
            for bad in ("open_seal", "_SEALED", "re1_seal", "re2_seal", "HIDDEN_COMMITMENT", "R6_", "cf1/records"):
                self.assertNotIn(bad, s, p.name)

    def test_lf_only(self):
        for p in list(PKG.glob("*.py")) + list(PKG.glob("*.md")) + list((PKG / "tests").glob("*.py")):
            self.assertNotIn(b"\r\n", p.read_bytes(), p.name)


def _screened():
    import prepare_db6
    return prepare_db6.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        p = PKG / "DB6_SEEDS.json"
        if not p.exists():
            self.skipTest("seeds not written yet")
        s = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys()))
        v = set(s["seeds"].values())
        self.assertEqual(len(v), len(s["seeds"]))
        with get_context("spawn").Pool(1) as pool:
            self.assertFalse(v & pool.apply(_screened))


if __name__ == "__main__":
    unittest.main()
