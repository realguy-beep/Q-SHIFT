"""DB2 tests: reduction to DB1, break-even hazard, tracker causality, gate modes, schedules, feasibility table,
source causality, seeds, LF-only files and no seal. No sampling."""
from __future__ import annotations

import json
import sys
import unittest
from multiprocessing import get_context
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import db2_config as C  # noqa: E402
import db2_core as G  # noqa: E402
import db_core as D  # noqa: E402

RISK = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["risk"]
TAU = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["tau_fit"]


class GateTests(unittest.TestCase):
    def test_reduces_to_db1_at_h0(self):
        rng = np.random.default_rng(7)
        for _ in range(400):
            gf = {s: float(rng.uniform(150, 260)) for s in C.STATES}
            L = int(rng.integers(1, 7))
            prev = C.STATES[int(rng.integers(0, 5))]
            kb, P = D.bank_decide(gf, L, TAU, RISK, prev)
            for mode in ("worst", "hybrid"):
                self.assertEqual(G.gate(P, RISK, G.Tracker(), prev, mode, C.KAPPA_PLAN, hazard=0.0), kb)

    def test_break_even(self):
        w = max(RISK[d]["A"] for d in C.STATES if d != "OFF")
        o = max(RISK[d]["OFF"] for d in C.STATES if d != "OFF")
        dO = RISK["OFF"]["A"] - RISK["OFF"]["OFF"]
        be = dO / (dO + o - w)
        self.assertAlmostEqual(be, 0.02577, places=4)
        t = G.Tracker()
        self.assertEqual(G.gate(["OFF"], RISK, t, "A", "worst", 0.0, hazard=be + 0.002), "A")
        self.assertNotEqual(G.gate(["OFF"], RISK, t, "A", "worst", 0.0, hazard=be - 0.002), "A")

    def test_prior_hazard_and_decay(self):
        t = G.Tracker()
        self.assertAlmostEqual(t.hazard("OFF"), 1 / 30)
        for _ in range(9):
            t.observe(["OFF"], False)
            t.commit(["OFF"])
        self.assertAlmostEqual(t.hazard("OFF"), 1 / 39)
        self.assertNotEqual(G.gate(["OFF"], RISK, t, "A", "hybrid", 0.0), "A")     # 1/39 < break-even

    def test_tracker_counts_change_only_after_alarm(self):
        t = G.Tracker()
        t.observe(["OFF"], False); t.commit(["OFF"])
        t.observe(["A"], False); t.commit(["A"])          # identity drift without an alarm: not a change
        self.assertEqual(t.outs["OFF"], [])
        t.observe(["A", "OFF"], True); t.commit(["A", "OFF"])   # alarm, ambiguous: pending
        self.assertEqual(t.outs["A"], [])
        t.observe(["OFF"], False); t.commit(["OFF"])      # first singleton after the alarm -> A -> OFF
        self.assertEqual(t.outs["A"], ["OFF"])
        t.observe(["OFF"], True); t.commit(["OFF"])       # false alarm: same identity, no change
        self.assertEqual(t.outs["OFF"], [])
        self.assertEqual(t.occ["OFF"], 3)

    def test_hybrid_learns_destination(self):
        t = G.Tracker()
        t.outs["OFF"] = ["B", "B"]
        t.occ["OFF"] = 5
        self.assertEqual(G.gate(["OFF"], RISK, t, "A", "hybrid", 0.0), "B")      # B recurs: hold B, not A
        self.assertEqual(G.gate(["OFF"], RISK, t, "A", "worst", 0.0), "A")       # approved rule holds A
        t.outs["OFF"] = ["A"]
        self.assertEqual(G.gate(["OFF"], RISK, t, "OFF", "hybrid", 0.0), "A")    # A recurs: hold A

    def test_unknown(self):
        self.assertIsNone(G.gate([], RISK, G.Tracker(), "A", "hybrid", 0.0))


class ScheduleTests(unittest.TestCase):
    def test_schedules(self):
        for e in range(60):
            for s, seq in (("R", ["A", "OFF", "A", "OFF"]), ("RB", ["B", "OFF", "B", "OFF"]),
                           ("R_long", ["A", "OFF"]), ("RX", ["A", "OFF", "B", "OFF", "A", "OFF"])):
                p = C.episode_params(s, e, 500 + e)
                ch = C.changes(s, p)
                self.assertIn(ch[0], (6, 7))
                self.assertEqual([C.block_state(s, c, p) for c in ch], seq[:len(ch)])
                self.assertTrue(all(4 <= b - a <= 5 for a, b in zip(ch, ch[1:])))
            self.assertGreaterEqual(len(C.changes("RX", C.episode_params("RX", e, 900 + e))), 5)
        self.assertEqual(C.changes("S4", {}), [10, 20])
        self.assertEqual(sum(C.EPISODES.values()), 23)

    def test_feasibility_table(self):
        import design_feasibility as F
        exp = {"R": 28.8, "R_long": 28.8, "RX": 38.8, "RB": 24.6, "S1": 42.0, "S4": 35.6, "N_OFF": 12.8, "C0": 28.8}
        for s, v in exp.items():
            self.assertAlmostEqual(F.cost(F.S[s], F.policy(F.S[s], "hybrid", 0.0, 6)), v, places=1)


class SourceTests(unittest.TestCase):
    src = (PKG / "db2_run.py").read_text(encoding="utf-8")

    def test_causal(self):
        s = self.src
        self.assertLess(s.index("u = t - 1"), s.index("x, y = D.sample(truth(t), nrow, sd)"))
        self.assertLess(s.index("trk.observe(P, alarm)"), s.index("k2 = G.gate("))
        self.assertLess(s.index("trk.commit(P)"), s.index('x, y = D.sample(st_t, n_eval, seed(t, "eval"))'))
        self.assertIn("kseg, nseg = ad3.pool(cnt[lo:t])", s)
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
    import prepare_db2
    return prepare_db2.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        p = PKG / "DB2_SEEDS.json"
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
