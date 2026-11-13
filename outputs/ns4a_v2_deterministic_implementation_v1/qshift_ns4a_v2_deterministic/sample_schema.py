"""Sample identity and root-archive validation; contains no sampler code."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .protocol import (CANDIDATE_IDS, CONDITIONS, EVALUATION_ARMS, ProtocolValidationError,
                       parse_root_id, shots_for_root)


ARCHIVE_SCHEMA = "qshift-ns4a-v2-root-archive-v1"
ARCHIVE_KEYS = frozenset({
    "schema_version", "partition", "condition_id", "root_id", "sample_ids",
    "detectors", "observables", "candidate_ids", "predictions", "metadata_json",
})


class ArchiveValidationError(ValueError):
    """Saved evidence is missing, malformed, duplicated, or inconsistent."""


def make_sample_ids(partition: str, condition_id: str, root_id: str, shots: int) -> tuple[str, ...]:
    if partition not in {"selection", "evaluation"}:
        raise ArchiveValidationError("partition must be selection or evaluation.")
    if condition_id not in CONDITIONS or not isinstance(root_id, str) or not root_id:
        raise ArchiveValidationError("condition_id/root_id is invalid.")
    if type(shots) is not int or shots <= 0:
        raise ArchiveValidationError("shots must be a positive integer.")
    try:
        root_index = parse_root_id(partition, condition_id, root_id)
        required_shots = shots_for_root(partition, condition_id, root_index)
    except ProtocolValidationError as exc:
        raise ArchiveValidationError(str(exc)) from exc
    if shots != required_shots:
        raise ArchiveValidationError(f"root has {shots} shots; V2 allocation requires {required_shots}.")
    return tuple(f"ns4a-v2|{partition}|{condition_id}|{root_id}|{offset:06d}" for offset in range(shots))


def validate_paired_sample_ids(
    detector_ids: Sequence[str], label_ids: Sequence[str], prediction_ids: Sequence[str],
) -> tuple[str, ...]:
    detector = tuple(detector_ids)
    labels = tuple(label_ids)
    predictions = tuple(prediction_ids)
    if not detector or detector != labels or detector != predictions:
        raise ArchiveValidationError("detector, label, and prediction row IDs must match exactly and be nonempty.")
    if any(not isinstance(value, str) or not value for value in detector):
        raise ArchiveValidationError("sample IDs must be nonempty strings.")
    if len(set(detector)) != len(detector):
        raise ArchiveValidationError("duplicate sample ID within a root batch.")
    return detector


def sample_id_sequence_sha256(sample_ids: Sequence[str]) -> str:
    encoded = "\n".join(sample_ids).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _scalar_string(value: Any, name: str) -> str:
    array = np.asarray(value)
    if array.shape != () or array.dtype.kind not in "US":
        raise ArchiveValidationError(f"{name} must be a scalar string array.")
    return str(array.item())


def _binary_uint8(value: Any, name: str) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype != np.dtype(np.uint8) or not np.isfinite(array).all() or np.any(array > 1):
        raise ArchiveValidationError(f"{name} must be uint8 containing only 0/1 values.")
    return array


@dataclass(frozen=True)
class ValidatedArchive:
    partition: str
    condition_id: str
    root_id: str
    sample_ids: tuple[str, ...]
    detectors: np.ndarray
    observables: np.ndarray
    candidate_ids: tuple[str, ...]
    predictions: np.ndarray
    metadata: Mapping[str, Any]


def validate_archive_mapping(archive: Mapping[str, Any]) -> ValidatedArchive:
    keys = frozenset(archive.keys())
    if keys != ARCHIVE_KEYS:
        missing, extra = sorted(ARCHIVE_KEYS - keys), sorted(keys - ARCHIVE_KEYS)
        raise ArchiveValidationError(f"archive key mismatch; missing={missing}, extra={extra}.")
    if _scalar_string(archive["schema_version"], "schema_version") != ARCHIVE_SCHEMA:
        raise ArchiveValidationError("unsupported archive schema version.")
    partition = _scalar_string(archive["partition"], "partition")
    condition = _scalar_string(archive["condition_id"], "condition_id")
    root_id = _scalar_string(archive["root_id"], "root_id")
    if partition not in {"selection", "evaluation"} or condition not in CONDITIONS or not root_id:
        raise ArchiveValidationError("invalid partition, condition, or root ID.")

    raw_ids = np.asarray(archive["sample_ids"])
    if raw_ids.ndim != 1 or raw_ids.dtype.kind not in "US":
        raise ArchiveValidationError("sample_ids must be a one-dimensional string array.")
    sample_ids = tuple(str(x) for x in raw_ids.tolist())
    expected_ids = make_sample_ids(partition, condition, root_id, len(sample_ids))
    if sample_ids != expected_ids:
        raise ArchiveValidationError("sample IDs do not match the declared root/partition/condition offsets.")

    detectors = _binary_uint8(archive["detectors"], "detectors")
    observables = _binary_uint8(archive["observables"], "observables")
    predictions = _binary_uint8(archive["predictions"], "predictions")
    candidate_raw = np.asarray(archive["candidate_ids"])
    if candidate_raw.ndim != 1 or candidate_raw.dtype.kind not in "US":
        raise ArchiveValidationError("candidate_ids must be a one-dimensional string array.")
    candidate_ids = tuple(str(x) for x in candidate_raw.tolist())
    expected_candidates = CANDIDATE_IDS if partition == "selection" else EVALUATION_ARMS
    if candidate_ids != expected_candidates:
        raise ArchiveValidationError("candidate IDs must exactly match the frozen ordered roster.")

    shots = len(sample_ids)
    if shots == 0 or detectors.shape != (shots, 40) or observables.shape != (shots, 1):
        raise ArchiveValidationError("detector/observable dimensions do not match the V2 [shots,40]/[shots,1] contract.")
    if predictions.shape != (len(candidate_ids), shots, 1):
        raise ArchiveValidationError("predictions dimensions do not match [candidate,shots,1].")

    metadata_text = _scalar_string(archive["metadata_json"], "metadata_json")
    try:
        metadata = json.loads(metadata_text)
    except json.JSONDecodeError as exc:
        raise ArchiveValidationError("metadata_json is invalid JSON.") from exc
    required_meta = {"sampling_identity_sha256", "model_identity_sha256_by_candidate", "row_identity_sha256", "root_seed_ref"}
    if not isinstance(metadata, dict) or not required_meta.issubset(metadata):
        raise ArchiveValidationError("metadata_json lacks required identity/provenance fields.")
    if metadata["row_identity_sha256"] != sample_id_sequence_sha256(sample_ids):
        raise ArchiveValidationError("row identity digest differs from the archived sample ID sequence.")
    model_ids = metadata["model_identity_sha256_by_candidate"]
    if not isinstance(model_ids, dict) or set(model_ids) != set(candidate_ids):
        raise ArchiveValidationError("decoder model identity map must cover exactly the candidate roster.")
    if any(not isinstance(value, str) or len(value) != 64
           or any(c not in "0123456789abcdef" for c in value) for value in model_ids.values()):
        raise ArchiveValidationError("decoder model identity values must be SHA-256 hex strings.")
    if (not isinstance(metadata["sampling_identity_sha256"], str)
            or len(metadata["sampling_identity_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in metadata["sampling_identity_sha256"])):
        raise ArchiveValidationError("sampling identity must be a SHA-256 hex string.")
    if not isinstance(metadata["root_seed_ref"], str) or not metadata["root_seed_ref"]:
        raise ArchiveValidationError("root_seed_ref must identify a later frozen seed-inventory entry.")

    return ValidatedArchive(
        partition, condition, root_id, sample_ids, detectors, observables,
        candidate_ids, predictions, metadata,
    )


def load_validated_archive(path: str | Path) -> tuple[ValidatedArchive, str]:
    path = Path(path)
    if not path.is_file():
        raise ArchiveValidationError(f"archive is missing: {path.name}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        with np.load(path, allow_pickle=False) as loaded:
            archive = {key: loaded[key] for key in loaded.files}
    except Exception as exc:
        raise ArchiveValidationError(f"archive could not be read safely: {type(exc).__name__}: {exc}") from exc
    return validate_archive_mapping(archive), digest
