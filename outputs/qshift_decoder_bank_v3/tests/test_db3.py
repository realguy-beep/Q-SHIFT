"""DB3 tests: candidates, selection rule, panels, predicted table, replay validity, source causality, seeds,
LF-only files and no seal. No sampling."""
from __future__ import annotations

import json
import sys
import unittest
from multiprocessing import get_context
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import db3_config as C  # noqa: E402
import db2_core as G  # noqa: E402
import db3_core as K  # noqa: E402

RISK = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["risk"]


class CandidateTests(unittest.TestCase):
    def test_candidates_are_db2_values(self):
        self.assertEqual(C.CANDIDATES["W0"], ("worst", 0.0))
        self.assertEqual(C.CANDIDATES["DB2_PLAN"], ("worst", C.C2.KAPPA_PLAN))
        self.assertEqual(C.CANDIDATES["DB2"], ("hybrid", C.C2.KAPPA_DB2))
        self.assertEqual((C.C2.HAZ_A0, C.C2.HAZ_B0, C.C2.DEST_ALPHA), (1.0, 29.0, 0.25))
        self.assertEqual(C.SIMPLICITY, ("W0", "DB2_PLAN", "DB2"))
        self.assertEqual(C.MARGIN, 12)

    def test_w0_leaves_A_in_off_where_plan_holds(self):
        t = G.Tracker()
        for _ in range(9):
            t.observe(["OFF"], False)
            t.commit(["OFF"])
        self.assertNotEqual(G.gate(["OFF"], RISK, t, "A", *C.CANDIDATES["W0"]), "A")
        self.assertEqual(G.gate(["OFF"], RISK, t, "A", *C.CANDIDATES["DB2_PLAN"]), "A")


class SelectionTests(unittest.TestCase):
    E = {"W0": True, "DB2_PLAN": True, "DB2": True}

    def test_lowest_wins(self):
        self.assertEqual(K.select({"W0": 250, "DB2_PLAN": 230, "DB2": 200}, self.E), "DB2")

    def test_simpler_within_margin(self):
        self.assertEqual(K.select({"W0": 211, "DB2_PLAN": 205, "DB2": 200}, self.E), "W0")
        self.assertEqual(K.select({"W0": 212.5, "DB2_PLAN": 205, "DB2": 200}, self.E), "DB2_PLAN")
        self.assertEqual(K.select({"W0": 212, "DB2_PLAN": 212, "DB2": 200}, self.E), "W0")

    def test_ineligible_excluded(self):
        self.assertEqual(K.select({"W0": 100, "DB2_PLAN": 230, "DB2": 200}, {**self.E, "W0": False}), "DB2")
        self.assertIsNone(K.select({"W0": 1, "DB2_PLAN": 1, "DB2": 1}, {k: False for k in self.E}))


class PanelTests(unittest.TestCase):
    def test_panels(self):
        for e in range(60):
            for s, (x, y) in C.TWO.items():
                p = C.episode_params(s, e, 700 + e)
                ch = C.changes(s, p)
                self.assertIn(ch[0], (6, 7))
                self.assertEqual([C.block_state(s, c, p) for c in ch], [x, "OFF", y, "OFF"])
                self.assertTrue(all(4 <= b - a <= 5 for a, b in zip(ch, ch[1:])))
                self.assertEqual(len(ch), 4)
        self.assertEqual({C.block_state("N_OFF", t, {}) for t in range(30)}, {"OFF"})
        self.assertEqual({C.block_state("N_C", t, {}) for t in range(30)}, {"C"})
        self.assertEqual(C.changes("N_OFF", {}), [])
        self.assertEqual(sum(C.EPISODES.values()), 18)

    def test_predicted_table(self):
        import design_feasibility as F

        def two(x, y):
            return ["OFF"] * 6 + [x] * 4 + ["OFF"] * 5 + [y] * 4 + ["OFF"] * 11
        S = {"N_OFF": ["OFF"] * 30, "N_C": ["C"] * 30, "AA": two("A", "A"), "BB": two("B", "B"),
             "AB": two("A", "B"), "BA": two("B", "A")}
        exp = {"W0": {"N_OFF": 12.8, "N_C": 24.0, "AA": 28.8, "BB": 48.8, "AB": 38.8, "BA": 38.8},
               "DB2_PLAN": {"N_OFF": 28.8, "N_C": 33.6, "AA": 28.8, "BB": 48.8, "AB": 38.8, "BA": 38.8},
               "DB2": {"N_OFF": 12.8, "N_C": 24.0, "AA": 28.8, "BB": 24.6, "AB": 38.8, "BA": 83.0}}
        tot = {}
        for c, (mode, kap) in C.CANDIDATES.items():
            for s, st in S.items():
                self.assertAlmostEqual(F.cost(st, F.policy(st, mode, kap, 6)), exp[c][s], places=1, msg=(c, s))
            tot[c] = sum(F.cost(st, F.policy(st, mode, kap, 6)) for st in S.values())
        self.assertEqual(K.select(tot, {c: True for c in tot}), "W0")


class ReplayTests(unittest.TestCase):
    def test_replay_reproduces_db2_arms(self):
        recs = [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted((C.DB2 / "results" / "dev" / "records").glob("*.json"))]
        self.assertEqual(len(recs), 23)
        for arm in ("DB2", "DB2_PLAN"):
            for r in recs:
                self.assertEqual([k for k, _ in K.replay(r, RISK, *C.CANDIDATES[arm])],
                                 [b["keys"][arm] for b in r["blocks"]], (arm, r["schedule"], r["episode"]))


class SourceTests(unittest.TestCase):
    src = (PKG / "db3_run.py").read_text(encoding="utf-8")

    def test_causal(self):
        s = self.src
        self.assertLess(s.index("u = t - 1"), s.index("x, y = D.sample(truth(t), nrow, sd)"))
        self.assertLess(s.index("trk.observe(P, alarm)"), s.index("G.gate(P, risk, trk, name(prev[arm]), gm, kap)"))
        self.assertLess(s.index("trk.commit(P)"), s.index('x, y = D.sample(st_t, n_eval, seed(t, "eval"))'))
        self.assertIn("kseg, nseg = ad3.pool(cnt[lo:t])", s)
        self.assertNotIn('b["state"]', s.split("def episode_job")[1].split("def cmd_fidelity")[0])

    def test_loop_matches_db2(self):
        """The per-block loop is DB2's with only the W0 arm generalisation."""
        d2 = (C.DB2 / "db2_run.py").read_text(encoding="utf-8")
        a = d2[d2.index("def episode_job"):d2.index("        k2 = G.gate(")]
        b = self.src[self.src.index("def episode_job"):self.src.index("        kn_arm = ")]
        self.assertEqual(a.replace('("BANK", "DB2", "DB2_PLAN")', "C.BANK_ARMS"), b)
        a2 = d2[d2.index("        est_s += time.perf_counter() - te"):d2.index("# ------------------------------------------------------------------ fidelity")]
        b2 = self.src[self.src.index("        est_s += time.perf_counter() - te"):self.src.index("# ------------------------------------------------------------------ fidelity")]
        self.assertEqual(a2.split("arm_key = ")[1].split("\n", 2)[2], b2.split("arm_key = ")[1].split("\n", 1)[1])

    def test_no_seal(self):
        for p in PKG.glob("*.py"):
            s = p.read_text(encoding="utf-8")
            for bad in ("open_seal", "_SEALED", "re1_seal", "re2_seal", "HIDDEN_COMMITMENT", "R6_"):
                self.assertNotIn(bad, s, p.name)

    def test_lf_only(self):
        for p in list(PKG.glob("*.py")) + list(PKG.glob("*.md")) + list((PKG / "tests").glob("*.py")):
            self.assertNotIn(b"\r\n", p.read_bytes(), p.name)


def _screened():
    import prepare_db3
    return prepare_db3.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        p = PKG / "DB3_SEEDS.json"
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
