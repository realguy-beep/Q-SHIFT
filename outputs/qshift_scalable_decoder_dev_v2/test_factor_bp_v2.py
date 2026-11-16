import itertools
import math
import pathlib
import sys
import unittest

import numpy as np
import stim

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from exact_reference import exact_posterior
from factor_bp_v2 import FactorBPV2, ImpossibleSyndromeError


class V2FactorBPTests(unittest.TestCase):
    def assert_matches_exact(self, dem, syndrome):
        exact = exact_posterior(dem, syndrome)
        self.assertIsNotNone(exact)
        result = FactorBPV2(dem, tolerance=1e-13).decode_one(syndrome, include_fault_marginals=True)
        self.assertTrue(result["converged"])
        self.assertLess(result["message_residual"], 1e-8)
        self.assertAlmostEqual(result["logical_p1_approx"], exact["logical_p1"], delta=1e-10)
        np.testing.assert_allclose(result["fault_p1_approx"], exact["fault_p1"], atol=1e-10, rtol=1e-10)
        return result

    def test_tree_exact_marginals_all_syndromes(self):
        dem = stim.DetectorErrorModel(
            "error(0.1) D0 L0\nerror(0.2) D0\nerror(0.3) L0\n"
            "detector D0\nlogical_observable L0"
        )
        for syndrome in ([0], [1]):
            self.assert_matches_exact(dem, syndrome)

    def test_hyperedge_tree_exact_marginals(self):
        dem = stim.DetectorErrorModel(
            "error(0.1) D0 D1 L0\nerror(0.2) D0\nerror(0.3) D1\n"
            "detector D0\ndetector D1\nlogical_observable L0"
        )
        for syndrome in itertools.product((0, 1), repeat=2):
            self.assert_matches_exact(dem, syndrome)

    def test_duplicate_detector_signatures_and_target_parity(self):
        dem = stim.DetectorErrorModel(
            "error(0.1) D0 L0\nerror(0.2) D0\nerror(0.3) D1 D1 L0\n"
            "detector D0\ndetector D1\nlogical_observable L0"
        )
        self.assert_matches_exact(dem, [0, 0])
        self.assert_matches_exact(dem, [1, 0])
        model = FactorBPV2(dem)
        self.assertEqual(model.det, [(0,), (0,), ()])

    def test_separator_preserves_one_hyperedge_mechanism(self):
        dem = stim.DetectorErrorModel(
            "error(0.1) D0 ^ D1 L0\ndetector D0\ndetector D1\nlogical_observable L0"
        )
        model = FactorBPV2(dem)
        self.assertEqual(model.det, [(0, 1)])
        self.assertEqual(model.logical, [True])

    def test_logical_joint_is_explicitly_approximate(self):
        dem = stim.DetectorErrorModel(
            "error(0.1) D0 L0\nerror(0.2) D0 L0\ndetector D0\nlogical_observable L0"
        )
        model = FactorBPV2(dem)
        for syndrome, expected in (([0], 0.0), ([1], 1.0)):
            result = model.decode_one(syndrome)
            exact = exact_posterior(dem, syndrome)
            self.assertFalse(result["logical_probability_exact"])
            self.assertAlmostEqual(exact["logical_p1"], expected, places=12)
            self.assertGreater(abs(result["logical_p1_approx"] - expected), 1e-3)

    def test_zero_and_unit_probability_mechanisms_are_exact(self):
        dem = stim.DetectorErrorModel(
            "error(0) D2 L0\nerror(1) D0 L0\nerror(0.2) D1\n"
            "detector D0\ndetector D1\ndetector D2\nlogical_observable L0"
        )
        model = FactorBPV2(dem)
        self.assertEqual(len(model.p), 1)
        result = model.decode_one([1, 0, 0])
        self.assertEqual(result["logical_p1_approx"], 1.0)
        self.assertTrue(result["logical_probability_exact"])
        with self.assertRaises(ImpossibleSyndromeError):
            model.decode_one([0, 0, 0])

    def test_gf2_reachability_rejects_dependent_impossible_syndrome(self):
        dem = stim.DetectorErrorModel(
            "error(0.1) D0 D1\nerror(0.2) D1 D2\nerror(0.3) D0 D2\n"
            "detector D0\ndetector D1\ndetector D2\nlogical_observable L0"
        )
        model = FactorBPV2(dem)
        with self.assertRaises(ImpossibleSyndromeError):
            model.decode_one([1, 0, 0])
        for syndrome in ([0, 0, 0], [1, 1, 0], [0, 1, 1], [1, 0, 1]):
            self.assertIsNotNone(model.decode_one(syndrome))

    def test_near_boundary_probabilities_remain_finite(self):
        dem = stim.DetectorErrorModel(
            "error(1e-15) D0 L0\nerror(0.999999999999999) D1\n"
            "detector D0\ndetector D1\nlogical_observable L0"
        )
        model = FactorBPV2(dem)
        result = model.decode_one([0, 1], include_fault_marginals=True)
        self.assertTrue(np.isfinite(result["logical_p1_approx"]))
        self.assertTrue(np.isfinite(result["message_residual"]))
        self.assertTrue(np.isfinite(result["fault_p1_approx"]).all())

    def test_fixed_model_repeats_identically(self):
        dem = stim.DetectorErrorModel("error(0.1) D0 L0\ndetector D0\nlogical_observable L0")
        model = FactorBPV2(dem)
        first = model.decode_one([1])
        second = model.decode_one([1])
        self.assertEqual(first, second)

    def test_invalid_solver_parameters_and_syndromes_fail_closed(self):
        dem = stim.DetectorErrorModel("error(0.1) D0 L0\ndetector D0\nlogical_observable L0")
        for kwargs in ({"iterations": 0}, {"damping": 1.0}, {"damping": -0.1},
                       {"tolerance": 0}, {"clip": 0}, {"clip": 0.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                FactorBPV2(dem, **kwargs)
        model = FactorBPV2(dem)
        for syndrome in ([], [2], [0, 1]):
            with self.subTest(syndrome=syndrome), self.assertRaises(ValueError):
                model.decode_one(syndrome)

    def test_random_logical_only_faults_with_zero_detector_edges(self):
        dem = stim.DetectorErrorModel(
            "error(0.1) L0\nerror(0.2) L0\nlogical_observable L0"
        )
        result = FactorBPV2(dem).decode_one([])
        exact = exact_posterior(dem, [])
        self.assertAlmostEqual(exact["logical_p1"], 0.26, places=12)
        self.assertAlmostEqual(result["logical_p1_approx"], exact["logical_p1"], places=12)
        self.assertTrue(result["logical_probability_exact"])
        self.assertEqual(result["converged"], True)
    def test_no_effect_model_has_exact_fixed_logical_result(self):
        dem = stim.DetectorErrorModel("error(0) L0\nlogical_observable L0")
        result = FactorBPV2(dem).decode_one([])
        self.assertEqual(result["logical_p1_approx"], 0.0)
        self.assertTrue(result["logical_probability_exact"])
        self.assertEqual(result["iterations"], 0)


if __name__ == "__main__":
    unittest.main()






