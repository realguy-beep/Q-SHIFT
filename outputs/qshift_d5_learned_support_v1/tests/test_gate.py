"""Phase B contract tests (no sampling)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import contract as K  # noqa: E402
import prepare_dev_seeds  # noqa: E402
from learner_d5 import dem_mechanisms  # noqa: E402
import learner_d5 as LD  # noqa: E402


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classes = K.load_classes()

    def test_bursts_classes_and_flips(self):
        want = {"SC": (790, 0, False), "CR": (901, 0, False), "M0": (213, 0, True), "M1": (223, 1, True)}
        for b, (idx, flip, mixed) in want.items():
            self.assertEqual(K.truth(self.classes, K.BURSTS[b]), (idx, flip))
            c = self.classes[idx]
            self.assertEqual(bool(c.supports_flip0 and c.supports_flip1), mixed)
            if mixed:
                self.assertNotEqual(c.min_weight_flip(), flip)

    def test_mixed_burst_rule(self):
        for flip, b in ((0, "M0"), (1, "M1")):
            first = next(i for i, c in enumerate(self.classes) if c.supports_flip0 and c.supports_flip1
                         and any(len(s) == 3 for s in (c.supports_flip0 if flip == 0 else c.supports_flip1)))
            pool = self.classes[first].supports_flip0 if flip == 0 else self.classes[first].supports_flip1
            self.assertEqual(min(s for s in pool if len(s) == 3), K.BURSTS[b])

    def test_cr_representative_same_burst_mechanisms(self):
        c = self.classes[901]
        def mech(s):
            return sorted((x.detectors, x.logical, round(x.p, 15)) for x in dem_mechanisms(LD.hyper_dem(K.SPEC, 0.01, s)))
        self.assertEqual(mech(c.representative(0)), mech(K.BURSTS["CR"]))

    def test_threshold(self):
        self.assertAlmostEqual(K.threshold(self.classes), 19.517, places=3)


class SeedTests(unittest.TestCase):
    def test_complete_disjoint_screened(self):
        s = json.loads((PKG / "DEV_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(K.all_keys()))
        self.assertEqual(set(s["rehearsal_seeds"]), set(K.all_keys(K.REHEARSAL_POOLS)))
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), 312)
        self.assertFalse(ev & rh)
        screened, _ = prepare_dev_seeds.screened_values()
        self.assertIn(1, screened)
        self.assertFalse((ev | rh) & screened)


if __name__ == "__main__":
    unittest.main()
