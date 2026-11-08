"""Fail-closed process ownership and deadline primitives for Stage 5 v3.4.2."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path


CHILD_ROLES = ("worker", "auditor", "finalizer")


class LockBusyError(RuntimeError):
    pass


class OwnershipUncertainError(LockBusyError):
    pass


class UncommittedCheckpointError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> bool:
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
    # Keep temporary basenames short. On Windows, embedding the long destination
    # name plus PID/UUID can exceed MAX_PATH even when the final file fits.
    tmp = path.with_name(f".qtmp-{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if fault: fault("after_temp_fsync_before_replace")
        digest = hashlib.sha256(data).hexdigest()
        os.replace(tmp, path)
        if fault: fault("after_replace_before_dir_fsync")
        _fsync_directory(path.parent)
        if fault: fault("after_replace_and_dir_fsync")
        return digest
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def atomic_json(path: Path, value, fault=None) -> str:
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    return _atomic_bytes(Path(path), payload, fault=fault)


def atomic_npz(path: Path, arrays: dict, fault=None) -> str:
    import numpy as np
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Same short-name rule as JSON writes; Stage 5 workspaces can approach the
    # classic Windows path limit after adding a sidecar suffix.
    tmp = path.with_name(f".qtmp-{uuid.uuid4().hex}.tmp")
    sidecar = path.with_suffix(path.suffix + ".commit.json")
    try:
        with tmp.open("xb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        if fault: fault("after_temp_fsync_before_replace")
        digest = file_sha256(tmp)
        os.replace(tmp, path)
        if fault: fault("after_replace_before_commit_marker")
        _fsync_directory(path.parent)
        atomic_json(sidecar, {"archive": path.name, "sha256": digest, "committed": True}, fault=fault)
        if fault: fault("after_commit_marker")
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
    marker = json.loads(sidecar.read_text(encoding="utf-8"))
    actual = file_sha256(path)
    if marker.get("committed") is not True or marker.get("archive") != path.name or marker.get("sha256") != actual:
        raise UncommittedCheckpointError(f"checkpoint hash/commit marker mismatch: {path.name}")
    return actual


class RunDirectoryLock:
    """Nonblocking OS lock; lock metadata never overrides kernel state."""
    def __init__(self, run_dir: Path, *, kind: str = "run"):
        if kind not in {"run", "launcher", "worker", "auditor", "finalizer", "intent"}:
            raise ValueError(f"invalid lock kind: {kind}")
        self.run_dir = Path(run_dir)
        self.kind = kind
        self.lock_path = self.run_dir / f".stage5-{kind}.lock"
        self.owner_path = self.run_dir / f".stage5-{kind}-owner.json"
        self._file = None
        self.token = uuid.uuid4().hex

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
                owner = json.loads(self.owner_path.read_text(encoding="utf-8"))
            except Exception as exc:
                self.release()
                raise OwnershipUncertainError("corrupt owner metadata; refusing takeover") from exc
            if owner.get("state") == "active":
                try:
                    proc = _process_identity(int(owner.get("pid", -1)))
                except OwnershipUncertainError:
                    self.release()
                    raise
                if proc is not None and _same_process(proc, owner.get("create_time")):
                    self.release()
                    raise LockBusyError(f"owner metadata still names a live {self.kind} process")
        atomic_json(self.owner_path, {"state": "active", "pid": os.getpid(),
                                     "create_time": _current_create_time(), "token": self.token,
                                     "acquired_monotonic": time.monotonic()})
        return self

    def release(self):
        if self._file is None:
            return
        try:
            if self.owner_path.exists():
                try:
                    owner = json.loads(self.owner_path.read_text(encoding="utf-8"))
                    if owner.get("token") == self.token:
                        owner.update({"state": "released", "released_monotonic": time.monotonic()})
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


class WindowsChildJob:
    """Kill-on-supervisor-exit job; children start suspended until job-bound."""
    CREATE_SUSPENDED = 0x00000004
    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    def __init__(self):
        self.handle=None
        if os.name != 'nt': return
        import ctypes
        from ctypes import wintypes
        self.ctypes=ctypes; self.wintypes=wintypes
        kernel32=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel32=kernel32
        kernel32.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype=wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel32.SetInformationJobObject.restype=wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype=wintypes.BOOL
        self.handle=kernel32.CreateJobObjectW(None,None)
        if not self.handle: raise ctypes.WinError(ctypes.get_last_error())
        class IO_COUNTERS(ctypes.Structure):
            _fields_=[('ReadOperationCount',ctypes.c_ulonglong),('WriteOperationCount',ctypes.c_ulonglong),
                      ('OtherOperationCount',ctypes.c_ulonglong),('ReadTransferCount',ctypes.c_ulonglong),
                      ('WriteTransferCount',ctypes.c_ulonglong),('OtherTransferCount',ctypes.c_ulonglong)]
        class BASIC_LIMIT(ctypes.Structure):
            _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),
              ('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),
              ('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),
              ('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
        class EXTENDED_LIMIT(ctypes.Structure):
            _fields_=[('BasicLimitInformation',BASIC_LIMIT),('IoInfo',IO_COUNTERS),
              ('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),
              ('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
        info=EXTENDED_LIMIT()
        info.BasicLimitInformation.LimitFlags=self.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(self.handle,self.JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                                                ctypes.byref(info),ctypes.sizeof(info)):
            err=ctypes.get_last_error(); self.close(); raise ctypes.WinError(err)

    def create_suspended(self, command, *, cwd, env, stdout, stderr, text=True):
        import subprocess
        if os.name!='nt':
            return subprocess.Popen(command,cwd=cwd,env=env,stdout=stdout,stderr=stderr,text=text)
        return subprocess.Popen(command,cwd=cwd,env=env,stdout=stdout,stderr=stderr,text=text,
                                creationflags=self.CREATE_SUSPENDED)

    def assign(self, proc):
        if os.name!='nt': return
        if not self.kernel32.AssignProcessToJobObject(self.handle,proc._handle):
            err=self.ctypes.get_last_error()
            try: proc.kill(); proc.wait(timeout=2)
            except Exception: pass
            raise self.ctypes.WinError(err)

    def resume(self, proc):
        if os.name!='nt': return
        import ctypes
        from ctypes import wintypes
        class THREADENTRY32(ctypes.Structure):
            _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),
              ('th32ThreadID',wintypes.DWORD),('th32OwnerProcessID',wintypes.DWORD),
              ('tpBasePri',wintypes.LONG),('tpDeltaPri',wintypes.LONG),('dwFlags',wintypes.DWORD)]
        k=self.kernel32
        k.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
        k.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
        k.Thread32First.argtypes=[wintypes.HANDLE,ctypes.POINTER(THREADENTRY32)]; k.Thread32First.restype=wintypes.BOOL
        k.Thread32Next.argtypes=[wintypes.HANDLE,ctypes.POINTER(THREADENTRY32)]; k.Thread32Next.restype=wintypes.BOOL
        k.OpenThread.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; k.OpenThread.restype=wintypes.HANDLE
        k.ResumeThread.argtypes=[wintypes.HANDLE]; k.ResumeThread.restype=wintypes.DWORD
        k.CloseHandle.argtypes=[wintypes.HANDLE]; k.CloseHandle.restype=wintypes.BOOL
        snapshot=k.CreateToolhelp32Snapshot(0x00000004,0)
        invalid=ctypes.c_void_p(-1).value
        if not snapshot or snapshot==invalid: raise ctypes.WinError(ctypes.get_last_error())
        resumed=False
        try:
            entry=THREADENTRY32(); entry.dwSize=ctypes.sizeof(entry)
            ok=k.Thread32First(snapshot,ctypes.byref(entry))
            while ok:
                if entry.th32OwnerProcessID==proc.pid:
                    thread=k.OpenThread(0x0002,False,entry.th32ThreadID)
                    if thread:
                        try:
                            prior=k.ResumeThread(thread)
                            if prior==0xFFFFFFFF: raise ctypes.WinError(ctypes.get_last_error())
                            resumed=True; break
                        finally: k.CloseHandle(thread)
                ok=k.Thread32Next(snapshot,ctypes.byref(entry))
        finally: k.CloseHandle(snapshot)
        if not resumed: raise RuntimeError('could not resume the suspended Stage 5 child process')

    def spawn(self, command, *, cwd, env, stdout, stderr, text=True):
        proc=self.create_suspended(command,cwd=cwd,env=env,stdout=stdout,stderr=stderr,text=text)
        try:
            self.assign(proc)
            return proc
        except BaseException:
            try: proc.kill(); proc.wait(timeout=2)
            except Exception: pass
            raise

    def close(self):
        if self.handle:
            self.kernel32.CloseHandle(self.handle)
            self.handle=None

    def __enter__(self): return self
    def __exit__(self,exc_type,exc,tb): self.close()


def _current_create_time() -> float:
    import psutil
    return float(psutil.Process(os.getpid()).create_time())


def _process_identity(pid: int):
    if pid <= 0:
        return None
    import psutil
    try:
        proc = psutil.Process(pid)
        if not proc.is_running():
            return None
        return {"pid": pid, "create_time": float(proc.create_time()), "cmdline": proc.cmdline()}
    except psutil.NoSuchProcess:
        return None
    except psutil.AccessDenied as exc:
        raise OwnershipUncertainError(f"cannot inspect process {pid}; refusing takeover") from exc


def _same_process(proc, recorded_create_time) -> bool:
    if proc is None:
        return False
    if recorded_create_time is None:
        return True
    return abs(float(proc["create_time"]) - float(recorded_create_time)) < 0.01


def _find_token_process(intent: dict):
    """Find an owned child even if its PID update was interrupted after spawn."""
    import psutil
    token = str(intent["token"])
    recorded_pid = intent.get("child_pid")
    recorded_ctime = intent.get("child_create_time")
    if recorded_pid is not None:
        proc = _process_identity(int(recorded_pid))
        if not _same_process(proc, recorded_ctime) or proc is None: return None
        args = proc.get("cmdline") or []
        if f"--qshift-owner-token={token}" not in args:
            raise OwnershipUncertainError("recorded PID is alive but its ownership token is unverifiable")
        return proc

    # Windows preserves a process's original parent PID inconsistently across
    # forced parent termination. Search all processes using this interpreter;
    # the random token is unique to one pending launch intent.
    expected_exe = os.path.normcase(os.path.abspath(sys.executable))
    for proc in psutil.process_iter(attrs=["pid", "exe", "cmdline", "create_time"]):
        try:
            info = proc.info
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as exc:
            # If this is another Python process but its arguments are not
            # inspectable, fail closed: it could be the unrecorded child.
            try:
                exe = os.path.normcase(os.path.abspath(proc.exe()))
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied as inner:
                raise OwnershipUncertainError("cannot inspect a possible Python child during recovery") from inner
            if exe == expected_exe:
                raise OwnershipUncertainError("cannot inspect a same-interpreter process during recovery") from exc
            continue
        exe = info.get("exe")
        if not exe or os.path.normcase(os.path.abspath(exe)) != expected_exe:
            continue
        cmdline = info.get("cmdline")
        if cmdline is None:
            raise OwnershipUncertainError("cannot inspect a same-interpreter process during recovery")
        if f"--qshift-owner-token={token}" in cmdline:
            return {"pid":int(info['pid']),'create_time':float(info['create_time']),'cmdline':cmdline}
    return None


def _token_process_alive(intent: dict) -> bool:
    return _find_token_process(intent) is not None


def _locked_intent(run_dir: Path):
    return RunDirectoryLock(run_dir, kind="intent")


def _read_intent(run_dir: Path):
    path = Path(run_dir) / ".stage5-child-intent.json"
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise OwnershipUncertainError("child intent metadata is corrupt; refusing takeover") from exc
    if not isinstance(record, dict) or not record.get("token") or record.get("role") not in CHILD_ROLES:
        raise OwnershipUncertainError("child intent metadata is incomplete; refusing takeover")
    return record


def assert_child_ownership_clear(run_dir: Path) -> dict:
    """Reject live or ambiguous child ownership before a launcher can proceed."""
    run_dir = Path(run_dir)
    for role in CHILD_ROLES:
        probe = RunDirectoryLock(run_dir, kind=role).acquire()
        probe.release()
    with _locked_intent(run_dir):
        intent = _read_intent(run_dir)
        if intent is None:
            return {"state": "clear"}
        live=_find_token_process(intent)
        if live is not None:
            # Before the PID claim, v3.4.2 only permits an unassigned, suspended
            # child. It cannot touch artifacts, so terminate that orphan safely.
            # Any other live child remains protected until its own deadline.
            expired=time.monotonic()>=float(intent.get('deadline_monotonic',float('inf')))
            pending_unassigned=(intent.get('state')=='launching' and intent.get('child_pid') is None)
            if pending_unassigned or expired:
                import psutil
                try:
                    proc=psutil.Process(int(live['pid']))
                    if abs(proc.create_time()-float(live['create_time']))>=0.01:
                        raise OwnershipUncertainError('candidate PID was reused during child cleanup')
                    proc.terminate(); proc.wait(timeout=3)
                except psutil.NoSuchProcess:
                    pass
                except psutil.TimeoutExpired as exc:
                    raise OwnershipUncertainError('orphaned suspended/expired child did not terminate') from exc
            else:
                raise LockBusyError(f"prior {intent['role']} process remains alive and owns this run")
        intent.update({"state": "stale_released", "resolved_monotonic": time.monotonic()})
        atomic_json(run_dir / ".stage5-child-intent.json", intent)
        return {"state": "stale_intent_cleared", "role": intent["role"]}


def publish_child_intent(run_dir: Path, role: str, deadline_monotonic: float) -> str:
    if role not in CHILD_ROLES:
        raise ValueError(f"invalid child role {role}")
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    assert_child_ownership_clear(run_dir)
    token = uuid.uuid4().hex
    record = {"schema": 1, "state": "launching", "role": role, "token": token,
              "supervisor_pid": os.getpid(), "supervisor_create_time": _current_create_time(),
              "created_monotonic": time.monotonic(), "deadline_monotonic": float(deadline_monotonic),
              "child_pid": None, "child_create_time": None}
    with _locked_intent(run_dir):
        existing = _read_intent(run_dir)
        if existing is not None and _token_process_alive(existing):
            raise LockBusyError(f"prior {existing['role']} process remains alive")
        atomic_json(run_dir / ".stage5-child-intent.json", record)
    return token


def record_child_spawn(run_dir: Path, token: str, pid: int) -> None:
    proc = _process_identity(pid)
    with _locked_intent(Path(run_dir)):
        record = _read_intent(Path(run_dir))
        if record is None or record.get("token") != token:
            raise OwnershipUncertainError("launch intent changed before child PID was recorded")
        if proc is None:
            # A very short-lived child may have claimed and released ownership
            # before Popen returns to the caller. Its own claim is authoritative.
            if record.get("child_pid") != int(pid) or record.get("state") not in {"acquired", "releasing"}:
                raise OwnershipUncertainError("child exited before ownership acquisition could be confirmed")
            return
        args = proc.get("cmdline") or []
        if f"--qshift-owner-token={token}" not in args:
            raise OwnershipUncertainError("spawned child command line does not contain its owner token")
        if record.get("state") not in {"acquired", "releasing"}:
            record["state"] = "spawned"
        record.update({"child_pid": int(pid), "child_create_time": float(proc["create_time"])})
        atomic_json(Path(run_dir) / ".stage5-child-intent.json", record)


class ChildOwnership:
    """A child must hold its role lock and claim the durable launch intent before work."""
    def __init__(self, run_dir: Path, role: str, token: str, deadline_monotonic: float):
        if role not in CHILD_ROLES:
            raise ValueError(f"invalid child role {role}")
        self.run_dir = Path(run_dir)
        self.role = role
        self.token = token
        self.deadline = float(deadline_monotonic)
        self.lock = RunDirectoryLock(self.run_dir, kind=role)

    def __enter__(self):
        self.lock.acquire()
        try:
            with _locked_intent(self.run_dir):
                record = _read_intent(self.run_dir)
                if record is None or record.get("token") != self.token or record.get("role") != self.role:
                    raise OwnershipUncertainError("child has no matching durable launch intent")
                if time.monotonic() >= self.deadline or self.deadline != float(record["deadline_monotonic"]):
                    raise TimeoutError("child launch deadline expired or does not match intent")
                record.update({"state": "acquired", "child_pid": os.getpid(),
                               "child_create_time": _current_create_time(),
                               "acquired_monotonic": time.monotonic()})
                atomic_json(self.run_dir / ".stage5-child-intent.json", record)
            return self
        except BaseException:
            self.lock.release()
            raise

    def __exit__(self, exc_type, exc, tb):
        try:
            with _locked_intent(self.run_dir):
                record = _read_intent(self.run_dir)
                if record is not None and record.get("token") == self.token:
                    record.update({"state": "releasing", "released_monotonic": time.monotonic()})
                    atomic_json(self.run_dir / ".stage5-child-intent.json", record)
        finally:
            self.lock.release()


def start_deadline_watchdog(deadline_monotonic: float, completed: threading.Event, role: str):
    """Hard-stop an orphaned child at the shared monotonic deadline."""
    def watch():
        while not completed.is_set():
            remaining = float(deadline_monotonic) - time.monotonic()
            if remaining <= 0:
                # Never report success from this watchdog. Parent will persist a
                # deadline status when alive; after parent loss the in-flight
                # record intentionally remains recoverable and not completed.
                os._exit(124)
            completed.wait(min(remaining, 0.1))
    thread = threading.Thread(target=watch, name=f"stage5-{role}-deadline", daemon=True)
    thread.start()
    return thread


class Deadline:
    def __init__(self, seconds: float | None = None, *, absolute_monotonic: float | None = None):
        if absolute_monotonic is None and seconds is None:
            raise ValueError("provide seconds or an absolute monotonic deadline")
        self.deadline = float(absolute_monotonic if absolute_monotonic is not None
                              else time.monotonic() + float(seconds))

    def remaining(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    def check(self, phase: str):
        if self.remaining() <= 0:
            raise TimeoutError(f"Stage 5 wall-clock deadline expired during {phase}")

