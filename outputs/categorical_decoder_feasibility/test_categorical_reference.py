import math
import unittest

from categorical_reference import (CategoricalLocation, CategoricalModel, FaultOutcome,
                                   decoder_risk, exact_posterior)
from toy_circuits import (one_qubit_model, two_qubit_model, stim_exhaustive_joint,
                          pymatching_decisions)


class TestCategoricalReference(unittest.TestCase):
    def test_one_qubit_locations_include_identity_and_normalize(self):
        model = one_qubit_model()
        self.assertEqual(model.configuration_count, 4 ** 3)
        for loc in model.locations:
            self.assertAlmostEqual(sum(o.probability for o in loc.outcomes), 1.0, places=14)
            self.assertEqual(sum(o.label == "I" for o in loc.outcomes), 1)
        result = exact_posterior(model)
        self.assertEqual(result.configuration_count, 64)
        self.assertAlmostEqual(result.total_probability, 1.0, places=12)

    def test_two_qubit_locations_are_16_way_categorical(self):
        model = two_qubit_model()
        self.assertEqual(model.configuration_count, 16 ** 2)
        for loc in model.locations:
            self.assertEqual(len(loc.outcomes), 16)
            self.assertEqual(loc.outcomes[0].label, "II")
            self.assertAlmostEqual(sum(o.probability for o in loc.outcomes), 1.0, places=14)

    def test_stim_exhaustive_reference_matches_analytic_masks(self):
        for kind, model in (("one_qubit", one_qubit_model()), ("two_qubit", two_qubit_model())):
            result = exact_posterior(model)
            stim_joint, visited = stim_exhaustive_joint(model, kind)
            self.assertEqual(visited, model.configuration_count)
            self.assertEqual(set(stim_joint), set(result.joint))
            for syndrome in result.joint:
                for a, b in zip(result.joint[syndrome], stim_joint[syndrome]):
                    self.assertTrue(math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12))

    def test_tie_uses_smallest_observable_bit_pattern(self):
        location = CategoricalLocation("undetectable_logical", (
            FaultOutcome("I", 0.5, 0, 0),
            FaultOutcome("L", 0.5, 0, 1),
        ), "I")
        result = exact_posterior(CategoricalModel(1, 1, (location,)))
        self.assertEqual(result.tie_syndromes, (0,))
        self.assertEqual(result.decisions[0], 0)
        self.assertEqual(result.conditional[0], (0.5, 0.5))
        self.assertAlmostEqual(result.logical_error_probability, 0.5)

    def test_invalid_probability_sum_is_rejected(self):
        location = CategoricalLocation("invalid", (
            FaultOutcome("I", 0.8, 0, 0),
            FaultOutcome("X", 0.1, 1, 1),
        ), "I")
        with self.assertRaisesRegex(ValueError, "sum to"):
            CategoricalModel(1, 1, (location,)).validate()

    def test_each_configuration_selects_one_outcome_per_location(self):
        model = one_qubit_model()
        configs = list(model.enumerate_configurations())
        self.assertEqual(len(configs), model.configuration_count)
        self.assertTrue(all(len(selected) == len(model.locations) for selected, *_ in configs))
        for selected, probability, _, _ in configs:
            self.assertAlmostEqual(probability, math.prod(o.probability for o in selected), places=15)

    def test_one_qubit_approximate_matching_matches_exact_toy(self):
        model = one_qubit_model()
        exact = exact_posterior(model)
        pm = pymatching_decisions("one_qubit", list(range(4)))
        for mode in ("correlation_disabled", "correlation_enabled"):
            pred = {int(k): int(v) for k, v in pm["decoders"][mode].items()}
            self.assertEqual(pred, exact.decisions)
            self.assertAlmostEqual(decoder_risk(exact.joint, pred), exact.logical_error_probability, places=14)

    def test_two_qubit_approximate_matching_misses_one_exact_map_case(self):
        model = two_qubit_model()
        exact = exact_posterior(model)
        pm = pymatching_decisions("two_qubit", list(range(4)))
        self.assertEqual(exact.decisions[3], 1)
        self.assertEqual(exact.tie_syndromes, (1, 2))
        for mode in ("correlation_disabled", "correlation_enabled"):
            pred = {int(k): int(v) for k, v in pm["decoders"][mode].items()}
            self.assertEqual(pred[3], 0)
            self.assertNotEqual(pred, exact.decisions)
            self.assertGreater(decoder_risk(exact.joint, pred), exact.logical_error_probability)


if __name__ == "__main__":
    unittest.main()
