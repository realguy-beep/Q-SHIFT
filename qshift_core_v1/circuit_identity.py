"""Versioned circuit identity and fail-closed decoder compatibility checks.

This module binds detector arrays to an explicitly declared Stim circuit/DEM
contract.  It validates declared identities; it cannot prove where an array
came from or that the caller's declaration is truthful.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from numbers import Real
from typing import Any, Mapping

import numpy as np

from .contracts import DecoderMetadata, DecoderPrediction, DecoderProtocol, binary_matrix


def _canonical_json(value: Any) -> bytes:
    """Serialize JSON-compatible metadata deterministically and reject NaNs."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Identity metadata must be finite JSON-compatible data.") from exc


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_sha256(value: str, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be a 64-character SHA-256 digest.")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be a hexadecimal SHA-256 digest.") from exc


def _coordinate_map(owner: Any, detector_count: int) -> tuple[tuple[float, ...] | None, ...]:
    """Read coordinates in explicit detector-ID order, retaining unknowns."""
    getter = getattr(owner, "get_detector_coordinates", None)
    if not callable(getter):
        return (None,) * detector_count
    try:
        raw = getter()
    except (AttributeError, NotImplementedError):
        return (None,) * detector_count
    if not isinstance(raw, Mapping):
        raise ValueError("Stim detector coordinate API returned a non-mapping.")
    result: list[tuple[float, ...] | None] = []
    for detector_id in range(detector_count):
        coord = raw.get(detector_id)
        if coord is None or len(coord) == 0:
            result.append(None)
            continue
        values = tuple(float(v) for v in coord)
        if not values or not all(math.isfinite(v) for v in values):
            raise ValueError(f"Detector {detector_id} has invalid coordinates.")
        result.append(values)
    extras = set(raw) - set(range(detector_count))
    if extras:
        raise ValueError(f"Coordinate map contains out-of-range detector IDs: {sorted(extras)}")
    return tuple(result)


@dataclass(frozen=True)
class DEMConstructionSettings:
    """Explicit settings that affect DEM semantics; None is not accepted."""

    decompose_errors: bool
    approximate_disjoint_errors: bool
    construction_note: str

    def __post_init__(self) -> None:
        if type(self.decompose_errors) is not bool or type(self.approximate_disjoint_errors) is not bool:
            raise ValueError("DEM decomposition settings must be explicit booleans.")
        if not isinstance(self.construction_note, str) or not self.construction_note.strip():
            raise ValueError("DEM construction_note is required.")


@dataclass(frozen=True)
class CircuitIdentity:
    """Stable circuit/DEM identity, kept separate from a decoder's identity."""

    schema: str
    circuit_sha256: str
    dem_sha256: str
    code_family: str | None
    distance: int | None
    rounds: int | None
    memory_basis: str | None
    detector_ids: tuple[int, ...]
    detector_coordinates: tuple[tuple[float, ...] | None, ...]
    dem_detector_coordinates: tuple[tuple[float, ...] | None, ...]
    detector_order_sha256: str
    observable_ids: tuple[int, ...]
    observable_interpretations: tuple[str | None, ...]
    noise_model_id: str | None
    noise_model_record_sha256: str | None
    dem_settings: DEMConstructionSettings
    stim_version: str

    CURRENT_SCHEMA = "qshift-circuit-identity-v1"

    def __post_init__(self) -> None:
        if self.schema != self.CURRENT_SCHEMA:
            raise ValueError(f"Unsupported circuit identity schema {self.schema!r}.")
        _require_sha256(self.circuit_sha256, "circuit_sha256")
        _require_sha256(self.dem_sha256, "dem_sha256")
        _require_sha256(self.detector_order_sha256, "detector_order_sha256")
        if self.noise_model_record_sha256 is not None:
            _require_sha256(self.noise_model_record_sha256, "noise_model_record_sha256")
        if not self.detector_ids or self.detector_ids != tuple(range(len(self.detector_ids))):
            raise ValueError("Detector IDs must be the complete contiguous Stim order 0..N-1.")
        if any(type(v) is not int for v in self.detector_ids):
            raise ValueError("Detector IDs must be integers, not booleans or coerced values.")
        if len(self.detector_coordinates) != len(self.detector_ids):
            raise ValueError("Circuit detector-coordinate map length differs from detector count.")
        if len(self.dem_detector_coordinates) != len(self.detector_ids):
            raise ValueError("DEM detector-coordinate map length differs from detector count.")
        for coordinate in (*self.detector_coordinates, *self.dem_detector_coordinates):
            if coordinate is not None and (
                not isinstance(coordinate, tuple) or not coordinate
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                           for v in coordinate)
            ):
                raise ValueError("Detector coordinates must be finite numeric tuples or None.")
        expected_order_payload = [
            {"detector_id": detector_id,
             "circuit_coordinates": self.detector_coordinates[detector_id],
             "dem_coordinates": self.dem_detector_coordinates[detector_id]}
            for detector_id in self.detector_ids
        ]
        if self.detector_order_sha256 != _sha256(_canonical_json(expected_order_payload)):
            raise ValueError("detector_order_sha256 does not match the declared detector IDs/coordinates.")
        if not self.observable_ids or self.observable_ids != tuple(range(len(self.observable_ids))):
            raise ValueError("Observable IDs must be the complete contiguous Stim order 0..M-1.")
        if any(type(v) is not int for v in self.observable_ids):
            raise ValueError("Observable IDs must be integers, not booleans or coerced values.")
        if len(self.observable_interpretations) != len(self.observable_ids):
            raise ValueError("Observable interpretations must have one entry per observable ID.")
        if any(value is not None and (not isinstance(value, str) or not value.strip())
               for value in self.observable_interpretations):
            raise ValueError("Observable interpretations must be nonempty text or explicitly unknown (None).")
        if not isinstance(self.dem_settings, DEMConstructionSettings):
            raise TypeError("dem_settings must be explicit DEMConstructionSettings.")
        if self.distance is not None and (isinstance(self.distance, bool) or not isinstance(self.distance, int)
                                          or self.distance <= 0):
            raise ValueError("distance must be a positive integer or explicitly unknown (None).")
        if self.rounds is not None and (isinstance(self.rounds, bool) or not isinstance(self.rounds, int)
                                        or self.rounds <= 0):
            raise ValueError("rounds must be a positive integer or explicitly unknown (None).")
        for field, value in (("code_family", self.code_family), ("memory_basis", self.memory_basis),
                             ("noise_model_id", self.noise_model_id)):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field} must be nonempty text or explicitly unknown (None).")
        if not isinstance(self.stim_version, str) or not self.stim_version.strip():
            raise ValueError("stim_version is required.")

    @classmethod
    def from_stim(
        cls,
        circuit: Any,
        dem: Any,
        *,
        code_family: str | None,
        distance: int | None,
        rounds: int | None,
        memory_basis: str | None,
        observable_interpretations: tuple[str | None, ...],
        noise_model_id: str | None,
        noise_model_record: Mapping[str, Any] | None,
        dem_settings: DEMConstructionSettings,
    ) -> "CircuitIdentity":
        """Create identity from exact Stim text plus caller-declared semantics.

        Semantic properties are keyword-only and have no defaults so callers
        must provide a value or explicitly pass None when it is unknown.
        """
        import stim  # local import keeps core contracts usable without Stim

        if not isinstance(circuit, stim.Circuit) or not isinstance(dem, stim.DetectorErrorModel):
            raise TypeError("circuit and dem must be Stim Circuit and DetectorErrorModel objects.")
        detector_count = int(circuit.num_detectors)
        observable_count = int(circuit.num_observables)
        if detector_count <= 0 or observable_count <= 0:
            raise ValueError("Circuit must declare at least one detector and observable.")
        if int(dem.num_detectors) != detector_count or int(dem.num_observables) != observable_count:
            raise ValueError("Circuit and DEM detector/observable dimensions do not match.")
        if len(observable_interpretations) != observable_count:
            raise ValueError("observable_interpretations must match circuit.num_observables.")
        for item in observable_interpretations:
            if item is not None and (not isinstance(item, str) or not item.strip()):
                raise ValueError("Observable interpretation must be nonempty text or None.")
        if noise_model_record is not None and not isinstance(noise_model_record, Mapping):
            raise ValueError("noise_model_record must be a mapping or explicitly unknown (None).")

        detector_ids = tuple(range(detector_count))
        observable_ids = tuple(range(observable_count))
        circuit_coords = _coordinate_map(circuit, detector_count)
        dem_coords = _coordinate_map(dem, detector_count)
        order_payload = [
            {"detector_id": detector_id,
             "circuit_coordinates": circuit_coords[detector_id],
             "dem_coordinates": dem_coords[detector_id]}
            for detector_id in detector_ids
        ]
        noise_digest = None if noise_model_record is None else _sha256(_canonical_json(noise_model_record))
        circuit_text = str(circuit).encode("utf-8")
        dem_text = str(dem).encode("utf-8")
        return cls(
            schema=cls.CURRENT_SCHEMA,
            circuit_sha256=_sha256(circuit_text),
            dem_sha256=_sha256(dem_text),
            code_family=code_family,
            distance=distance,
            rounds=rounds,
            memory_basis=memory_basis,
            detector_ids=detector_ids,
            detector_coordinates=circuit_coords,
            dem_detector_coordinates=dem_coords,
            detector_order_sha256=_sha256(_canonical_json(order_payload)),
            observable_ids=observable_ids,
            observable_interpretations=tuple(observable_interpretations),
            noise_model_id=noise_model_id,
            noise_model_record_sha256=noise_digest,
            dem_settings=dem_settings,
            stim_version=str(stim.__version__),
        )

    @property
    def identity_sha256(self) -> str:
        return _sha256(_canonical_json(self.to_dict()))

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe representation. Unknown semantic declarations remain null."""
        return {
            "schema": self.schema,
            "circuit_sha256": self.circuit_sha256,
            "dem_sha256": self.dem_sha256,
            "code_family": self.code_family,
            "distance": self.distance,
            "rounds": self.rounds,
            "memory_basis": self.memory_basis,
            "detector_ids": list(self.detector_ids),
            "detector_coordinates": [None if x is None else list(x) for x in self.detector_coordinates],
            "dem_detector_coordinates": [None if x is None else list(x) for x in self.dem_detector_coordinates],
            "detector_order_sha256": self.detector_order_sha256,
            "observable_ids": list(self.observable_ids),
            "observable_interpretations": list(self.observable_interpretations),
            "noise_model_id": self.noise_model_id,
            "noise_model_record_sha256": self.noise_model_record_sha256,
            "dem_settings": asdict(self.dem_settings),
            "stim_version": self.stim_version,
        }

    def require_compatibility_semantics(self) -> None:
        unknown = []
        for key in ("code_family", "distance", "rounds", "memory_basis", "noise_model_id",
                    "noise_model_record_sha256"):
            if getattr(self, key) is None:
                unknown.append(key)
        if any(value is None for value in self.observable_interpretations):
            unknown.append("observable_interpretations")
        if unknown:
            raise ValueError("Cannot establish decoder compatibility; identity has unknown fields: "
                             + ", ".join(unknown))


@dataclass(frozen=True)
class ExternalDecoderSpec:
    """Minimum declared boundary for a separately implemented decoder."""

    metadata: DecoderMetadata
    input_representation: str
    supported_circuit_identity_sha256: tuple[str, ...]
    detector_order_sha256: str
    observable_ids: tuple[int, ...]
    observable_interpretations: tuple[str, ...]
    noise_model_id: str
    correlation_mode: bool | None
    provenance: str
    runtime_requirements: str
    requires_detector_coordinates: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, DecoderMetadata):
            raise TypeError("metadata must be DecoderMetadata.")
        if self.input_representation != "unpacked-binary-uint8[shots,detectors]":
            raise ValueError("Unsupported input representation; no conversion is performed implicitly.")
        if not self.supported_circuit_identity_sha256:
            raise ValueError("At least one exact supported circuit identity is required.")
        for digest in self.supported_circuit_identity_sha256:
            _require_sha256(digest, "supported_circuit_identity_sha256 entry")
        _require_sha256(self.detector_order_sha256, "detector_order_sha256")
        if not self.observable_ids or self.observable_ids != tuple(range(len(self.observable_ids))):
            raise ValueError("Observable IDs must be declared in contiguous order.")
        if len(self.observable_interpretations) != len(self.observable_ids):
            raise ValueError("One observable convention is required per observable ID.")
        for name, text in (("noise_model_id", self.noise_model_id), ("provenance", self.provenance),
                           ("runtime_requirements", self.runtime_requirements)):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{name} is required.")
        if self.correlation_mode is not None and type(self.correlation_mode) is not bool:
            raise ValueError("correlation_mode must be true, false, or None.")
        if type(self.requires_detector_coordinates) is not bool:
            raise ValueError("requires_detector_coordinates must be bool.")


@dataclass(frozen=True)
class DetectorBatch:
    """Binary detector batch plus caller-declared identity/order fingerprints."""

    bits: np.ndarray
    circuit_identity_sha256: str
    column_detector_ids: tuple[int, ...]
    detector_order_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "bits", binary_matrix(self.bits, name="detector batch"))
        _require_sha256(self.circuit_identity_sha256, "circuit_identity_sha256")
        _require_sha256(self.detector_order_sha256, "detector_order_sha256")
        if not self.column_detector_ids or any(
            isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in self.column_detector_ids
        ):
            raise ValueError("column_detector_ids must explicitly label each detector column.")
        if len(self.column_detector_ids) != self.bits.shape[1]:
            raise ValueError("column_detector_ids length differs from detector array width.")


def validate_detector_batch(batch: DetectorBatch, identity: CircuitIdentity) -> np.ndarray:
    """Validate shape and declared circuit/order identity before decoder input."""
    if not isinstance(batch, DetectorBatch):
        raise TypeError("batch must be a DetectorBatch with explicit identity metadata.")
    identity.require_compatibility_semantics()
    if batch.circuit_identity_sha256 != identity.identity_sha256:
        raise ValueError("Detector batch circuit identity does not match the declared circuit.")
    if batch.column_detector_ids != identity.detector_ids:
        raise ValueError("Detector batch detector ordering/column IDs are permuted or incompatible.")
    if batch.detector_order_sha256 != identity.detector_order_sha256:
        raise ValueError("Detector batch detector ordering does not match the declared order.")
    if batch.bits.shape[1] != len(identity.detector_ids):
        raise ValueError("Detector batch width does not match the circuit detector count.")
    return batch.bits


def assert_decoder_compatible(spec: ExternalDecoderSpec, identity: CircuitIdentity) -> None:
    """Fail closed unless the decoder explicitly supports this exact contract."""
    if not isinstance(spec, ExternalDecoderSpec) or not isinstance(identity, CircuitIdentity):
        raise TypeError("spec and identity must use the versioned compatibility contract.")
    identity.require_compatibility_semantics()
    if identity.identity_sha256 not in spec.supported_circuit_identity_sha256:
        raise ValueError("Decoder does not declare support for this exact circuit/DEM identity.")
    if spec.metadata.detector_count != len(identity.detector_ids):
        raise ValueError("Decoder detector dimension differs from circuit identity.")
    if spec.metadata.observable_count != len(identity.observable_ids):
        raise ValueError("Decoder observable dimension differs from circuit identity.")
    if spec.detector_order_sha256 != identity.detector_order_sha256:
        raise ValueError("Decoder detector ordering fingerprint differs from circuit identity.")
    if spec.observable_ids != identity.observable_ids:
        raise ValueError("Decoder observable ID order differs from circuit identity.")
    if spec.observable_interpretations != identity.observable_interpretations:
        raise ValueError("Decoder observable convention differs from circuit identity.")
    if spec.noise_model_id != identity.noise_model_id or spec.metadata.noise_model_id != identity.noise_model_id:
        raise ValueError("Decoder noise-model assumption differs from circuit identity.")
    if spec.correlation_mode != spec.metadata.correlation_mode:
        raise ValueError("Decoder correlation-mode declaration differs from DecoderMetadata.")
    if spec.requires_detector_coordinates and any(x is None for x in identity.detector_coordinates):
        raise ValueError("Decoder requires detector coordinates that are unknown for this circuit.")


def decode_checked(
    decoder: DecoderProtocol,
    spec: ExternalDecoderSpec,
    identity: CircuitIdentity,
    batch: DetectorBatch,
) -> DecoderPrediction:
    """Run an already selected decoder only after compatibility validation."""
    assert_decoder_compatible(spec, identity)
    detectors = validate_detector_batch(batch, identity)
    registered = getattr(decoder, "metadata", None)
    if (not isinstance(registered, DecoderMetadata) or registered != spec.metadata
            or not callable(getattr(decoder, "decode", None))):
        raise TypeError("Decoder implementation does not conform to its registered metadata/protocol.")
    registered_fields = asdict(registered)
    result = decoder.decode(np.array(detectors, dtype=np.uint8, order="C", copy=True))
    current_metadata = getattr(decoder, "metadata", None)
    if not isinstance(current_metadata, DecoderMetadata) or asdict(current_metadata) != registered_fields:
        raise ValueError("Decoder metadata mutated during checked inference.")
    if not isinstance(result, DecoderPrediction):
        raise TypeError("Decoder must return DecoderPrediction.")
    if not isinstance(result.metadata, DecoderMetadata) or asdict(result.metadata) != registered_fields:
        raise ValueError("Returned prediction metadata differs from the decoder compatibility spec.")
    prediction_bits = binary_matrix(
        result.bits, name="checked decoder predictions", columns=len(identity.observable_ids)
    )
    if prediction_bits.shape != (len(detectors), len(identity.observable_ids)):
        raise ValueError("Decoder prediction dimensions do not match detector shots and observables.")
    elapsed = result.elapsed_seconds
    if elapsed is not None and (
        isinstance(elapsed, bool) or not isinstance(elapsed, Real)
        or not math.isfinite(elapsed) or elapsed < 0
    ):
        raise ValueError("Decoder elapsed_seconds must be finite and nonnegative, not bool.")
    stable_metadata = DecoderMetadata(**registered_fields)
    return DecoderPrediction(
        np.array(prediction_bits, dtype=np.uint8, order="C", copy=True), stable_metadata,
        float(elapsed) if elapsed is not None else None,
    )
