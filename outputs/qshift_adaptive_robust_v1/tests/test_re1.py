"""RE1 build tests: seeds, seal pool rules, and the analysis decision logic on synthetic archives (no sampling)."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import prepare_re1  # noqa: E402
import re1  # noqa: E402
import re1_config as R  # noqa: E402
import re1_seal  # noqa: E402


class SeedTests(unittest.TestCase):
    def test_complete_disjoint_screened(self):
        s = json.loads((PKG / "RE1_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(R.all_keys()))
        self.assertEqual(set(s["rehearsal_seeds"]), set(R.rehearsal_keys()))
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(s["seeds"]))
        self.assertFalse(ev & rh)
        screened, _, _ = prepare_re1.screened()
        self.assertFalse((ev | rh) & screened)


class SealPoolTests(unittest.TestCase):
    def test_pool_excludes_near_and_rehearsal(self):
        pool = re1_seal.candidate_pool()
        self.assertGreater(len(pool), 1000)
        for s in pool:
            for n in re1_seal.NEAR.values():
                self.assertLess(len(set(s) & set(n)), 2)
        self.assertNotIn(re1_seal.rehearsal_support(), pool)

    def test_fresh_mismatch_values(self):
        import dev2_config as D
        used = {(kw.get("gate_p"), kw.get("bias_ratio") if kw.get("regime") == "z_biased" else None)
                for kw, _ in D.OG.values()} | {(kw.get("gate_p"), kw.get("bias_ratio") if kw.get("regime") == "z_biased" else None)
                                               for kw in D.E2E.values()}
        for c, (kw, _, gated, _) in R.CONDITIONS.items():
            if gated and c != "R5":
                key = (kw.get("gate_p"), kw.get("bias_ratio") if kw.get("regime") == "z_biased" else None)
                self.assertNotIn(key, used, c)


def _write_synthetic_run(run: Path, rates: dict, n=2000, seed=5, paired=False):
    """Synthetic records/archives for every condition and root; per-arm Bernoulli error bits."""
    rng = np.random.default_rng(seed)
    (run / "roots").mkdir(parents=True)
    (run / "archives").mkdir(parents=True)
    seeds = json.loads((PKG / "RE1_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    for c, (_, _, _, roots) in R.CONDITIONS.items():
        for r in range(roots):
            bits, per_q = {}, {}
            for qi, q in enumerate(R.QS):
                errs = {}
                drawn = {a: rng.random(n) < rates[a][qi] for a in R.ARMS}
                if paired:                              # exact learning: candidate predictions equal the oracle's
                    drawn["L2L_R"] = drawn["L2s_true"].copy()
                for a in R.ARMS:
                    bits[f"q{qi}_{a}"] = np.packbits(drawn[a])
                    errs[a] = int(drawn[a].sum())
                per_q[str(q)] = {"shots": n, "errors": errs}
            arc = run / "archives" / f"{c}_r{r:02d}.npz"
            np.savez_compressed(arc, **bits)
            rec = {"cond": c, "root": r, "seeds": {R.root_key(c, r, "eval", 0): seeds[R.root_key(c, r, "eval", 0)]},
                   "fit": {"p_hat": 0.003, "b_hat": 1.0, "flagged": False}, "learn_R": {"learned_correct": True},
                   "learn_N": {"learned_correct": False}, "s_star": "Astar_Nm", "per_q": per_q,
                   "archive": f"archives/{arc.name}", "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest()}
            (run / "roots" / f"{c}_r{r:02d}.json").write_text(json.dumps(rec), encoding="utf-8")
    (run / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "head": "x", "started": "s",
                                                     "finished": "f", "wall_seconds": 0, "n_jobs": 0}), encoding="utf-8")


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _rates(self, cand, sstar, oracle, q0=(0.0006, 0.001)):
        base = {a: (q0[1], 0.004, 0.004) for a in R.ARMS}
        base["L2L_R"] = (q0[0], cand, cand)
        base["L2s_true"] = (q0[0], oracle, oracle)
        base["Astar_Nm"] = (0.002, sstar, sstar)
        base["A_nominal"] = (q0[1], 0.01, 0.01)
        return base

    def test_confirmed_when_equal_to_oracle_and_better_than_matcher(self):
        _write_synthetic_run(self.tmp / "a", self._rates(0.001, 0.006, 0.001), paired=True)
        out = re1.analyze("eval", self.tmp / "a")
        self.assertEqual(out["overall_verdict"], "CONFIRMED", {c: v.get("status") for c, v in out["conditions"].items()})

    def test_not_confirmed_when_far_worse_than_oracle(self):
        _write_synthetic_run(self.tmp / "b", self._rates(0.004, 0.006, 0.001))
        out = re1.analyze("eval", self.tmp / "b")
        self.assertEqual(out["overall_verdict"], "NOT_CONFIRMED")

    def test_tamper_detected(self):
        _write_synthetic_run(self.tmp / "c", self._rates(0.001, 0.006, 0.001))
        p = self.tmp / "c" / "archives" / "R1_r00.npz"
        p.write_bytes(p.read_bytes() + b"x")
        with self.assertRaises(ValueError):
            re1.analyze("eval", self.tmp / "c")


if __name__ == "__main__":
    unittest.main()
