from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stage5_secondary_stats import (conservative_cutoff, dkw_epsilon, envelope_p,
                                    holm_reject, statistic, wilson)


class SecondaryStatsTests(unittest.TestCase):
    def test_dkw_bound_decreases_with_reference_size(self):
        self.assertGreater(dkw_epsilon(1000, 6, 0.001), dkw_epsilon(100000, 6, 0.001))

    def test_empirical_cdf_is_right_continuous_at_ties(self):
        ref = np.array([0.0, 1.0, 1.0, 2.0])
        p = envelope_p([ref], 0.01, np.array([1.0]))
        self.assertAlmostEqual(float(p[0]), 0.76)

    def test_envelope_p_is_monotone_and_no_smaller_than_any_component(self):
        refs = [np.array([-2.0, -1.0, 0.0, 1.0]), np.array([-1.5, -0.5, 0.5, 1.5])]
        t = np.array([-1.0, 0.0, 1.0])
        p = envelope_p(refs, 0.02, t)
        self.assertTrue(np.all(np.diff(p) >= 0))
        for ref in refs:
            component = np.minimum(1.0, np.searchsorted(ref, t, side="right") / len(ref) + 0.02)
            self.assertTrue(np.all(p >= component))

    def test_location_shift_and_scale_invariance_of_studentized_statistic(self):
        x = np.array([-1.0, 0.5, 0.25, 2.0])
        n = len(x)
        base = statistic(np.array([x.mean()]), np.array([x.std(ddof=1)]), n)
        scaled = statistic(np.array([(7.0 + 3.0 * x).mean() - 7.0]), np.array([(3.0 * x).std(ddof=1)]), n)
        self.assertAlmostEqual(float(base[0]), float(scaled[0]), places=12)

    def test_degenerate_sample_is_conservative(self):
        t = statistic(np.array([0.0, 0.2, -0.2]), np.array([0.0, 0.0, 0.0]), 20)
        self.assertTrue(np.isposinf(t[0]))
        self.assertTrue(np.isposinf(t[1]))
        self.assertTrue(np.isneginf(t[2]))

    def test_holm_stepdown_includes_ties_and_maps_original_conditions(self):
        p = np.array([[0.0125, 0.05, 0.025, 1.0 / 60.0],
                      [0.02, 0.03, 0.04, 0.05],
                      [0.01, 0.02, 0.03, 0.10]])
        got = holm_reject(p)
        self.assertEqual(got[0].tolist(), [True, True, True, True])
        self.assertEqual(got[1].tolist(), [False, False, False, False])
        self.assertEqual(got[2].tolist(), [True, False, False, False])

    def test_conservative_cutoff_respects_all_shapes_and_right_cdf(self):
        refs = [np.array([-3., -2., -1., 0., 1., 2.]), np.array([-2.5, -1.5, -0.5, .5, 1.5, 2.5])]
        eps = 0.01
        cutoff = conservative_cutoff(refs, eps, 0.5)
        self.assertLessEqual(float(envelope_p(refs, eps, np.array([np.nextafter(cutoff, -np.inf)]))[0]), 0.5)
        self.assertGreater(float(envelope_p(refs, eps, np.array([cutoff]))[0]), 0.5)

    def test_wilson_contains_observed_rate_and_handles_zero_count(self):
        lo, hi = wilson(0, 100)
        self.assertAlmostEqual(lo, 0.0, places=15)
        self.assertGreater(hi, 0.0)


if __name__ == "__main__":
    unittest.main()
