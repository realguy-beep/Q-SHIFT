"""Transactional root archives and commit-marker verification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from qshift_ns4a_v2_deterministic.checkpoint import (
    CheckpointError,
    atomic_save_npz,
    atomic_write_json,
    root_commit_marker,
)
from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS, EVALUATION_ARMS, CONDITIONS
from qshift_ns4a_v2_deterministic.sample_schema import (
    ARCHIVE_SCHEMA,
    load_validated_archive,
    make_sample_ids,
    sample_id_sequence_sha256,
    validate_archive_mapping,
)


class TransactionError(RuntimeError):
    """A root archive transaction is incomplete or inconsistent."""


def archive_path(root_dir: str | Path, partition: str, condition_id: str, root_id: str) -> Path:
    if partition not in {"selection", "evaluation"} or condition_id not in CONDITIONS:
        raise TransactionError("invalid archive partition or condition.")
    if not root_id.startswith(f"{partition}:{condition_id}:r"):
        raise TransactionError("root ID does not match archive partition/condition.")
    return Path(root_dir) / "roots" / f"{partition}__{condition_id}__{root_id.split(':')[-1]}.npz"


def build_archive_arrays(
    *, partition: str, condition_id: str, root_id: str,
    detectors: Any, observables: Any, predictions: Any,
    model_identity_sha256_by_candidate: Mapping[str, str],
    sampling_identity_sha256: str, root_seed_ref: str,
    extra_metadata: Mapping[str, Any] | None = None,
) -> dict[str, np.ndarray]:
    det = np.asarray(detectors)
    obs = np.asarray(observables)
    pred = np.asarray(predictions)
    candidates = CANDIDATE_IDS if partition == "selection" else EVALUATION_ARMS
    if obs.ndim == 1:
        obs = obs[:, None]
    if det.ndim != 2 or obs.ndim != 2 or det.dtype != np.uint8 or obs.dtype != np.uint8:
        raise TransactionError("archive detector/observable inputs must be uint8 matrices.")
    if pred.dtype != np.uint8 or pred.shape != (len(candidates), len(det), 1):
        raise TransactionError("prediction stack must follow the frozen candidate/arm order.")
    if not isinstance(model_identity_sha256_by_candidate, Mapping) or tuple(model_identity_sha256_by_candidate) != candidates:
        raise TransactionError("model-identity map must follow the complete frozen roster order.")
    if obs.shape != (len(det), 1):
        raise TransactionError("observable rows do not match detector rows.")
    ids = make_sample_ids(partition, condition_id, root_id, len(det))
    metadata: dict[str, Any] = {
        "sampling_identity_sha256": sampling_identity_sha256,
        "model_identity_sha256_by_candidate": dict(model_identity_sha256_by_candidate),
        "row_identity_sha256": sample_id_sequence_sha256(ids),
        "root_seed_ref": root_seed_ref,
    }
    if extra_metadata:
        extras = dict(extra_metadata)
        if set(extras).intersection(metadata):
            raise TransactionError("extra metadata cannot override row identity or seed provenance.")
        metadata.update(extras)
    mapping = {
        "schema_version": np.asarray(ARCHIVE_SCHEMA),
        "partition": np.asarray(partition),
        "condition_id": np.asarray(condition_id),
        "root_id": np.asarray(root_id),
        "sample_ids": np.asarray(ids),
        "detectors": det,
        "observables": obs,
        "candidate_ids": np.asarray(candidates),
        "predictions": pred,
        "metadata_json": np.asarray(json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False)),
    }
    try:
        validate_archive_mapping(mapping)
    except Exception as exc:
        raise TransactionError(f"constructed root archive violates frozen schema: {exc}") from exc
    return mapping


def _root_record(archive: Any, archive_sha256: str, root_seed_ref: str) -> dict[str, Any]:
    sample_ids = archive.sample_ids
    row = {
        "partition": archive.partition,
        "condition_id": archive.condition_id,
        "root_id": archive.root_id,
        "shots": len(sample_ids),
        "archive_sha256": archive_sha256,
        "sample_ids_sha256": sample_id_sequence_sha256(sample_ids),
        "root_seed_ref": root_seed_ref,
        "sample_id_start": sample_ids[0],
        "sample_id_end": sample_ids[-1],
        "committed": True,
    }
    row["commit_marker_sha256"] = root_commit_marker(row)
    return row


def commit_root_archive(
    root_dir: str | Path, arrays: Mapping[str, Any], *, root_seed_ref: str,
) -> dict[str, Any]:
    """Write archive, verify bytes, write its marker; never overwrite a root."""
    if not isinstance(root_seed_ref, str) or not root_seed_ref.strip():
        raise TransactionError("root_seed_ref is required.")
    archive = validate_archive_mapping(arrays)
    path = archive_path(root_dir, archive.partition, archive.condition_id, archive.root_id)
    marker_path = path.with_suffix(".commit.json")
    if path.exists() or marker_path.exists():
        raise TransactionError("archive or commit marker already exists; duplicate root write refused.")
    archive_sha = atomic_save_npz(path, arrays)
    validated, verified_sha = load_validated_archive(path)
    if verified_sha != archive_sha:
        raise TransactionError("archive hash changed after atomic write.")
    record = _root_record(validated, verified_sha, root_seed_ref)
    marker = {**record, "marker_schema": "qshift-ns4a-v2-root-commit-v1"}
    try:
        atomic_write_json(marker_path, marker)
    except Exception:
        # Leave any committed bytes untouched. Presence without a matching
        # checkpoint/marker is an explicit recovery blocker, never overwrite.
        raise
    checked = read_and_verify_commit(path, marker_path)
    if checked != record:
        raise TransactionError("written commit marker did not round-trip exactly.")
    return record


def read_and_verify_commit(path: str | Path, marker_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(path)
    marker_file = Path(marker_path) if marker_path is not None else path.with_suffix(".commit.json")
    if not path.is_file() or not marker_file.is_file():
        raise TransactionError("committed root requires both archive and marker.")
    try:
        marker = json.loads(marker_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TransactionError("root commit marker is unreadable.") from exc
    if not isinstance(marker, dict) or marker.pop("marker_schema", None) != "qshift-ns4a-v2-root-commit-v1":
        raise TransactionError("unsupported root commit-marker schema.")
    try:
        archive, archive_sha = load_validated_archive(path)
    except Exception as exc:
        raise TransactionError(f"committed archive is invalid: {exc}") from exc
    if hashlib.sha256(path.read_bytes()).hexdigest() != archive_sha or marker.get("archive_sha256") != archive_sha:
        raise TransactionError("root archive hash differs from its durable commit marker.")
    if marker.get("partition") != archive.partition or marker.get("condition_id") != archive.condition_id:
        raise TransactionError("commit marker identity differs from archive.")
    if marker.get("root_id") != archive.root_id or marker.get("shots") != len(archive.sample_ids):
        raise TransactionError("commit marker root/shot count differs from archive.")
    if marker.get("sample_ids_sha256") != sample_id_sequence_sha256(archive.sample_ids):
        raise TransactionError("commit marker sample identity digest differs from archive.")
    if root_commit_marker(marker) != marker.get("commit_marker_sha256"):
        raise TransactionError("root commit-marker digest is invalid.")
    if set(marker) != {
        "partition", "condition_id", "root_id", "shots", "archive_sha256",
        "sample_ids_sha256", "root_seed_ref", "sample_id_start", "sample_id_end",
        "committed", "commit_marker_sha256",
    }:
        raise TransactionError("commit marker contains missing or unexpected fields.")
    if marker.get("committed") is not True:
        raise TransactionError("root commit marker is not committed.")
    expected_ids = make_sample_ids(archive.partition, archive.condition_id, archive.root_id, len(archive.sample_ids))
    if archive.sample_ids != expected_ids or marker.get("sample_id_start") != expected_ids[0] or marker.get("sample_id_end") != expected_ids[-1]:
        raise TransactionError("commit marker sample-ID range differs from archived rows.")
    return marker
