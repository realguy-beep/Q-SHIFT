"""Run-directory verification with independent saved-array recomputation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from qshift_ns4a_v2_deterministic.audit_saved_arrays import audit_saved_arrays
from qshift_ns4a_v2_deterministic.protocol import CONDITIONS, make_root_id

from .archive_store import archive_path, read_and_verify_commit


class RunAuditError(RuntimeError):
    """Persisted run evidence fails independent integrity/completeness checks."""


def audit_run_directory(run_directory: str | Path, checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    """Re-open every root archive; recompute outcomes without runner aggregates."""
    root = Path(run_directory)
    root_rows = checkpoint.get("committed_roots")
    if not isinstance(root_rows, list):
        raise RunAuditError("checkpoint has no committed-root inventory.")
    expected = {
        (partition, condition, index)
        for partition, n_roots in (("selection", 8), ("evaluation", 10))
        for condition in CONDITIONS
        for index in range(n_roots)
    }
    by_key = {}
    for row in root_rows:
        key = (row.get("partition"), row.get("condition_id"), row.get("root_id"))
        if key in by_key:
            raise RunAuditError(f"duplicate checkpoint root record: {key}.")
        by_key[key] = row
    if set((part, cond, int(rootid[-2:])) for part, cond, rootid in by_key) != expected:
        raise RunAuditError("checkpoint root inventory is not the complete 108-root allocation.")

    ordered_paths: dict[str, list[Path]] = {"selection": [], "evaluation": []}
    for partition, n_roots in (("selection", 8), ("evaluation", 10)):
        for condition in CONDITIONS:
            for index in range(n_roots):
                root_id = make_root_id(partition, condition, index)
                path = archive_path(root, partition, condition, root_id)
                marker = read_and_verify_commit(path)
                row = by_key[(partition, condition, root_id)]
                for field in ("archive_sha256", "sample_ids_sha256", "commit_marker_sha256", "root_seed_ref", "shots"):
                    if marker.get(field) != row.get(field):
                        raise RunAuditError(f"checkpoint/commit-marker mismatch for {root_id} field {field}.")
                ordered_paths[partition].append(path)

    roots_dir = root / "roots"
    expected_archives = {p.resolve() for values in ordered_paths.values() for p in values}
    actual_archives = {p.resolve() for p in roots_dir.glob("*.npz")}
    expected_markers = {p.with_suffix(".commit.json").resolve() for p in expected_archives}
    actual_markers = {p.resolve() for p in roots_dir.glob("*.commit.json")}
    partials = list(roots_dir.glob("*.partial-*"))
    if actual_archives != expected_archives or actual_markers != expected_markers or partials:
        raise RunAuditError("archive/commit-marker directory contains missing, extra, or partial artifacts.")

    # This auditor has independent schema and aggregation code; it imports no
    # runner, selection scorer, statistics implementation, or checkpoint code.
    selection = audit_saved_arrays(ordered_paths["selection"], partition="selection")
    evaluation = audit_saved_arrays(ordered_paths["evaluation"], partition="evaluation")
    if checkpoint.get("selection_frozen") is not True:
        raise RunAuditError("selection is not marked frozen in checkpoint.")
    selection_path = root / "selection_winner.json"
    if not selection_path.is_file():
        raise RunAuditError("immutable selection winner file is missing.")
    winner_hash = hashlib.sha256(selection_path.read_bytes()).hexdigest()
    if winner_hash != checkpoint.get("selection_freeze_sha256"):
        raise RunAuditError("selection freeze hash differs from checkpoint.")
    winner = json.loads(selection_path.read_text(encoding="utf-8"))
    if winner.get("selected_candidate") != selection.get("selection", {}).get("selected_candidate"):
        raise RunAuditError("saved selected candidate differs from independent selection recomputation.")
    if winner.get("selected_candidate") != checkpoint.get("selected_candidate"):
        raise RunAuditError("saved winner, checkpoint, and independent score disagree.")
    return {
        "audit": "PASS",
        "scope": "synthetic fixture" if all(
            str(by_key[(p, c, make_root_id(p, c, r))]["root_seed_ref"]).startswith("fixture-only:")
            for p, n in (("selection", 8), ("evaluation", 10))
            for c in CONDITIONS for r in range(n)
        ) else "production evidence",
        "verified_roots": 108,
        "selection_shots": selection["unique_shots"],
        "evaluation_shots": evaluation["unique_shots"],
        "total_shots": selection["unique_shots"] + evaluation["unique_shots"],
        "selected_candidate": winner["selected_candidate"],
        "selection_archive_audit": selection,
        "evaluation_archive_audit": evaluation,
        "selection_freeze_sha256": winner_hash,
        "archive_files": [str(p.name) for part in ("selection", "evaluation") for p in ordered_paths[part]],
    }
