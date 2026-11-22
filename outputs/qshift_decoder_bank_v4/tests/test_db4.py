"""DB4 tests: the fallback truth table, W0F = W0 off the unknown path, the seen-data replay table, loop identity
with DB3, panels, causality, seeds, LF-only files and no seal. No sampling."""
from __future__ import annotations

import json
import sys
import unittest
from multiprocessing import get_context
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import db4_config as C  # noqa: E402
import db4_core as F  # noqa: E402

RISK = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["risk"]


def _recs():
    out = []
    for d in (C.DB2, C.DB3):
        out += [(d.name, json.loads(p.read_text(encoding="utf-8")))
                for p in sorted((d / "results" / "dev" / "records").glob("*.json"))]
    return out


class FallbackTests(unittest.TestCase):
    def test_truth_table(self):
        ad = '["est", 0.003, 1.0, [20]]'
        cases = [({"flagged": False, "class_index": 747}, (ad, "learn")),
                 ({"flagged": False, "class_index": None}, ("bank:A", "static_fallback")),
                 ({"flagged": True, "class_index": 747}, ("bank:A", "static_fallback")),
                 ({"flagged": True, "class_index": None}, ("bank:A", "static_fallback"))]
        for est, exp in cases:
            self.assertEqual(F.fallback_key(None, est, ad, "bank:OFF", "A"), exp, est)

    def test_known_P_unchanged(self):
        for est in ({"flagged": True, "class_index": None}, {"flagged": False, "class_index": 3}):
            self.assertEqual(F.fallback_key("C", est, "x", "bank:A", "A"), ("bank:C", "bank"))

    def test_config(self):
        self.assertEqual(C.CANDIDATES["W0F"], ("worst", 0.0))
        self.assertEqual(C.FALLBACK_ARMS, ("W0F",))
        self.assertEqual(sum(C.EPISODES.values()), 21)
        self.assertEqual(set(C.ARMS) - set(C.C3.ARMS), {"W0F"})


class ReplayTests(unittest.TestCase):
    """PLAN_DB4.md table: exact replay on DB2's and DB3's 41 stored episodes."""

    @classmethod
    def setUpClass(cls):
        cls.rows = []
        for d, r in _recs():
            base = F.replay(r, RISK, "worst", 0.0, fallback=False)
            fb = F.replay(r, RISK, "worst", 0.0, fallback=True)
            cls.rows.append((d, r, base, fb))

    def test_exact_and_reproduces_records(self):
        self.assertEqual(len(self.rows), 41)
        for d, r, base, fb in self.rows:
            self.assertNotIn(None, [x for _, x, _ in base] + [x for _, x, _ in fb])
            if "W0" in r["blocks"][0]["keys"]:
                self.assertEqual([k for k, _, _ in base], [b["keys"]["W0"] for b in r["blocks"]])

    def test_table(self):
        tot_b = sum(x for *_, base, _ in self.rows for _, x, _ in base)
        tot_f = sum(x for *_, fb in self.rows for _, x, _ in fb)
        self.assertEqual((tot_b, tot_f), (1667, 1570))
        aa = [(sum(x for _, x, _ in base), sum(x for _, x, _ in fb)) for d, r, base, fb in self.rows
              if d.endswith("v3") and r["schedule"] == "AA"]
        self.assertEqual(aa, [(40, 40), (132, 35)])
        self.assertEqual(sum(t for *_, fb in self.rows for _, _, t in fb), 10)
        for d, r, base, fb in self.rows:
            if r["schedule"] != "AA" or not d.endswith("v3"):
                self.assertLessEqual(sum(x for _, x, _ in fb) - sum(x for _, x, _ in base), 0, (d, r["schedule"]))
        a1 = next(fb for d, r, base, fb in self.rows if d.endswith("v3") and r["schedule"] == "AA" and r["episode"] == 1)
        self.assertEqual([b for b, (_, _, t) in zip(range(6, 30), a1) if t], [8, 9, 12, 17])


class PanelTests(unittest.TestCase):
    def test_panels(self):
        p = C.episode_params("U", 0, 11)
        self.assertIn(p["onset"], range(8, 13))
        self.assertEqual(C.block_state("U", p["onset"], p), "E")
        self.assertEqual(C.changes("S4", {}), [10, 20])
        self.assertEqual(C.changes("S1", {}), [15])
        for s in C.C3.TWO:
            p = C.episode_params(s, 0, 5)
            self.assertEqual(len(C.changes(s, p)), 4)
        self.assertEqual(C.changes("N_C", {}), [])


class SourceTests(unittest.TestCase):
    src = (PKG / "db4_run.py").read_text(encoding="utf-8")

    def test_loop_is_db3_plus_fallback(self):
        d3 = (C.DB3 / "db3_run.py").read_text(encoding="utf-8")
        cut = lambda s: s[s.index("def _bank_arm"):s.index("# ------------------------------------------------------------------ fidelity")]  # noqa: E731
        old = "            keys[arm], srcs[arm] = _bank_arm(kn, est, k_ad, prev[arm])"
        new = ("            keys[arm], srcs[arm] = F.fallback_key(kn, est, k_ad, prev[arm], static) if arm in C.FALLBACK_ARMS \\\n"
               "                else _bank_arm(kn, est, k_ad, prev[arm])")
        self.assertEqual(cut(d3).replace(old, new).rstrip("\n"), cut(self.src).rstrip("\n"))

    def test_causal(self):
        s = self.src
        self.assertLess(s.index("u = t - 1"), s.index("x, y = D.sample(truth(t), nrow, sd)"))
        self.assertLess(s.index("trk.commit(P)"), s.index('x, y = D.sample(st_t, n_eval, seed(t, "eval"))'))
        self.assertNotIn('b["state"]', s.split("def episode_job")[1].split("def cmd_fidelity")[0])

    def test_no_seal(self):
        for p in PKG.glob("*.py"):
            s = p.read_text(encoding="utf-8")
            for bad in ("open_seal", "_SEALED", "re1_seal", "re2_seal", "HIDDEN_COMMITMENT", "R6_"):
                self.assertNotIn(bad, s, p.name)

    def test_lf_only(self):
        for p in list(PKG.glob("*.py")) + list(PKG.glob("*.md")) + list((PKG / "tests").glob("*.py")):
            self.assertNotIn(b"\r\n", p.read_bytes(), p.name)


def _screened():
    import prepare_db4
    return prepare_db4.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        p = PKG / "DB4_SEEDS.json"
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
