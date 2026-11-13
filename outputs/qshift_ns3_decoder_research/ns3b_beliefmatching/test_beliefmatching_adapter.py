from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest

import numpy as np
import stim

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
WORKSPACE = PACKAGE.parents[1]
NS2B_PROJECT = Path(os.environ.get(
    "QSHIFT_NS2B_ROOT", str(WORKSPACE.parent / "qshift-ns2b-sampling-model-identity")
))
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(PACKAGE / ".." / "phase3a_correlated_noise_preflight"))
sys.path.insert(0, str(PACKAGE / ".." / "phase2b_pauli_bias"))
sys.path.insert(0, str(WORKSPACE / "outputs" / "qshift_ns3_decoder_research"))
sys.path.insert(0, str(NS2B_PROJECT))

from beliefmatching_adapter import (  # noqa: E402
    BeliefMatchingAdapter,
    BeliefMatchingConstructionError,
    BeliefMatchingContractError,
    BeliefMatchingDisabledError,
)
from decoder_prototypes import DetectorModel, ExactMAPOracle  # noqa: E402


class FakeDecoder:
    def __init__(self, predictions=None, exception=None):
        self.predictions = predictions
        self.exception = exception
        self.closed = False

    def decode_batch(self, x):
        if self.exception:
            raise self.exception
        return np.asarray(self.predictions)

    def close(self):
        self.closed = True


def toy_models():
    dem = stim.DetectorErrorModel("error(0.1) D0 L0\nerror(0.2) D1")
    sampling = stim.Circuit(
        "M 0 1\nDETECTOR rec[-2]\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-2]"
    )
    return dem, sampling


def fake_adapter(predictions, *, dem=None, enabled=True):
    dem = dem or toy_models()[0]
    sampling = toy_models()[1]
    return BeliefMatchingAdapter.from_dem(
        decoder_dem=dem,
        sampling_circuit=sampling,
        generating_noise_identity="test-generator-profile-v1",
        assumed_noise_provenance="explicit deterministic test fixture",
        enabled=enabled,
        factory=lambda model, **kwargs: FakeDecoder(predictions),
    )


class BeliefMatchingAdapterTests(unittest.TestCase):
    def test_disabled_by_default_and_does_not_construct(self):
        called = []
        dem, sampling = toy_models()
        adapter = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem, sampling_circuit=sampling,
            generating_noise_identity="generator-v1", assumed_noise_provenance="test fixture",
            factory=lambda *a, **k: called.append(True),
        )
        self.assertFalse(adapter.enabled)
        self.assertEqual(called, [])
        with self.assertRaises(BeliefMatchingDisabledError):
            adapter.decode_batch(np.zeros((1, 2), dtype=np.uint8))

    def test_toy_dem_against_exact_map_all_syndromes(self):
        dem, sampling = toy_models()
        adapter = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem, sampling_circuit=sampling,
            generating_noise_identity="independent-Bernoulli-toy",
            assumed_noise_provenance="same exact toy DEM weights supplied to oracle and BM",
            enabled=True, max_bp_iters=50,
        )
        model = DetectorModel.from_stim_dem(dem)
        x = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.uint8)
        actual = adapter.decode_batch(x)
        expected = ExactMAPOracle(model).decode_batch(x)
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(actual.dtype, np.uint8)
        self.assertEqual(actual.shape, (4, 1))

    def test_multiple_observable_outputs_keep_l_order_and_shape(self):
        dem = stim.DetectorErrorModel("error(0.1) D0 L0\nerror(0.2) D1 L1")
        sampling = stim.Circuit(
            "M 0 1\nDETECTOR rec[-2]\nDETECTOR rec[-1]\n"
            "OBSERVABLE_INCLUDE(0) rec[-2]\nOBSERVABLE_INCLUDE(1) rec[-1]"
        )
        adapter = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem,
            sampling_circuit=sampling,
            generating_noise_identity="two-observable-fixture",
            assumed_noise_provenance="two-observable deterministic independent DEM",
            enabled=True,
        )
        rows = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.uint8)
        predictions = adapter.decode_batch(rows, observable_ids=(0, 1))
        self.assertEqual(predictions.shape, (4, 2))
        np.testing.assert_array_equal(predictions, [[0, 0], [1, 0], [0, 1], [1, 1]])

    def test_input_order_shape_binary_and_immutability_guards(self):
        adapter = fake_adapter([[0]])
        x = np.array([[1, 0]], dtype=np.uint8)
        original = x.copy()
        np.testing.assert_array_equal(adapter.decode_batch(x, detector_ids=(0, 1)), [[0]])
        np.testing.assert_array_equal(x, original)
        with self.assertRaisesRegex(BeliefMatchingContractError, "detector column IDs/order"):
            adapter.decode_batch(x, detector_ids=(1, 0))
        with self.assertRaisesRegex(BeliefMatchingContractError, "shape"):
            adapter.decode_batch(np.zeros((1, 3), dtype=np.uint8))
        with self.assertRaisesRegex(BeliefMatchingContractError, "binary"):
            adapter.decode_batch(np.array([[0, 2]]))

    def test_observable_count_and_order_mismatch_rejected(self):
        adapter = fake_adapter([[0]])
        with self.assertRaisesRegex(BeliefMatchingContractError, "observable IDs/order"):
            adapter.decode_batch(np.zeros((1, 2), dtype=np.uint8), observable_ids=(1,))

    def test_invalid_prediction_shape_and_values_rejected(self):
        for prediction, pattern in (([[0, 1]], "shape"), ([[0.5]], "nonbinary"), ([[np.nan]], "finite")):
            adapter = fake_adapter(prediction)
            with self.subTest(prediction=prediction), self.assertRaisesRegex(BeliefMatchingContractError, pattern):
                adapter.decode_batch(np.zeros((1, 2), dtype=np.uint8))

    def test_construction_failure_is_contextualized(self):
        dem, sampling = toy_models()

        def fail(*args, **kwargs):
            raise RuntimeError("fixture construction failure")

        with self.assertRaisesRegex(BeliefMatchingConstructionError, "fixture construction failure"):
            BeliefMatchingAdapter.from_dem(
                decoder_dem=dem, sampling_circuit=sampling,
                generating_noise_identity="generator-v1", assumed_noise_provenance="fixture",
                enabled=True, factory=fail,
            )

    def test_dem_with_conflicting_observable_signatures_is_rejected(self):
        dem = stim.DetectorErrorModel("error(0.1) D0\nerror(0.2) D0 L0")
        sampling = stim.Circuit(
            "M 0\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-1]"
        )
        factory_called = []
        with self.assertRaisesRegex(BeliefMatchingContractError, "different observable signatures"):
            BeliefMatchingAdapter.from_dem(
                decoder_dem=dem, sampling_circuit=sampling,
                generating_noise_identity="generator-v1", assumed_noise_provenance="fixture",
                enabled=True, factory=lambda *a, **k: factory_called.append(True),
            )
        self.assertEqual(factory_called, [])

    def test_upstream_alias_counterexample_is_detected_against_exact_map(self):
        """Pin a deterministic upstream failure; the adapter must reject it."""
        import pymatching
        from beliefmatching import BeliefMatching

        dem = stim.DetectorErrorModel("error(0.002) D0\nerror(0.0005) D0 L0")
        rows = np.array([[0], [1]], dtype=np.uint8)
        exact = ExactMAPOracle(DetectorModel.from_stim_dem(dem)).decode_batch(rows)
        matching = pymatching.Matching.from_detector_error_model(dem).decode_batch(rows)
        direct_upstream = BeliefMatching(dem, max_bp_iters=30).decode_batch(rows)
        np.testing.assert_array_equal(exact, [[0], [0]])
        np.testing.assert_array_equal(matching, [[0], [0]])
        np.testing.assert_array_equal(direct_upstream.astype(np.uint8), [[0], [1]])
        with self.assertRaisesRegex(BeliefMatchingContractError, "different observable signatures"):
            BeliefMatchingAdapter.from_dem(
                decoder_dem=dem, sampling_circuit=stim.Circuit(
                    "M 0\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-1]"
                ),
                generating_noise_identity="generator-v1", assumed_noise_provenance="fixture",
                enabled=True,
            )

    def test_identity_separates_generator_and_decoder_model(self):
        dem, sampling = toy_models()
        adapter = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem, sampling_circuit=sampling,
            generating_noise_identity="generating-profile-A",
            assumed_noise_provenance="decoder assumes profile-B",
            factory=lambda *a, **k: FakeDecoder([[0]]),
        )
        self.assertNotEqual(adapter.identity.sampling_circuit_sha256, adapter.identity.decoder_dem_sha256)
        self.assertEqual(adapter.identity.generating_noise_identity, "generating-profile-A")
        self.assertEqual(adapter.identity.assumed_noise_provenance, "decoder assumes profile-B")
        self.assertTrue(adapter.identity.identity.startswith("beliefmatching-dem-sha256:"))
        self.assertEqual(adapter.identity.detector_ids, (0, 1))
        self.assertEqual(adapter.identity.observable_ids, (0,))

    def test_sampling_circuit_and_decoder_dem_dimension_mismatch_rejected(self):
        dem, _ = toy_models()
        one_detector = stim.Circuit(
            "M 0\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-1]"
        )
        with self.assertRaisesRegex(BeliefMatchingContractError, "detector count differs"):
            BeliefMatchingAdapter.from_dem(
                decoder_dem=dem,
                sampling_circuit=one_detector,
                generating_noise_identity="generator-v1",
                assumed_noise_provenance="fixture",
            )

    def test_repeatability_and_resource_cleanup(self):
        decoder = FakeDecoder([[1]])
        dem, sampling = toy_models()
        adapter = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem, sampling_circuit=sampling,
            generating_noise_identity="generator-v1", assumed_noise_provenance="fixture",
            enabled=True, factory=lambda *a, **k: decoder,
        )
        x = np.array([[0, 0]], dtype=np.uint8)
        np.testing.assert_array_equal(adapter.decode_batch(x), adapter.decode_batch(x))
        adapter.close()
        self.assertTrue(decoder.closed)
        with self.assertRaises(BeliefMatchingDisabledError):
            adapter.decode_batch(x)

    def test_qshift_five_saved_fixtures_and_pymatching(self):
        import pymatching
        import simulator

        result = json.loads((PACKAGE / "benchmark_results_ns3a.json").read_text(encoding="utf-8"))
        fixtures = np.asarray(result["qshift_fixed_model"]["fixed_syndromes"], dtype=np.uint8)
        circuit = simulator.build_spatial_burst_circuit(
            memory_basis="z", regime="balanced", distance=3, rounds=5,
            gate_p=.003, measurement_p=.003, bias_ratio=10.0,
            burst_probability=.01, burst_pair=(8, 10),
        )
        dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
        adapter = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem,
            sampling_circuit=circuit,
            generating_noise_identity="balanced-z-d3-r5 gate=.003 meas=.003 burst=.01 pair=(8,10)",
            assumed_noise_provenance="static model DEM built from declared development configuration; not a learned estimate",
            enabled=True, max_bp_iters=20,
        )
        before = fixtures.copy()
        got = adapter.decode_batch(fixtures, detector_ids=tuple(range(40)), observable_ids=(0,))
        self.assertEqual(got.shape, (5, 1))
        self.assertEqual(got.dtype, np.uint8)
        self.assertTrue(np.isin(got, (0, 1)).all())
        np.testing.assert_array_equal(fixtures, before)
        matcher = pymatching.Matching.from_detector_error_model(dem)
        pm = np.asarray(matcher.decode_batch(fixtures), dtype=np.uint8)
        self.assertEqual(pm.shape, got.shape)
        self.assertEqual(int(np.any(got != pm, axis=1).sum()), 0)
        np.testing.assert_array_equal(got, adapter.decode_batch(fixtures))
        # A one-iteration run on the single-D0 fixture is a deterministic
        # nonconvergence case for this pinned model; upstream should execute
        # its reweighted-MWPM fallback and still meet the output contract.
        fallback = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem,
            sampling_circuit=circuit,
            generating_noise_identity="balanced-z-d3-r5 gate=.003 meas=.003 burst=.01 pair=(8,10)",
            assumed_noise_provenance="static model DEM built from declared development configuration; not a learned estimate",
            enabled=True, max_bp_iters=1,
        )
        fallback_prediction = fallback.decode_batch(fixtures[1:2])
        self.assertFalse(fallback._decoder._bpd.converge)
        self.assertEqual(fallback_prediction.shape, (1, 1))
        self.assertTrue(np.isin(fallback_prediction, (0, 1)).all())

    def test_ns2c_checked_adapter_and_experimental_opt_in(self):
        import simulator
        from qshift_core_v1.decoder_runtime_v2 import (
            CheckedDecoderAdapter, CompatibilityAwareDecoderBank,
        )
        from qshift_core_v1.sampling_model_identity import (
            DEMConstructionSettingsV2, SamplingIdentity, StimDEMArtifact,
            TrustedDetectorBatchAdapter,
        )

        circuit = simulator.build_spatial_burst_circuit(
            memory_basis="z", regime="balanced", distance=3, rounds=5,
            gate_p=.003, measurement_p=.003, bias_ratio=10.0,
            burst_probability=.01, burst_pair=(8, 10),
        )
        generating_id = "qshift-balanced-z-d3-r5-development-generator-v1"
        meanings = ("Stim OBSERVABLE_INCLUDE(0) parity; 1 predicts logical observable flip",)
        sampling = SamplingIdentity.from_stim(
            circuit,
            generating_noise_model_id=generating_id,
            generating_noise_provenance={"scope": "deterministic development fixture", "sampling": False},
            code_family="rotated surface code",
            distance=3,
            rounds=5,
            memory_basis="z",
            observable_interpretations=meanings,
            observable_polarities=(1,),
        )
        artifact = StimDEMArtifact.build(
            circuit,
            DEMConstructionSettingsV2(
                decompose_errors=True,
                approximate_disjoint_errors=True,
                construction_note="NS-3B fixed Q-SHIFT deterministic decoder model",
            ),
            observable_interpretations=meanings,
            observable_polarities=(1,),
        )
        dem = artifact.dem
        adapter = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem,
            sampling_circuit=circuit,
            generating_noise_identity=generating_id,
            assumed_noise_provenance="static explicit development DEM; not estimated from detector history",
            enabled=True,
            max_bp_iters=20,
        )
        model = adapter.bind_ns2c(
            sampling_identity=sampling,
            dem_record=artifact.record,
            assumed_noise_model_id="qshift-static-burst-0.01-assumed-v1",
            assumed_noise_provenance={
                "kind": "static assumed decoder profile",
                "dem_sha256": artifact.record.dem_sha256,
                "beliefmatching_version": "0.2.0",
                "beliefmatching_commit": "4458c278bbec273c8c1a26411dadccc49222f8ef",
                "decompose_errors": True,
                "approximate_disjoint_errors": True,
            },
        )
        result = json.loads((PACKAGE / "benchmark_results_ns3a.json").read_text(encoding="utf-8"))
        fixtures = np.asarray(result["qshift_fixed_model"]["fixed_syndromes"], dtype=np.uint8)
        batch = TrustedDetectorBatchAdapter(sampling).from_stim_detector_samples(
            circuit, fixtures, column_detector_ids=tuple(range(40)),
        )
        checked = CheckedDecoderAdapter(
            adapter, model_identity=model, sampling_identity=sampling,
        )
        execution = checked.predict(batch)
        self.assertEqual(execution.status, "ok")
        self.assertEqual(execution.prediction.bits.shape, (5, 1))
        self.assertEqual(execution.prediction.bits.dtype, np.uint8)
        bank = CompatibilityAwareDecoderBank(sampling)
        with self.assertRaises(PermissionError):
            bank.register(checked)
        bank.register(checked, experimental_opt_in=True)
        self.assertEqual(bank.names(), ("beliefmatching",))


if __name__ == "__main__":
    unittest.main(verbosity=2)
