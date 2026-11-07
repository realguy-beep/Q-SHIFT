from __future__ import annotations

import unittest
import inspect

import numpy as np

from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (
    BURST_DETECTOR_PAIRS,
    DetectorProfileEstimator,
    build_decoder,
    decode_prediction,
    detector_features,
    logical_error_mask,
)


class Stage4PrototypeTests(unittest.TestCase):
    def test_detector_features_use_only_40_binary_detectors(self):
        d = np.zeros((3, 40), dtype=np.uint8)
        for a, b in BURST_DETECTOR_PAIRS:
            d[0, a] = d[0, b] = 1
        f = detector_features(d)
        self.assertEqual(f.shape, (3, 45))
        self.assertTrue(np.all(f[0, 40:] == 1))
        self.assertTrue(np.all(f[1:] == 0))

    def test_rejects_nonbinary_or_wrong_shape_detectors(self):
        with self.assertRaises(ValueError):
            detector_features(np.zeros((2, 39), dtype=np.uint8))
        bad = np.zeros((2, 40), dtype=np.uint8)
        bad[0, 0] = 2
        with self.assertRaises(ValueError):
            detector_features(bad)

    def test_profile_estimator_interpolates_without_labels_at_inference(self):
        rng = np.random.default_rng(20261107)
        batches = []
        for p, rate in [(0.002, 0.15), (0.010, 0.35), (0.018, 0.55)]:
            # Deterministic fixture: synthetic detector-only calibration profiles.
            d = (rng.random((512, 40)) < rate).astype(np.uint8)
            batches.append((p, d))
        model = DetectorProfileEstimator.fit(batches)
        query = (rng.random((512, 40)) < 0.45).astype(np.uint8)
        estimate = model.estimate(query)
        self.assertGreaterEqual(estimate, 0.002)
        self.assertLessEqual(estimate, 0.018)

    def test_estimator_rejects_one_profile_and_bad_probability(self):
        d = np.zeros((4, 40), dtype=np.uint8)
        with self.assertRaises(ValueError):
            DetectorProfileEstimator.fit([(0.01, d)])
        with self.assertRaises(ValueError):
            DetectorProfileEstimator.fit([(-0.1, d), (0.1, d)])

    def test_inference_signature_accepts_only_calibration_detectors(self):
        parameters = list(inspect.signature(DetectorProfileEstimator.estimate).parameters)
        self.assertEqual(parameters, ["self", "calibration_detectors"])

    def test_pilot_seed_streams_are_unique_and_fresh(self):
        from outputs.stage4_noise_adaptive_feasibility_v1.prepare_stage4 import STREAMS
        seeds = [row["seed"] for row in STREAMS]
        self.assertEqual(len(seeds), 19)
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertEqual(seeds, list(range(4100000001, 4100000020)))

    def test_dem_rebuild_updates_only_the_declared_burst_mechanisms(self):
        c0, dem0, m0 = build_decoder(0.0)
        c1, dem1, m1 = build_decoder(0.01)
        self.assertEqual((c0.num_detectors, c0.num_observables), (40, 1))
        self.assertEqual((dem0.num_detectors, dem0.num_observables), (40, 1))
        self.assertEqual((dem1.num_detectors, dem1.num_observables), (40, 1))
        lines = [x for x in str(dem1).splitlines() if x.startswith("error(") and any(f"D{a} D{b}" in x for a, b in BURST_DETECTOR_PAIRS)]
        self.assertEqual(len(lines), 5)
        self.assertTrue(all("error(0.01)" in line for line in lines))
        for a, b in BURST_DETECTOR_PAIRS:
            edge = m1.get_edge_data(a, b)
            self.assertAlmostEqual(edge["error_probability"], 0.01)
            self.assertAlmostEqual(edge["weight"], np.log(0.99 / 0.01), places=6)
        sample = np.zeros((7, 40), dtype=np.uint8)
        self.assertEqual(decode_prediction(m0, sample).shape, (7,))
        self.assertEqual(decode_prediction(m1, sample).shape, (7,))

    def test_xor_convention_and_paired_shapes(self):
        pred = np.asarray([0, 1, 1, 0], dtype=np.uint8)
        obs = np.asarray([0, 0, 1, 1], dtype=np.uint8)
        np.testing.assert_array_equal(logical_error_mask(pred, obs), [0, 1, 0, 1])
        with self.assertRaises(ValueError):
            logical_error_mask(pred, np.asarray([0, 1], dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()
