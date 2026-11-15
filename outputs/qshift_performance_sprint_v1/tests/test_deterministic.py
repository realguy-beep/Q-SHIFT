from __future__ import annotations

import unittest
import numpy as np

from outputs.qshift_performance_sprint_v1.estimator import RidgeProfile
from outputs.qshift_performance_sprint_v1.prepare_seed_inventory import build_inventory


class DeterministicTests(unittest.TestCase):
    def test_ridge_uses_detector_features_and_clips(self):
        x = np.zeros((40, 40), dtype=np.uint8)
        y = np.linspace(0.0, 0.016, 40)
        for i in range(40):
            x[i, 0] = int(i >= 20)
        model = RidgeProfile.fit(x, y, alpha=10.0)
        pred = model.predict(x)
        self.assertEqual(pred.shape, (40,))
        self.assertTrue(np.isfinite(pred).all())
        self.assertTrue(np.all((pred >= 0) & (pred <= 0.016)))
        self.assertGreater(float(pred[-1]), float(pred[0]))

    def test_rejects_bad_features_and_targets(self):
        with self.assertRaises(ValueError):
            RidgeProfile.fit(np.zeros((4, 39)), np.zeros(4))
        with self.assertRaises(ValueError):
            RidgeProfile.fit(np.zeros((4, 40)), np.array([0, 0, 0, 0.02]))
        model = RidgeProfile.fit(np.zeros((4, 40)), np.zeros(4))
        with self.assertRaises(ValueError):
            model.predict(np.full((1, 40), 2))

    def test_seed_inventory_unique_disjoint_stream_labels(self):
        inv = build_inventory()
        values = list(inv["seeds"].values())
        self.assertEqual(inv["seed_count_including_statistics_stream"], 108)
        self.assertEqual(len(values), len(set(values)))
        self.assertIn("train:p0", inv["seeds"])
        self.assertNotEqual(inv["seeds"]["cal:p0:r00"], inv["seeds"]["eval:p0:r00"])

    def test_allocation_arithmetic(self):
        from pathlib import Path
        import json
        cfg = json.loads((Path(__file__).parents[1] / "config.json").read_text())
        a = cfg["allocation"]
        total = (5 * a["training_shots_per_probability"]
                 + 5 * a["roots_per_probability"] * a["calibration_shots_per_root"]
                 + 5 * a["roots_per_probability"] * a["evaluation_shots_per_root"])
        self.assertEqual(total, a["total_unique_shots"])
        self.assertEqual(a["sampler_calls"], 5 + 50 + 50)

    def test_root_stratified_bootstrap_is_deterministic(self):
        from outputs.qshift_performance_sprint_v1.analyze import paired_bootstrap
        values = np.array([[0.0, 0.1, 0.2], [-0.1, 0.0, 0.1]])
        a = paired_bootstrap(values, np.random.default_rng(81), replicates=200)
        b = paired_bootstrap(values, np.random.default_rng(81), replicates=200)
        self.assertEqual(a.shape, (200,))
        np.testing.assert_array_equal(a, b)

    def test_paired_evaluator_keeps_labels_out_of_decoder_calls(self):
        from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction
        from qshift_core_v1.evaluation import evaluate_paired

        seen = []
        class Fixture:
            def __init__(self, name):
                self.metadata = DecoderMetadata(name=name, implementation="fixture", version="1",
                                                detector_count=3, observable_count=1)
            def decode(self, detectors):
                seen.append(np.array(detectors, copy=True))
                return DecoderPrediction(np.zeros((len(detectors), 1), dtype=np.uint8), self.metadata)

        detector = np.array([[0,1,0],[1,0,0]], dtype=np.uint8)
        labels = np.array([[1],[0]], dtype=np.uint8)
        result = evaluate_paired(detector, labels,
                                 {"base": Fixture("base"), "candidate": Fixture("candidate")},
                                 baseline_name="base", scope="heldout-development",
                                 sample_id="fixture-only")
        self.assertEqual(len(seen), 2)
        np.testing.assert_array_equal(seen[0], seen[1])
        self.assertEqual(result["records"]["base"]["errors"], 1)


if __name__ == "__main__":
    unittest.main()