"""Execution-only durability, locking, and deadline helpers for Stage 5 v3."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import uuid
from pathlib import Path


class LockBusyError(RuntimeError):
    pass


class UncommittedCheckpointError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _fsync_directory(path: Path) -> bool:
    """Return False when the platform does not expose directory fsync."""
    if os.name == "nt":
        return False
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return True


def _atomic_bytes(path: Path, data: bytes, fault=None) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if fault:
            fault("after_temp_fsync_before_replace")
        digest = hashlib.sha256(data).hexdigest()
        os.replace(tmp, path)
        if fault:
            fault("after_replace_before_dir_fsync")
        _fsync_directory(path.parent)
        if fault:
            fault("after_replace_and_dir_fsync")
        return digest
    finally:
        # A killed process may leave a temp file for forensic inspection.
        # Normal error paths remove only their own incomplete temp.
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def atomic_json(path: Path, value, fault=None) -> str:
    data = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    return _atomic_bytes(Path(path), data, fault=fault)


def atomic_npz(path: Path, arrays: dict, fault=None) -> str:
    import numpy as np

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    sidecar = path.with_suffix(path.suffix + ".commit.json")
    try:
        with tmp.open("xb") as f:
            np.savez_compressed(f, **arrays)
            f.flush()
            os.fsync(f.fileno())
        if fault:
            fault("after_temp_fsync_before_replace")
        digest = file_sha256(tmp)
        os.replace(tmp, path)
        if fault:
            fault("after_replace_before_commit_marker")
        _fsync_directory(path.parent)
        atomic_json(sidecar, {"archive": path.name, "sha256": digest, "committed": True}, fault=fault)
        if fault:
            fault("after_commit_marker")
        return digest
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def verify_committed_npz(path: Path) -> str:
    path = Path(path)
    sidecar = path.with_suffix(path.suffix + ".commit.json")
    if not path.is_file() or not sidecar.is_file():
        raise UncommittedCheckpointError(f"checkpoint lacks durable commit marker: {path.name}")
    try:
        marker = json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception as exc:
        raise UncommittedCheckpointError(f"invalid checkpoint commit marker: {path.name}") from exc
    actual = file_sha256(path)
    if marker.get("committed") is not True or marker.get("archive") != path.name or marker.get("sha256") != actual:
        raise UncommittedCheckpointError(f"checkpoint hash/commit marker mismatch: {path.name}")
    return actual


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        import psutil
        return bool(psutil.pid_exists(pid))
    except Exception:
        pass
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class RunDirectoryLock:
    """OS-backed exclusive lock; metadata never overrides kernel lock state."""

    def __init__(self, run_dir: Path, *, kind: str = "run"):
        self.run_dir = Path(run_dir)
        if kind not in {"run", "launcher", "worker"}:
            raise ValueError(f"invalid lock kind: {kind}")
        self.kind = kind
        self.lock_path = self.run_dir / f".stage5-{kind}.lock"
        self.owner_path = self.run_dir / f".stage5-{kind}-owner.json"
        self._file = None
        self.token = uuid.uuid4().hex
        self.previous_owner = None
        self.directory_fsync_supported = os.name != "nt"

    def acquire(self):
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.lock_path.open("a+b")
        self._file.seek(0, os.SEEK_END)
        if self._file.tell() == 0:
            self._file.write(b"\0")
            self._file.flush()
        self._file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self._file.close()
            self._file = None
            raise LockBusyError(f"another process owns {self.lock_path}") from exc
        if self.owner_path.exists():
            try:
                self.previous_owner = json.loads(self.owner_path.read_text(encoding="utf-8"))
            except Exception:
                self.release()
                raise LockBusyError("previous lock-owner metadata is corrupt; refusing to replace it")
            if self.previous_owner.get("state") == "active" and _pid_alive(int(self.previous_owner.get("pid", -1))):
                self.release()
                raise LockBusyError("prior owner metadata names a live process; refusing lock takeover")
        atomic_json(self.owner_path, {
            "state": "active", "pid": os.getpid(), "token": self.token,
            "acquired_unix": time.time(), "previous_owner": self.previous_owner,
        })
        return self

    def release(self):
        if self._file is None:
            return
        try:
            if self.owner_path.exists():
                try:
                    owner = json.loads(self.owner_path.read_text(encoding="utf-8"))
                    if owner.get("token") == self.token:
                        owner.update({"state": "released", "released_unix": time.time()})
                        atomic_json(self.owner_path, owner)
                except Exception:
                    pass
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc, tb):
        self.release()


class Deadline:
    def __init__(self, seconds: float, started: float | None = None):
        self.started = time.monotonic() if started is None else started
        self.deadline = self.started + float(seconds)

    def remaining(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    def check(self, phase: str):
        if self.remaining() <= 0:
            raise TimeoutError(f"Stage 5 wall-clock deadline expired during {phase}")

