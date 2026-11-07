import unittest

import numpy as np

from outputs.stage4c_cnn_noise_estimation_v1.analysis import holm_adjust, signflip_p
from outputs.stage4c_cnn_noise_estimation_v1.prepare_inventory import audit_inventory, make_inventory


class Stage4CStatisticalTests(unittest.TestCase):
    def test_equal_seed_inventory_and_shot_partition_totals(self):
        inv = make_inventory()
        self.assertEqual(inv["unique_seed_count"], 554)
        self.assertEqual(inv["total_simulation_shots"], 277500)
        self.assertEqual(sum(s["shots"] for s in inv["streams"]), 277500)

    def test_recoverable_historical_seed_audit_has_no_collision(self):
        audit = audit_inventory(make_inventory())
        self.assertEqual(audit["status"], "PASS_RECOVERABLE_DEVELOPMENT_METADATA")
        self.assertEqual(audit["stage4c_historical_collisions"], [])
        self.assertEqual(audit["historical_unique_seed_count"], 3254)

    def test_signflip_is_deterministic_and_detects_constant_direction(self):
        d = np.full((4, 7), -0.001, dtype=np.float64)
        a = signflip_p(d, np.random.default_rng(123), assignments=10000)
        b = signflip_p(d, np.random.default_rng(123), assignments=10000)
        self.assertEqual(a, b)
        self.assertLess(a, 0.05)

    def test_signflip_rejects_wrong_strata_shape(self):
        with self.assertRaises(ValueError):
            signflip_p(np.zeros((5, 7)), np.random.default_rng(1), assignments=100)

    def test_holm_adjustment_is_monotone_and_bounded(self):
        adjusted = holm_adjust({"a": 0.01, "b": 0.04, "c": 0.2})
        self.assertEqual(adjusted, {"a": 0.03, "b": 0.08, "c": 0.2})
        self.assertTrue(all(0 <= p <= 1 for p in adjusted.values()))


if __name__ == "__main__":
    unittest.main()
