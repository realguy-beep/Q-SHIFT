"""Windows-safe atomic persistence primitives for Stage 5 v3.4.3.

This module is operational only. It does not generate samples or change Stage 5
scientific parameters. Every intended payload is journaled before replacement;
failed replacements preserve the temporary and journal payload for recovery.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import time
import uuid
from contextlib import AbstractContextManager
from pathlib import Path


RETRYABLE_WINDOWS_ERRORS = {5, 32, 33}
DEFAULT_BACKOFF_SECONDS = (0.02, 0.04, 0.08, 0.16, 0.24)


class ConcurrentStateError(RuntimeError):
    """A target changed since the caller's verified snapshot."""


class LockBusyError(RuntimeError):
    """Another cooperating process owns the target write lock."""


class ReplaceRetryExhausted(OSError):
    """A retryable replacement remained blocked; pending bytes are retained."""


class UncommittedCheckpointError(RuntimeError):
    """A checkpoint has no matching archive commit marker."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    path = Path(path)
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _fsync_directory(path: Path) -> bool:
    # Windows does not expose a portable directory-fsync through Python. The
    # file content is fsynced and the limitation is recorded in the report.
    if os.name == "nt":
        return False
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return True


def _relative_under(path: Path, root: Path) -> str:
    """Return a safe normalized relative path, rejecting escapes and symlinks."""
    root = Path(root).resolve()
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"target symlinks are not supported: {path}")
    resolved = Path(path).resolve(strict=False)
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"path escapes run directory: {path}") from exc


class InterProcessFileLock(AbstractContextManager):
    """Nonblocking kernel lock. OS release on process exit; never steals locks."""
    def __init__(self, path: Path, *, deadline_monotonic: float | None = None,
                 poll_seconds: float = 0.025):
        self.path = Path(path)
        self.deadline = deadline_monotonic
        self.poll = float(poll_seconds)
        self.handle = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0, os.SEEK_END)
        if self.handle.tell() == 0:
            self.handle.write(b"\0")
            self.handle.flush()
            os.fsync(self.handle.fileno())
        while True:
            self.handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (OSError, BlockingIOError):
                if self.deadline is None or time.monotonic() >= self.deadline:
                    self.handle.close()
                    self.handle = None
                    raise LockBusyError(f"write lock busy: {self.path}")
                time.sleep(min(self.poll, max(0.0, self.deadline - time.monotonic())))

    def release(self):
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc, tb):
        self.release()


def _write_new_file(path: Path, data: bytes) -> None:
    """Create-only durable write. Existing content is never replaced."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_directory(path.parent)


def _mark_applied(event_path: Path, txid: str, payload_sha256: str) -> None:
    marker = event_path.with_suffix(".applied.json")
    payload = (json.dumps({"transaction_id": txid, "payload_sha256": payload_sha256},
                          sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if marker.exists():
        saved = json.loads(marker.read_text(encoding="utf-8"))
        if saved != {"transaction_id": txid, "payload_sha256": payload_sha256}:
            raise ConcurrentStateError(f"applied marker conflicts: {marker}")
        return
    _write_new_file(marker, payload)


def _check_expected_target(path: Path, expected_sha256: str | None) -> None:
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ConcurrentStateError(
            f"target changed: {path}; expected={expected_sha256!r}, actual={actual!r}"
        )


def replace_with_retry(src: Path, dst: Path, *, expected_destination_sha256: str | None,
                       deadline_monotonic: float, backoff=DEFAULT_BACKOFF_SECONDS,
                       fault=None) -> int:
    """Replace only the exact expected destination; retry bounded Windows errors.

    The caller must hold the matching InterProcessFileLock. On exhausted retry
    `src` is deliberately retained. The expected target hash is rechecked before
    every attempt so a newer cooperating writer is never silently overwritten.
    """
    src, dst = Path(src), Path(dst)
    attempts = len(backoff) + 1
    for index in range(attempts):
        if time.monotonic() >= deadline_monotonic:
            raise TimeoutError(f"deadline expired before replace: {dst}")
        _check_expected_target(dst, expected_destination_sha256)
        try:
            os.replace(src, dst)
            if fault:
                fault("after_replace")
            _fsync_directory(dst.parent)
            return index + 1
        except OSError as exc:
            winerror = getattr(exc, "winerror", None)
            retryable = (os.name == "nt" and winerror in RETRYABLE_WINDOWS_ERRORS)
            if not retryable:
                raise
            if index >= len(backoff):
                raise ReplaceRetryExhausted(
                    f"replace still blocked after {attempts} attempts; winerror={winerror}; "
                    f"pending bytes retained at {src}"
                ) from exc
            remaining = deadline_monotonic - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"deadline expired during replace retry: {dst}") from exc
            time.sleep(min(float(backoff[index]), remaining))
    raise AssertionError("unreachable")


def atomic_write_bytes(path: Path, payload: bytes, *, run_dir: Path,
                       expected_old_sha256: str | None, deadline_monotonic: float,
                       backoff=DEFAULT_BACKOFF_SECONDS, fault=None) -> dict:
    """Fsync exact bytes to a pending temp, journal its hash, then replace."""
    path, run_dir = Path(path), Path(run_dir).resolve()
    target_rel = _relative_under(path, run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    txn_id = uuid.uuid4().hex
    lock_path = path.with_name(f".{path.name}.v43.lock")
    txn_dir = run_dir / ".stage5-v43-transactions" / "writes"
    event_path = txn_dir / f"{txn_id}.json"
    temp_path = path.with_name(f".qtmp-v43-{txn_id}.tmp")
    payload_sha = sha256_bytes(payload)

    with InterProcessFileLock(lock_path, deadline_monotonic=deadline_monotonic):
        _check_expected_target(path, expected_old_sha256)
        with temp_path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(temp_path.parent)
        if fault:
            fault("after_temp_fsync")
        event = {
            "format": "qshift-stage5-v43-write-intent",
            "transaction_id": txn_id,
            "target_rel": target_rel,
            "temp_rel": _relative_under(temp_path, run_dir),
            "expected_old_sha256": expected_old_sha256,
            "payload_sha256": payload_sha,
        }
        _write_new_file(event_path, (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode())
        if fault:
            fault("after_intent_fsync")
        tries = replace_with_retry(temp_path, path,
            expected_destination_sha256=expected_old_sha256,
            deadline_monotonic=deadline_monotonic, backoff=backoff)
        if fault:
            fault("after_replace_before_applied_marker")
        _mark_applied(event_path, txn_id, payload_sha)
        return {"transaction_id": txn_id, "payload_sha256": payload_sha, "attempts": tries,
                "event_path": str(event_path.relative_to(run_dir))}


def atomic_write_json(path: Path, value, *, run_dir: Path,
                      expected_old_sha256: str | None, deadline_monotonic: float,
                      backoff=DEFAULT_BACKOFF_SECONDS, fault=None) -> dict:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return atomic_write_bytes(path, payload, run_dir=run_dir,
                              expected_old_sha256=expected_old_sha256,
                              deadline_monotonic=deadline_monotonic,
                              backoff=backoff, fault=fault)


def recover_write_intent(event_path: Path, *, run_dir: Path, deadline_monotonic: float,
                         backoff=DEFAULT_BACKOFF_SECONDS) -> dict:
    """Idempotently finish a journaled write or reject any newer/conflicting state."""
    event_path, run_dir = Path(event_path), Path(run_dir).resolve()
    txn_root = run_dir / ".stage5-v43-transactions" / "writes"
    _relative_under(event_path, txn_root)
    event = json.loads(event_path.read_text(encoding="utf-8"))
    if event.get("format") != "qshift-stage5-v43-write-intent":
        raise ValueError(f"unknown transaction format: {event_path}")
    target = run_dir / event["target_rel"]
    temp = run_dir / event["temp_rel"]
    if _relative_under(target, run_dir) != event["target_rel"] or _relative_under(temp, run_dir) != event["temp_rel"]:
        raise ValueError("transaction path is not a normalized in-run relative path")
    lock_path = target.with_name(f".{target.name}.v43.lock")
    with InterProcessFileLock(lock_path, deadline_monotonic=deadline_monotonic):
        actual = sha256_file(target)
        if actual == event["payload_sha256"]:
            _mark_applied(event_path, event["transaction_id"], event["payload_sha256"])
            return {"state": "already_applied", "sha256": actual}
        if actual != event["expected_old_sha256"]:
            raise ConcurrentStateError(
                f"recovery refuses newer/unknown target: expected old={event['expected_old_sha256']!r}, actual={actual!r}"
            )
        if not temp.is_file():
            raise UncommittedCheckpointError("write intent has no durable pending temporary; refusing reconstruction")
        if sha256_file(temp) != event["payload_sha256"]:
            raise ValueError("pending temporary payload does not match journal")
        tries = replace_with_retry(temp, target,
            expected_destination_sha256=event["expected_old_sha256"],
            deadline_monotonic=deadline_monotonic, backoff=backoff)
        _mark_applied(event_path, event["transaction_id"], event["payload_sha256"])
        return {"state": "recovered", "sha256": event["payload_sha256"], "attempts": tries}


def write_committed_npz(path: Path, arrays: dict, *, run_dir: Path,
                        expected_archive_sha256: str | None,
                        expected_marker_sha256: str | None,
                        deadline_monotonic: float, backoff=DEFAULT_BACKOFF_SECONDS,
                        fault=None) -> dict:
    """Write an NPZ and its commit marker through separately journaled writes."""
    import numpy as np
    path, run_dir = Path(path), Path(run_dir).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    payload = buffer.getvalue()
    digest = sha256_bytes(payload)
    archive_tx = atomic_write_bytes(path, payload, run_dir=run_dir,
        expected_old_sha256=expected_archive_sha256,
        deadline_monotonic=deadline_monotonic, backoff=backoff,
        fault=(lambda stage: fault("after_archive_replace_before_sidecar") if stage == "after_replace_before_applied_marker" and fault else fault(stage) if fault else None))
    if fault:
        fault("after_archive_commit_before_sidecar")
    marker_path = Path(str(path) + ".commit.json")
    marker = {"archive": path.name, "committed": True, "sha256": digest}
    marker_payload = (json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    marker_tx = atomic_write_bytes(marker_path, marker_payload, run_dir=run_dir,
        expected_old_sha256=expected_marker_sha256,
        deadline_monotonic=deadline_monotonic, backoff=backoff,
        fault=(lambda stage: fault("after_commit_marker") if stage == "after_replace_before_applied_marker" and fault else fault(stage) if fault else None))
    if sha256_file(path) != digest:
        raise UncommittedCheckpointError(f"archive changed during commit: {path}")
    saved_marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if saved_marker != marker:
        raise UncommittedCheckpointError(f"commit marker failed read-back: {marker_path}")
    return {"archive_sha256": digest, "archive_transaction": archive_tx,
            "marker_transaction": marker_tx}


def verify_committed_npz(path: Path) -> str:
    path = Path(path)
    marker_path = Path(str(path) + ".commit.json")
    if not path.is_file() or not marker_path.is_file():
        raise UncommittedCheckpointError(f"archive or commit marker missing: {path}")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    actual = sha256_file(path)
    if marker != {"archive": path.name, "committed": True, "sha256": actual}:
        raise UncommittedCheckpointError(f"archive/marker mismatch: {path}")
    return actual


def recover_npz_commit(path: Path, *, run_dir: Path, deadline_monotonic: float) -> dict:
    """Repair a committed archive's missing/stale marker only from exact write intents."""
    path, run_dir = Path(path), Path(run_dir).resolve()
    committed_digest = None
    try:
        committed_digest = verify_committed_npz(path)
    except UncommittedCheckpointError:
        pass
    archive_digest = sha256_file(path)
    transactions = run_dir / ".stage5-v43-transactions" / "writes"
    matching = []
    if transactions.exists():
        for event_path in transactions.glob("*.json"):
            if event_path.name.endswith(".applied.json"):
                continue
            event = json.loads(event_path.read_text(encoding="utf-8"))
            if event.get("format") != "qshift-stage5-v43-write-intent":
                continue
            if event.get("target_rel") != _relative_under(path, run_dir):
                continue
            current = sha256_file(path)
            if event.get("payload_sha256") == current or event.get("expected_old_sha256") == current:
                matching.append(event_path)
    # Prefer one uniquely pending transition. This handles a crash after a new
    # intent was fsynced but before replacing an archive that has an older,
    # already-applied transaction. Multiple pending transitions are ambiguous.
    pending = [p for p in matching if not p.with_suffix(".applied.json").exists()]
    if committed_digest is not None and not pending:
        return {"state": "already_committed", "sha256": committed_digest}
    if len(pending) == 1:
        matching = pending
    elif len(pending) > 1:
        matching = pending
    else:
        matching = [p for p in matching
                    if json.loads(p.read_text(encoding="utf-8")).get("payload_sha256") == archive_digest]
    if len(matching) != 1:
        raise UncommittedCheckpointError(f"no unique durable archive transaction for {path}; matches={len(matching)}")
    event_path = matching[0]
    event = json.loads(event_path.read_text(encoding="utf-8"))
    # The archive may be absent because the process died after journaling but
    # before replacement. Replay only this exact hash-verified intent.
    recover_write_intent(event_path, run_dir=run_dir, deadline_monotonic=deadline_monotonic)
    archive_digest = sha256_file(path)
    if archive_digest != event["payload_sha256"]:
        raise UncommittedCheckpointError(f"archive does not match recovered transaction: {path}")
    marker_path = Path(str(path) + ".commit.json")
    current_marker_sha = sha256_file(marker_path)
    marker = {"archive": path.name, "committed": True, "sha256": archive_digest}
    atomic_write_json(marker_path, marker, run_dir=run_dir,
        expected_old_sha256=current_marker_sha, deadline_monotonic=deadline_monotonic)
    return {"state": "marker_reconstructed_from_intent", "sha256": archive_digest}
