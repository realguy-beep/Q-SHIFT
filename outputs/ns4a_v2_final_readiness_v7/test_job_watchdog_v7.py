from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time
import unittest
import ctypes
from unittest.mock import patch

from job_watchdog_v7 import (
    WAIT_OBJECT_0,
    WAIT_TIMEOUT,
    WindowsJobBackend,
    _BasicAccountingInformation,
    _ExtendedLimitInformation,
    _ProcessEntry32W,
    run_watchdog,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(0.0001, seconds)


class FakeBackend:
    """Deterministic Job Object event source; never starts a process."""

    def __init__(self, snapshots=None, *, query_error=False, terminate_drains=True, assign_error=False):
        self.snapshots = list(snapshots or [(0, [], [])])
        self.query_error = query_error
        self.terminate_drains = terminate_drains
        self.assign_error = assign_error
        self.unassigned_terminated = False
        self.terminated = False
        self.closed = False
        self.kill_on_close = False
        self.index = 0

    def create_job(self): return object()
    def enable_kill_on_close(self, job): self.kill_on_close = True
    def spawn_suspended(self, command, cwd, log_path): return type("P", (), {"pid": 101})()
    def assign(self, job, process):
        if self.assign_error:
            raise OSError("injected assignment failure")
    def resume(self, process): pass
    def close_child_log(self, process): pass
    def wait_root(self, process, milliseconds): return WAIT_OBJECT_0
    def root_exit_code(self, process): return 0
    def terminate_unassigned(self, process, code):
        self.unassigned_terminated = True
        return True

    def _current(self):
        if self.terminated and self.terminate_drains:
            return (0, [], [])
        return self.snapshots[min(self.index, len(self.snapshots) - 1)]

    def active_count(self, job):
        if self.query_error:
            raise OSError("injected accounting query failure")
        return self._current()[0]

    def process_ids(self, job):
        if self.query_error:
            raise OSError("injected Job PID-list query failure")
        row = self._current()
        self.index += 1
        return list(row[1])

    def inspect_process(self, pid, job):
        row = self.snapshots[min(max(0, self.index - 1), len(self.snapshots) - 1)]
        return dict(row[2][0])

    def terminate_job(self, job, code): self.terminated = True
    def close_process(self, process): pass
    def close_job(self, job): self.closed = True


def fake_member(pid=202, *, state="live", created=100, path="synthetic.exe", parent=101):
    return {"pid": pid, "state": state, "creation_time_filetime": created,
            "executable_path": path, "parent_pid": parent, "exit_code": None}


@unittest.skipUnless(os.name == "nt", "real Job Object fixtures require Windows")
class V7RealWindowsFixtures(unittest.TestCase):
    def _run(self, script: str, *args: str, grace: float = 0.25):
        return run_watchdog([sys.executable, "-c", script, *args], timeout_seconds=5,
                            grace_seconds=grace, poll_seconds=0.01)

    @staticmethod
    def _pid_done(pid: int, timeout: float = 1.0) -> bool:
        k = __import__("ctypes").WinDLL("kernel32", use_last_error=True)
        from ctypes import wintypes
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject.restype = wintypes.DWORD
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
        if not handle:
            return True
        try:
            return int(k.WaitForSingleObject(handle, int(timeout * 1000))) == WAIT_OBJECT_0
        finally:
            k.CloseHandle(handle)

    def test_01_immediate_root_exit_without_children_drains(self):
        status = self._run("pass")
        self.assertEqual(status["state"], "completed")
        self.assertEqual(status["drain"], "zero_active_and_zero_job_pids")

    def test_02_normal_short_lived_python_process(self):
        status = self._run("import time; time.sleep(0.04)")
        self.assertEqual(status["state"], "completed")
        self.assertEqual(status["root_exit_code"], 0)

    def test_child_stdout_stderr_are_preserved_in_append_only_log(self):
        with tempfile.TemporaryDirectory(prefix="qshift_v7_log_") as temp:
            log = pathlib.Path(temp) / "synthetic.log"
            log.write_text("preserved-prefix\n", encoding="utf-8")
            status = run_watchdog([sys.executable, "-c",
                "import sys; print('fixture-stdout'); print('fixture-stderr',file=sys.stderr)"],
                timeout_seconds=4, log_path=log)
            self.assertEqual(status["state"], "completed")
            content = log.read_text(encoding="utf-8", errors="replace")
            self.assertIn("preserved-prefix", content)
            self.assertIn("fixture-stdout", content)
            self.assertIn("fixture-stderr", content)

    def test_04_parent_waiting_for_brief_child(self):
        script = "import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(0.06)']); p.wait()"
        status = self._run(script)
        self.assertEqual(status["state"], "completed")
        self.assertTrue(any(s["job_process_ids"] for s in status["process_snapshots"]) or
                        status["drain"] == "zero_active_and_zero_job_pids")

    def test_05_persistent_child_is_terminated_and_is_failure(self):
        with tempfile.TemporaryDirectory(prefix="qshift_v7_synth_") as temp:
            pidfile = pathlib.Path(temp) / "child.pid"
            script = "import subprocess,sys,pathlib; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']); pathlib.Path(sys.argv[1]).write_text(str(p.pid))"
            status = self._run(script, str(pidfile), grace=0.12)
            self.assertEqual(status["state"], "persistent_live_descendant_terminated")
            self.assertTrue(status["termination"]["termination_requested"])
            self.assertTrue(status["termination"]["job_drained_after_termination"])
            self.assertTrue(pidfile.exists())
            member_records = [m for snap in status["process_snapshots"] for m in snap["members"]]
            self.assertTrue(any(m.get("creation_time_filetime") for m in member_records))
            self.assertTrue(any(m.get("parent_pid") is not None for m in member_records))
            self.assertTrue(any(isinstance(m.get("executable_path"), str) for m in member_records))
            self.assertTrue(self._pid_done(int(pidfile.read_text()), 1.0))

    def test_06_child_exiting_during_grace_is_natural_drain(self):
        script = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time;time.sleep(0.08)'])"
        status = self._run(script, grace=0.30)
        self.assertEqual(status["state"], "completed")
        self.assertGreaterEqual(len(status["process_snapshots"]), 1)

    def test_11_forced_termination_and_zero_process_cleanup_remains_failure(self):
        with tempfile.TemporaryDirectory(prefix="qshift_v7_synth_") as temp:
            pidfile = pathlib.Path(temp) / "child.pid"
            script = "import subprocess,sys,pathlib; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']); pathlib.Path(sys.argv[1]).write_text(str(p.pid))"
            status = self._run(script, str(pidfile), grace=0.05)
            self.assertEqual(status["state"], "persistent_live_descendant_terminated")
            self.assertTrue(status["termination"]["job_drained_after_termination"])
            self.assertNotEqual(status["state"], "completed")

    def test_12_kill_on_close_cleans_descendant_tree(self):
        backend = WindowsJobBackend()
        job = backend.create_job()
        process = None
        child_pid = None
        try:
            backend.enable_kill_on_close(job)
            with tempfile.TemporaryDirectory(prefix="qshift_v7_jobclose_") as temp:
                pidfile = pathlib.Path(temp) / "child.pid"
                script = "import subprocess,sys,pathlib,time; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']); pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(30)"
                process = backend.spawn_suspended([sys.executable, "-c", script, str(pidfile)], None, None)
                backend.assign(job, process)
                backend.resume(process)
                deadline = time.monotonic() + 3
                while not pidfile.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(pidfile.exists(), "synthetic child did not start")
                child_pid = int(pidfile.read_text())
                backend.close_job(job)
                job = None
                self.assertTrue(self._pid_done(process.pid, 1.0))
                self.assertTrue(self._pid_done(child_pid, 1.0))
        finally:
            if job is not None:
                try: backend.terminate_job(job, 125)
                except Exception: pass
                backend.close_job(job)
            if process is not None:
                backend.close_process(process)


class V7DeterministicStateFixtures(unittest.TestCase):
    def _run_fake(self, api, *, timeout=1.0, grace=0.05, clock=None):
        clock = clock or FakeClock()
        status = run_watchdog(["synthetic-command"], timeout_seconds=timeout,
            grace_seconds=grace, poll_seconds=0.01, api=api, clock=clock,
            sleep=clock.sleep)
        self.assertTrue(api.kill_on_close)
        self.assertTrue(api.closed)
        return status

    def test_03_transient_console_host_teardown_is_polled_not_immediate_orphan(self):
        member = fake_member(303, path=r"C:\Windows\System32\conhost.exe")
        api = FakeBackend([(1, [303], [member]), (1, [303], [member]), (0, [], [])])
        status = self._run_fake(api, grace=0.10)
        self.assertEqual(status["state"], "completed")
        self.assertGreaterEqual(len(status["process_snapshots"]), 3)

    def test_07_inaccessible_metadata_persists_and_fails_closed(self):
        member = {"pid": 404, "state": "inaccessible", "winerror": 5}
        api = FakeBackend([(1, [404], [member])])
        status = self._run_fake(api, grace=0.03)
        self.assertEqual(status["state"], "unclassified_member_terminated")
        self.assertTrue(status["termination"]["termination_requested"])

    def test_08_pid_reuse_or_stale_pid_observation_fails_closed(self):
        api = FakeBackend([
            (1, [505], [fake_member(505, created=100)]),
            (1, [505], [fake_member(505, created=200)]),
        ])
        status = self._run_fake(api, grace=0.02)
        self.assertEqual(status["state"], "unclassified_member_terminated")
        self.assertTrue(any(m.get("state") == "pid_reused" for s in status["process_snapshots"] for m in s["members"]))

    def test_08b_stale_pid_not_in_job_fails_closed_if_persistent(self):
        member = {"pid": 506, "state": "stale_or_reused_pid", "in_job": False}
        status = self._run_fake(FakeBackend([(1, [506], [member])]), grace=0.02)
        self.assertEqual(status["state"], "unclassified_member_terminated")

    def test_09_job_query_failure_fails_closed_and_requests_termination(self):
        api = FakeBackend(query_error=True)
        status = self._run_fake(api)
        self.assertEqual(status["state"], "job_query_failed")
        self.assertIn("injected", status["query_error"])
        self.assertTrue(status["termination"]["termination_requested"])

    def test_assignment_failure_terminates_suspended_root_outside_job(self):
        api = FakeBackend(assign_error=True)
        status = self._run_fake(api)
        self.assertEqual(status["state"], "failed_closed")
        self.assertTrue(api.unassigned_terminated)
        self.assertFalse(api.terminated)
        self.assertTrue(status["unassigned_root_terminated"])

    def test_10_deadline_expiration_during_grace_does_not_extend_deadline(self):
        clock = FakeClock()
        api = FakeBackend([(1, [607], [fake_member(607)])])
        status = self._run_fake(api, timeout=0.05, grace=1.0, clock=clock)
        self.assertEqual(status["state"], "deadline_expired_during_grace")
        self.assertLessEqual(clock.now, 0.0601)
        self.assertTrue(status["termination"]["termination_requested"])

    def test_force_cleanup_never_relabels_success(self):
        api = FakeBackend([(1, [608], [fake_member(608)])])
        status = self._run_fake(api, grace=0.01)
        self.assertEqual(status["state"], "persistent_live_descendant_terminated")
        self.assertTrue(status["termination"]["job_drained_after_termination"])
        self.assertNotEqual(status["state"], "completed")

    def test_unsupported_os_rejected(self):
        with patch("job_watchdog_v7.os.name", "posix"):
            with self.assertRaisesRegex(RuntimeError, "requires Windows"):
                WindowsJobBackend()

    def test_timeout_cannot_exceed_frozen_600_seconds(self):
        with self.assertRaisesRegex(ValueError, "600"):
            run_watchdog(["synthetic-command"], timeout_seconds=600.001, api=FakeBackend())

    def test_win32_job_process_structures_have_expected_layout(self):
        self.assertEqual(ctypes.sizeof(_BasicAccountingInformation), 48)
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            self.assertEqual(ctypes.sizeof(_ExtendedLimitInformation), 144)
            self.assertEqual(ctypes.sizeof(_ProcessEntry32W), 568)
        else:
            self.assertGreaterEqual(ctypes.sizeof(_ExtendedLimitInformation), 108)
            self.assertEqual(ctypes.sizeof(_ProcessEntry32W), 556)


if __name__ == "__main__":
    unittest.main(verbosity=2)
