from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from neural_collapse_diagnostics import (balanced_batch_indices, confusion_counts,
                                         debias_weighted_logits, group_label_bound)


class NeuralCollapseDiagnosticTests(unittest.TestCase):
    def test_weighted_bce_logit_correction_recovers_true_probability(self):
        p = np.array([0.01, 0.1, 0.5, 0.9, 0.99])
        weight = 17.0
        weighted_logit = logit(p) + np.log(weight)
        corrected = debias_weighted_logits(weighted_logit, weight)
        np.testing.assert_allclose(expit(corrected), p, rtol=1e-12, atol=1e-12)

    def test_duplicate_feature_contradictions_bound_deterministic_accuracy(self):
        d = np.array([[0, 0], [0, 0], [1, 0], [1, 0], [1, 1]], dtype=np.uint8)
        y = np.array([0, 1, 1, 1, 0], dtype=np.uint8)
        result = group_label_bound(d, y)
        self.assertEqual(result["unique_feature_vectors"], 3)
        self.assertEqual(result["contradictory_feature_vectors"], 1)
        self.assertEqual(result["best_deterministic_correct"], 4)
        self.assertAlmostEqual(result["best_deterministic_accuracy"], 0.8)

    def test_balanced_batch_is_deterministic_and_class_balanced(self):
        labels = np.array([0] * 95 + [1] * 5, dtype=np.uint8)
        a = balanced_batch_indices(labels, 64, np.random.default_rng(1234))
        b = balanced_batch_indices(labels, 64, np.random.default_rng(1234))
        np.testing.assert_array_equal(a, b)
        self.assertEqual(int(labels[a].sum()), 32)
        self.assertEqual(len(a), 64)

    def test_confusion_count_convention(self):
        self.assertEqual(confusion_counts([0, 0, 1, 1], [0, 1, 0, 1]),
                         {"tn": 1, "fp": 1, "fn": 1, "tp": 1})


if __name__ == "__main__":
    unittest.main()
