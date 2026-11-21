"""DB1 tests: fit statistic, identification, risk gate, hysteresis, correctness rule, schedules, events, criteria,
seeds and causality. No sampling; no seal is read."""
from __future__ import annotations

import json
import sys
import unittest
from multiprocessing import get_context
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import db_config as C  # noqa: E402
import db_core as D  # noqa: E402
import db_run as R  # noqa: E402

TAU = {str(L): 150.0 for L in range(1, 7)}
RISK = {"OFF": {"OFF": .002, "A": .003, "B": .004, "C": .004, "D": .004},
        "A": {"OFF": .030, "A": .002, "B": .030, "C": .030, "D": .030},
        "B": {"OFF": .030, "A": .030, "B": .002, "C": .030, "D": .030},
        "C": {"OFF": .030, "A": .030, "B": .030, "C": .002, "D": .030},
        "D": {"OFF": .030, "A": .030, "B": .030, "C": .030, "D": .002}}


def G(**kw):
    g = {s: 999.0 for s in C.STATES}
    g.update(kw)
    return g


class FitTests(unittest.TestCase):
    def test_g_fit(self):
        p = np.full(120, 0.03)
        k = np.full(120, 60)
        self.assertAlmostEqual(D.g_fit(k, 2000, p), 0.0, places=6)
        self.assertGreater(D.g_fit(k + 20, 2000, p), 0.0)
        r = np.random.default_rng(3)
        x = (r.random((2000, 120)) < 0.03).astype(np.uint8)
        g = D.g_fit(*D.counts(x), p)
        self.assertTrue(60 < g < 200, g)                 # about chi2 with 120 dof

    def test_template(self):
        self.assertTrue(np.allclose(D.template(np.array([0, 10]), 9), [0.05, 1.05]))


class DecisionTests(unittest.TestCase):
    def test_unknown(self):
        self.assertEqual(D.bank_decide(G(), 1, TAU, RISK, "OFF"), (None, []))
        self.assertEqual(D.id_decide(G(), 1, TAU)[0], None)

    def test_single(self):
        self.assertEqual(D.bank_decide(G(B=100.0), 1, TAU, RISK, "OFF")[0], "B")
        self.assertEqual(D.id_decide(G(B=100.0), 1, TAU)[0], "B")

    def test_ambiguous_off_vs_on_picks_burst_key(self):
        # OFF data decoded with A's key costs little; A data with OFF's key costs a lot -> worst-case picks A
        k, P = D.bank_decide(G(OFF=120.0, A=140.0), 1, TAU, RISK, "OFF")
        self.assertEqual(sorted(P), ["A", "OFF"])
        self.assertEqual(k, "A")
        self.assertEqual(D.id_decide(G(OFF=120.0, A=140.0), 1, TAU)[0], "OFF")   # the ablation picks best fit

    def test_hysteresis(self):
        risk = {s: dict(v) for s, v in RISK.items()}
        risk["OFF"]["A"] = 0.0024
        self.assertEqual(D.bank_decide(G(OFF=100.0), 1, TAU, risk, "A")[0], "A")    # 0.0024 <= 0.002 + 0.0005
        risk["OFF"]["A"] = 0.0026
        self.assertEqual(D.bank_decide(G(OFF=100.0), 1, TAU, risk, "A")[0], "OFF")

    def test_correctness_rule(self):
        import mm_contract as K
        classes = K.B.load_classes()
        self.assertTrue(D.acceptable(None, "OFF", classes))
        self.assertFalse(D.acceptable(None, "A", classes))
        self.assertTrue(D.acceptable(C.support("A"), "A", classes))
        self.assertFalse(D.acceptable(C.support("A"), "B", classes))
        self.assertFalse(D.acceptable(C.support("A"), "OFF", classes))


class ScheduleTests(unittest.TestCase):
    def test_unknown_burst(self):
        self.assertEqual(C.UNKNOWN["label"], "W06")
        self.assertNotIn(C.UNKNOWN["label"], [v["label"] for v in C.BURSTS.values()])
        self.assertNotIn("E", C.STATES)

    def test_schedules(self):
        for e in range(50):
            p = C.episode_params("R", e, 1000 + e)
            ch = C.changes("R", p)
            self.assertEqual(len(ch), 4)
            self.assertIn(ch[0], (6, 7))
            self.assertTrue(all(4 <= b - a <= 5 for a, b in zip(ch, ch[1:])))
            self.assertEqual([C.block_state("R", c, p) for c in ch], ["A", "OFF", "A", "OFF"])
            u = C.episode_params("U", e, 2000 + e)
            self.assertTrue(8 <= u["onset"] <= 12)
            self.assertIn(C.episode_params("N", e, 3000 + e)["state"], C.STATES)
        self.assertEqual(C.changes("S4", {}), [10, 20])
        self.assertEqual(C.changes("C0", {}), [])

    def test_events(self):
        states = ["OFF"] * 6 + ["A"] * 5 + ["OFF"] * 5 + ["A"] * 4 + ["OFF"] * 10
        blocks = [{"block": t, "acceptable": {a: (t >= 7 and states[t] == "A") or (t >= 12 and states[t] == "OFF")
                                              for a in R.EVENT_ARMS}} for t in C.SCORED]
        evs = R.events({"states": states, "true_changes": [6, 11, 16, 20], "blocks": blocks})
        self.assertEqual([e["type"] for e in evs], ["first_on", "off", "recurrent_on", "off"])
        self.assertEqual([e["delay"]["BANK"] for e in evs], [1, 1, 0, 0])


class SourceTests(unittest.TestCase):
    src = (PKG / "db_run.py").read_text(encoding="utf-8")

    def test_causal(self):
        s = self.src
        self.assertLess(s.index("u = t - 1"), s.index("x, y = D.sample(truth(t), nrow, sd)"))
        self.assertIn("ad2.estimate(dets[w0:t], labx[w0:t], laby[w0:t]", s)
        self.assertIn("kseg, nseg = ad3.pool(cnt[lo:t])", s)
        self.assertLess(s.index("D.bank_decide("), s.index('x, y = D.sample(st_t, n_eval, seed(t, "eval"))'))
        self.assertIn("for k in dict.fromkeys(arm_key.values())", s)

    def test_no_seal(self):
        for n in ("db_run.py", "db_core.py", "db_config.py", "db_train.py", "prepare_db1.py"):
            s = (PKG / n).read_text(encoding="utf-8")
            for bad in ("open_seal", "_SEALED", "re1_seal", "re2_seal", "HIDDEN_COMMITMENT"):
                self.assertNotIn(bad, s, n)

    def test_lf_only(self):
        for p in PKG.glob("*.py"):
            self.assertNotIn(b"\r\n", p.read_bytes(), p.name)


def _screened():
    import prepare_db1
    return prepare_db1.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        s = json.loads((PKG / "DB1_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys()))
        self.assertEqual(set(s["train_seeds"]), set(C.train_keys()))
        a, b = set(s["seeds"].values()), set(s["train_seeds"].values())
        self.assertEqual(len(a) + len(b), len(a | b))
        with get_context("spawn").Pool(1) as pool:
            self.assertFalse((a | b) & pool.apply(_screened))


if __name__ == "__main__":
    unittest.main()
