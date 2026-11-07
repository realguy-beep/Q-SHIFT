import unittest
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "categorical_decoder_feasibility"))

from categorical_reference import exact_posterior
from factor_graph import make_factor_graph, run_dense_ve
from structured_inference import direct_xor_dp, map_metrics, xor_walsh_posterior
from toy_circuits import one_qubit_model, two_qubit_model
from phase2b_fragments import extract_model


class TestStructuredInference(unittest.TestCase):
    def _check_model(self, model):
        exact = exact_posterior(model)
        transformed, meta = xor_walsh_posterior(model)
        dp = direct_xor_dp(model)
        self.assertAlmostEqual(float(transformed.sum()), 1.0, places=12)
        self.assertAlmostEqual(meta["raw_mass_before_clipping"], 1.0, places=12)
        for mask, probability in dp.items():
            self.assertTrue(math.isclose(float(transformed[mask]), probability, rel_tol=0, abs_tol=1e-12))
        joint = {}
        for mask, probability in dp.items():
            s = mask & ((1 << model.detector_count)-1)
            l = mask >> model.detector_count
            joint.setdefault(s, [0.0]*(1 << model.observable_count))[l] += probability
        self.assertEqual(set(joint), set(exact.joint))
        for s in joint:
            for a,b in zip(joint[s], exact.joint[s]):
                self.assertTrue(math.isclose(a,b,rel_tol=0,abs_tol=1e-12))
        metrics = map_metrics(transformed, model.detector_count, model.observable_count)
        self.assertEqual(metrics["decisions"], exact.decisions)
        self.assertAlmostEqual(metrics["logical_error_probability"], exact.logical_error_probability, places=12)
        info = make_factor_graph(model)
        self.assertEqual(len(info["parity_scopes"]), model.detector_count+model.observable_count)
        for heuristic in ("min_fill", "min_degree"):
            ve = run_dense_ve(model, heuristic)
            self.assertAlmostEqual(ve["total_mass"], 1.0, places=12)
            self.assertEqual(ve["decisions"], exact.decisions)
            self.assertAlmostEqual(ve["risk"], exact.logical_error_probability, places=12)
            self.assertEqual(set(ve["joint"]), set(exact.joint))
            for s in exact.joint:
                for a,b in zip(ve["joint"][s], exact.joint[s]):
                    self.assertTrue(math.isclose(a,b,rel_tol=0,abs_tol=1e-12))

    def test_one_qubit_categorical_model(self):
        self._check_model(one_qubit_model())

    def test_two_qubit_categorical_model_and_ties(self):
        model = two_qubit_model()
        exact = exact_posterior(model)
        self.assertEqual(exact.tie_syndromes, (1,2))
        self._check_model(model)

    def test_phase2b_one_round_fragment_masks_and_normalization(self):
        _, model, info = extract_model(rounds=1, memory_basis="z", regime="x_biased")
        self.assertEqual((info["detectors"], info["observables"], info["fault_locations"]), (8,1,49))
        self.assertEqual(info["forced_nonidentity_checks"], 401)
        for location in model.locations:
            self.assertAlmostEqual(sum(o.probability for o in location.outcomes), 1.0, places=12)
        transformed, _ = xor_walsh_posterior(model)
        direct = direct_xor_dp(model)
        self.assertAlmostEqual(float(transformed.sum()), 1.0, places=12)
        for mask, probability in direct.items():
            self.assertTrue(math.isclose(float(transformed[mask]), probability, rel_tol=0, abs_tol=1e-10))


if __name__ == "__main__":
    unittest.main()
