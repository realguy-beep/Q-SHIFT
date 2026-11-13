"""NS-2B deterministic contract tests; no sampler or stochastic shots invoked."""
from __future__ import annotations

from dataclasses import replace
import sys
from pathlib import Path
import unittest

import numpy as np
import stim

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction
from qshift_core_v1.controller import NoiseEstimate, SelectionProposal
from qshift_core_v1.sampling_model_identity import (
    DEMConstructionSettingsV2, DecoderModelIdentity, IdentityAwareDecoderRegistry,
    SamplingIdentity, StimDEMArtifact, TrustedDetectorBatchAdapter,
    assert_model_compatible, decode_model_checked, evaluate_identity_aware_paired,
)

OBSERVABLE_MEANING = "Stim observable 0; bit 1 denotes logical Z-memory parity flip"


def _circuit(gate_p: float = 0.001, meas_p: float = 0.006) -> stim.Circuit:
    return stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=3, rounds=5,
        after_clifford_depolarization=gate_p, before_round_data_depolarization=0,
        before_measure_flip_probability=meas_p,
    )


def _sampling(circuit: stim.Circuit) -> SamplingIdentity:
    return SamplingIdentity.from_stim(
        circuit, generating_noise_model_id="measurement-heavy-gate-0.001-meas-0.006",
        generating_noise_provenance={"gate_p": 0.001, "measurement_p": 0.006,
                                     "record": "deterministic NS-2B fixture"},
        code_family="rotated_surface_code", distance=3, rounds=5, memory_basis="z",
        observable_interpretations=(OBSERVABLE_MEANING,),
        observable_polarities=(1,),
    )


def _model(sampling: SamplingIdentity, name: str, *, artifact: StimDEMArtifact,
           assumed_noise: str = "nominal-0.003", experimental: bool = False,
           correlation_mode: bool = False) -> DecoderModelIdentity:
    import pymatching
    metadata = DecoderMetadata(
        name=name, implementation="PyMatching", version=str(pymatching.__version__),
        detector_count=artifact.record.detector_count,
        observable_count=artifact.record.observable_count,
        noise_model_id=assumed_noise, correlation_mode=correlation_mode,
        experimental=experimental, construction_provenance="fixture DEM artifact",
    )
    return DecoderModelIdentity.create(
        sampling, metadata, dem_record=artifact.record,
        decoder_assumed_noise_model_id=assumed_noise,
        decoder_assumed_noise_provenance={"assumed_noise": assumed_noise},
        correlation_semantics=("PyMatching construction and decode_batch use the declared flag"
                               if correlation_mode else "PyMatching correlation mode explicitly disabled"),
    )


class _Decoder:
    def __init__(self, metadata, *, value=0, mutate_input=False, mutate_metadata=False,
                 alias=False, bad_type=False, bad_timing=None, shot_delta=0, nonbinary=False):
        self.metadata = metadata
        self.value = value
        self.mutate_input = mutate_input
        self.mutate_metadata = mutate_metadata
        self.alias = alias
        self.bad_type = bad_type
        self.bad_timing = bad_timing
        self.shot_delta = shot_delta
        self.nonbinary = nonbinary
        self.received = []
        self.output = None

    def decode(self, detectors):
        self.received.append(detectors.tobytes())
        if self.mutate_input:
            detectors[:] = 1
        if self.mutate_metadata:
            self.metadata = replace(self.metadata, version="mutated")
        if self.bad_type:
            return {"not": "a prediction"}
        rows = len(detectors) + self.shot_delta
        self.output = np.full((rows, self.metadata.observable_count), self.value, dtype=np.uint8)
        if self.nonbinary:
            self.output[:] = 2
        if self.bad_timing is not None:
            result = object.__new__(DecoderPrediction)
            object.__setattr__(result, "bits", self.output if self.alias else self.output.copy())
            object.__setattr__(result, "metadata", self.metadata)
            object.__setattr__(result, "elapsed_seconds", self.bad_timing)
            return result
        return DecoderPrediction(self.output if self.alias else self.output.copy(), self.metadata, 0.001)


class NS2BSamplingModelIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuit = _circuit()
        cls.sampling = _sampling(cls.circuit)
        cls.decomp_settings = DEMConstructionSettingsV2(
            decompose_errors=True, approximate_disjoint_errors=True,
            construction_note="decomposed PyMatching fixture",
        )
        cls.raw_settings = DEMConstructionSettingsV2(
            decompose_errors=False, approximate_disjoint_errors=False,
            construction_note="undecomposed reference-model fixture",
        )
        cls.decomp = StimDEMArtifact.build(
            cls.circuit, cls.decomp_settings,
            observable_interpretations=(OBSERVABLE_MEANING,), observable_polarities=(1,),
        )
        # A different generating circuit supplies the nominal decoder's model.
        # It has the same code/output structure but a distinct noise assumption.
        cls.nominal_circuit = _circuit(0.003, 0.003)
        cls.raw = StimDEMArtifact.build(
            cls.nominal_circuit, cls.raw_settings,
            observable_interpretations=(OBSERVABLE_MEANING,), observable_polarities=(1,),
        )

    def make_batch(self, values=None, circuit=None, identity=None):
        circuit = circuit or self.circuit
        identity = identity or self.sampling
        array = (np.arange(3 * int(circuit.num_detectors), dtype=np.uint8)
                 .reshape(3, int(circuit.num_detectors)) % 2 if values is None else values)
        return TrustedDetectorBatchAdapter(identity).from_stim_detector_samples(
            circuit, array, column_detector_ids=identity.detector_ids,
        )

    def test_sampling_identity_is_stable_and_separate_from_dem(self):
        same = _sampling(self.circuit)
        self.assertEqual(self.sampling.identity_sha256, same.identity_sha256)
        self.assertNotIn("dem_sha256", self.sampling.to_dict())
        self.assertEqual(self.sampling.generating_noise_provenance_sha256,
                         same.generating_noise_provenance_sha256)

    def test_dem_settings_v2_covers_stim_conversion_options(self):
        settings = DEMConstructionSettingsV2(
            decompose_errors=True, flatten_loops=True, allow_gauge_detectors=True,
            approximate_disjoint_errors=0.02, ignore_decomposition_failures=True,
            block_decomposition_from_introducing_remnant_edges=True,
            construction_note="explicit option inventory fixture",
        )
        kwargs = settings.stim_kwargs()
        self.assertEqual(set(kwargs), {
            "decompose_errors", "flatten_loops", "allow_gauge_detectors",
            "approximate_disjoint_errors", "ignore_decomposition_failures",
            "block_decomposition_from_introducing_remnant_edges",
        })
        self.assertEqual(kwargs["approximate_disjoint_errors"], 0.02)

    def test_distinct_dem_models_share_sampling_identity_without_equivalence_claim(self):
        decomp_model = _model(self.sampling, "fixed-decomposed", artifact=self.decomp)
        reference_model = _model(self.sampling, "reference-undecomposed", artifact=self.raw,
                                 assumed_noise="nominal-0.003")
        self.assertEqual(decomp_model.sampling_identity_sha256, reference_model.sampling_identity_sha256)
        self.assertNotEqual(decomp_model.identity_sha256, reference_model.identity_sha256)
        self.assertTrue(decomp_model.dem_record.settings.decompose_errors)
        self.assertFalse(reference_model.dem_record.settings.decompose_errors)
        self.assertNotEqual(decomp_model.dem_record.source_circuit_sha256,
                            reference_model.dem_record.source_circuit_sha256)
        assert_model_compatible(reference_model, self.sampling)

    def test_nominal_assumption_may_differ_from_generating_noise(self):
        model = _model(self.sampling, "nominal-fixed", artifact=self.raw,
                       assumed_noise="nominal-0.003")
        self.assertNotEqual(model.decoder_assumed_noise_model_id,
                            self.sampling.generating_noise_model_id)
        assert_model_compatible(model, self.sampling)

    def test_non_dem_decoder_and_static_resource_provenance_are_supported(self):
        metadata = DecoderMetadata("non-dem", "external-hypergraph", "0.1", 40, 1,
                                   noise_model_id="training-distribution-v1",
                                   correlation_mode=None)
        model = DecoderModelIdentity.create(
            self.sampling, metadata, dem_record=None,
            decoder_assumed_noise_model_id="training-distribution-v1",
            decoder_assumed_noise_provenance={"training_distribution": "synthetic-family-A",
                                              "calibration_source": "development-only"},
            correlation_semantics=None, static_resource_sha256=("d" * 64,),
            static_resource_note="Model weights represented by one SHA-256 digest.",
        )
        assert_model_compatible(model, self.sampling)
        self.assertIsNone(model.dem_record)
        self.assertEqual(model.to_dict()["decoder_assumed_noise_provenance"]["calibration_source"],
                         "development-only")
        with self.assertRaisesRegex(ValueError, "provenance is required"):
            DecoderModelIdentity.create(
                self.sampling, metadata, dem_record=None,
                decoder_assumed_noise_model_id="training-distribution-v1",
                decoder_assumed_noise_provenance={}, correlation_semantics=None,
            )

    def test_wrong_circuit_identity_or_structure_is_rejected(self):
        batch = self.make_batch()
        other_sampling = _sampling(_circuit(0.002, 0.006))
        model = _model(self.sampling, "decoder", artifact=self.decomp)
        with self.assertRaisesRegex(ValueError, "sampling identity"):
            assert_model_compatible(model, other_sampling)
        with self.assertRaisesRegex(ValueError, "sampling identity"):
            from qshift_core_v1.sampling_model_identity import validate_batch
            validate_batch(batch, other_sampling)
        with self.assertRaisesRegex(ValueError, "circuit digest"):
            self.make_batch(circuit=self.nominal_circuit)

    def test_detector_order_and_observable_semantics_are_checked(self):
        model = _model(self.sampling, "decoder", artifact=self.decomp)
        bad_order = replace(model, detector_order_sha256="a" * 64)
        with self.assertRaisesRegex(ValueError, "ordering"):
            assert_model_compatible(bad_order, self.sampling)
        bad_observable = replace(model, observable_semantics_sha256="b" * 64)
        with self.assertRaisesRegex(ValueError, "observable interpretation"):
            assert_model_compatible(bad_observable, self.sampling)
        with self.assertRaisesRegex(ValueError, "Stim detector order"):
            TrustedDetectorBatchAdapter(self.sampling).from_stim_detector_samples(
                self.circuit, np.zeros((1, 40), dtype=np.uint8),
                column_detector_ids=tuple(reversed(self.sampling.detector_ids)),
            )
        with self.assertRaises(TypeError):
            TrustedDetectorBatchAdapter(self.sampling).from_stim_detector_samples(
                self.circuit, np.zeros((1, 40), dtype=np.uint8),
            )
        with self.assertRaises(ValueError):
            TrustedDetectorBatchAdapter(self.sampling).from_stim_detector_samples(
                self.circuit, np.zeros((1, 40), dtype=np.uint8),
                column_detector_ids=(False, *range(1, 40)),
            )
        bad_dem_order = _model(self.sampling, "dem-order", artifact=self.decomp)
        malformed_record = replace(bad_dem_order.dem_record, detector_order_sha256="c" * 64)
        bad_dem_order = replace(bad_dem_order, dem_record=malformed_record)
        with self.assertRaisesRegex(ValueError, "DEM detector ordering"):
            assert_model_compatible(bad_dem_order, self.sampling)
        bad_dem_observable = _model(self.sampling, "dem-observable", artifact=self.decomp)
        malformed_record = replace(bad_dem_observable.dem_record,
                                   observable_semantics_sha256="e" * 64)
        bad_dem_observable = replace(bad_dem_observable, dem_record=malformed_record)
        with self.assertRaisesRegex(ValueError, "DEM observable semantics"):
            assert_model_compatible(bad_dem_observable, self.sampling)

    def test_batch_bytes_are_immutable_and_hash_checked(self):
        source = np.zeros((2, 40), dtype=np.uint8)
        batch = self.make_batch(source)
        source[:] = 1
        self.assertFalse(batch.detector_bits.flags.writeable)
        self.assertEqual(int(batch.detector_bits.sum()), 0)
        with self.assertRaises(ValueError):
            batch.detector_bits[0, 0] = 1

    def test_decoder_metadata_mutation_is_detected(self):
        model = _model(self.sampling, "mutator", artifact=self.decomp)
        decoder = _Decoder(model.metadata, mutate_metadata=True)
        with self.assertRaisesRegex(ValueError, "metadata mutated"):
            decode_model_checked(decoder, model, self.sampling, self.make_batch())

    def test_input_mutation_and_output_aliasing_are_contained(self):
        model = _model(self.sampling, "mutator", artifact=self.decomp)
        source = np.zeros((2, 40), dtype=np.uint8)
        batch = self.make_batch(source)
        decoder = _Decoder(model.metadata, value=1, mutate_input=True, alias=True)
        prediction = decode_model_checked(decoder, model, self.sampling, batch)
        self.assertEqual(int(batch.detector_bits.sum()), 0)
        self.assertEqual(int(prediction.bits.sum()), 2)
        decoder.output[:] = 0
        self.assertEqual(int(prediction.bits.sum()), 2)

    def test_prediction_type_shape_binary_and_elapsed_are_checked(self):
        model = _model(self.sampling, "invalid", artifact=self.decomp)
        cases = [
            (_Decoder(model.metadata, bad_type=True), TypeError, "DecoderPrediction"),
            (_Decoder(model.metadata, shot_delta=-1), ValueError, "shot count"),
            (_Decoder(model.metadata, nonbinary=True), ValueError, "only finite 0/1"),
        ]
        for decoder, error, match in cases:
            with self.subTest(match=match), self.assertRaisesRegex(error, match):
                decode_model_checked(decoder, model, self.sampling, self.make_batch())
        for bad_time in (True, float("nan"), float("inf"), -0.1):
            decoder = _Decoder(model.metadata, bad_timing=bad_time)
            with self.subTest(bad_time=bad_time), self.assertRaisesRegex(ValueError, "elapsed_seconds"):
                decode_model_checked(decoder, model, self.sampling, self.make_batch())

    def test_registry_and_paired_evaluator_use_identical_detector_bytes_and_hide_labels(self):
        fixed_model = _model(self.sampling, "fixed", artifact=self.decomp)
        candidate_model = _model(self.sampling, "candidate", artifact=self.raw,
                                  assumed_noise="nominal-0.003", experimental=True)
        fixed = _Decoder(fixed_model.metadata, value=0)
        candidate = _Decoder(candidate_model.metadata, value=1)
        registry = IdentityAwareDecoderRegistry()
        registry.register(fixed, model=fixed_model, sampling=self.sampling)
        registry.register(candidate, model=candidate_model, sampling=self.sampling)
        detector_matrix = np.zeros((3, 40), dtype=np.uint8)
        batch = self.make_batch(detector_matrix)
        labels = np.ones((3, 1), dtype=np.uint8)
        result = evaluate_identity_aware_paired(
            registry, batch, labels, decoder_names=("fixed", "candidate"),
            baseline_name="fixed", scope="development", sample_id="ns2b-fixed-fixture",
        )
        self.assertEqual(fixed.received, candidate.received)
        self.assertEqual(fixed.received[0], detector_matrix.tobytes())
        self.assertEqual(result["records"]["fixed"]["errors"], 3)
        self.assertEqual(result["records"]["candidate"]["errors"], 0)
        self.assertEqual(result["paired_detector_content_sha256"], batch.content_sha256)
        self.assertIn("labels are not decoder inputs", result["label_isolation"])
        self.assertEqual(len(result["decoder_model_identity_sha256"]), 2)

    def test_protected_scope_is_rejected_before_any_decoder_call(self):
        model = _model(self.sampling, "fixed", artifact=self.decomp)
        decoder = _Decoder(model.metadata)
        registry = IdentityAwareDecoderRegistry()
        registry.register(decoder, model=model, sampling=self.sampling)
        with self.assertRaises(PermissionError):
            evaluate_identity_aware_paired(
                registry, self.make_batch(), object(), decoder_names=("fixed",),
                baseline_name="fixed", scope="protected-test", sample_id="sealed",
            )
        self.assertEqual(decoder.received, [])

    def test_fixed_fallback_and_experimental_opt_in_are_preserved(self):
        fixed_model = _model(self.sampling, "fixed", artifact=self.decomp)
        experimental_model = _model(self.sampling, "experimental", artifact=self.raw, experimental=True)
        registry = IdentityAwareDecoderRegistry()
        registry.register(_Decoder(fixed_model.metadata), model=fixed_model, sampling=self.sampling)
        registry.register(_Decoder(experimental_model.metadata), model=experimental_model, sampling=self.sampling)
        estimate = NoiseEstimate({"profile": 1.0}, 0.99, 128)
        proposal = SelectionProposal("experimental", 0.99, 0, "fixture", estimate)
        blocked = registry.selector(fallback_name="fixed", allow_experimental=False)
        self.assertEqual(blocked.choose(1, proposal).selected_decoder, "fixed")
        allowed = registry.selector(fallback_name="fixed", allow_experimental=True,
                                    hysteresis_blocks=1, minimum_dwell_blocks=1)
        self.assertEqual(allowed.choose(1, proposal).selected_decoder, "experimental")

    def test_existing_correlation_modes_construct_and_decode_without_sampling(self):
        from qshift_core_v1.pymatching_adapter import PyMatchingDecoder
        for mode in (False, True):
            with self.subTest(correlation_mode=mode):
                decoder = PyMatchingDecoder.from_detector_error_model(
                    self.decomp.dem, correlation_mode=mode, name=f"legacy-{mode}",
                    noise_model_id="nominal-0.003",
                )
                prediction = decoder.decode(np.zeros((2, 40), dtype=np.uint8))
                self.assertEqual(prediction.bits.shape, (2, 1))
                self.assertEqual(decoder.metadata.correlation_mode, mode)

    def test_ns1_checked_boundary_is_hardened_without_changing_valid_contract(self):
        from qshift_core_v1.circuit_identity import (
            CircuitIdentity, DEMConstructionSettings, DetectorBatch as LegacyBatch,
            ExternalDecoderSpec, decode_checked,
        )
        old_identity = CircuitIdentity.from_stim(
            self.circuit, self.decomp.dem, code_family="rotated_surface_code",
            distance=3, rounds=5, memory_basis="z",
            observable_interpretations=("Stim logical observable 0 parity flip",),
            noise_model_id=self.sampling.generating_noise_model_id,
            noise_model_record={"gate_p": 0.001, "measurement_p": 0.006},
            dem_settings=DEMConstructionSettings(True, True, "legacy fixture"),
        )
        metadata = DecoderMetadata("legacy", "fixture", "1", 40, 1,
                                   noise_model_id=old_identity.noise_model_id,
                                   correlation_mode=False)
        spec = ExternalDecoderSpec(
            metadata=metadata, input_representation="unpacked-binary-uint8[shots,detectors]",
            supported_circuit_identity_sha256=(old_identity.identity_sha256,),
            detector_order_sha256=old_identity.detector_order_sha256,
            observable_ids=(0,), observable_interpretations=old_identity.observable_interpretations,
            noise_model_id=old_identity.noise_model_id, correlation_mode=False,
            provenance="NS-2B deterministic fixture", runtime_requirements="small CPU fixture",
        )
        original = np.zeros((2, 40), dtype=np.uint8)
        batch = LegacyBatch(original.copy(), old_identity.identity_sha256,
                            old_identity.detector_ids, old_identity.detector_order_sha256)
        decoder = _Decoder(metadata, value=1, mutate_input=True, alias=True)
        result = decode_checked(decoder, spec, old_identity, batch)
        self.assertEqual(int(batch.bits.sum()), 0)
        self.assertEqual(int(result.bits.sum()), 2)
        decoder.output[:] = 0
        self.assertEqual(int(result.bits.sum()), 2)

        mutator = _Decoder(metadata, mutate_metadata=True)
        with self.assertRaisesRegex(ValueError, "metadata mutated"):
            decode_checked(mutator, spec, old_identity, batch)

        for bad_time in (True, float("nan"), float("inf"), -1.0):
            invalid_time = _Decoder(metadata, bad_timing=bad_time)
            with self.subTest(bad_time=bad_time), self.assertRaisesRegex(ValueError, "elapsed_seconds"):
                decode_checked(invalid_time, spec, old_identity, batch)


if __name__ == "__main__":
    unittest.main()
