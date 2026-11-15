from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from outputs.qshift_decoder_sensitivity_diagnostic_v1.diagnostic import (
    PAIR_MAP, StandardizedRidge, detector_signature_pairs, feature_matrix, sha_array,
    load_evaluation_detectors_only,
)


class DiagnosticTests(unittest.TestCase):
    def test_five_pair_cofire_features_append_to_forty_marginals(self):
        x = np.zeros((3, 40), dtype=np.uint8)
        x[0, [8, 10]] = 1
        x[1, [16, 18, 24]] = 1
        x[2, [36, 38]] = 1
        out = feature_matrix(x)
        self.assertEqual(out.shape, (3, 45))
        np.testing.assert_array_equal(out[:, 40:], np.array([[1, 0, 0, 0, 0],
                                                             [0, 1, 0, 0, 0],
                                                             [0, 0, 0, 0, 1]], dtype=np.uint8))

    def test_dem_derived_feature_pair_map_matches_frozen_order(self):
        self.assertEqual(detector_signature_pairs(), PAIR_MAP)

    def test_standardized_ridge_predicts_clipped_probability(self):
        x = np.zeros((100, 45), dtype=np.float64)
        y = np.zeros(100, dtype=np.float64)
        x[50:, 40] = 1
        y[50:] = 0.016
        model = StandardizedRidge(0.01).fit(x, y)
        pred = model.predict(x)
        self.assertTrue(np.isfinite(pred).all())
        self.assertTrue(np.all((pred >= 0) & (pred <= 0.016)))
        self.assertGreater(float(pred[-1]), float(pred[0]))

    def test_array_hash_binds_shape_dtype_and_bytes(self):
        base = np.array([[0, 1], [1, 0]], dtype=np.uint8)
        self.assertEqual(sha_array(base), sha_array(base.copy()))
        self.assertNotEqual(sha_array(base), sha_array(base.reshape(4)))
        self.assertNotEqual(sha_array(base), sha_array(base.astype(np.int8)))

    def test_evaluation_loader_requests_only_detector_member(self):
        class Archive:
            requested = []

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def __getitem__(self, key):
                self.requested.append(key)
                if key != "detectors":
                    raise AssertionError("evaluation labels must remain inaccessible")
                return np.zeros((2000, 40), dtype=np.uint8)

        archive = Archive()
        with patch("outputs.qshift_decoder_sensitivity_diagnostic_v1.diagnostic.np.load",
                   return_value=archive):
            result = load_evaluation_detectors_only(Path("fixture.npz"))
        self.assertEqual(result.shape, (2000, 40))
        self.assertEqual(archive.requested, ["detectors"])


if __name__ == "__main__":
    unittest.main()
