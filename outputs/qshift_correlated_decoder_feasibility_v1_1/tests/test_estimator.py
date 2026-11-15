from __future__ import annotations

import numpy as np
import unittest

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import BurstEvent, BurstRateEstimator


EVENTS = tuple(BurstEvent((3 * i, 3 * i + 1, 3 * i + 2), i % 2) for i in range(5))


def synthetic_rows(active_rows: int, n: int = 1000) -> np.ndarray:
    x = np.zeros((n, 40), dtype=np.uint8)
    x[:active_rows, list(EVENTS[0].detector_ids)] = 1
    return x


class EstimatorTests(unittest.TestCase):
    def test_fit_uses_numpy_polyfit_slope_intercept_order(self) -> None:
        # Event rate is active_rows/(5*n): 0.002, 0.004, 0.006 at q 0,.01,.02.
        # The reversed V1 assignment gives slope=.002, intercept=.2 and fails this.
        train = np.vstack([synthetic_rows(n) for n in (10, 20, 30)])
        targets = np.repeat(np.asarray([0.0, 0.01, 0.02]), 1000)
        estimator = BurstRateEstimator(EVENTS).fit(train, targets)
        self.assertAlmostEqual(estimator.slope, 0.2, delta=1e-12)
        self.assertAlmostEqual(estimator.intercept, 0.002, delta=1e-12)
        self.assertAlmostEqual(estimator.estimate(synthetic_rows(25)), 0.015, delta=1e-12)


    def test_estimates_are_ordered_and_bounded(self) -> None:
        train = np.vstack([synthetic_rows(n) for n in (10, 20, 30)])
        targets = np.repeat(np.asarray([0.0, 0.01, 0.02]), 1000)
        estimator = BurstRateEstimator(EVENTS).fit(train, targets)
        estimates = [estimator.estimate(synthetic_rows(n)) for n in (10, 20, 30)]
        np.testing.assert_allclose(estimates, [0.0, 0.01, 0.02], atol=1e-12, rtol=0)
        self.assertEqual(estimator.estimate(np.zeros((100, 40), dtype=np.uint8)), 0.0)
        saturated = np.zeros((100, 40), dtype=np.uint8)
        saturated[:5, list(EVENTS[0].detector_ids)] = 1
        self.assertEqual(estimator.estimate(saturated), 0.02)


    def test_fit_rejects_non_increasing_training_signal(self) -> None:
        train = np.vstack([synthetic_rows(n) for n in (30, 20, 10)])
        targets = np.repeat(np.asarray([0.0, 0.01, 0.02]), 1000)
        with self.assertRaisesRegex(RuntimeError, "increasing"):
            BurstRateEstimator(EVENTS).fit(train, targets)


    def test_fit_rejects_misaligned_or_nonbinary_inputs(self) -> None:
        train = np.zeros((300, 40), dtype=np.uint8)
        targets = np.repeat([0.0, 0.01, 0.02], 99)
        with self.assertRaises(ValueError):
            BurstRateEstimator(EVENTS).fit(train, targets)
        invalid = np.zeros((300, 40), dtype=np.uint8)
        invalid[0, 0] = 2
        aligned_targets = np.repeat([0.0, 0.01, 0.02], 100)
        with self.assertRaises(ValueError):
            BurstRateEstimator(EVENTS).fit(invalid, aligned_targets)


if __name__ == "__main__":
    unittest.main()
