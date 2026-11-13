"""NS-2D deterministic integration tests; no Stim sampling or training."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import stim

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction
from qshift_core_v1.decoder_runtime_v2 import (
    CheckedDecoderAdapter,
    CompatibilityAwareDecoderBank,
    evaluate_paired_batch,
)
from qshift_core_v1.pymatching_adapter import PyMatchingDecoder
from qshift_core_v1.research_adapters.beliefmatching_adapter_ns3b import (
    BeliefMatchingAdapter,
    BeliefMatchingContractError,
    BeliefMatchingDisabledError,
)
from qshift_core_v1.research_adapters.beliefmatching_integration_ns2d import (
    register_beliefmatching,
)
from qshift_core_v1.sampling_model_identity import (
    DEMConstructionSettingsV2,
    DecoderModelIdentity,
    SamplingIdentity,
    StimDEMArtifact,
    TrustedDetectorBatchAdapter,
)

_SIMULATOR_PATH = ROOT / "outputs" / "phase3a_correlated_noise_preflight" / "simulator.py"
_SIMULATOR_SPEC = importlib.util.spec_from_file_location(
    "qshift_ns2d_correlated_simulator_fixture", _SIMULATOR_PATH,
)
if _SIMULATOR_SPEC is None or _SIMULATOR_SPEC.loader is None:
    raise RuntimeError(f"Cannot load deterministic circuit builder at {_SIMULATOR_PATH}")
simulator = importlib.util.module_from_spec(_SIMULATOR_SPEC)
_SIMULATOR_SPEC.loader.exec_module(simulator)


GENERATOR_ID = "qshift-ns3b-balanced-z-d3-r5-static-burst-v1"
NOISE_ID = "shared-qshift-decomposed-dem-static-model-v1"
OBSERVABLE_MEANING = "Stim OBSERVABLE_INCLUDE(0) parity; 1 predicts logical observable flip"
NOISE_PROVENANCE = {
    "source": "shared explicit deterministic development fixture model",
    "gate_p": 0.003,
    "measurement_p": 0.003,
    "bias_ratio": 10.0,
    "burst_probability": 0.01,
    "burst_pair": [8, 10],
    "dem_decompose_errors": True,
    "dem_approximate_disjoint_errors": True,
}


def _bundle():
    circuit = simulator.build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=0.003, measurement_p=0.003, bias_ratio=10.0,
        burst_probability=0.01, burst_pair=(8, 10),
    )
    sampling = SamplingIdentity.from_stim(
        circuit,
        generating_noise_model_id=GENERATOR_ID,
        generating_noise_provenance={**NOISE_PROVENANCE, "role": "data-generating circuit"},
        code_family="rotated_surface_code", distance=3, rounds=5, memory_basis="z",
        observable_interpretations=(OBSERVABLE_MEANING,), observable_polarities=(1,),
    )
    artifact = StimDEMArtifact.build(
        circuit,
        DEMConstructionSettingsV2(
            decompose_errors=True,
            approximate_disjoint_errors=True,
            construction_note="NS-3B handoff DEM conversion; deterministic integration only",
        ),
        observable_interpretations=(OBSERVABLE_MEANING,), observable_polarities=(1,),
    )
    return circuit, sampling, artifact


def _pymatching_model(sampling, artifact, decoder):
    return DecoderModelIdentity.create(
        sampling, decoder.metadata, dem_record=artifact.record,
        decoder_assumed_noise_model_id=NOISE_ID,
        decoder_assumed_noise_provenance=NOISE_PROVENANCE,
        correlation_semantics=(
            "PyMatching correlation-enabled graph construction and batch decode"
            if decoder.metadata.correlation_mode
            else "PyMatching correlation-disabled graph construction and batch decode"
        ),
    )


class _FailingDecoder:
    def __init__(self, metadata):
        self.metadata = metadata

    def decode(self, detectors):
        raise RuntimeError("deterministic integration failure fixture")


class BeliefMatchingNS2CIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuit, cls.sampling, cls.artifact = _bundle()
        cls.bank = CompatibilityAwareDecoderBank(cls.sampling)
        cls.pm_decoders = {}
        cls.pm_construction_seconds = {}
        for correlation_mode, name in ((False, "pymatching_ordinary"), (True, "pymatching_correlated")):
            import time
            started = time.perf_counter()
            decoder = PyMatchingDecoder.from_detector_error_model(
                cls.artifact.dem, correlation_mode=correlation_mode,
                name=name, noise_model_id=NOISE_ID, experimental=False,
            )
            model = _pymatching_model(cls.sampling, cls.artifact, decoder)
            checked = CheckedDecoderAdapter(
                decoder, model_identity=model, sampling_identity=cls.sampling,
            )
            cls.bank.register(checked)
            cls.pm_decoders[name] = decoder
            cls.pm_construction_seconds[name] = max(0.0, time.perf_counter() - started)

        cls.bm_registration = register_beliefmatching(
            cls.bank,
            sampling_circuit=cls.circuit,
            sampling_identity=cls.sampling,
            dem_artifact=cls.artifact,
            assumed_noise_model_id=NOISE_ID,
            assumed_noise_provenance=NOISE_PROVENANCE,
            information_reference_decoder="pymatching_ordinary",
            experimental_opt_in=True,
            max_bp_iters=20,
        )
        cls.detectors = np.zeros((5, len(cls.sampling.detector_ids)), dtype=np.uint8)
        cls.detectors[1, 0] = 1
        cls.detectors[2, 1] = 1
        cls.detectors[3, [8, 10]] = 1
        cls.detectors[4, -1] = 1
        cls.batch = TrustedDetectorBatchAdapter(cls.sampling).from_stim_detector_samples(
            cls.circuit, cls.detectors, column_detector_ids=cls.sampling.detector_ids,
        )
        cls.report = evaluate_paired_batch(
            cls.bank,
            cls.batch,
            decoder_names=("pymatching_ordinary", "pymatching_correlated", "beliefmatching"),
            baseline_name="pymatching_ordinary",
            scope="development",
            sample_id="ns2d-fixed-detector-fixture-v1",
            observables=None,
        )

    @classmethod
    def tearDownClass(cls):
        cls.bm_registration.adapter.close()

    def _bank_with_reference(self):
        bank = CompatibilityAwareDecoderBank(self.sampling)
        baseline = self.bank.adapter("pymatching_ordinary")
        bank.register(baseline)
        return bank, baseline

    def _registration_kwargs(self, bank):
        return {
            "bank": bank,
            "sampling_circuit": self.circuit,
            "sampling_identity": self.sampling,
            "dem_artifact": self.artifact,
            "assumed_noise_model_id": NOISE_ID,
            "assumed_noise_provenance": NOISE_PROVENANCE,
            "information_reference_decoder": "pymatching_ordinary",
            "experimental_opt_in": True,
            "max_bp_iters": 20,
        }

    def test_dem_identity_and_information_access_match_across_decoder_arms(self):
        ids = self.report["sample_identity"]["decoder_model_identity_sha256"]
        self.assertEqual(len(set(ids.values())), 3)  # distinct decoder-model records
        for name in self.bank.names():
            model = self.bank.adapter(name).model_identity
            self.assertEqual(model.sampling_identity_sha256, self.sampling.identity_sha256)
            self.assertEqual(model.dem_record.dem_sha256, self.artifact.record.dem_sha256)
            self.assertEqual(model.decoder_assumed_noise_model_id, NOISE_ID)
            self.assertEqual(
                model.decoder_assumed_noise_provenance_json,
                self.bm_registration.model_identity.decoder_assumed_noise_provenance_json,
            )
        bm_model = self.bm_registration.model_identity
        self.assertEqual(bm_model.metadata.name, "beliefmatching")
        self.assertTrue(bm_model.metadata.experimental)
        self.assertEqual(bm_model.metadata.observable_count, 1)
        self.assertEqual(bm_model.metadata.detector_count, self.artifact.record.detector_count)
        reference = self.bank.adapter("pymatching_ordinary").model_identity
        self.assertEqual(bm_model.dem_record.dem_sha256, reference.dem_record.dem_sha256)
        self.assertEqual(
            bm_model.decoder_assumed_noise_provenance_json,
            reference.decoder_assumed_noise_provenance_json,
        )

    def test_same_fixed_arrays_decode_in_all_arms_with_checked_outputs(self):
        self.assertEqual(self.batch.shape, (5, 40))
        self.assertEqual(self.report["sample_identity"]["detector_content_sha256"], self.batch.content_sha256)
        self.assertEqual(self.report["label_isolation"].startswith("Decoder implementations received detector-only"), True)
        self.assertIsNone(self.report["records"]["beliefmatching"]["logical_error_rate"])
        self.assertEqual(self.report["shots"], 5)
        direct = {
            name: self.bank.adapter(name).predict(self.batch)
            for name in ("pymatching_ordinary", "pymatching_correlated", "beliefmatching")
        }
        for name, execution in direct.items():
            self.assertEqual(execution.status, "ok")
            self.assertEqual(execution.prediction.bits.shape, (5, 1))
            self.assertEqual(execution.prediction.bits.dtype, np.uint8)
            self.assertEqual(
                self.report["records"][name]["prediction_sha256"],
                hashlib.sha256(execution.prediction.bits.tobytes(order="C")).hexdigest(),
            )
        self.assertEqual(self.detectors.tobytes(), self.batch.detector_bits.tobytes())

    def test_pymatching_modes_are_explicit_and_correlated_path_is_unchanged(self):
        ordinary = self.pm_decoders["pymatching_ordinary"]
        correlated = self.pm_decoders["pymatching_correlated"]
        self.assertIs(ordinary.metadata.correlation_mode, False)
        self.assertIs(correlated.metadata.correlation_mode, True)
        np.testing.assert_array_equal(
            ordinary.decode(self.detectors.copy()).bits,
            self.bank.adapter("pymatching_ordinary").predict(self.batch).prediction.bits,
        )
        np.testing.assert_array_equal(
            correlated.decode(self.detectors.copy()).bits,
            self.bank.adapter("pymatching_correlated").predict(self.batch).prediction.bits,
        )

    def test_wrong_detector_order_fails_closed_at_batch_and_adapter_boundaries(self):
        wrong = tuple(reversed(self.sampling.detector_ids))
        with self.assertRaisesRegex(ValueError, "Detector columns"):
            TrustedDetectorBatchAdapter(self.sampling).from_stim_detector_samples(
                self.circuit, self.detectors, column_detector_ids=wrong,
            )
        with self.assertRaisesRegex(BeliefMatchingContractError, "detector column IDs/order"):
            self.bm_registration.adapter.decode_batch(self.detectors, detector_ids=wrong)

    def test_alias_collision_guard_rejects_before_upstream_construction(self):
        bad_dem = stim.DetectorErrorModel("error(0.002) D0\nerror(0.0005) D0 L0")
        one_detector_circuit = stim.Circuit(
            "M 0\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-1]"
        )
        constructed = []
        with self.assertRaisesRegex(BeliefMatchingContractError, "different observable signatures"):
            BeliefMatchingAdapter.from_dem(
                decoder_dem=bad_dem,
                sampling_circuit=one_detector_circuit,
                generating_noise_identity="alias-guard-fixture",
                assumed_noise_provenance="deterministic collision test",
                enabled=True,
                factory=lambda *args, **kwargs: constructed.append(True),
            )
        self.assertEqual(constructed, [])

    def test_two_observable_order_is_checked_explicitly(self):
        circuit = stim.Circuit(
            "R 0 1\nX_ERROR(0.1) 0\nX_ERROR(0.2) 1\nM 0 1\n"
            "DETECTOR rec[-2]\nDETECTOR rec[-1]\n"
            "OBSERVABLE_INCLUDE(0) rec[-2]\nOBSERVABLE_INCLUDE(1) rec[-1]"
        )
        dem = circuit.detector_error_model(
            decompose_errors=True, approximate_disjoint_errors=True,
        )
        adapter = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem,
            sampling_circuit=circuit,
            generating_noise_identity="two-observable-fixture",
            assumed_noise_provenance="explicit deterministic two-observable fixture",
            enabled=True,
        )
        rows = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.uint8)
        prediction = adapter.decode_batch(rows, detector_ids=(0, 1), observable_ids=(0, 1))
        self.assertEqual(prediction.shape, (4, 2))
        with self.assertRaisesRegex(BeliefMatchingContractError, "observable IDs/order"):
            adapter.decode_batch(rows, detector_ids=(0, 1), observable_ids=(1, 0))
        adapter.close()

    def test_opt_in_and_unsupported_dem_settings_fail_closed(self):
        bank = CompatibilityAwareDecoderBank(self.sampling)
        with self.assertRaises(PermissionError):
            register_beliefmatching(
                bank, sampling_circuit=self.circuit, sampling_identity=self.sampling,
                dem_artifact=self.artifact, assumed_noise_model_id=NOISE_ID,
                assumed_noise_provenance=NOISE_PROVENANCE,
                information_reference_decoder="pymatching_ordinary",
            )
        small_circuit = stim.Circuit(
            "R 0\nX_ERROR(0.1) 0\nM 0\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-1]"
        )
        small_meaning = "Stim observable 0 from deterministic settings fixture"
        small_sampling = SamplingIdentity.from_stim(
            small_circuit, generating_noise_model_id="settings-fixture-generator",
            generating_noise_provenance={"kind": "no-sampler settings test"},
            code_family="toy-contract-fixture", distance=1, rounds=1, memory_basis="z",
            observable_interpretations=(small_meaning,), observable_polarities=(1,),
        )
        unsupported = StimDEMArtifact.build(
            small_circuit,
            DEMConstructionSettingsV2(
                decompose_errors=True, approximate_disjoint_errors=False,
                construction_note="negative settings fixture",
            ),
            observable_interpretations=(small_meaning,), observable_polarities=(1,),
        )
        with self.assertRaisesRegex(ValueError, "approximate_disjoint_errors=True"):
            register_beliefmatching(
                CompatibilityAwareDecoderBank(small_sampling),
                sampling_circuit=small_circuit, sampling_identity=small_sampling,
                dem_artifact=unsupported, assumed_noise_model_id="settings-fixture-model",
                assumed_noise_provenance={"kind": "settings mismatch"}, experimental_opt_in=True,
                information_reference_decoder="pymatching_ordinary",
            )
        self.assertEqual(bank.names(), ())

    def test_information_parity_requires_a_matching_registered_reference(self):
        bank = CompatibilityAwareDecoderBank(self.sampling)
        with self.assertRaisesRegex(ValueError, "not registered"):
            register_beliefmatching(
                bank, sampling_circuit=self.circuit, sampling_identity=self.sampling,
                dem_artifact=self.artifact, assumed_noise_model_id=NOISE_ID,
                assumed_noise_provenance=NOISE_PROVENANCE,
                information_reference_decoder="pymatching_ordinary",
                experimental_opt_in=True,
            )
        reference = self.bank.adapter("pymatching_ordinary")
        bank.register(reference)
        with self.assertRaisesRegex(ValueError, "noise provenance differ"):
            register_beliefmatching(
                bank, sampling_circuit=self.circuit, sampling_identity=self.sampling,
                dem_artifact=self.artifact, assumed_noise_model_id=NOISE_ID,
                assumed_noise_provenance={**NOISE_PROVENANCE, "measurement_p": 0.004},
                information_reference_decoder="pymatching_ordinary",
                experimental_opt_in=True,
            )

    def test_construction_failure_does_not_register_candidate(self):
        bank, baseline = self._bank_with_reference()
        before = bank.names()
        with patch.object(
            BeliefMatchingAdapter, "from_dem",
            side_effect=RuntimeError("injected construction failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected construction failure"):
                register_beliefmatching(**self._registration_kwargs(bank))
        self.assertEqual(bank.names(), before)
        self.assertIs(bank.adapter("pymatching_ordinary"), baseline)
        self.assertNotIn("beliefmatching", bank.names())

    def test_binding_failure_closes_constructed_adapter_without_registration(self):
        bank, baseline = self._bank_with_reference()
        before = bank.names()
        constructed = []
        original_factory = BeliefMatchingAdapter.from_dem

        def track_construction(**kwargs):
            adapter = original_factory(**kwargs)
            constructed.append(adapter)
            return adapter

        def fail_binding(self, **kwargs):
            raise RuntimeError("injected binding failure")

        with patch.object(BeliefMatchingAdapter, "from_dem", side_effect=track_construction):
            with patch.object(BeliefMatchingAdapter, "bind_ns2c", new=fail_binding):
                with self.assertRaisesRegex(RuntimeError, "injected binding failure"):
                    register_beliefmatching(**self._registration_kwargs(bank))

        self.assertEqual(len(constructed), 1)
        self.assertFalse(constructed[0].enabled)
        with self.assertRaises(BeliefMatchingDisabledError):
            constructed[0].decode_batch(np.zeros((1, len(self.sampling.detector_ids)), dtype=np.uint8))
        self.assertEqual(bank.names(), before)
        self.assertIs(bank.adapter("pymatching_ordinary"), baseline)

    def test_registration_failure_closes_candidate_and_preserves_bank(self):
        bank, baseline = self._bank_with_reference()
        before = bank.names()
        constructed = []
        original_factory = BeliefMatchingAdapter.from_dem

        def track_construction(**kwargs):
            adapter = original_factory(**kwargs)
            constructed.append(adapter)
            return adapter

        def fail_registration(*args, **kwargs):
            # Inject failure before the bank mutates either registry.
            raise RuntimeError("injected registration failure")

        with patch.object(BeliefMatchingAdapter, "from_dem", side_effect=track_construction):
            with patch.object(bank, "register", side_effect=fail_registration):
                with self.assertRaisesRegex(RuntimeError, "injected registration failure"):
                    register_beliefmatching(**self._registration_kwargs(bank))

        self.assertEqual(len(constructed), 1)
        self.assertFalse(constructed[0].enabled)
        with self.assertRaises(BeliefMatchingDisabledError):
            constructed[0].decode_batch(np.zeros((1, len(self.sampling.detector_ids)), dtype=np.uint8))
        self.assertEqual(bank.names(), before)
        self.assertIs(bank.adapter("pymatching_ordinary"), baseline)
        with self.assertRaises(KeyError):
            bank.adapter("beliefmatching")

    def test_actual_duplicate_registration_failure_keeps_original_and_closes_new_candidate(self):
        bank, baseline = self._bank_with_reference()
        duplicate_metadata = DecoderMetadata(
            name="beliefmatching", implementation="duplicate registration fixture", version="1",
            detector_count=self.artifact.record.detector_count, observable_count=1,
            noise_model_id=NOISE_ID, construction_provenance="deterministic duplicate-name test",
            experimental=True,
        )
        duplicate_implementation = _FailingDecoder(duplicate_metadata)
        duplicate_identity = DecoderModelIdentity.create(
            self.sampling, duplicate_metadata, dem_record=self.artifact.record,
            decoder_assumed_noise_model_id=NOISE_ID,
            decoder_assumed_noise_provenance=NOISE_PROVENANCE,
            correlation_semantics=None,
        )
        duplicate_adapter = CheckedDecoderAdapter(
            duplicate_implementation, model_identity=duplicate_identity,
            sampling_identity=self.sampling,
        )
        bank.register(duplicate_adapter, experimental_opt_in=True)
        before = bank.names()
        constructed = []
        original_factory = BeliefMatchingAdapter.from_dem

        def track_construction(**kwargs):
            adapter = original_factory(**kwargs)
            constructed.append(adapter)
            return adapter

        with patch.object(BeliefMatchingAdapter, "from_dem", side_effect=track_construction):
            with self.assertRaisesRegex(ValueError, "already registered"):
                register_beliefmatching(**self._registration_kwargs(bank))

        self.assertEqual(len(constructed), 1)
        self.assertFalse(constructed[0].enabled)
        with self.assertRaises(BeliefMatchingDisabledError):
            constructed[0].decode_batch(np.zeros((1, len(self.sampling.detector_ids)), dtype=np.uint8))
        self.assertEqual(bank.names(), before)
        self.assertIs(bank.adapter("pymatching_ordinary"), baseline)
        self.assertIs(bank.adapter("beliefmatching"), duplicate_adapter)
        self.assertIs(bank._registry.get("beliefmatching"), duplicate_implementation)

    def test_construction_and_inference_timing_are_reported_separately(self):
        self.assertGreaterEqual(self.bm_registration.construction_seconds, 0.0)
        self.assertGreaterEqual(self.pm_construction_seconds["pymatching_ordinary"], 0.0)
        for name, row in self.report["records"].items():
            self.assertEqual(row["status"], "ok", name)
            self.assertGreaterEqual(row["wall_seconds"], 0.0)
            self.assertGreaterEqual(row["decoder_reported_seconds"], 0.0)
        self.assertGreaterEqual(
            self.report["records"]["beliefmatching"]["wall_seconds"], 0.0,
        )

    def test_failed_decoder_is_reported_without_prediction_substitution(self):
        bank = CompatibilityAwareDecoderBank(self.sampling)
        baseline = self.bank.adapter("pymatching_ordinary")
        bank.register(baseline)
        metadata = DecoderMetadata(
            name="fixture_failure", implementation="failure fixture", version="1",
            detector_count=self.artifact.record.detector_count, observable_count=1,
            noise_model_id=NOISE_ID, construction_provenance="deliberate failure test",
        )
        model = DecoderModelIdentity.create(
            self.sampling, metadata, dem_record=self.artifact.record,
            decoder_assumed_noise_model_id=NOISE_ID,
            decoder_assumed_noise_provenance=NOISE_PROVENANCE,
            correlation_semantics=None,
        )
        bank.register(CheckedDecoderAdapter(
            _FailingDecoder(metadata), model_identity=model, sampling_identity=self.sampling,
        ))
        report = evaluate_paired_batch(
            bank, self.batch, decoder_names=("pymatching_ordinary", "fixture_failure"),
            baseline_name="pymatching_ordinary", scope="development",
            sample_id="ns2d-failure-fixture",
        )
        self.assertEqual(report["records"]["pymatching_ordinary"]["status"], "ok")
        self.assertEqual(report["records"]["fixture_failure"]["status"], "failed")
        self.assertIsNone(report["records"]["fixture_failure"]["prediction_sha256"])
        self.assertFalse(report["paired_vs_baseline"]["fixture_failure"]["available"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
