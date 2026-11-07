from __future__ import annotations
import unittest

import numpy as np

from exact_toy import exact_joint_likelihoods, exact_posterior
from reference_decoder import SampledPosteriorDecoder


class Phase2CTests(unittest.TestCase):
    def test_exhaustive_categorical_posterior(self):
        # One categorical fault location: D=1 occurs with total mass .3,
        # of which .1 also flips the observable.
        joint = exact_joint_likelihoods([[(0.7, 0, 0), (0.2, 1, 0), (0.1, 1, 1)]])
        self.assertAlmostEqual(sum(joint.values()), 1.0)
        self.assertAlmostEqual(exact_posterior(joint, 1), 1 / 3)
        self.assertAlmostEqual(exact_posterior(joint, 0), 0.0)

    def test_independent_locations_xor_detector_and_logical_bits(self):
        a = [(0.8, 0, 0), (0.2, 1, 1)]
        b = [(0.75, 0, 0), (0.25, 1, 0)]
        joint = exact_joint_likelihoods([a, b])
        self.assertAlmostEqual(sum(joint.values()), 1.0)
        # D=0,L=1 requires both events; its mass is .2*.25=.05.
        # D=0,L=0 has mass .8*.75=.60.
        self.assertAlmostEqual(exact_posterior(joint, 0), 0.05 / 0.65)

    def test_exact_enumerator_rejects_invalid_distribution(self):
        with self.assertRaises(ValueError):
            exact_joint_likelihoods([[(0.6, 0, 0), (0.3, 1, 1)]])

    def test_sampled_decoder_learns_a_known_toy_map(self):
        rng = np.random.default_rng(71001)
        n = 4000
        d = rng.integers(0, 2, size=(n, 3), dtype=np.uint8)
        y = d[:, 0].copy()
        decoder = SampledPosteriorDecoder(seed=71002, n_estimators=64, min_samples_leaf=1)
        decoder.fit(d, y)
        self.assertGreater(np.mean(decoder.predict(d) == y), 0.99)
        self.assertTrue(np.all((decoder.predict_probability(d) >= 0) & (decoder.predict_probability(d) <= 1)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
