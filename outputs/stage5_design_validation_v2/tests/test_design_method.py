import json
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import design_simulation as candidate


def independent_studentized(x, null):
    # Deliberately separate loop-based reference implementation.
    b, k, n = x.shape
    out = []
    for r in range(b):
        means, variances = [], []
        for j in range(k):
            vals = [float(v) for v in x[r, j]]
            mu = sum(vals) / n
            variance = sum((v - mu) ** 2 for v in vals) / (n - 1)
            means.append(mu)
            variances.append(variance)
        estimate = sum(means) / k
        v = sum(variances[j] / (k * k * n) for j in range(k))
        se = v ** 0.5
        tstat = (estimate - null) / se if se else (float("-inf") if estimate < null else float("inf") if estimate > null else 0.0)
        denom = sum((variances[j] / (k * k * n)) ** 2 / (n - 1) for j in range(k))
        df = v * v / denom if denom else float("inf")
        out.append((estimate, se, tstat, df))
    return np.asarray(out)


class TestDesignMethod(unittest.TestCase):
    def test_studentized_formula_against_independent_loop(self):
        x = np.array([
            [[0, 1, 2, 3, 5], [1, 1, 2, 2, 4], [-2, -1, 0, 1, 1], [4, 2, 1, 3, 8]],
            [[2, 2, 3, 4, 6], [-1, 0, 0, 1, 2], [3, 1, 1, 0, -1], [0, 0, 1, 1, 1]],
        ], dtype=np.float64)
        ref = independent_studentized(x, -0.2)
        got = candidate.studentized(x, -0.2)
        for idx, arr in enumerate(got):
            np.testing.assert_allclose(arr, ref[:, idx], rtol=1e-12, atol=1e-12)

    def test_zero_variance_tie_handling_is_conservative_at_boundary(self):
        x = np.zeros((3, 4, 10), dtype=np.float64)
        _, se, tstat, df = candidate.studentized(x, 0.0)
        self.assertTrue(np.all(se == 0))
        self.assertTrue(np.all(tstat == 0))
        self.assertTrue(np.all(np.isinf(df)))

    def test_no_harm_p0_tie_handling(self):
        x = np.zeros((3, 10), dtype=np.float64)
        _, se, tstat, _ = candidate.p0_stat(x, 0.0002)
        self.assertTrue(np.all(se == 0))
        self.assertTrue(np.all(tstat < 0))

    def test_generator_shapes_and_reproducibility(self):
        families = ["normal", "student_t5", "student_t3", "lognormal_sigma1", "zero_inflated65_normal", "tied_asymmetric65"]
        for family in families:
            a = candidate.draw_root_values(np.random.default_rng(17), 32, 12, np.zeros(4), np.ones(4) * 0.001, family)
            b = candidate.draw_root_values(np.random.default_rng(17), 32, 12, np.zeros(4), np.ones(4) * 0.001, family)
            self.assertEqual(a.shape, (32, 4, 12))
            np.testing.assert_array_equal(a, b)
            self.assertTrue(np.all(np.isfinite(a)))

    def test_allocation_arithmetic(self):
        expected = {578: 13005000, 640: 14400000, 666: 14985000}
        for n, shots in expected.items():
            self.assertEqual(n * 5 * 4500, shots)


if __name__ == "__main__":
    unittest.main()
