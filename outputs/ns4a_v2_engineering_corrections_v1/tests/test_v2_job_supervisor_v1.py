from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time
import unittest
import ctypes
import hashlib
import json
import ast
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v2_job_supervisor_v1 import (
    WAIT_OBJECT_0,
    WAIT_TIMEOUT,
    WindowsJobBackend,
    _BasicAccountingInformation,
    _ExtendedLimitInformation,
    _ProcessEntry32W,
    run_supervisor,
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
class V2SupervisorRealWindowsFixtures(unittest.TestCase):
    def _run(self, script: str, *args: str, grace: float = 0.25):
        return run_supervisor([sys.executable, "-c", script, *args], timeout_seconds=5,
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
            status = run_supervisor([sys.executable, "-c",
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


class V2SupervisorDeterministicFixtures(unittest.TestCase):
    def _run_fake(self, api, *, timeout=1.0, grace=0.05, clock=None):
        clock = clock or FakeClock()
        status = run_supervisor(["synthetic-command"], timeout_seconds=timeout,
            grace_seconds=grace, poll_seconds=0.01, api=api, clock=clock,
            sleep=clock.sleep)
        self.assertTrue(api.kill_on_close)
        self.assertTrue(api.closed)
        return status

    @staticmethod
    def _run_real(script: str, *args: str, timeout: float = 5.0):
        return run_supervisor(
            [sys.executable, "-c", script, *args],
            timeout_seconds=timeout,
            grace_seconds=0.05,
            poll_seconds=0.01,
        )

    @staticmethod
    def _pid_done(pid: int, timeout: float = 1.0) -> bool:
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        from ctypes import wintypes
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject.restype = wintypes.DWORD
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k.OpenProcess(0x00100000, False, pid)
        if not handle:
            return True
        try:
            return int(k.WaitForSingleObject(handle, int(timeout * 1000))) == WAIT_OBJECT_0
        finally:
            k.CloseHandle(handle)

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
        with patch("v2_job_supervisor_v1.os.name", "posix"):
            with self.assertRaisesRegex(RuntimeError, "requires Windows"):
                WindowsJobBackend()

    def test_timeout_cannot_exceed_v2_1800_seconds(self):
        with self.assertRaisesRegex(ValueError, "1800"):
            run_supervisor(["synthetic-command"], timeout_seconds=1800.001, api=FakeBackend())

    def test_v2_full_1800_second_limit_is_accepted_without_waiting(self):
        status = self._run_fake(FakeBackend(), timeout=1800.0)
        self.assertEqual(status["state"], "completed")
        self.assertEqual(status["timeout_seconds"], 1800.0)

    def test_success_observed_after_native_wait_deadline_is_failure(self):
        clock = FakeClock()

        class LateWaitBackend(FakeBackend):
            def wait_root(self, process, milliseconds):
                clock.now += 0.06
                return WAIT_OBJECT_0

        api = LateWaitBackend()
        status = self._run_fake(api, timeout=0.05, clock=clock)
        self.assertEqual(status["state"], "deadline_expired_after_root_wait")
        self.assertNotEqual(status["state"], "completed")

    @unittest.skipUnless(os.name == "nt", "real Job Object fixtures require Windows")
    def test_synthetic_failure_in_sampling_analysis_archive_and_finalization(self):
        worker = pathlib.Path(__file__).with_name("synthetic_pipeline_worker.py")
        for phase in ("sampling", "analysis", "archive", "finalization"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory(prefix="qshift_v2_fail_") as temp:
                artifact = pathlib.Path(temp) / f"{phase}.json"
                status = run_supervisor(
                    [sys.executable, str(worker), "--phase", phase, "--mode", "fail",
                     "--artifact", str(artifact)],
                    timeout_seconds=3,
                )
                self.assertEqual(status["state"], "root_failed")
                self.assertNotEqual(status["root_exit_code"], 0)
                if phase in {"archive", "finalization"}:
                    self.assertTrue(pathlib.Path(str(artifact) + ".partial").exists())
                    self.assertFalse(artifact.exists())

    @unittest.skipUnless(os.name == "nt", "real Job Object fixtures require Windows")
    def test_deadline_terminates_blocking_synthetic_pipeline_stages(self):
        worker = pathlib.Path(__file__).with_name("synthetic_pipeline_worker.py")
        for phase in ("sampling", "analysis", "archive", "finalization"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory(prefix="qshift_v2_stage_") as temp:
                marker = pathlib.Path(temp) / "entered.json"
                artifact = pathlib.Path(temp) / f"{phase}.json"
                status = run_supervisor(
                    [sys.executable, str(worker), "--phase", phase, "--mode", "block",
                     "--marker", str(marker), "--artifact", str(artifact), "--duration", "10"],
                    timeout_seconds=1.5,
                )
                self.assertTrue(marker.exists(), f"{phase} fixture did not enter its blocking stage")
                self.assertIn(status["state"], {"deadline_expired", "deadline_expired_after_root_wait"})
                self.assertTrue(self._pid_done(status["root_pid"], 1.0))
                if phase in {"archive", "finalization"}:
                    self.assertTrue(pathlib.Path(str(artifact) + ".partial").exists())
                    self.assertFalse(artifact.exists())

    @unittest.skipUnless(os.name == "nt", "real Job Object fixtures require Windows")
    def test_repeated_execution_creates_and_cleans_independent_jobs(self):
        statuses = [
            self._run_real("pass")
            for _ in range(3)
        ]
        self.assertEqual([s["state"] for s in statuses], ["completed"] * 3)
        self.assertEqual(len({s["root_pid"] for s in statuses}), 3)

    @unittest.skipUnless(os.name == "nt", "real Job Object fixtures require Windows")
    def test_historical_v6_v7_files_are_unchanged_by_synthetic_run(self):
        repo = pathlib.Path(__file__).resolve().parents[3]
        paths = [
            repo / "outputs" / "ns4a_v2_final_readiness_v6",
            repo / "outputs" / "ns4a_v2_final_readiness_v7",
        ]

        def snapshot():
            records = []
            for root in paths:
                for item in sorted(root.rglob("*")):
                    if item.is_file():
                        raw = item.read_bytes()
                        records.append((str(item.relative_to(repo)), len(raw), hashlib.sha256(raw).hexdigest()))
            return records

        before = snapshot()
        status = self._run_real("pass")
        self.assertEqual(status["state"], "completed")
        self.assertEqual(snapshot(), before)

    def test_status_artifact_is_write_once(self):
        with tempfile.TemporaryDirectory(prefix="qshift_v2_status_") as temp:
            path = pathlib.Path(temp) / "status.json"
            path.write_text("original\n", encoding="utf-8")
            from v2_job_supervisor_v1 import SupervisorError, _write_status_once
            with self.assertRaisesRegex(SupervisorError, "refusing to overwrite"):
                _write_status_once(path, {"state": "completed"})
            self.assertEqual(path.read_text(encoding="utf-8"), "original\n")

    def test_engineering_package_has_no_stim_import_or_sampler_call(self):
        package = pathlib.Path(__file__).resolve().parents[1]
        for source_path in package.rglob("*.py"):
            with self.subTest(source=source_path.name):
                tree = ast.parse(source_path.read_text(encoding="utf-8"))
                imported = []
                calls = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported.extend(alias.name.lower() for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported.append(node.module.lower())
                    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                        calls.append(node.func.attr.lower())
                self.assertFalse(any(name == "stim" or name.startswith("stim.") for name in imported))
                self.assertNotIn("compile_detector_sampler", calls)
                self.assertNotIn("sample", calls)

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
