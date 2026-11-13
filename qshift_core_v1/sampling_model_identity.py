"""NS-2B contracts separating sampled-circuit identity from decoder models.

This module is additive to the NS-1 v1 API.  A sampling identity describes the
actual Stim-generated detector stream.  A decoder-model identity describes
one decoder's assumptions and resources; it may intentionally use a different
noise model or DEM construction from the generating circuit.

The adapter checks declarations and byte-level invariants.  Python metadata
and a content hash cannot prove the upstream provenance of arbitrary arrays.
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
from .controller import DecoderRegistry, SafeDecoderSelector
from .evaluation import ALLOWED_SCOPES, evaluate_paired


SAMPLING_IDENTITY_SCHEMA = "qshift-sampling-identity-v2"
DECODER_MODEL_SCHEMA = "qshift-decoder-model-identity-v2"
DETECTOR_REPRESENTATION = "unpacked-binary-uint8[shots,detectors]"


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Identity records must contain finite JSON-compatible values.") from exc


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_digest(value: str, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be a SHA-256 hex digest.")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be a SHA-256 hex digest.") from exc


def _coords(circuit: Any, detector_count: int) -> tuple[tuple[float, ...] | None, ...]:
    getter = getattr(circuit, "get_detector_coordinates", None)
    raw = getter() if callable(getter) else {}
    if not isinstance(raw, Mapping):
        raise ValueError("Circuit detector coordinate API returned a non-mapping.")
    result = []
    for detector_id in range(detector_count):
        item = raw.get(detector_id)
        if item is None or len(item) == 0:
            result.append(None)
            continue
        coordinate = tuple(float(x) for x in item)
        if not coordinate or any(not math.isfinite(x) for x in coordinate):
            raise ValueError(f"Detector {detector_id} has invalid coordinates.")
        result.append(coordinate)
    if set(raw) - set(range(detector_count)):
        raise ValueError("Circuit coordinate map contains out-of-range detector IDs.")
    return tuple(result)


def _ordering_digest(detector_ids: tuple[int, ...],
                     coordinates: tuple[tuple[float, ...] | None, ...]) -> str:
    return _sha(_canonical([
        {"detector_id": i, "coordinates": coordinates[i]} for i in detector_ids
    ]))


def _observable_digest(ids: tuple[int, ...], meanings: tuple[str, ...],
                       polarities: tuple[int, ...]) -> str:
    return _sha(_canonical([
        {"observable_id": i, "interpretation": meanings[i], "polarity": polarities[i]}
        for i in ids
    ]))


@dataclass(frozen=True)
class SamplingIdentity:
    """Identity of the data-generating circuit and its ordered outputs."""

    schema: str
    circuit_sha256: str
    stim_version: str
    generating_noise_model_id: str
    generating_noise_provenance_json: str
    generating_noise_provenance_sha256: str
    code_family: str
    distance: int
    rounds: int
    memory_basis: str
    detector_ids: tuple[int, ...]
    detector_coordinates: tuple[tuple[float, ...] | None, ...]
    detector_order_sha256: str
    observable_ids: tuple[int, ...]
    observable_interpretations: tuple[str, ...]
    observable_polarities: tuple[int, ...]
    observable_semantics_sha256: str

    def __post_init__(self) -> None:
        if self.schema != SAMPLING_IDENTITY_SCHEMA:
            raise ValueError(f"Unsupported sampling identity schema {self.schema!r}.")
        _check_digest(self.circuit_sha256, "circuit_sha256")
        _check_digest(self.generating_noise_provenance_sha256,
                      "generating_noise_provenance_sha256")
        _check_digest(self.detector_order_sha256, "detector_order_sha256")
        _check_digest(self.observable_semantics_sha256, "observable_semantics_sha256")
        for name in ("stim_version", "generating_noise_model_id", "code_family", "memory_basis"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required and cannot be unknown.")
        for name in ("distance", "rounds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")
        if (not isinstance(self.detector_ids, tuple)
                or any(type(v) is not int for v in self.detector_ids)
                or not self.detector_ids or self.detector_ids != tuple(range(len(self.detector_ids)))):
            raise ValueError("Detector IDs must be the complete contiguous Stim order 0..N-1.")
        if not isinstance(self.detector_coordinates, tuple) or len(self.detector_coordinates) != len(self.detector_ids):
            raise ValueError("Detector coordinates must match the detector count.")
        for coordinate in self.detector_coordinates:
            if coordinate is not None and (not isinstance(coordinate, tuple) or not coordinate or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in coordinate
            )):
                raise ValueError("Detector coordinates must be finite tuples or explicitly unknown.")
        if self.detector_order_sha256 != _ordering_digest(self.detector_ids, self.detector_coordinates):
            raise ValueError("Detector-order digest does not match ordered IDs and coordinates.")
        if (not isinstance(self.observable_ids, tuple)
                or any(type(v) is not int for v in self.observable_ids)
                or not self.observable_ids or self.observable_ids != tuple(range(len(self.observable_ids)))):
            raise ValueError("Observable IDs must be the complete contiguous Stim order 0..M-1.")
        if (not isinstance(self.observable_interpretations, tuple)
                or len(self.observable_interpretations) != len(self.observable_ids)):
            raise ValueError("Each observable needs an explicit interpretation.")
        if any(not isinstance(x, str) or not x.strip() for x in self.observable_interpretations):
            raise ValueError("Observable interpretations must be nonempty explicit text.")
        if (not isinstance(self.observable_polarities, tuple)
                or len(self.observable_polarities) != len(self.observable_ids) or any(
            isinstance(x, bool) or x not in (-1, 1) for x in self.observable_polarities
        )):
            raise ValueError("Observable polarity must be explicitly +1 or -1 per observable.")
        if self.observable_semantics_sha256 != _observable_digest(
            self.observable_ids, self.observable_interpretations, self.observable_polarities
        ):
            raise ValueError("Observable-semantics digest does not match IDs, meanings, and polarity.")
        try:
            provenance = json.loads(self.generating_noise_provenance_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Generating-noise provenance must be canonical JSON.") from exc
        if (not isinstance(provenance, dict) or not provenance
                or _canonical(provenance).decode("utf-8") != self.generating_noise_provenance_json):
            raise ValueError("Generating-noise provenance must be a canonical JSON object.")
        if _sha(self.generating_noise_provenance_json.encode("utf-8")) != self.generating_noise_provenance_sha256:
            raise ValueError("Generating-noise provenance digest mismatch.")

    @classmethod
    def from_stim(
        cls, circuit: Any, *, generating_noise_model_id: str,
        generating_noise_provenance: Mapping[str, Any], code_family: str,
        distance: int, rounds: int, memory_basis: str,
        observable_interpretations: tuple[str, ...],
        observable_polarities: tuple[int, ...],
    ) -> "SamplingIdentity":
        import stim
        if not isinstance(circuit, stim.Circuit):
            raise TypeError("circuit must be a Stim Circuit.")
        if not isinstance(generating_noise_provenance, Mapping) or not generating_noise_provenance:
            raise ValueError("An explicit generating-noise provenance record is required.")
        detector_count = int(circuit.num_detectors)
        observable_count = int(circuit.num_observables)
        if detector_count <= 0 or observable_count <= 0:
            raise ValueError("Circuit must declare at least one detector and one observable.")
        if len(observable_interpretations) != observable_count or len(observable_polarities) != observable_count:
            raise ValueError("Observable semantics must match circuit.num_observables.")
        provenance_json = _canonical(dict(generating_noise_provenance)).decode("utf-8")
        detector_ids = tuple(range(detector_count))
        coordinates = _coords(circuit, detector_count)
        observable_ids = tuple(range(observable_count))
        return cls(
            schema=SAMPLING_IDENTITY_SCHEMA,
            circuit_sha256=_sha(str(circuit).encode("utf-8")),
            stim_version=str(stim.__version__),
            generating_noise_model_id=generating_noise_model_id,
            generating_noise_provenance_json=provenance_json,
            generating_noise_provenance_sha256=_sha(provenance_json.encode("utf-8")),
            code_family=code_family, distance=distance, rounds=rounds, memory_basis=memory_basis,
            detector_ids=detector_ids, detector_coordinates=coordinates,
            detector_order_sha256=_ordering_digest(detector_ids, coordinates),
            observable_ids=observable_ids,
            observable_interpretations=tuple(observable_interpretations),
            observable_polarities=tuple(observable_polarities),
            observable_semantics_sha256=_observable_digest(
                observable_ids, tuple(observable_interpretations), tuple(observable_polarities)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "circuit_sha256": self.circuit_sha256,
            "stim_version": self.stim_version,
            "generating_noise_model_id": self.generating_noise_model_id,
            "generating_noise_provenance": json.loads(self.generating_noise_provenance_json),
            "generating_noise_provenance_sha256": self.generating_noise_provenance_sha256,
            "code_family": self.code_family, "distance": self.distance, "rounds": self.rounds,
            "memory_basis": self.memory_basis, "detector_ids": list(self.detector_ids),
            "detector_coordinates": [None if x is None else list(x) for x in self.detector_coordinates],
            "detector_order_sha256": self.detector_order_sha256,
            "observable_ids": list(self.observable_ids),
            "observable_interpretations": list(self.observable_interpretations),
            "observable_polarities": list(self.observable_polarities),
            "observable_semantics_sha256": self.observable_semantics_sha256,
        }

    @property
    def identity_sha256(self) -> str:
        return _sha(_canonical(self.to_dict()))


@dataclass(frozen=True)
class DEMConstructionSettingsV2:
    """All Stim DEM conversion options are explicit and retained verbatim."""

    decompose_errors: bool = False
    flatten_loops: bool = False
    allow_gauge_detectors: bool = False
    approximate_disjoint_errors: bool | float = False
    ignore_decomposition_failures: bool = False
    block_decomposition_from_introducing_remnant_edges: bool = False
    construction_note: str = "Stim Circuit.detector_error_model"

    def __post_init__(self) -> None:
        for name in ("decompose_errors", "flatten_loops", "allow_gauge_detectors",
                     "ignore_decomposition_failures", "block_decomposition_from_introducing_remnant_edges"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be an explicit bool.")
        value = self.approximate_disjoint_errors
        if type(value) is not bool:
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("approximate_disjoint_errors must be bool or a finite threshold in [0,1].")
            object.__setattr__(self, "approximate_disjoint_errors", float(value))
        if not isinstance(self.construction_note, str) or not self.construction_note.strip():
            raise ValueError("construction_note is required.")

    def stim_kwargs(self) -> dict[str, Any]:
        return {
            "decompose_errors": self.decompose_errors,
            "flatten_loops": self.flatten_loops,
            "allow_gauge_detectors": self.allow_gauge_detectors,
            "approximate_disjoint_errors": self.approximate_disjoint_errors,
            "ignore_decomposition_failures": self.ignore_decomposition_failures,
            "block_decomposition_from_introducing_remnant_edges": self.block_decomposition_from_introducing_remnant_edges,
        }


@dataclass(frozen=True)
class DEMConstructionRecord:
    """Digest and declared construction provenance for one concrete Stim DEM."""

    dem_sha256: str
    source_circuit_sha256: str
    stim_version: str
    detector_count: int
    observable_count: int
    detector_order_sha256: str
    observable_semantics_sha256: str
    settings: DEMConstructionSettingsV2

    def __post_init__(self) -> None:
        _check_digest(self.dem_sha256, "dem_sha256")
        _check_digest(self.source_circuit_sha256, "source_circuit_sha256")
        _check_digest(self.detector_order_sha256, "DEM detector_order_sha256")
        _check_digest(self.observable_semantics_sha256, "DEM observable_semantics_sha256")
        if not isinstance(self.stim_version, str) or not self.stim_version.strip():
            raise ValueError("stim_version is required.")
        for field in ("detector_count", "observable_count"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field} must be a positive integer.")
        if not isinstance(self.settings, DEMConstructionSettingsV2):
            raise TypeError("settings must be DEMConstructionSettingsV2.")

    def to_dict(self) -> dict[str, Any]:
        return {"dem_sha256": self.dem_sha256, "source_circuit_sha256": self.source_circuit_sha256,
                "stim_version": self.stim_version, "detector_count": self.detector_count,
                "observable_count": self.observable_count,
                "detector_order_sha256": self.detector_order_sha256,
                "observable_semantics_sha256": self.observable_semantics_sha256,
                "settings": asdict(self.settings)}


@dataclass(frozen=True)
class StimDEMArtifact:
    """A DEM built by this helper; construction arguments and exact text are hashed."""

    record: DEMConstructionRecord
    _dem_text: str

    def __post_init__(self) -> None:
        if not isinstance(self.record, DEMConstructionRecord) or not isinstance(self._dem_text, str):
            raise TypeError("StimDEMArtifact requires a construction record and exact DEM text.")
        if _sha(self._dem_text.encode("utf-8")) != self.record.dem_sha256:
            raise ValueError("DEM artifact text does not match its recorded digest.")
        dem = self.dem
        if (int(dem.num_detectors) != self.record.detector_count
                or int(dem.num_observables) != self.record.observable_count):
            raise ValueError("DEM artifact dimensions do not match its construction record.")
        actual_order = _ordering_digest(
            tuple(range(int(dem.num_detectors))), _coords(dem, int(dem.num_detectors))
        )
        if actual_order != self.record.detector_order_sha256:
            raise ValueError("DEM detector ordering differs from its construction record.")

    @classmethod
    def build(
        cls, circuit: Any, settings: DEMConstructionSettingsV2, *,
        observable_interpretations: tuple[str, ...],
        observable_polarities: tuple[int, ...],
    ) -> "StimDEMArtifact":
        import stim
        if not isinstance(circuit, stim.Circuit):
            raise TypeError("circuit must be a Stim Circuit.")
        if not isinstance(settings, DEMConstructionSettingsV2):
            raise TypeError("settings must be DEMConstructionSettingsV2.")
        observable_ids = tuple(range(int(circuit.num_observables)))
        if len(observable_interpretations) != len(observable_ids) or len(observable_polarities) != len(observable_ids):
            raise ValueError("Source observable semantics must match the DEM source circuit.")
        meanings, polarities = tuple(observable_interpretations), tuple(observable_polarities)
        if any(not isinstance(value, str) or not value.strip() for value in meanings):
            raise ValueError("Source observable interpretations must be explicit nonempty text.")
        if any(isinstance(value, bool) or value not in (-1, 1) for value in polarities):
            raise ValueError("Source observable polarity must be explicitly +1 or -1.")
        dem = circuit.detector_error_model(**settings.stim_kwargs())
        text = str(dem)
        record = DEMConstructionRecord(
            dem_sha256=_sha(text.encode("utf-8")),
            source_circuit_sha256=_sha(str(circuit).encode("utf-8")),
            stim_version=str(stim.__version__), detector_count=int(dem.num_detectors),
            observable_count=int(dem.num_observables),
            detector_order_sha256=_ordering_digest(
                tuple(range(int(dem.num_detectors))),
                _coords(dem, int(dem.num_detectors)),
            ),
            observable_semantics_sha256=_observable_digest(observable_ids, meanings, polarities),
            settings=settings,
        )
        return cls(record=record, _dem_text=text)

    @property
    def dem(self) -> Any:
        import stim
        if _sha(self._dem_text.encode("utf-8")) != self.record.dem_sha256:
            raise ValueError("DEM artifact text changed after identity was recorded.")
        return stim.DetectorErrorModel(self._dem_text)


@dataclass(frozen=True)
class DecoderModelIdentity:
    """Identity of one decoder's model, assumptions, and static representation."""

    schema: str
    sampling_identity_sha256: str
    metadata: DecoderMetadata
    input_representation: str
    detector_order_sha256: str
    observable_semantics_sha256: str
    dem_record: DEMConstructionRecord | None
    decoder_assumed_noise_model_id: str
    decoder_assumed_noise_provenance_json: str
    decoder_assumed_noise_provenance_sha256: str
    correlation_semantics: str | None
    requires_detector_coordinates: bool
    static_resource_sha256: tuple[str, ...] = ()
    static_resource_note: str = "No additional static resource declared."

    def __post_init__(self) -> None:
        if self.schema != DECODER_MODEL_SCHEMA:
            raise ValueError(f"Unsupported decoder model schema {self.schema!r}.")
        _check_digest(self.sampling_identity_sha256, "sampling_identity_sha256")
        _check_digest(self.detector_order_sha256, "detector_order_sha256")
        _check_digest(self.observable_semantics_sha256, "observable_semantics_sha256")
        if not isinstance(self.metadata, DecoderMetadata):
            raise TypeError("metadata must be DecoderMetadata.")
        if self.input_representation != DETECTOR_REPRESENTATION:
            raise ValueError("Only explicit unpacked-binary detector matrices are currently supported.")
        if (not isinstance(self.decoder_assumed_noise_model_id, str)
                or not self.decoder_assumed_noise_model_id.strip()):
            raise ValueError("Decoder-assumed noise identity must be explicitly named.")
        _check_digest(self.decoder_assumed_noise_provenance_sha256,
                      "decoder_assumed_noise_provenance_sha256")
        try:
            assumption_provenance = json.loads(self.decoder_assumed_noise_provenance_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Decoder assumed-noise provenance must be canonical JSON.") from exc
        if (not isinstance(assumption_provenance, dict)
                or _canonical(assumption_provenance).decode("utf-8") != self.decoder_assumed_noise_provenance_json
                or _sha(self.decoder_assumed_noise_provenance_json.encode("utf-8"))
                != self.decoder_assumed_noise_provenance_sha256):
            raise ValueError("Decoder assumed-noise provenance record/digest mismatch.")
        if self.metadata.noise_model_id != self.decoder_assumed_noise_model_id:
            raise ValueError("DecoderMetadata noise identity must describe the decoder assumption.")
        if self.metadata.correlation_mode is not None and not self.correlation_semantics:
            raise ValueError("Matching correlation mode requires explicit implementation semantics.")
        if self.metadata.correlation_mode is None and self.correlation_semantics is not None:
            raise ValueError("Correlation semantics must be None when the decoder has no correlation mode.")
        if type(self.requires_detector_coordinates) is not bool:
            raise ValueError("requires_detector_coordinates must be bool.")
        if not isinstance(self.static_resource_note, str) or not self.static_resource_note.strip():
            raise ValueError("static_resource_note must say which static resources are represented or absent.")
        if self.dem_record is not None:
            if not isinstance(self.dem_record, DEMConstructionRecord):
                raise TypeError("dem_record must be a DEMConstructionRecord or None.")
            if (self.dem_record.detector_count != self.metadata.detector_count
                    or self.dem_record.observable_count != self.metadata.observable_count):
                raise ValueError("DEM dimensions differ from decoder metadata.")
        elif self.metadata.implementation.lower().startswith("pymatching"):
            raise ValueError("A PyMatching model must retain its concrete DEM construction record.")
        if not isinstance(self.static_resource_sha256, tuple):
            raise ValueError("static_resource_sha256 must be an immutable tuple.")
        for digest in self.static_resource_sha256:
            _check_digest(digest, "static_resource_sha256 entry")

    @classmethod
    def create(
        cls, sampling: SamplingIdentity, metadata: DecoderMetadata, *,
        dem_record: DEMConstructionRecord | None,
        decoder_assumed_noise_model_id: str,
        decoder_assumed_noise_provenance: Mapping[str, Any],
        correlation_semantics: str | None,
        requires_detector_coordinates: bool = False,
        static_resource_sha256: tuple[str, ...] = (),
        static_resource_note: str = "No additional static resource declared.",
    ) -> "DecoderModelIdentity":
        if not isinstance(decoder_assumed_noise_provenance, Mapping) or not decoder_assumed_noise_provenance:
            raise ValueError("Explicit decoder assumed-noise/model provenance is required.")
        noise_json = _canonical(dict(decoder_assumed_noise_provenance)).decode("utf-8")
        noise_digest = _sha(noise_json.encode("utf-8"))
        return cls(
            schema=DECODER_MODEL_SCHEMA, sampling_identity_sha256=sampling.identity_sha256,
            metadata=metadata, input_representation=DETECTOR_REPRESENTATION,
            detector_order_sha256=sampling.detector_order_sha256,
            observable_semantics_sha256=sampling.observable_semantics_sha256,
            dem_record=dem_record,
            decoder_assumed_noise_model_id=decoder_assumed_noise_model_id,
            decoder_assumed_noise_provenance_json=noise_json,
            decoder_assumed_noise_provenance_sha256=noise_digest,
            correlation_semantics=correlation_semantics,
            requires_detector_coordinates=requires_detector_coordinates,
            static_resource_sha256=tuple(static_resource_sha256),
            static_resource_note=static_resource_note,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "sampling_identity_sha256": self.sampling_identity_sha256,
            "metadata": asdict(self.metadata), "input_representation": self.input_representation,
            "detector_order_sha256": self.detector_order_sha256,
            "observable_semantics_sha256": self.observable_semantics_sha256,
            "dem_record": None if self.dem_record is None else self.dem_record.to_dict(),
            "decoder_assumed_noise_model_id": self.decoder_assumed_noise_model_id,
            "decoder_assumed_noise_provenance": json.loads(self.decoder_assumed_noise_provenance_json),
            "decoder_assumed_noise_provenance_sha256": self.decoder_assumed_noise_provenance_sha256,
            "correlation_semantics": self.correlation_semantics,
            "requires_detector_coordinates": self.requires_detector_coordinates,
            "static_resource_sha256": list(self.static_resource_sha256),
            "static_resource_note": self.static_resource_note,
        }

    @property
    def identity_sha256(self) -> str:
        return _sha(_canonical(self.to_dict()))


def assert_model_compatible(model: DecoderModelIdentity, sampling: SamplingIdentity) -> None:
    """Require explicit intended support and exact detector/observable semantics."""
    if not isinstance(model, DecoderModelIdentity) or not isinstance(sampling, SamplingIdentity):
        raise TypeError("model and sampling must use the NS-2B versioned contracts.")
    if model.sampling_identity_sha256 != sampling.identity_sha256:
        raise ValueError("Decoder does not declare support for this exact sampling identity.")
    if model.metadata.detector_count != len(sampling.detector_ids):
        raise ValueError("Decoder detector dimension differs from sampling identity.")
    if model.metadata.observable_count != len(sampling.observable_ids):
        raise ValueError("Decoder observable dimension differs from sampling identity.")
    if model.detector_order_sha256 != sampling.detector_order_sha256:
        raise ValueError("Decoder detector ordering differs from sampling identity.")
    if (model.dem_record is not None
            and model.dem_record.detector_order_sha256 != sampling.detector_order_sha256):
        raise ValueError("DEM detector ordering/coordinates differ from sampling identity.")
    if (model.dem_record is not None
            and model.dem_record.observable_semantics_sha256 != sampling.observable_semantics_sha256):
        raise ValueError("DEM observable semantics differ from sampling identity.")
    if model.observable_semantics_sha256 != sampling.observable_semantics_sha256:
        raise ValueError("Decoder observable interpretation or polarity differs from sampling identity.")
    if model.requires_detector_coordinates and any(x is None for x in sampling.detector_coordinates):
        raise ValueError("Decoder requires detector coordinates that are unknown.")
    # Deliberately do not compare decoder_assumed_noise_model_id with the
    # generating-noise model ID. Their difference is an auditable model mismatch.


@dataclass(frozen=True, init=False)
class DetectorBatch:
    """Immutable detector-only bytes bound to one sampling identity.

    Instances should be created by TrustedDetectorBatchAdapter. This is a
    programming boundary, not cryptographic proof of upstream provenance.
    """

    _data: bytes
    sampling_identity_sha256: str
    detector_order_sha256: str
    shape: tuple[int, int]
    source_circuit_sha256: str
    content_sha256: str

    @property
    def detector_bits(self) -> np.ndarray:
        return np.frombuffer(self._data, dtype=np.uint8).reshape(self.shape)


class TrustedDetectorBatchAdapter:
    """Attach identity at the sampling boundary and reject declared reordering."""

    def __init__(self, sampling: SamplingIdentity):
        if not isinstance(sampling, SamplingIdentity):
            raise TypeError("sampling must be SamplingIdentity.")
        self.sampling = sampling

    def from_stim_detector_samples(
        self, circuit: Any, detector_samples: Any, *,
        column_detector_ids: tuple[int, ...],
    ) -> DetectorBatch:
        import stim
        if not isinstance(circuit, stim.Circuit):
            raise TypeError("circuit must be Stim Circuit.")
        if str(stim.__version__) != self.sampling.stim_version:
            raise ValueError("Installed Stim version differs from the sampling identity.")
        source_sha = _sha(str(circuit).encode("utf-8"))
        if source_sha != self.sampling.circuit_sha256:
            raise ValueError("Sampling circuit digest differs from the trusted sampling identity.")
        if (not isinstance(column_detector_ids, tuple)
                or any(type(v) is not int for v in column_detector_ids)
                or tuple(column_detector_ids) != self.sampling.detector_ids):
            raise ValueError("Detector columns are not in the declared Stim detector order.")
        bits = binary_matrix(detector_samples, name="Stim detector samples",
                             columns=len(self.sampling.detector_ids))
        if len(bits) <= 0:
            raise ValueError("Detector batch must contain at least one shot.")
        data = bits.tobytes(order="C")
        batch = object.__new__(DetectorBatch)
        object.__setattr__(batch, "_data", data)
        object.__setattr__(batch, "sampling_identity_sha256", self.sampling.identity_sha256)
        object.__setattr__(batch, "detector_order_sha256", self.sampling.detector_order_sha256)
        object.__setattr__(batch, "shape", tuple(int(x) for x in bits.shape))
        object.__setattr__(batch, "source_circuit_sha256", source_sha)
        object.__setattr__(batch, "content_sha256", _sha(data))
        return batch


def validate_batch(batch: DetectorBatch, sampling: SamplingIdentity) -> np.ndarray:
    if not isinstance(batch, DetectorBatch):
        raise TypeError("batch must be produced by TrustedDetectorBatchAdapter.")
    if batch.sampling_identity_sha256 != sampling.identity_sha256:
        raise ValueError("Detector batch sampling identity mismatch.")
    if batch.source_circuit_sha256 != sampling.circuit_sha256:
        raise ValueError("Detector batch source circuit digest mismatch.")
    if batch.detector_order_sha256 != sampling.detector_order_sha256:
        raise ValueError("Detector batch column ordering fingerprint mismatch.")
    if len(batch.shape) != 2 or batch.shape[1] != len(sampling.detector_ids):
        raise ValueError("Detector batch shape differs from sampling identity.")
    if _sha(batch._data) != batch.content_sha256 or len(batch._data) != batch.shape[0] * batch.shape[1]:
        raise ValueError("Detector batch bytes fail integrity or shape validation.")
    return batch.detector_bits


def _validate_elapsed(value: Any) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0:
        raise ValueError("Decoder elapsed_seconds must be a finite, nonnegative real number, not bool.")


def decode_model_checked(
    decoder: DecoderProtocol, model: DecoderModelIdentity,
    sampling: SamplingIdentity, batch: DetectorBatch,
) -> DecoderPrediction:
    """Decode a defensive copy, validate immutable registration before/after."""
    assert_model_compatible(model, sampling)
    source = validate_batch(batch, sampling)
    if not callable(getattr(decoder, "decode", None)):
        raise TypeError("Decoder must implement decode(detectors).")
    registered = getattr(decoder, "metadata", None)
    if not isinstance(registered, DecoderMetadata) or registered != model.metadata:
        raise ValueError("Decoder metadata differs from its registered decoder-model identity.")
    # Snapshot field values, not the metadata object reference: even a hostile
    # decoder using object.__setattr__ must not rewrite the comparison target.
    registered_fields = asdict(registered)
    input_copy = np.array(source, dtype=np.uint8, order="C", copy=True)
    result = decoder.decode(input_copy)
    current_metadata = getattr(decoder, "metadata", None)
    if not isinstance(current_metadata, DecoderMetadata) or asdict(current_metadata) != registered_fields:
        raise ValueError("Decoder metadata mutated during inference.")
    if not isinstance(result, DecoderPrediction):
        raise TypeError("Decoder must return DecoderPrediction.")
    if not isinstance(result.metadata, DecoderMetadata) or asdict(result.metadata) != registered_fields:
        raise ValueError("Prediction metadata differs from the registered decoder metadata.")
    bits = binary_matrix(result.bits, name="decoder predictions",
                         columns=len(sampling.observable_ids))
    if bits.shape != (batch.shape[0], len(sampling.observable_ids)):
        raise ValueError("Prediction shape/shot count differs from detector batch and observable count.")
    _validate_elapsed(result.elapsed_seconds)
    # Copy to detach from decoder-owned arrays; result remains a valid common
    # v1 DecoderPrediction for existing downstream consumers.
    stable_metadata = DecoderMetadata(**registered_fields)
    return DecoderPrediction(np.array(bits, dtype=np.uint8, order="C", copy=True),
                             stable_metadata, float(result.elapsed_seconds)
                             if result.elapsed_seconds is not None else None)


class IdentityAwareDecoderRegistry:
    """Compatibility-aware wrapper; the v1 DecoderRegistry remains unchanged."""

    def __init__(self, sampling_identity: SamplingIdentity | None = None) -> None:
        if sampling_identity is not None and not isinstance(sampling_identity, SamplingIdentity):
            raise TypeError("sampling_identity must be SamplingIdentity or None.")
        self.core_registry = DecoderRegistry()
        self.sampling_identity = sampling_identity
        self._models: dict[str, DecoderModelIdentity] = {}
        self._sampling: dict[str, SamplingIdentity] = {}

    def register(
        self, decoder: DecoderProtocol, *, model: DecoderModelIdentity,
        sampling: SamplingIdentity,
    ) -> None:
        assert_model_compatible(model, sampling)
        if (self.sampling_identity is not None
                and self.sampling_identity.identity_sha256 != sampling.identity_sha256):
            raise ValueError("This registry is bound to a different sampling identity.")
        if decoder.metadata != model.metadata:
            raise ValueError("Decoder metadata does not match decoder-model identity at registration.")
        if self.sampling_identity is None:
            self.sampling_identity = sampling
        name = model.metadata.name
        self.core_registry.register(name, decoder)
        self._models[name] = model
        self._sampling[name] = sampling

    def names(self) -> tuple[str, ...]:
        return self.core_registry.names()

    def get(self, name: str) -> DecoderProtocol:
        return self.core_registry.get(name)

    def model_identity(self, name: str) -> DecoderModelIdentity:
        return self._models[name]

    def selector(self, *, fallback_name: str, **kwargs: Any) -> SafeDecoderSelector:
        """Use the existing fallback/experimental opt-in controller unchanged."""
        return SafeDecoderSelector(self.core_registry, fallback_name=fallback_name, **kwargs)

    def decode(self, name: str, batch: DetectorBatch) -> DecoderPrediction:
        return decode_model_checked(self.get(name), self._models[name], self._sampling[name], batch)


class _SavedPredictionDecoder:
    def __init__(self, prediction: DecoderPrediction):
        self.metadata = prediction.metadata
        self._prediction = prediction

    def decode(self, detectors: np.ndarray) -> DecoderPrediction:
        return DecoderPrediction(self._prediction.bits.copy(), self.metadata,
                                 self._prediction.elapsed_seconds)


def evaluate_identity_aware_paired(
    registry: IdentityAwareDecoderRegistry, batch: DetectorBatch,
    observables: Any, *, decoder_names: tuple[str, ...], baseline_name: str,
    scope: str, sample_id: str,
) -> dict[str, Any]:
    """Run all decoder calls on a shared detector batch, then score labels.

    Observable labels are accepted by this evaluator but are never passed to a
    decoder. Scope is rejected before any decode unless it is development-only.
    """
    if not isinstance(scope, str):
        raise ValueError("scope must be a string.")
    if scope not in ALLOWED_SCOPES:
        if scope == "protected-test":
            raise PermissionError("Protected-test evaluation is not supported by this development API.")
        raise ValueError(f"Unsupported evaluation scope {scope!r}.")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError("sample_id is required for paired evidence provenance.")
    if (not isinstance(decoder_names, tuple) or not decoder_names
            or any(not isinstance(name, str) or not name.strip() for name in decoder_names)
            or not isinstance(baseline_name, str) or baseline_name not in decoder_names):
        raise ValueError("decoder_names must include the requested baseline.")
    if len(set(decoder_names)) != len(decoder_names):
        raise ValueError("decoder_names must be unique.")
    if any(name not in registry.names() for name in decoder_names):
        raise ValueError("Every requested decoder must be registered before paired evaluation.")
    if any(registry._sampling[name].identity_sha256 != batch.sampling_identity_sha256
           for name in decoder_names):
        raise ValueError("All paired decoders must support the detector batch sampling identity.")
    detector_bytes = validate_batch(batch, registry._sampling[decoder_names[0]]).tobytes(order="C")
    predictions: dict[str, DecoderPrediction] = {}
    identities: dict[str, str] = {}
    for name in decoder_names:
        sampling = registry._sampling[name]
        predictions[name] = registry.decode(name, batch)
        identities[name] = registry.model_identity(name).identity_sha256
        if validate_batch(batch, sampling).tobytes(order="C") != detector_bytes:
            raise RuntimeError("Detector batch changed during paired decoder evaluation.")
    # The labels enter only after every underlying decoder has returned.
    proxies = {name: _SavedPredictionDecoder(predictions[name]) for name in decoder_names}
    report = evaluate_paired(
        batch.detector_bits, observables, proxies, baseline_name=baseline_name,
        scope=scope, sample_id=sample_id,
    )
    report["sampling_identity_sha256"] = batch.sampling_identity_sha256
    report["decoder_model_identity_sha256"] = identities
    report["paired_detector_content_sha256"] = batch.content_sha256
    report["label_isolation"] = "All model decodes completed before labels were scored; labels are not decoder inputs."
    return report
