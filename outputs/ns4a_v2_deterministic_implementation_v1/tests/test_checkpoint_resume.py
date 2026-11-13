from __future__ import annotations

import hashlib

import numpy as np
import pytest

from qshift_ns4a_v2_deterministic.checkpoint import (
    CheckpointError, atomic_save_npz, atomic_write_json, root_commit_marker,
    validate_checkpoint_payload, validate_resume_state,
)
from qshift_ns4a_v2_deterministic.protocol import CONDITIONS, make_root_id, selection_shots


PROTO = "a" * 64
SOURCE = "b" * 64


def _committed_selection_root(tmp_path):
    condition = CONDITIONS[0]
    root_id = make_root_id("selection", condition, 0)
    shots = selection_shots(0, 0)
    archive = tmp_path / "root.npz"
    archive_sha = atomic_save_npz(archive, {"fixture": np.zeros((shots, 1), dtype=np.uint8)})
    ids_blob = "\n".join(
        f"ns4a-v2|selection|{condition}|{root_id}|{i:06d}" for i in range(shots)
    ).encode("utf-8")
    row = {
        "partition": "selection", "condition_id": condition, "root_id": root_id,
        "shots": shots, "archive_sha256": archive_sha,
        "sample_ids_sha256": hashlib.sha256(ids_blob).hexdigest(),
        "root_seed_ref": "fixture-only/root-0",
        "sample_id_start": f"ns4a-v2|selection|{condition}|{root_id}|000000",
        "sample_id_end": f"ns4a-v2|selection|{condition}|{root_id}|{shots - 1:06d}",
        "committed": True,
    }
    row["commit_marker_sha256"] = root_commit_marker(row)
    payload = {"schema": "qshift-ns4a-v2-checkpoint-v1", "state": "paused",
               "protocol_sha256": PROTO, "source_manifest_sha256": SOURCE,
               "committed_roots": [row], "in_flight_root": None}
    return archive, row, payload


def test_atomic_state_update_requires_exact_prior_hash_and_preserves_lock_fail_closed(tmp_path):
    path = tmp_path / "status.json"
    first = atomic_write_json(path, {"state": "paused", "counter": 1})
    assert first == hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(CheckpointError, match="expected prior hash"):
        atomic_write_json(path, {"state": "paused", "counter": 2})
    second = atomic_write_json(path, {"state": "paused", "counter": 2}, expected_previous_sha256=first)
    assert second == hashlib.sha256(path.read_bytes()).hexdigest()
    lock = path.with_suffix(".json.lock")
    lock.write_text("held-by-test", encoding="utf-8")
    with pytest.raises(CheckpointError, match="lock exists"):
        atomic_write_json(path, {"state": "completed"}, expected_previous_sha256=second)
    assert '"counter":2' in path.read_text(encoding="utf-8")


def test_atomic_archive_never_overwrites_and_failed_replace_leaves_no_partial(tmp_path, monkeypatch):
    import qshift_ns4a_v2_deterministic.checkpoint as module
    path = tmp_path / "archive.npz"
    original = atomic_save_npz(path, {"x": np.asarray([1], dtype=np.uint8)})
    with pytest.raises(CheckpointError, match="already exists"):
        atomic_save_npz(path, {"x": np.asarray([2], dtype=np.uint8)})
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original

    failed = tmp_path / "failed.npz"
    def fail_replace(_source, _target):
        raise PermissionError("deterministic fixture replace failure")
    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(PermissionError, match="fixture replace failure"):
        atomic_save_npz(failed, {"x": np.asarray([3], dtype=np.uint8)})
    assert not failed.exists()
    assert not list(tmp_path.glob("failed.npz.partial-*.npz"))


def test_resume_accepts_hash_verified_committed_root_and_rejects_tamper_or_partial(tmp_path):
    archive, row, payload = _committed_selection_root(tmp_path)
    counts = validate_checkpoint_payload(payload)
    assert counts["selection_roots"] == 1 and counts["selection_shots"] == row["shots"]
    key = "|".join((row["partition"], row["condition_id"], row["root_id"]))
    resumed = validate_resume_state(payload, expected_protocol_sha256=PROTO,
        expected_source_manifest_sha256=SOURCE, archive_paths_by_key={key: archive})
    assert resumed == counts
    partial = tmp_path / "status.partial-000"
    partial.write_text("{", encoding="utf-8")
    with pytest.raises(CheckpointError, match="partial/uncommitted"):
        validate_resume_state(payload, expected_protocol_sha256=PROTO,
            expected_source_manifest_sha256=SOURCE, archive_paths_by_key={key: archive},
            uncommitted_files=[partial])
    archive.write_bytes(archive.read_bytes() + b"tamper")
    with pytest.raises(CheckpointError, match="archive hash mismatch"):
        validate_resume_state(payload, expected_protocol_sha256=PROTO,
            expected_source_manifest_sha256=SOURCE, archive_paths_by_key={key: archive})


def test_duplicate_root_bad_commit_marker_and_incomplete_completed_state_fail_closed(tmp_path):
    _archive, row, payload = _committed_selection_root(tmp_path)
    duplicate = dict(payload)
    duplicate["committed_roots"] = [row, dict(row)]
    with pytest.raises(CheckpointError, match="duplicate or invalid"):
        validate_checkpoint_payload(duplicate)
    corrupted = dict(payload)
    bad_row = dict(row)
    bad_row["commit_marker_sha256"] = "0" * 64
    corrupted["committed_roots"] = [bad_row]
    with pytest.raises(CheckpointError, match="commit marker"):
        validate_checkpoint_payload(corrupted)
    incomplete = dict(payload)
    incomplete["state"] = "completed"
    with pytest.raises(CheckpointError, match="exact 108 roots"):
        validate_checkpoint_payload(incomplete)


def test_resume_rejects_unpaused_hash_drift_and_inflight_root(tmp_path):
    archive, row, payload = _committed_selection_root(tmp_path)
    key = "|".join((row["partition"], row["condition_id"], row["root_id"]))
    with pytest.raises(CheckpointError, match="paused state"):
        validate_resume_state({**payload, "state": "in_progress"}, expected_protocol_sha256=PROTO,
            expected_source_manifest_sha256=SOURCE, archive_paths_by_key={key: archive})
    with pytest.raises(CheckpointError, match="hash differs"):
        validate_resume_state(payload, expected_protocol_sha256="c" * 64,
            expected_source_manifest_sha256=SOURCE, archive_paths_by_key={key: archive})
    with pytest.raises(CheckpointError, match="in-flight"):
        validate_resume_state({**payload, "in_flight_root": {"root_id": row["root_id"]}},
            expected_protocol_sha256=PROTO, expected_source_manifest_sha256=SOURCE,
            archive_paths_by_key={key: archive})
