"""Transactional finalization helper for future Q-SHIFT runs.

Historical runners and verifiers are deliberately untouched. A verifier passed
to this helper must check scientific artifacts without requiring a terminal
"completed" status (it is called while the status is "finalizing").
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


class FinalizationError(RuntimeError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise FinalizationError(f"Cannot read JSON {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise FinalizationError(f"Expected a JSON object in {path.name}")
    return value


def _resolve_evidence(root: Path, paths: Iterable[str | Path]) -> list[tuple[str, Path]]:
    root = root.resolve()
    pairs: dict[str, Path] = {}
    for item in paths:
        raw = Path(item)
        if raw.is_absolute():
            path = raw.resolve()
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError as exc:
                raise FinalizationError(f"Evidence escapes run directory: {item}") from exc
        else:
            rel = raw.as_posix()
            path = (root / raw).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise FinalizationError(f"Evidence escapes run directory: {item}") from exc
        if rel in ("", ".") or rel.startswith("../"):
            raise FinalizationError(f"Invalid evidence path: {item}")
        if not path.is_file():
            raise FinalizationError(f"Required evidence is missing: {rel}")
        pairs[rel] = path
    if not pairs:
        raise FinalizationError("Refusing to finalize without evidence files")
    return sorted(pairs.items())


def _snapshot(evidence: list[tuple[str, Path]]) -> dict[str, dict[str, Any]]:
    result = {}
    for rel, path in evidence:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        result[rel] = {"sha256": h.hexdigest(), "bytes": path.stat().st_size}
    return result


def _manifest_hashes(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    files = manifest.get("files")
    if not isinstance(files, list):
        raise FinalizationError("Evidence manifest has no files list")
    result: dict[str, dict[str, Any]] = {}
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise FinalizationError("Malformed evidence manifest file entry")
        rel = entry["path"]
        if rel in result:
            raise FinalizationError(f"Duplicate manifest path: {rel}")
        result[rel] = {"sha256": entry.get("sha256"), "bytes": entry.get("bytes")}
    return result


def _check_snapshot(root: Path, expected: dict[str, dict[str, Any]]) -> None:
    current = _snapshot(_resolve_evidence(root, expected.keys()))
    if current != expected:
        bad = sorted(k for k in set(current) | set(expected) if current.get(k) != expected.get(k))
        raise FinalizationError("Evidence changed since finalization began: " + ", ".join(bad[:10]))


def _verify_committed_manifest(root: Path, manifest_path: Path,
                               expected_paths: list[tuple[str, Path]]) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    actual = _manifest_hashes(manifest)
    expected_names = {rel for rel, _ in expected_paths}
    if set(actual) != expected_names:
        raise FinalizationError("Committed manifest inventory differs from expected evidence inventory")
    _check_snapshot(root, actual)
    return manifest


def finalize_run(
    run_dir: str | Path,
    evidence_paths: Iterable[str | Path],
    verifier: Callable[[Path], dict[str, Any] | bool | None],
    *,
    progress_name: str = "PROGRESS.json",
    manifest_name: str = "EVIDENCE_MANIFEST.json",
) -> dict[str, Any]:
    """Verify evidence, atomically commit its manifest, then mark completed.

    Re-entry from `finalizing` uses the first-pass SHA-256 snapshot stored in
    progress.json. A missing snapshot, changed artifact, malformed manifest, or
    failed verifier prevents success. Completed runs are idempotently checked.
    """
    root = Path(run_dir).resolve()
    progress_path = root / progress_name
    manifest_path = root / manifest_name
    if not root.is_dir() or not progress_path.is_file():
        raise FinalizationError("Run directory or progress file is missing")
    expected = _resolve_evidence(root, evidence_paths)
    state = _read_json(progress_path)

    if state.get("status") == "completed":
        manifest = _verify_committed_manifest(root, manifest_path, expected)
        verdict = verifier(root)
        if verdict is False:
            raise FinalizationError("Scientific verifier rejected completed evidence")
        return {"status": "completed", "idempotent": True, "manifest": manifest}

    if state.get("status") == "finalizing":
        frozen_snapshot = state.get("finalization_snapshot")
        if not isinstance(frozen_snapshot, dict):
            message = "Interrupted finalization lacks its evidence snapshot; cannot safely resume"
            state.update({"status": "failed", "finalization_error": message,
                          "finalization_failed_utc": _utc()})
            _atomic_json(progress_path, state)
            raise FinalizationError(message)
        try:
            _check_snapshot(root, frozen_snapshot)
        except FinalizationError as exc:
            state.update({"status": "failed", "finalization_error": str(exc),
                          "finalization_failed_utc": _utc()})
            _atomic_json(progress_path, state)
            raise
    elif state.get("status") in {"sampling", "validating", "paused"}:
        frozen_snapshot = _snapshot(expected)
        state.update({"status": "finalizing", "finalization_started_utc": _utc(),
                      "finalization_attempt": int(state.get("finalization_attempt", 0)) + 1,
                      "finalization_snapshot": frozen_snapshot,
                      "finalization_error": None})
        _atomic_json(progress_path, state)
    else:
        raise FinalizationError(f"Cannot finalize from state {state.get('status')!r}")

    try:
        verdict = verifier(root)
        if verdict is False:
            raise FinalizationError("Scientific verifier returned false")
        _check_snapshot(root, frozen_snapshot)
        if manifest_path.exists():
            # A prior interrupted commit is reusable only if it exactly matches
            # the frozen snapshot. Never silently overwrite a suspect manifest.
            existing = _verify_committed_manifest(root, manifest_path, expected)
            if _manifest_hashes(existing) != frozen_snapshot:
                raise FinalizationError("Existing evidence manifest conflicts with frozen snapshot")
            manifest = existing
        else:
            manifest = {
                "schema_version": 1,
                "status": "integrity_verified",
                "created_utc": _utc(),
                "run_id": state.get("run_id"),
                "files": [{"path": rel, **frozen_snapshot[rel]} for rel, _ in expected],
                "verifier": verdict if isinstance(verdict, dict) else {"passed": True},
            }
            _atomic_json(manifest_path, manifest)
        # Read back and verify after the atomic replace before terminal commit.
        _verify_committed_manifest(root, manifest_path, expected)
        manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        state = _read_json(progress_path)
        state.update({"status": "completed", "completed_utc": _utc(),
                      "evidence_manifest": manifest_name,
                      "evidence_manifest_sha256": manifest_digest,
                      "finalization_error": None})
        _atomic_json(progress_path, state)
        return {"status": "completed", "idempotent": False,
                "manifest_sha256": manifest_digest, "verifier": verdict}
    except Exception as exc:
        # Do not convert hard interruption signals (KeyboardInterrupt/SystemExit)
        # into a successful or failed commit; `finalizing` remains recoverable.
        state = _read_json(progress_path)
        state.update({"status": "failed", "finalization_error": f"{type(exc).__name__}: {exc}",
                      "finalization_failed_utc": _utc()})
        _atomic_json(progress_path, state)
        if isinstance(exc, FinalizationError):
            raise
        raise FinalizationError(f"Finalization verification failed: {exc}") from exc
