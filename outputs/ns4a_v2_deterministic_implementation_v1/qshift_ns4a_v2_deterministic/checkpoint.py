"""Atomic archive/checkpoint helpers and fail-closed resume validation.

These helpers are not a production runner. They never call a sampler and do
not create experiment samples.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator, Mapping, Sequence

from .protocol import CONDITIONS, parse_root_id, shots_for_root


class CheckpointError(ValueError):
    """Checkpoint is ambiguous, corrupted, duplicated, or unsafe to resume."""


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CheckpointError("checkpoint payload must be finite JSON-compatible data.") from exc


@contextmanager
def _exclusive_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise CheckpointError("checkpoint lock exists; fail closed without stealing it.") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(str(os.getpid()))
            stream.flush()
            os.fsync(stream.fileno())
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def atomic_write_json(path: str | Path, payload: Mapping[str, Any], *, expected_previous_sha256: str | None = None) -> str:
    """Write JSON via same-directory temp+fsync+replace under exclusive lock.

    Existing state is replaced only when the caller supplies its exact current
    SHA-256; this prevents stale status from silently overwriting newer state.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    content = _canonical_json(payload) + b"\n"
    with _exclusive_lock(lock):
        exists = path.exists()
        if exists:
            actual_old = hashlib.sha256(path.read_bytes()).hexdigest()
            if expected_previous_sha256 is None or actual_old != expected_previous_sha256:
                raise CheckpointError("existing checkpoint differs from the caller's expected prior hash.")
        elif expected_previous_sha256 is not None:
            raise CheckpointError("expected prior checkpoint is missing.")
        fd, temp_name = tempfile.mkstemp(prefix=path.name + ".partial-", dir=path.parent)
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                actual_old = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual_old != expected_previous_sha256:
                    raise CheckpointError("checkpoint changed during atomic update; refusing replacement.")
            os.replace(temp, path)
        except Exception:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
            raise
    return hashlib.sha256(content).hexdigest()


def atomic_save_npz(path: str | Path, arrays: Mapping[str, Any]) -> str:
    """Create a new archive atomically; an existing archive is never replaced."""
    import numpy as np

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_lock(path.with_suffix(path.suffix + ".lock")):
        if path.exists():
            raise CheckpointError("archive already exists; duplicate root/archive write rejected.")
        fd, temp_name = tempfile.mkstemp(prefix=path.name + ".partial-", suffix=".npz", dir=path.parent)
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                np.savez_compressed(stream, **arrays)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                raise CheckpointError("archive target appeared during write; refusing overwrite.")
            os.replace(temp, path)
        except Exception:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
            raise
    return hashlib.sha256(path.read_bytes()).hexdigest()


def root_commit_marker(record: Mapping[str, Any]) -> str:
    required = {"partition", "condition_id", "root_id", "shots", "archive_sha256", "sample_ids_sha256", "root_seed_ref"}
    if not required.issubset(record):
        raise CheckpointError("root commit record lacks required fields.")
    body = {key: record[key] for key in sorted(required)}
    return hashlib.sha256(_canonical_json(body)).hexdigest()


def validate_checkpoint_payload(payload: Mapping[str, Any]) -> dict[str, int]:
    if payload.get("schema") != "qshift-ns4a-v2-checkpoint-v1":
        raise CheckpointError("unsupported checkpoint schema.")
    if payload.get("state") not in {"paused", "in_progress", "completed", "failed"}:
        raise CheckpointError("checkpoint state is invalid.")
    for field in ("protocol_sha256", "source_manifest_sha256"):
        value = payload.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise CheckpointError(f"{field} must be a lowercase SHA-256 digest.")
    roots = payload.get("committed_roots")
    if not isinstance(roots, list):
        raise CheckpointError("committed_roots must be a list.")
    seen_keys: set[tuple[str, str, str]] = set()
    seen_ranges: set[tuple[str, str, str]] = set()
    seen_seed_refs: set[str] = set()
    counts = {"selection_roots": 0, "evaluation_roots": 0, "selection_shots": 0, "evaluation_shots": 0}
    root_indices_by_cell: dict[tuple[str, str], set[int]] = {}
    for row in roots:
        if not isinstance(row, Mapping) or row.get("committed") is not True:
            raise CheckpointError("every checkpoint root must have a committed archive marker.")
        key = (row.get("partition"), row.get("condition_id"), row.get("root_id"))
        if key in seen_keys or key[0] not in {"selection", "evaluation"} or key[1] not in {
            "balanced_no_burst", "x_biased_no_burst", "z_biased_no_burst",
            "balanced_burst_0.005", "balanced_burst_0.010", "balanced_burst_0.015",
        } or not key[2]:
            raise CheckpointError("duplicate or invalid committed root key.")
        if type(row.get("shots")) is not int or row["shots"] <= 0:
            raise CheckpointError("root shots must be a positive integer.")
        seen_keys.add(key)
        try:
            root_index = parse_root_id(key[0], key[1], key[2])
            required_shots = shots_for_root(key[0], key[1], root_index)
        except Exception as exc:
            raise CheckpointError(f"noncanonical root ID or partition: {key!r}.") from exc
        if row["shots"] != required_shots:
            raise CheckpointError(f"committed root {key!r} has an incorrect shot count.")
        cell = (key[0], key[1])
        root_indices_by_cell.setdefault(cell, set())
        if root_index in root_indices_by_cell[cell]:
            raise CheckpointError("duplicate root index within a condition.")
        root_indices_by_cell[cell].add(root_index)
        sample_id_start, sample_id_end = row.get("sample_id_start"), row.get("sample_id_end")
        expected_start = f"ns4a-v2|{key[0]}|{key[1]}|{key[2]}|000000"
        expected_end = f"ns4a-v2|{key[0]}|{key[1]}|{key[2]}|{row['shots'] - 1:06d}"
        if sample_id_start != expected_start or sample_id_end != expected_end:
            raise CheckpointError("root sample-ID range is missing or invalid.")
        range_key = (key[0], sample_id_start, sample_id_end)
        if range_key in seen_ranges:
            raise CheckpointError("duplicate sample range in checkpoint.")
        seen_ranges.add(range_key)
        for digest_field in ("archive_sha256", "sample_ids_sha256", "commit_marker_sha256"):
            digest = row.get(digest_field)
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise CheckpointError(f"{digest_field} must be a lowercase SHA-256 digest.")
        if root_commit_marker(row) != row["commit_marker_sha256"]:
            raise CheckpointError("root commit marker does not match committed record.")
        seed_ref = row.get("root_seed_ref")
        if not isinstance(seed_ref, str) or not seed_ref or seed_ref in seen_seed_refs:
            raise CheckpointError("root seed reference is missing or reused.")
        seen_seed_refs.add(seed_ref)
        prefix = "selection" if key[0] == "selection" else "evaluation"
        counts[f"{prefix}_roots"] += 1
        counts[f"{prefix}_shots"] += row["shots"]
    if payload.get("state") == "completed":
        if counts != {"selection_roots": 48, "evaluation_roots": 60,
                      "selection_shots": 64_000, "evaluation_shots": 240_000}:
            raise CheckpointError("completed state lacks exact 108 roots and 304000 committed shots.")
        for condition in CONDITIONS:
            if root_indices_by_cell.get(("selection", condition)) != set(range(8)):
                raise CheckpointError("completed state lacks all eight selection roots in a condition.")
            if root_indices_by_cell.get(("evaluation", condition)) != set(range(10)):
                raise CheckpointError("completed state lacks all ten evaluation roots in a condition.")
    return counts


def validate_resume_state(
    payload: Mapping[str, Any], *, expected_protocol_sha256: str,
    expected_source_manifest_sha256: str, archive_paths_by_key: Mapping[str, str | Path],
    uncommitted_files: Sequence[str | Path] = (),
) -> dict[str, int]:
    counts = validate_checkpoint_payload(payload)
    if payload.get("state") != "paused":
        raise CheckpointError("only an explicitly paused state can be resumed.")
    if payload.get("protocol_sha256") != expected_protocol_sha256 or payload.get("source_manifest_sha256") != expected_source_manifest_sha256:
        raise CheckpointError("checkpoint protocol/source hash differs from the current freeze.")
    if payload.get("in_flight_root") is not None:
        raise CheckpointError("in-flight sampler state is ambiguous; manual review required.")
    if uncommitted_files:
        raise CheckpointError("partial/uncommitted files exist; recovery fails closed.")
    for row in payload["committed_roots"]:
        key = "|".join((row["partition"], row["condition_id"], row["root_id"]))
        path = archive_paths_by_key.get(key)
        if path is None or not Path(path).is_file():
            raise CheckpointError(f"committed archive missing for {key}.")
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != row["archive_sha256"]:
            raise CheckpointError(f"committed archive hash mismatch for {key}.")
    return counts
