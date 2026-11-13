"""NS-2C deterministic decoder-runtime tests; never invokes a Stim sampler."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

import numpy as np
import stim

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction
from qshift_core_v1.decoder_runtime_v2 import (
    CheckedDecoderAdapter,
    CompatibilityAwareDecoderBank,
    DeterministicParityDecoder,
    evaluate_paired_batch,
)
from qshift_core_v1.sampling_model_identity import (
    DEMConstructionSettingsV2,
    DecoderModelIdentity,
    SamplingIdentity,
    StimDEMArtifact,
    TrustedDetectorBatchAdapter,
)


MEANING = "Fixture observable 0; binary output convention inherited from Stim observable 0"


def _fixture():
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=3, rounds=5,
        after_clifford_depolarization=0.001,
        before_round_data_depolarization=0,
        before_measure_flip_probability=0.006,
    )
    sampling = SamplingIdentity.from_stim(
        circuit,
        generating_noise_model_id="ns2c-deterministic-fixture",
        generating_noise_provenance={"kind": "deterministic test; no shots sampled"},
        code_family="rotated_surface_code", distance=3, rounds=5, memory_basis="z",
        observable_interpretations=(MEANING,), observable_polarities=(1,),
    )
    settings = DEMConstructionSettingsV2(
        decompose_errors=True, approximate_disjoint_errors=False,
        construction_note="deterministic integration fixture only",
    )
    artifact = StimDEMArtifact.build(
        circuit, settings, observable_interpretations=(MEANING,), observable_polarities=(1,),
    )
    return circuit, sampling, artifact


def _reference(sampling, *, name, group, experimental=False, shared=None, assumed_noise="deterministic-fixture-model"):
    metadata = DecoderMetadata(
        name=name, implementation="NS-2C deterministic parity fixture", version="1",
        detector_count=len(sampling.detector_ids), observable_count=1,
        noise_model_id=assumed_noise, correlation_mode=None,
        experimental=experimental, construction_provenance="fixed detector-column parity; test only",
    )
    model = DecoderModelIdentity.create(
        sampling, metadata, dem_record=None,
        decoder_assumed_noise_model_id=assumed_noise,
        decoder_assumed_noise_provenance={"purpose": "engineering contract test", "decoder": name,
                                          "assumed_model": assumed_noise},
        correlation_semantics=None,
        static_resource_note="No trained weights; deterministic parity rule only.",
    )
    decoder = _SharedParityDecoder(metadata, group, shared=shared)
    return CheckedDecoderAdapter(decoder, model_identity=model, sampling_identity=sampling)


class _SharedParityDecoder:
    def __init__(self, metadata, group, *, shared=None):
        self.metadata = metadata
        self.group = group
        self.shared = shared if shared is not None else {}

    def decode(self, detectors):
        self.shared.setdefault("inputs", []).append(detectors.tobytes())
        self.shared.setdefault("arrays", [])
        bits = self.shared.get("scratch")
        if bits is None or bits.shape != (len(detectors), 1):
            bits = np.zeros((len(detectors), 1), dtype=np.uint8)
            self.shared["scratch"] = bits
        bits[:, 0] = np.bitwise_xor.reduce(detectors[:, self.group], axis=1).astype(np.uint8)
        self.shared["arrays"].append(bits)
        return DecoderPrediction(bits, self.metadata, elapsed_seconds=0.0)


class _MutatingParityDecoder(_SharedParityDecoder):
    def decode(self, detectors):
        before = detectors.tobytes()
        result = super().decode(detectors)
        detectors[:] = 1
        self.shared.setdefault("before", []).append(before)
        return result


class _FailingDecoder(_SharedParityDecoder):
    def decode(self, detectors):
        raise RuntimeError("fixture decoder failure")


class _BadContractDecoder(_SharedParityDecoder):
    def __init__(self, metadata, mode):
        super().__init__(metadata, (0,))
        self.mode = mode

    def decode(self, detectors):
        if self.mode == "type":
            return {"prediction": "invalid"}
        if self.mode == "shape":
            return DecoderPrediction(np.zeros((len(detectors) + 1, 1), dtype=np.uint8), self.metadata)
        if self.mode == "metadata":
            wrong = DecoderMetadata(
                name=self.metadata.name, implementation=self.metadata.implementation,
                version="spoofed", detector_count=self.metadata.detector_count,
                observable_count=self.metadata.observable_count,
                noise_model_id=self.metadata.noise_model_id,
                correlation_mode=self.metadata.correlation_mode,
                experimental=self.metadata.experimental,
                construction_provenance=self.metadata.construction_provenance,
            )
            return DecoderPrediction(np.zeros((len(detectors), 1), dtype=np.uint8), wrong)
        raise AssertionError(self.mode)


class DecoderRuntimeV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuit, cls.sampling, cls.artifact = _fixture()
        cls.batch_values = np.zeros((4, len(cls.sampling.detector_ids)), dtype=np.uint8)
        cls.batch_values[1, 0] = 1
        cls.batch_values[2, 1] = 1
        cls.batch_values[3, 0:2] = 1
        cls.batch = TrustedDetectorBatchAdapter(cls.sampling).from_stim_detector_samples(
            cls.circuit, cls.batch_values, column_detector_ids=cls.sampling.detector_ids,
        )

    def test_paired_reference_decoders_share_samples_and_report_shot_metrics(self):
        bank = CompatibilityAwareDecoderBank(self.sampling)
        shared = {}
        fixed = _reference(self.sampling, name="fixture_fixed", group=(0,), shared=shared)
        candidate = _reference(
            self.sampling, name="fixture_candidate", group=(1,), shared=shared,
            assumed_noise="alternate-detector-profile",
        )
        bank.register(fixed)
        bank.register(candidate)
        labels = np.array([0, 1, 1, 0], dtype=np.uint8)
        report = evaluate_paired_batch(
            bank, self.batch, decoder_names=("fixture_fixed", "fixture_candidate"),
            baseline_name="fixture_fixed", scope="development", sample_id="fixed-fixture-1",
            observables=labels,
        )
        self.assertEqual(shared["inputs"], [self.batch_values.tobytes(), self.batch_values.tobytes()])
        self.assertEqual(report["records"]["fixture_fixed"]["errors"], 2)
        self.assertEqual(report["records"]["fixture_candidate"]["errors"], 2)
        self.assertEqual(report["paired_vs_baseline"]["fixture_candidate"]["prediction_disagreements"], 2)
        self.assertEqual(report["paired_vs_baseline"]["fixture_candidate"]["candidate_only_failures"], 1)
        self.assertEqual(report["paired_vs_baseline"]["fixture_candidate"]["baseline_only_failures"], 1)
        self.assertTrue(report["records"]["fixture_fixed"]["wall_seconds"] >= 0)
        self.assertEqual(report["records"]["fixture_fixed"]["decoder_reported_seconds"], 0.0)
        self.assertEqual(report["sample_identity"]["detector_content_sha256"], self.batch.content_sha256)
        self.assertNotEqual(
            report["sample_identity"]["decoder_model_identity_sha256"]["fixture_fixed"],
            report["sample_identity"]["decoder_model_identity_sha256"]["fixture_candidate"],
        )

    def test_real_pymatching_adapter_runs_without_changing_decoder_behavior(self):
        import pymatching
        from qshift_core_v1.pymatching_adapter import PyMatchingDecoder

        decoder = PyMatchingDecoder.from_detector_error_model(
            self.artifact.dem, correlation_mode=False, name="pymatching_fixed",
            noise_model_id="fixture-dem-model", experimental=False,
        )
        model = DecoderModelIdentity.create(
            self.sampling, decoder.metadata, dem_record=self.artifact.record,
            decoder_assumed_noise_model_id="fixture-dem-model",
            decoder_assumed_noise_provenance={"source": "fixture DEM", "pymatching": pymatching.__version__},
            correlation_semantics="PyMatching correlation mode disabled at construction and decode",
        )
        bank = CompatibilityAwareDecoderBank(self.sampling)
        bank.register(CheckedDecoderAdapter(
            decoder, model_identity=model, sampling_identity=self.sampling,
        ))
        direct = decoder.decode(self.batch_values.copy())
        report = evaluate_paired_batch(
            bank, self.batch, decoder_names=("pymatching_fixed",),
            baseline_name="pymatching_fixed", scope="development", sample_id="pymatching-fixture",
        )
        record = report["records"]["pymatching_fixed"]
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["prediction_shape"], [4, 1])
        self.assertEqual(record["model_information"]["metadata"]["correlation_mode"], False)
        self.assertEqual(record["decoder_version"], str(pymatching.__version__))
        self.assertIsNone(record["logical_error_rate"])
        self.assertEqual(
            record["prediction_sha256"],
            hashlib.sha256(direct.bits.tobytes(order="C")).hexdigest(),
        )
        selector = bank.selector(fallback_name="pymatching_fixed")
        self.assertEqual(selector.choose(0, None).selected_decoder, "pymatching_fixed")

    def test_input_mutation_is_isolated_and_output_arrays_do_not_alias(self):
        metadata0 = DecoderMetadata(
            name="mutator", implementation="fixture", version="1",
            detector_count=self.batch_values.shape[1], observable_count=1,
            noise_model_id="fixture", construction_provenance="test",
        )
        model0 = DecoderModelIdentity.create(
            self.sampling, metadata0, dem_record=None,
            decoder_assumed_noise_model_id="fixture",
            decoder_assumed_noise_provenance={"source": "test"}, correlation_semantics=None,
        )
        shared = {}
        mutator = CheckedDecoderAdapter(
            _MutatingParityDecoder(metadata0, (0,), shared=shared),
            model_identity=model0, sampling_identity=self.sampling,
        )
        other = _reference(self.sampling, name="other", group=(1,), shared=shared)
        bank = CompatibilityAwareDecoderBank(self.sampling)
        bank.register(mutator)
        bank.register(other)
        before = self.batch.detector_bits.tobytes()
        report = evaluate_paired_batch(
            bank, self.batch, decoder_names=("mutator", "other"), baseline_name="mutator",
            scope="development", sample_id="mutation-fixture",
        )
        self.assertEqual(before, self.batch.detector_bits.tobytes())
        self.assertEqual(shared["inputs"][0], before)
        self.assertEqual(shared["inputs"][1], before)
        p0 = report["records"]["mutator"]
        p1 = report["records"]["other"]
        self.assertNotEqual(p0["prediction_sha256"], p1["prediction_sha256"])
        arrays = shared["arrays"]
        self.assertTrue(np.shares_memory(arrays[0], arrays[1]))  # deliberate decoder scratch-buffer alias
        self.assertNotEqual(p0["prediction_sha256"], p1["prediction_sha256"])  # detached outputs survived overwrite

    def test_failures_are_recorded_without_substitute_prediction(self):
        bank = CompatibilityAwareDecoderBank(self.sampling)
        bank.register(_reference(self.sampling, name="fixed", group=(0,)))
        metadata = DecoderMetadata(
            name="failing", implementation="fixture", version="1",
            detector_count=len(self.sampling.detector_ids), observable_count=1,
            noise_model_id="fixture", construction_provenance="test",
        )
        model = DecoderModelIdentity.create(
            self.sampling, metadata, dem_record=None,
            decoder_assumed_noise_model_id="fixture",
            decoder_assumed_noise_provenance={"source": "test"}, correlation_semantics=None,
        )
        bank.register(CheckedDecoderAdapter(
            _FailingDecoder(metadata, (0,)), model_identity=model, sampling_identity=self.sampling,
        ))
        report = evaluate_paired_batch(
            bank, self.batch, decoder_names=("fixed", "failing"), baseline_name="fixed",
            scope="development", sample_id="failure-fixture",
            observables=np.zeros(len(self.batch_values), dtype=np.uint8),
        )
        failed = report["records"]["failing"]
        self.assertEqual(failed["status"], "failed")
        self.assertIsNone(failed["prediction_sha256"])
        self.assertEqual(failed["failure_type"], "RuntimeError")
        self.assertEqual(failed["errors"], None)
        self.assertFalse(report["paired_vs_baseline"]["failing"]["available"])

    def test_invalid_prediction_contracts_are_reported(self):
        for mode, expected_error in (("type", "TypeError"), ("shape", "ValueError"), ("metadata", "ValueError")):
            with self.subTest(mode=mode):
                metadata = DecoderMetadata(
                    name=f"bad_{mode}", implementation="fixture", version="1",
                    detector_count=len(self.sampling.detector_ids), observable_count=1,
                    noise_model_id="fixture", construction_provenance="test",
                )
                model = DecoderModelIdentity.create(
                    self.sampling, metadata, dem_record=None,
                    decoder_assumed_noise_model_id="fixture",
                    decoder_assumed_noise_provenance={"source": "test"}, correlation_semantics=None,
                )
                bank = CompatibilityAwareDecoderBank(self.sampling)
                bank.register(_reference(self.sampling, name="fixed", group=(0,)))
                bank.register(CheckedDecoderAdapter(
                    _BadContractDecoder(metadata, mode), model_identity=model,
                    sampling_identity=self.sampling,
                ))
                report = evaluate_paired_batch(
                    bank, self.batch, decoder_names=("fixed", f"bad_{mode}"),
                    baseline_name="fixed", scope="development", sample_id=f"bad-{mode}",
                )
                self.assertEqual(report["records"][f"bad_{mode}"]["status"], "failed")
                self.assertEqual(report["records"][f"bad_{mode}"]["failure_type"], expected_error)
                self.assertIsNone(report["records"][f"bad_{mode}"]["prediction_sha256"])

    def test_experimental_registration_requires_explicit_opt_in(self):
        experimental = _reference(self.sampling, name="experimental", group=(0,), experimental=True)
        bank = CompatibilityAwareDecoderBank(self.sampling)
        with self.assertRaises(PermissionError):
            bank.register(experimental)
        bank.register(experimental, experimental_opt_in=True)
        self.assertEqual(bank.names(), ("experimental",))

    def test_incompatible_sampling_identity_is_rejected_at_registration(self):
        other_circuit = stim.Circuit.generated(
            "surface_code:rotated_memory_x", distance=3, rounds=5,
            after_clifford_depolarization=0.001,
            before_round_data_depolarization=0,
            before_measure_flip_probability=0.006,
        )
        other_sampling = SamplingIdentity.from_stim(
            other_circuit, generating_noise_model_id="different-basis-fixture",
            generating_noise_provenance={"kind": "deterministic compatibility fixture"},
            code_family="rotated_surface_code", distance=3, rounds=5, memory_basis="x",
            observable_interpretations=("Fixture observable 0; logical X-memory parity flip",),
            observable_polarities=(1,),
        )
        incompatible = _reference(other_sampling, name="wrong_circuit", group=(0,))
        bank = CompatibilityAwareDecoderBank(self.sampling)
        with self.assertRaises(ValueError):
            bank.register(incompatible)

    def test_labels_are_not_passed_and_protected_scope_is_rejected(self):
        bank = CompatibilityAwareDecoderBank(self.sampling)
        shared = {}
        bank.register(_reference(self.sampling, name="fixed", group=(0,), shared=shared))
        bank.register(_reference(self.sampling, name="candidate", group=(1,), shared=shared))
        class Labels:
            def __array__(self, *args, **kwargs):
                raise AssertionError("labels should not be accessed before decode")
        with self.assertRaises(AssertionError):
            evaluate_paired_batch(
                bank, self.batch, decoder_names=("fixed", "candidate"), baseline_name="fixed",
                scope="development", sample_id="label-order", observables=Labels(),
            )
        with self.assertRaises(PermissionError):
            evaluate_paired_batch(
                bank, self.batch, decoder_names=("fixed", "candidate"), baseline_name="fixed",
                scope="protected-test", sample_id="protected",
            )
        self.assertEqual(len(shared["inputs"]), 2)


if __name__ == "__main__":
    unittest.main()
