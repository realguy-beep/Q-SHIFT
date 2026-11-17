"""Phase A tests for the d=5 learner (numpy DEM draws only; no Stim sampler calls)."""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import learner_d5 as LD  # noqa: E402
from learner_d5 import L, m, dem_mechanisms  # noqa: E402

D3 = m.CodeSpec()
D5 = m.CodeSpec(distance=5, gate_p=0.003, measurement_p=0.003)


def draw(dem, shots, seed):
    rng = np.random.default_rng(seed)
    x = np.zeros((shots, dem.num_detectors), dtype=np.uint8)
    y = np.zeros(shots, dtype=np.uint8)
    for mm in dem_mechanisms(dem):
        fire = rng.random(shots) < mm.p
        if mm.detectors:
            x[np.ix_(fire, list(mm.detectors))] ^= 1
        if mm.logical:
            y[fire] ^= 1
    return x, y


class D3EquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classes = L.signature_classes(D3)
        cls.slow = L.ParityLearner(cls.classes, L.base_dem(D3), 11.57)
        cls.fast = LD.FastParityLearner(cls.classes, L.base_dem(D3), 11.57)

    def test_counts_match_v1_6(self):
        self.assertEqual(len(self.classes), 15)
        self.assertEqual(sum(len(c.supports_flip0) + len(c.supports_flip1) for c in self.classes), 119)

    def test_threshold_rule_reproduces_v1_6b(self):
        self.assertAlmostEqual(LD.threshold(15), 11.58, places=2)

    def test_construction_identical(self):
        self.assertEqual(self.fast.subsets, self.slow.subsets)
        np.testing.assert_allclose(self.fast.base_log, self.slow.base_log, rtol=0, atol=1e-12)
        np.testing.assert_array_equal(self.fast.n, self.slow.n)

    def test_selection_identical(self):
        idx = next(i for i, c in enumerate(self.classes) if (8, 12, 15) in c.supports_flip0)
        for dem, seed in ((L.class_dem(D3, self.classes[idx], 0, 0.02), 1), (L.base_dem(D3), 2),
                          (L.class_dem(D3, self.classes[3], 1, 0.01), 3)):
            x, _ = draw(dem, 8000, seed)
            a, b = self.slow.select(x), self.fast.select(x)
            self.assertEqual(a["class_index"], b["class_index"])
            self.assertAlmostEqual(a["q_hat"], b["q_hat"], places=12)
            self.assertAlmostEqual(a["delta"], b["delta"], places=6)


class D5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = json.loads((PKG / "CLASSES_D5.json").read_text(encoding="utf-8"))
        cls.classes = L.signature_classes(D5)
        cls.fast = LD.FastParityLearner(cls.classes, L.base_dem(D5), LD.threshold(len(cls.classes)))

    def test_class_record_deterministic(self):
        rec = LD.classes_record(D5)
        self.assertEqual(rec["classes_sha256"], self.rec["classes_sha256"])
        self.assertEqual((rec["n_classes"], rec["n_supports"], rec["n_mixed_classes"]), (1003, 2621, 86))

    def test_base_log_matches_direct_formula_on_sample(self):
        mechs = dem_mechanisms(L.base_dem(D5))
        rng = np.random.default_rng(0)
        for i in rng.choice(len(self.fast.subsets), 25, replace=False):
            a = set(self.fast.subsets[i])
            direct = sum(math.log1p(-2 * mm.p) for mm in mechs if len(set(mm.detectors) & a) % 2)
            self.assertAlmostEqual(self.fast.base_log[i], direct, places=10)
            c = rng.integers(len(self.classes))
            self.assertEqual(self.fast.n[c, i], sum(len(set(s) & a) % 2 for s in self.classes[c].events))

    def test_recovers_known_scaled_v1_class(self):
        k = self.rec["known_families"]["scaled_v1"]
        x, _ = draw(LD.hyper_dem(D5, 0.02, tuple(k["support"])), 12000, 5)
        out = self.fast.select(x)
        self.assertEqual(out["class_index"], k["class_index"])
        self.assertLess(abs(out["q_hat"] - 0.02), 0.006)

    def test_pure_class_flip_needs_no_labels(self):
        c = self.classes[self.rec["known_families"]["centre_row"]["class_index"]]
        self.assertEqual(LD.learn_flip(D5, c, np.zeros((1, 120), np.uint8), np.zeros(1))["method"], "pure_class")

    def test_mixed_class_flip_recovered_by_l2(self):
        idx = next(i for i, c in enumerate(self.classes) if c.supports_flip0 and c.supports_flip1
                   and len(c.events[0]) >= 2)
        c = self.classes[idx]
        for true_flip in (0, 1):
            x, y = draw(LD.hyper_dem(D5, 0.02, c.representative(true_flip)), 600, 20 + true_flip)
            out = LD.learn_flip(D5, c, x, y)
            self.assertEqual(out["flip"], true_flip, out)


if __name__ == "__main__":
    unittest.main()
