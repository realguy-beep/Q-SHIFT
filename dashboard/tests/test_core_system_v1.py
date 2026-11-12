"""Deterministic core-contract tests. These tests do not invoke any sampler."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import stim

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = REPO_ROOT / "dashboard"
for entry in (str(REPO_ROOT), str(DASHBOARD)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from configuration import DEFAULT_CONFIG, validate_config
import seed_protocol
from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction
from qshift_core_v1.controller import (
    DecoderRegistry,
    NoiseEstimate,
    SafeDecoderSelector,
    SelectionProposal,
)
from qshift_core_v1.evaluation import evaluate_paired
from qshift_core_v1.baselines import IdentityObservableDecoder
from qshift_core_v1.pymatching_adapter import PyMatchingDecoder
from simulator import decode_matching, prepare, sample
from qshift_core_v1.seeds import SeedLedger, derive_seed


class ConstantDecoder:
    def __init__(self, name: str, value: int, *, experimental: bool = False, detector_count: int = 2):
        self.value = value
        self.metadata = DecoderMetadata(name, "test-double", "1", detector_count, 1,
                                        experimental=experimental)
        self.seen_hashes = []

    def decode(self, detectors):
        d = np.asarray(detectors)
        self.seen_hashes.append(d.tobytes())
        return DecoderPrediction(np.full((len(d), 1), self.value, dtype=np.uint8), self.metadata, 0.0)


class ConfigurationValidationTests(unittest.TestCase):
    def test_defaults_remain_valid(self):
        config = validate_config({})
        self.assertEqual(config["distance"], 3)
        self.assertEqual(config["rounds"], 5)
        self.assertIs(config["mixed_precision"], True)

    def test_coercive_types_are_rejected(self):
        cases = [
            {"distance": True},
            {"distance": "3"},
            {"training_shots": 10.5},
            {"seed": "42"},
            {"mixed_precision": "false"},
            {"gate_p": "0.003"},
            {"learning_rate": float("nan")},
            {"bias_ratio": float("inf")},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                validate_config(case)

    def test_stim_seed_range_is_checked_before_sampling(self):
        with self.assertRaisesRegex(ValueError, "Seed must be"):
            validate_config({"seed": 2_147_483_648})
        with self.assertRaisesRegex(ValueError, "distance must be an integer"):
            from simulator import prepare
            prepare({"distance": "3"})

    def test_sampling_inputs_fail_before_sampler_invocation(self):
        class NeverSampler:
            num_observables = 1
            num_detectors = 40
            def compile_detector_sampler(self, **_kwargs):
                raise AssertionError("sampler must not be invoked for invalid inputs")

        for seed, shots in ((True, 1), (0, 1), (1, 0), (1, 1.5)):
            with self.subTest(seed=seed, shots=shots), self.assertRaises(ValueError):
                sample(NeverSampler(), seed, shots)

    def test_sampling_failure_has_seed_shot_context_and_keeps_cause(self):
        class BrokenSampler:
            num_observables = 1
            num_detectors = 40
            def compile_detector_sampler(self, **_kwargs):
                raise OSError("fixture sampler failure")

        with self.assertRaisesRegex(RuntimeError, "seed=123, shots=5") as caught:
            sample(BrokenSampler(), 123, 5)
        self.assertIsInstance(caught.exception.__cause__, OSError)

    def test_sampling_checks_dimensions_without_a_stim_sampler(self):
        class MalformedSampler:
            num_observables = 1
            num_detectors = 40
            def compile_detector_sampler(self, **_kwargs):
                return self
            def sample(self, *, shots, separate_observables):
                self.asserted = (shots, separate_observables)
                return np.zeros((shots, 39), dtype=bool), np.zeros((shots, 1), dtype=bool)

        with self.assertRaisesRegex(RuntimeError, "unexpected sampled arrays"):
            sample(MalformedSampler(), 123, 5)

    def test_non_object_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            validate_config(None)


class PyMatchingAdapterTests(unittest.TestCase):
    def test_dem_constructor_and_decode_share_correlation_mode(self):
        dem = stim.DetectorErrorModel("error(0.1) D0 L0")
        for correlation_mode in (False, True):
            with self.subTest(correlation_mode=correlation_mode):
                decoder = PyMatchingDecoder.from_detector_error_model(
                    dem, correlation_mode=correlation_mode, name="fixture"
                )
                result = decoder.decode(np.array([[0], [1]], dtype=np.uint8))
                self.assertEqual(result.bits.shape, (2, 1))
                self.assertEqual(result.bits[:, 0].tolist(), [0, 1])
                self.assertEqual(decoder.metadata.correlation_mode, correlation_mode)
                self.assertGreaterEqual(result.elapsed_seconds, 0)

    def test_legacy_dashboard_decode_preserves_one_observable_shape_and_mode(self):
        # Highest detector ID gives the 40-detector interface expected by the
        # existing dashboard; construction mirrors the frozen Phase 2B bank.
        dem = stim.DetectorErrorModel("error(0.1) D39 L0")
        import pymatching
        model = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
        prediction = decode_matching(model, np.zeros((3, 40), dtype=np.uint8))
        self.assertEqual(prediction.shape, (3,))
        self.assertTrue(np.all(prediction == 0))

    def test_actual_qshift_zero_syndrome_fixture_decodes_zero(self):
        circuit, _, _, matching, _, _ = prepare(DEFAULT_CONFIG)
        zero_syndrome = np.zeros((1, circuit.num_detectors), dtype=np.uint8)
        prediction = decode_matching(matching, zero_syndrome)
        self.assertEqual(circuit.num_detectors, 40)
        self.assertEqual(circuit.num_observables, 1)
        self.assertEqual(prediction.tolist(), [0])

    def test_decoder_rejects_wrong_dimensions_and_nonbinary_data(self):
        decoder = PyMatchingDecoder.from_detector_error_model(
            stim.DetectorErrorModel("error(0.1) D0 L0"), correlation_mode=True
        )
        with self.assertRaises(ValueError):
            decoder.decode(np.zeros((2, 2), dtype=np.uint8))
        with self.assertRaises(ValueError):
            decoder.decode(np.array([[2]], dtype=np.uint8))


class ControllerContractTests(unittest.TestCase):
    def setUp(self):
        self.registry = DecoderRegistry()
        self.registry.register("fixed", ConstantDecoder("fixed", 0))
        self.registry.register("specialist", ConstantDecoder("specialist", 1, experimental=True))
        self.selector = SafeDecoderSelector(
            self.registry, fallback_name="fixed", minimum_confidence=0.8,
            hysteresis_blocks=2, minimum_dwell_blocks=2, allow_experimental=True,
        )
        self.estimate = NoiseEstimate({"burst_probability": 0.02}, 0.95, 256)

    def test_detector_only_proposal_requires_prior_block_and_hysteresis(self):
        first = self.selector.choose(0, SelectionProposal("specialist", .95, -1, "profile match", self.estimate))
        second = self.selector.choose(
            1, SelectionProposal("specialist", .95, 0, "profile match", self.estimate),
            configured_noise={"nominal_probability": .003},
        )
        self.assertEqual(first.selected_decoder, "fixed")
        self.assertEqual(second.selected_decoder, "specialist")
        self.assertTrue(second.switched)
        self.assertEqual(second.estimated_noise["burst_probability"], .02)
        self.assertEqual(second.configured_noise["nominal_probability"], .003)

    def test_same_block_or_future_estimate_fails_closed(self):
        decision = self.selector.choose(0, SelectionProposal("specialist", .99, 0, "invalid", self.estimate))
        self.assertEqual(decision.selected_decoder, "fixed")
        self.assertTrue(decision.fallback_used)
        self.assertIn("non-causal", decision.reason)

    def test_low_confidence_unknown_and_missing_estimates_fall_back(self):
        proposals = [
            SelectionProposal("specialist", .2, -1, "low", self.estimate),
            SelectionProposal("missing", .99, -1, "unknown", self.estimate),
            SelectionProposal("specialist", .99, -1, "no estimate", None),
        ]
        for block, proposal in enumerate(proposals):
            with self.subTest(proposal=proposal):
                self.assertEqual(self.selector.choose(block, proposal).selected_decoder, "fixed")

    def test_invalid_proposal_object_fails_closed(self):
        decision = self.selector.choose(0, object())
        self.assertEqual(decision.selected_decoder, "fixed")
        self.assertIn("invalid proposal", decision.reason)

    def test_effective_confidence_cannot_exceed_estimator_confidence(self):
        weak = NoiseEstimate({"burst_probability": .02}, .3, 256)
        decision = self.selector.choose(0, SelectionProposal("specialist", .99, -1, "weak estimate", weak))
        self.assertEqual(decision.selected_decoder, "fixed")
        self.assertEqual(decision.confidence, .3)

    def test_decision_logs_conservative_effective_confidence(self):
        estimate = NoiseEstimate({"burst_probability": .02}, .85, 256)
        decision = self.selector.choose(0, SelectionProposal("specialist", .99, -1, "profile", estimate))
        self.assertEqual(decision.confidence, .85)

    def test_experimental_decoder_requires_explicit_opt_in(self):
        with self.assertRaises(ValueError):
            SafeDecoderSelector(self.registry, fallback_name="specialist")
        enabled = SafeDecoderSelector(self.registry, fallback_name="fixed", allow_experimental=True)
        self.assertEqual(enabled.fallback_name, "fixed")

    def test_estimates_cannot_label_themselves_as_hidden_regime_truth(self):
        valid = NoiseEstimate({"burst_probability": .01, "bias_ratio": 10.0}, .9, 10)
        self.assertEqual(valid.parameters["bias_ratio"], 10.0)
        with self.assertRaisesRegex(ValueError, "detector-only"):
            NoiseEstimate({"burst_probability": .01}, .9, 10, source="hidden_regime")


class PairedEvaluationTests(unittest.TestCase):
    def test_identity_baseline_is_zero_observable_prediction(self):
        baseline = IdentityObservableDecoder(detector_count=2, observable_count=1)
        result = baseline.decode(np.array([[0, 1], [1, 0]], dtype=np.uint8))
        self.assertEqual(result.bits.tolist(), [[0], [0]])
        self.assertIn("Always predicts observable mask zero", baseline.metadata.construction_provenance)

    def test_all_decoders_receive_identical_detectors_and_labels_only_score_after_decode(self):
        detectors = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.uint8)
        labels = np.array([0, 0, 1, 1], dtype=np.uint8)
        fixed = ConstantDecoder("fixed", 0)
        candidate = ConstantDecoder("candidate", 1)
        record = evaluate_paired(
            detectors, labels, {"fixed": fixed, "candidate": candidate},
            baseline_name="fixed", scope="development", sample_id="fixture-01",
        )
        self.assertEqual(fixed.seen_hashes, candidate.seen_hashes)
        self.assertEqual(record["shots"], 4)
        self.assertEqual(record["records"]["fixed"]["errors"], 2)
        self.assertEqual(record["records"]["candidate"]["errors"], 2)
        self.assertEqual(record["records"]["candidate"]["prediction_disagreements_vs_baseline"], 4)
        self.assertEqual(record["records"]["candidate"]["candidate_only_failures"], 2)
        self.assertEqual(record["records"]["candidate"]["baseline_only_failures"], 2)
        self.assertTrue(record["sample_sha256"])

    def test_protected_test_scope_is_refused(self):
        decoder = ConstantDecoder("fixed", 0)
        with self.assertRaises(PermissionError):
            evaluate_paired(np.zeros((1, 2)), np.zeros(1), {"fixed": decoder},
                            baseline_name="fixed", scope="protected-test", sample_id="sealed")

    def test_evaluation_rejects_label_shape_and_decoder_dimension_mismatch(self):
        decoder = ConstantDecoder("fixed", 0)
        with self.assertRaises(ValueError):
            evaluate_paired(np.zeros((2, 2)), np.zeros(1), {"fixed": decoder},
                            baseline_name="fixed", scope="development", sample_id="bad")
        wrong = ConstantDecoder("wide", 0, detector_count=3)
        with self.assertRaises(ValueError):
            evaluate_paired(np.zeros((1, 2)), np.zeros(1), {"wide": wrong},
                            baseline_name="wide", scope="development", sample_id="bad")


class SeedContractTests(unittest.TestCase):
    def test_domain_separated_seed_derivation_is_reproducible_and_screened(self):
        first = derive_seed(123456, "calibration", 0)
        self.assertEqual(first, derive_seed(123456, "calibration", 0))
        self.assertNotEqual(first, derive_seed(123456, "evaluation", 0))
        ledger = SeedLedger()
        self.assertEqual(ledger.derive(123456, "calibration", 0), first)
        with self.assertRaisesRegex(ValueError, "collision"):
            ledger.add(first, "duplicate")

    def test_existing_dashboard_seed_planner_rejects_coercive_types(self):
        for arguments in (
            (True, 8_000, 1_000, 1_000, 256),
            (10, 8_000.5, 1_000, 1_000, 256),
            (10, 8_000, 1_000, 1_000, True),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                seed_protocol.seed_plan(*arguments)


class DashboardSemanticsTests(unittest.TestCase):
    def test_page_distinguishes_logical_prediction_from_physical_correction(self):
        html = (REPO_ROOT / "dashboard" / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn("configured simulation input", html)
        self.assertIn("does not provide a physical gate sequence", html)
        self.assertIn("simulated observable labels", html)


if __name__ == "__main__":
    unittest.main()
