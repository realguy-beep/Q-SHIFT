from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from outputs.stage4_noise_adaptive_development_v1.analysis import (
    NONZERO_P, evaluate_gate, exact_stratum_signflip, holm_adjust,
    monte_carlo_signflip, stratified_cluster_bootstrap, stratified_primary,
)
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (
    DetectorProfileEstimator, build_decoder, decode_prediction,
)
from outputs.stage4_noise_adaptive_development_v1.run_stage4 import diagnostic, stream_map
from outputs.stage4_noise_adaptive_development_v1 import audit_stage4

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]


class Stage4Tests(unittest.TestCase):
    def test_allocation_has_79_sample_and_3_analysis_seeds(self):
        inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
        seeds = [int(s["seed"]) for s in inv["streams"]]
        self.assertEqual(len(seeds), 82)
        self.assertEqual(len(set(seeds)), 82)
        self.assertEqual(len(stream_map(inv)), 79)

    def test_profile_inference_api_is_detector_only(self):
        self.assertEqual(list(inspect.signature(DetectorProfileEstimator.estimate).parameters),
                         ["self", "calibration_detectors"])
        with self.assertRaises(ValueError):
            DetectorProfileEstimator.fit([(0.0, np.zeros((5, 39), dtype=np.uint8)),
                                          (0.01, np.zeros((5, 39), dtype=np.uint8))])

    def test_frozen_circuit_decoder_and_noiseless_fixture(self):
        report = diagnostic()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual((report["detectors"], report["observables"]), (40, 1))
        circuit, dem, matcher = build_decoder(0.008)
        self.assertEqual((circuit.num_detectors, circuit.num_observables), (40, 1))
        self.assertEqual((dem.num_detectors, dem.num_observables), (40, 1))
        pred = decode_prediction(matcher, np.zeros((4, 40), dtype=np.uint8))
        self.assertEqual(pred.shape, (4,))

    def test_primary_is_equal_stratum_weighted_and_seeded(self):
        differences = {p: np.full(7, -0.001 * (i + 1)) for i, p in enumerate(NONZERO_P)}
        self.assertAlmostEqual(stratified_primary(differences), -0.0025)
        a = stratified_cluster_bootstrap(differences, rng=np.random.default_rng(4200000080), resamples=100)
        b = stratified_cluster_bootstrap(differences, rng=np.random.default_rng(4200000080), resamples=100)
        np.testing.assert_array_equal(a, b)
        observed, pvalue = monte_carlo_signflip(
            differences, rng=np.random.default_rng(4200000081), assignments=1000)
        self.assertAlmostEqual(observed, -0.0025)
        self.assertTrue(0 < pvalue <= 1)
        self.assertGreaterEqual(exact_stratum_signflip(np.ones(7) * -0.1), 0)

    def test_holm_and_separate_zero_harm_gate(self):
        self.assertEqual(holm_adjust({"a": .01, "b": .02, "c": .5, "d": .8}),
                         {"a": .04, "b": .06, "c": 1.0, "d": 1.0})
        estimates = {p: 7 for p in NONZERO_P}
        favorable = {p: -0.001 for p in NONZERO_P}
        good = evaluate_gate(nonzero_mae=.001, nonzero_bias=.0002,
                             within_005_by_stratum=estimates, primary_mean=-.001,
                             primary_ci_upper=-.0003, nonzero_stratum_means=favorable,
                             zero_harm_ci_upper=.0001, median_rebuild_seconds=.1,
                             peak_rss_bytes=1_000_000)
        self.assertEqual(good["status"], "PASS")
        harmed_zero = evaluate_gate(nonzero_mae=.001, nonzero_bias=.0002,
                                    within_005_by_stratum=estimates, primary_mean=-.001,
                                    primary_ci_upper=-.0003, nonzero_stratum_means=favorable,
                                    zero_harm_ci_upper=.00021, median_rebuild_seconds=.1,
                                    peak_rss_bytes=1_000_000)
        self.assertEqual(harmed_zero["checks"]["zero_burst_one_sided_harm_upper_within_0.0002"], False)

    def test_report_renderer_accepts_recomputed_result_schema(self):
        p = 0.004
        condition = {"probability": p, "shots": 7, "raw_observable_errors": 1,
                     "raw_observable_ler": 1/7, "fixed_nominal_errors": 1,
                     "fixed_nominal_ler": 1/7, "detector_estimated_errors": 0,
                     "detector_estimated_ler": 0.0, "privileged_true_probability_errors": 0,
                     "privileged_true_probability_ler": 0.0, "estimated_minus_fixed": -1/7,
                     "estimated_minus_fixed_bootstrap_95ci": [-1/7, -1/7],
                     "estimated_candidate_only": 0, "estimated_fixed_only": 1}
        totals = {k: {"errors": e, "shots": 7, "ler": e/7}
                  for k, e in (("fixed_nominal", 1), ("detector_estimated", 0),
                               ("privileged_true_probability", 0))}
        totals.update({"estimated_candidate_only_vs_fixed": 0,
                       "estimated_fixed_only_vs_fixed": 1,
                       "estimated_prediction_disagreements": 1})
        stats = {"nonzero_relative_error_reduction": 1.0, "gate_checks": {"example": True},
                 "gate_status": "FAIL", "primary_difference": -0.1,
                 "primary_bootstrap_95ci": [-0.2, 0.0], "primary_two_sided_signflip_p": .1,
                 "zero_burst_difference": 0.0, "zero_burst_one_sided_95_bootstrap_upper": .1,
                 "estimation_nonzero_mae": .001, "estimation_nonzero_bias": 0.0,
                 "estimation_within_0.005_count": {str(x): 5 for x in NONZERO_P},
                 "profile_conditional_interval_coverage": 3, "profile_conditional_interval_count": 4}
        results = {"aggregate": {"evaluation_totals": totals, "total_unique_shots": 10,
                                 "profile_shots": 1, "calibration_shots": 2,
                                 "paired_evaluation_shots": 7},
                   "statistics": stats, "per_condition": [condition],
                   "software": {"stim": "1.16.0", "pymatching": "2.4.0", "numpy": "2.5.3"},
                   "integrity": {"unique_partition_count_hash_checked": 114}}
        status = {"status": "completed", "audit_status": "PASS", "active_runtime_seconds": 3.0,
                  "peak_rss_bytes": 1000}
        with tempfile.TemporaryDirectory() as td:
            old_here = audit_stage4.HERE
            audit_stage4.HERE = Path(td)
            Path(td, "seed_audit.json").write_text(json.dumps({"recoverable_historical_seed_count": 10}),
                                                   encoding="utf-8")
            Path(td, "additional_development_seed_audit.json").write_text(
                json.dumps({"recoverable_historical_development_seed_values_union": 12}), encoding="utf-8")
            try:
                audit_stage4.write_reports(results, status)
                self.assertTrue(Path(td, "STAGE4_RESULTS.md").is_file())
                self.assertIn("FAIL", Path(td, "STAGE4_RESULTS.md").read_text(encoding="utf-8"))
            finally:
                audit_stage4.HERE = old_here


if __name__ == "__main__":
    unittest.main()
