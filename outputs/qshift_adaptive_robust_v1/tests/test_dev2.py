"""OG/E2E build tests. Synthetic Bernoulli draws from model rate vectors only; no study samples."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import dev2_config as D  # noqa: E402
import dev2  # noqa: E402
import estimate2 as E  # noqa: E402
import prepare_dev2  # noqa: E402


def synth(p, b, regime="z_biased", n=12_000, seed=7):
    from outputs.qshift_correlated_decoder_v1_6 import learner as L
    import he1 as H
    spec = D.spec(gate_p=p, measurement_p=p, regime=regime, bias_ratio=b)
    r = H.detector_rates(L.base_dem(spec))
    return (np.random.default_rng(seed).random((n, len(r))) < r).astype(np.uint8)


class SeedTests(unittest.TestCase):
    def test_complete_disjoint_screened(self):
        s = json.loads((PKG / "DEV2_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(D.all_keys()))
        self.assertEqual(set(s["rehearsal_seeds"]), set(D.rehearsal_keys()))
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(s["seeds"]))
        self.assertFalse(ev & rh)
        screened, _, _ = prepare_dev2.screened()
        self.assertFalse((ev | rh) & screened)


class ConfigTests(unittest.TestCase):
    def test_in_family_values_are_off_grid(self):
        import he1b as HB
        lp = np.log(HB.P_GRID)
        step = lp[1] - lp[0]
        for c, (kw, fam) in D.OG.items():
            if not fam:
                continue
            if "p" in D.OFF_GRID[c]:
                d = np.min(np.abs(lp - np.log(kw["gate_p"]))) / step
                self.assertGreaterEqual(d, 0.3, (c, "p", d))
            if "b" in D.OFF_GRID[c]:
                self.assertNotIn(kw["bias_ratio"], HB.B_GRID, c)
        self.assertEqual(set(D.OFF_GRID), {c for c, (_, fam) in D.OG.items() if fam})

    def test_flag_threshold_recorded(self):
        self.assertGreater(E.flag_threshold(), 0)


class EstimatorTests(unittest.TestCase):
    def test_b2_recovers_off_grid_in_family(self):
        for p, b in ((0.0027, 6.0), (0.0033, 1.0), (0.003, 12.0)):
            f = E.fit_b2(synth(p, b))
            # 3%: with 12k rows p and b trade off along a flat ridge; on (0.0027, 6) seeds 7-10 the estimate's
            # objective is BELOW the truth's, so the ~2% p error is sampling noise, not an optimiser failure.
            self.assertAlmostEqual(f["p_hat"] / p, 1.0, delta=0.03, msg=(p, b, f))
            x = synth(p, b)
            n = len(x)
            obs = np.maximum(x.mean(axis=0), 0.5 / n)
            self.assertLessEqual(f["objective"], E.objective(np.log(obs), n * obs, p, b) + 1e-6)
            self.assertAlmostEqual(np.log(f["b_hat"] / b), 0.0, delta=0.25, msg=(p, b, f))
            self.assertLessEqual(f["objective"], f["obj_grid"] + 1e-9)
            self.assertFalse(f["flagged"], (p, b, f))

    def test_mcnemar(self):
        self.assertAlmostEqual(dev2.mcnemar_less(0, 10), 2 ** -10)
        self.assertEqual(dev2.mcnemar_less(0, 0), 1.0)
        self.assertGreater(dev2.mcnemar_less(10, 0), 0.99)


if __name__ == "__main__":
    unittest.main()
