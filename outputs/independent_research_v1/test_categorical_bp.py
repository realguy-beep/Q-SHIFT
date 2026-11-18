from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "outputs/categorical_decoder_feasibility"))

from categorical_reference import decoder_risk, exact_posterior
from toy_circuits import one_qubit_model, two_qubit_model
from categorical_bp import logical_one_probability


class CategoricalBeliefPropagationTests(unittest.TestCase):
    def test_small_exact_models_return_normalized_logical_posterior(self):
        for model in (one_qubit_model(), two_qubit_model()):
            exact = exact_posterior(model)
            decisions = {}
            for syndrome in exact.joint:
                result = logical_one_probability(model, syndrome)
                self.assertGreaterEqual(result.logical_one_probability, 0.0)
                self.assertLessEqual(result.logical_one_probability, 1.0)
                decisions[syndrome] = int(result.logical_one_probability > 0.5)
            self.assertEqual(set(decisions), set(exact.joint))
            self.assertTrue(0.0 <= decoder_risk(exact.joint, decisions) <= 1.0)

    def test_invalid_inputs_are_rejected(self):
        model = one_qubit_model()
        with self.assertRaises(ValueError):
            logical_one_probability(model, -1)
        with self.assertRaises(ValueError):
            logical_one_probability(model, 0, damping=0)


if __name__ == "__main__":
    unittest.main()
