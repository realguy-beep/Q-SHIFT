"""Deterministic unit tests for the independent post-run audit primitives."""
from __future__ import annotations

import unittest

import numpy as np

import audit_saved_run as audit


class PostrunAuditTests(unittest.TestCase):
    def test_root_scores_are_paired_and_count_disagreements(self):
        detectors = np.zeros((4, 40), dtype=np.uint8)
        labels = np.array([[0], [1], [1], [0]], dtype=np.uint8)
        predictions = {
            "A": np.array([[0], [0], [1], [1]], dtype=np.uint8),
            "A2": np.array([[0], [1], [0], [0]], dtype=np.uint8),
            "B": np.array([[1], [0], [1], [0]], dtype=np.uint8),
            "C": np.array([[1], [1], [1], [0]], dtype=np.uint8),
        }
        row = audit.root_scores(detectors, labels, predictions, 0.01, 3)
        self.assertEqual(row["A_errors"], 2)
        self.assertEqual(row["B_errors"], 2)
        self.assertEqual(row["A_B_prediction_disagreements"], 2)
        self.assertEqual(row["B_only_errors_vs_A"], 1)
        self.assertEqual(row["A_only_errors_vs_B"], 1)

    def test_bootstrap_reproducible_and_equal_weighted(self):
        diffs = {0.0: [0.0] * 10, 0.01: [-0.01] * 10, 0.02: [0.03] * 10}
        first = audit.stratified_bootstrap(diffs, seed=17, replicates=1000)
        second = audit.stratified_bootstrap(diffs, seed=17, replicates=1000)
        self.assertEqual(first, second)
        self.assertAlmostEqual(first[0], 0.01)
        self.assertTrue(np.allclose(first[1], [0.01, 0.01], rtol=0, atol=1e-15))

    def test_zero_condition_bootstrap_percentiles(self):
        result = audit.zero_condition_bounds([0.001] * 10, seed=21, replicates=1000)
        self.assertTrue(np.allclose(result, [0.001, 0.001], rtol=0, atol=1e-15))

    def test_nonbinary_and_wrong_shape_rejected(self):
        with self.assertRaises(ValueError):
            audit._validate_binary("bad", np.array([[2]], dtype=np.uint8), (1, 1))
        with self.assertRaises(ValueError):
            audit._validate_binary("bad", np.zeros((1, 2), dtype=np.uint8), (1, 1))


if __name__ == "__main__":
    unittest.main()
