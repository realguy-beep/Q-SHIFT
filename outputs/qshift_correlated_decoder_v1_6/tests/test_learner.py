from __future__ import annotations

import itertools
import math
import unittest

import numpy as np
import stim

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
from outputs.qshift_correlated_decoder_v1_6 import learner as L
from outputs.qshift_v1_4b_decoder_optimality.mld import dem_mechanisms

SPEC = m.CodeSpec()
CLASSES = L.signature_classes()
KNOWN = (8, 12, 15)


def known_class_index() -> int:
    return next(i for i, c in enumerate(CLASSES) if KNOWN in c.supports_flip0 + c.supports_flip1)


class SignatureClassTests(unittest.TestCase):
    def test_119_supports_collapse_to_15_classes_each_logically_ambiguous(self) -> None:
        self.assertEqual(len(CLASSES), 15)
        self.assertEqual(sum(len(c.supports_flip0) + len(c.supports_flip1) for c in CLASSES), 119)
        self.assertTrue(all(c.supports_flip0 and c.supports_flip1 for c in CLASSES))

    def test_known_burst_class_and_min_weight_heuristic_is_wrong_for_it(self) -> None:
        c = CLASSES[known_class_index()]
        self.assertIn(KNOWN, c.supports_flip0)
        self.assertIn((1, 12), c.supports_flip1)
        self.assertEqual(c.min_weight_flip(), 1)  # lowest-weight explanation flips the logical: wrong here

    def test_class_dem_burst_mechanisms_depend_only_on_signature_and_flip(self) -> None:
        c = CLASSES[known_class_index()]
        for flip in (0, 1):
            pool = c.supports_flip0 if flip == 0 else c.supports_flip1
            mech = [sorted((x.detectors, x.logical, round(x.p, 15)) for x in dem_mechanisms(
                m.build_candidate_circuit(SPEC, 0.01, s).detector_error_model(
                    decompose_errors=False, approximate_disjoint_errors=True)))
                for s in pool[:2]]
            # Same burst mechanisms; base mechanisms identical; so the merged DEMs coincide.
            self.assertEqual(mech[0], mech[1])


class ParityIdentityTests(unittest.TestCase):
    def test_parity_expectation_factorizes_exactly(self) -> None:
        # Brute-force a tiny DEM: E[(-1)^{x_A}] = prod over odd-overlap mechanisms of (1 - 2p).
        dem = stim.DetectorErrorModel("error(0.1) D0 D1\nerror(0.2) D1 D2\nerror(0.05) D0 D2\nerror(0.15) D2 L0\n")
        mechs = dem_mechanisms(dem)
        for a in [(0,), (1,), (0, 1, 2), (2,)]:
            exact = 0.0
            for bits in itertools.product((0, 1), repeat=len(mechs)):
                prob, x = 1.0, [0, 0, 0]
                for b, mm in zip(bits, mechs):
                    prob *= mm.p if b else 1 - mm.p
                    if b:
                        for d in mm.detectors:
                            x[d] ^= 1
                exact += prob * (-1) ** (sum(x[i] for i in a) % 2)
            pred = math.prod(1 - 2 * mm.p for mm in mechs if len(set(mm.detectors) & set(a)) % 2)
            self.assertAlmostEqual(exact, pred, places=12)


class LearnerSyntheticTests(unittest.TestCase):
    """Synthetic detector data drawn from the exact DEM (numpy; no Stim sampler)."""

    @staticmethod
    def draw(dem: stim.DetectorErrorModel, shots: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
        rng = np.random.default_rng(seed)
        mechs = dem_mechanisms(dem)
        x = np.zeros((shots, dem.num_detectors), dtype=np.uint8)
        y = np.zeros(shots, dtype=np.uint8)
        for mm in mechs:
            fire = rng.random(shots) < mm.p
            if mm.detectors:
                x[np.ix_(fire, list(mm.detectors))] ^= 1
            if mm.logical:
                y[fire] ^= 1
        return x, y

    def setUp(self) -> None:
        self.learner = L.ParityLearner(CLASSES, L.base_dem(), threshold=11.57)

    def test_recovers_known_class_and_rate(self) -> None:
        idx = known_class_index()
        dem = L.class_dem(SPEC, CLASSES[idx], 0, 0.02)
        x, _ = self.draw(dem, 20000, 1)
        out = self.learner.select(x)
        self.assertEqual(out["class_index"], idx)
        self.assertLess(abs(out["q_hat"] - 0.02), 0.005)

    def test_no_burst_data_selects_none(self) -> None:
        x, _ = self.draw(L.base_dem(), 20000, 2)
        self.assertIsNone(self.learner.select(x)["class_index"])

    def test_flip_stage_recovers_each_logical_effect(self) -> None:
        idx = known_class_index()
        for true_flip in (0, 1):
            x, y = self.draw(L.class_dem(SPEC, CLASSES[idx], true_flip, 0.02), 1500, 10 + true_flip)
            self.assertEqual(L.learn_flip(SPEC, CLASSES[idx], 0.02, x, y)["flip"], true_flip)


if __name__ == "__main__":
    unittest.main()
