"""Deterministic NS-1 contract tests; constructs circuits but never samples shots."""
from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
import sys
import unittest

import numpy as np
import stim

from qshift_core_v1.circuit_identity import (
    CircuitIdentity,
    DEMConstructionSettings,
    DetectorBatch,
    ExternalDecoderSpec,
    assert_decoder_compatible,
    decode_checked,
    validate_detector_batch,
)
from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction


SETTINGS = DEMConstructionSettings(
    decompose_errors=True,
    approximate_disjoint_errors=True,
    construction_note="deterministic NS-1 fixture conversion",
)


def _identity(*, distance: int = 3, p: float = 0.003,
              code_family: str | None = "rotated_surface_code") -> CircuitIdentity:
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=distance, rounds=5,
        after_clifford_depolarization=p, before_measure_flip_probability=0.003,
    )
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=True,
    )
    return CircuitIdentity.from_stim(
        circuit, dem,
        code_family=code_family,
        distance=distance,
        rounds=5,
        memory_basis="z",
        observable_interpretations=("Stim logical observable 0: Z-memory parity flip",),
        noise_model_id=f"fixture-gate-p-{p:.3f}",
        noise_model_record={"gate_p": p, "measurement_p": 0.003, "fixture": "deterministic"},
        dem_settings=SETTINGS,
    )


class _ZeroDecoder:
    def __init__(self, metadata: DecoderMetadata, *, invalid: bool = False):
        self.metadata = metadata
        self.invalid = invalid
        self.received = None

    def decode(self, detectors: np.ndarray):
        self.received = detectors.copy()
        if self.invalid:
            return np.zeros((len(detectors), 1), dtype=np.uint8)
        return DecoderPrediction(np.zeros((len(detectors), 1), dtype=np.uint8), self.metadata)


def _spec(identity: CircuitIdentity, *, metadata: DecoderMetadata | None = None,
          order: str | None = None, interpretations: tuple[str, ...] | None = None,
          supported: tuple[str, ...] | None = None, coordinates: bool = True) -> ExternalDecoderSpec:
    meta = metadata or DecoderMetadata(
        name="test-decoder", implementation="fixture", version="1",
        detector_count=len(identity.detector_ids), observable_count=len(identity.observable_ids),
        noise_model_id=identity.noise_model_id, correlation_mode=None,
    )
    return ExternalDecoderSpec(
        metadata=meta,
        input_representation="unpacked-binary-uint8[shots,detectors]",
        supported_circuit_identity_sha256=supported or (identity.identity_sha256,),
        detector_order_sha256=order or identity.detector_order_sha256,
        observable_ids=identity.observable_ids,
        observable_interpretations=interpretations or identity.observable_interpretations,
        noise_model_id=identity.noise_model_id,
        correlation_mode=meta.correlation_mode,
        provenance="deterministic unit-test fixture",
        runtime_requirements="CPU fixture; one batch in memory",
        requires_detector_coordinates=coordinates,
    )


class CircuitIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = _identity()

    def test_identity_is_stable_and_preserves_stim_order_and_time_coordinates(self):
        again = _identity()
        self.assertEqual(self.identity.identity_sha256, again.identity_sha256)
        self.assertEqual(self.identity.detector_ids, tuple(range(40)))
        self.assertEqual(self.identity.observable_ids, (0,))
        self.assertEqual(len(self.identity.detector_coordinates), 40)
        self.assertTrue(all(c is not None and len(c) >= 3 for c in self.identity.detector_coordinates))
        # Stim's documented detector coordinates include the initial slice and
        # five measurement-round slices in this generated memory circuit.
        self.assertEqual({c[2] for c in self.identity.detector_coordinates if c is not None},
                         {0, 1, 2, 3, 4, 5})

    def test_equal_dimensions_do_not_imply_same_semantic_identity(self):
        other = _identity(p=0.004)
        self.assertEqual(len(other.detector_ids), len(self.identity.detector_ids))
        self.assertNotEqual(other.identity_sha256, self.identity.identity_sha256)
        with self.assertRaisesRegex(ValueError, "exact circuit/DEM identity"):
            assert_decoder_compatible(_spec(self.identity), other)

    def test_declared_detector_order_permutation_is_rejected(self):
        permuted_fingerprint = hashlib.sha256(b"permuted detector order").hexdigest()
        batch = DetectorBatch(
            np.eye(2, 40, dtype=np.uint8), self.identity.identity_sha256,
            (1, 0, *range(2, 40)), permuted_fingerprint,
        )
        with self.assertRaisesRegex(ValueError, "detector ordering"):
            validate_detector_batch(batch, self.identity)
        with self.assertRaisesRegex(ValueError, "ordering fingerprint"):
            assert_decoder_compatible(_spec(self.identity, order=permuted_fingerprint), self.identity)

    def test_observable_convention_and_dimension_must_match(self):
        with self.assertRaisesRegex(ValueError, "observable convention"):
            assert_decoder_compatible(
                _spec(self.identity, interpretations=("logical X parity",)), self.identity,
            )
        wrong_meta = DecoderMetadata(
            name="test-decoder", implementation="fixture", version="1",
            detector_count=40, observable_count=2, noise_model_id=self.identity.noise_model_id,
        )
        with self.assertRaisesRegex(ValueError, "observable dimension"):
            assert_decoder_compatible(_spec(self.identity, metadata=wrong_meta), self.identity)

    def test_multi_observable_order_is_explicit(self):
        circuit = stim.Circuit("""R 0
M 0
DETECTOR rec[-1]
OBSERVABLE_INCLUDE(0) rec[-1]
OBSERVABLE_INCLUDE(1) rec[-1]
""")
        dem = circuit.detector_error_model()
        identity = CircuitIdentity.from_stim(
            circuit, dem, code_family="analytic_toy", distance=1, rounds=1,
            memory_basis="z", observable_interpretations=("toy logical A", "toy logical B"),
            noise_model_id="toy-noiseless", noise_model_record={"channel": "none"},
            dem_settings=DEMConstructionSettings(False, False, "direct deterministic conversion"),
        )
        spec = _spec(identity, interpretations=("toy logical B", "toy logical A"))
        with self.assertRaisesRegex(ValueError, "observable convention"):
            assert_decoder_compatible(spec, identity)

    def test_noise_and_correlation_metadata_must_agree(self):
        with self.assertRaisesRegex(ValueError, "noise-model assumption"):
            assert_decoder_compatible(replace(_spec(self.identity), noise_model_id="different-noise"),
                                      self.identity)
        with self.assertRaisesRegex(ValueError, "correlation-mode declaration"):
            assert_decoder_compatible(replace(_spec(self.identity), correlation_mode=True), self.identity)

    def test_unknown_semantics_are_preserved_but_not_accepted_as_compatible(self):
        unknown = _identity(code_family=None)
        self.assertIsNone(unknown.code_family)
        self.assertIsNone(unknown.to_dict()["code_family"])
        with self.assertRaisesRegex(ValueError, "unknown fields: code_family"):
            assert_decoder_compatible(_spec(unknown), unknown)

    def test_different_geometry_is_not_implicitly_supported(self):
        distance_five = _identity(distance=5)
        self.assertNotEqual(distance_five.detector_order_sha256, self.identity.detector_order_sha256)
        with self.assertRaisesRegex(ValueError, "exact circuit/DEM identity"):
            assert_decoder_compatible(_spec(self.identity), distance_five)

    def test_checked_decode_validates_contract_and_passes_only_detectors(self):
        spec = _spec(self.identity)
        decoder = _ZeroDecoder(spec.metadata)
        detectors = np.zeros((3, 40), dtype=np.uint8)
        batch = DetectorBatch(detectors, self.identity.identity_sha256, self.identity.detector_ids,
                              self.identity.detector_order_sha256)
        result = decode_checked(decoder, spec, self.identity, batch)
        self.assertEqual(result.bits.shape, (3, 1))
        np.testing.assert_array_equal(decoder.received, detectors)

    def test_prediction_contract_is_enforced(self):
        spec = _spec(self.identity)
        decoder = _ZeroDecoder(spec.metadata, invalid=True)
        batch = DetectorBatch(np.zeros((1, 40), dtype=np.uint8), self.identity.identity_sha256,
                              self.identity.detector_ids, self.identity.detector_order_sha256)
        with self.assertRaisesRegex(TypeError, "DecoderPrediction"):
            decode_checked(decoder, spec, self.identity, batch)

    def test_dashboard_distance3_fiveround_pymatching_path_is_unchanged(self):
        # prepare constructs the historical fixed model; this test supplies an
        # explicit deterministic all-zero syndrome and never calls a sampler.
        dashboard_path = str(Path(__file__).resolve().parents[1])
        if dashboard_path not in sys.path:
            sys.path.insert(0, dashboard_path)
        from dashboard.configuration import DEFAULT_CONFIG
        from dashboard.simulator import decode_matching, prepare

        _, _, _, matching, _, _ = prepare(dict(DEFAULT_CONFIG))
        prediction = decode_matching(matching, np.zeros((1, 40), dtype=np.uint8))
        self.assertEqual(prediction.shape, (1,))
        self.assertIn(int(prediction[0]), (0, 1))


if __name__ == "__main__":
    unittest.main()
