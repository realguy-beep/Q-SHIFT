from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import peak_working_set_v1 as memory
import verify_source_manifest


class FakeFunction:
    def __init__(self, callback):
        self.callback = callback
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self.callback(*args)


class FakeKernel32:
    def __init__(self, handle=-1):
        self.handle = handle
        self.GetCurrentProcess = FakeFunction(lambda: self.handle)


class FakePsapi:
    def __init__(self, peak=1000, current=800, *, result=True, wrong_cb=False):
        self.peak = peak
        self.current = current
        self.result = result
        self.wrong_cb = wrong_cb
        self.handle_seen = None
        self.cb_argument = None
        self.GetProcessMemoryInfo = FakeFunction(self.get_info)

    def get_info(self, handle, out_pointer, cb):
        self.handle_seen = handle
        self.cb_argument = int(cb)
        counters = ctypes.cast(
            out_pointer, ctypes.POINTER(memory.PROCESS_MEMORY_COUNTERS_EX)
        ).contents
        counters.PeakWorkingSetSize = self.peak
        counters.WorkingSetSize = self.current
        if self.wrong_cb:
            counters.cb = self.cb_argument - 1
        return self.result


class PeakWorkingSetTests(unittest.TestCase):
    def test_package_and_read_only_reference_hash_manifest(self):
        report = verify_source_manifest.verify()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["manifest_self_hash"], "excluded")

    def test_structure_uses_native_size_t_layout(self):
        expected = 2 * ctypes.sizeof(wintypes.DWORD) + 9 * ctypes.sizeof(ctypes.c_size_t)
        self.assertEqual(ctypes.sizeof(memory.PROCESS_MEMORY_COUNTERS_EX), expected)

    def test_valid_measurement_reports_peak_and_current_separately(self):
        kernel = FakeKernel32(-1)
        psapi = FakePsapi(peak=4096, current=2048)
        snapshot = memory.measure_current_process(kernel32=kernel, psapi=psapi)
        self.assertEqual(snapshot.peak_working_set_bytes, 4096)
        self.assertEqual(snapshot.current_working_set_bytes, 2048)
        self.assertEqual(memory.enforce_peak_working_set(snapshot), 4096)
        self.assertEqual(kernel.GetCurrentProcess.restype, wintypes.HANDLE)
        self.assertEqual(len(psapi.GetProcessMemoryInfo.argtypes), 3)
        self.assertEqual(psapi.GetProcessMemoryInfo.restype, wintypes.BOOL)
        self.assertEqual(psapi.cb_argument, ctypes.sizeof(memory.PROCESS_MEMORY_COUNTERS_EX))
        self.assertEqual(
            ctypes.cast(psapi.handle_seen, ctypes.c_void_p).value,
            ctypes.c_void_p(-1).value,
        )

    def test_api_failure_fails_closed(self):
        with self.assertRaisesRegex(memory.MemoryMeasurementError, "returned failure"):
            memory.measure_current_process(kernel32=FakeKernel32(), psapi=FakePsapi(result=False))

    def test_zero_or_inconsistent_measurements_fail_closed(self):
        for peak, current in ((0, 0), (0, 1), (10, 11)):
            with self.subTest(peak=peak, current=current):
                with self.assertRaises(memory.MemoryMeasurementError):
                    memory.measure_current_process(
                        kernel32=FakeKernel32(), psapi=FakePsapi(peak=peak, current=current)
                    )

    def test_invalid_structure_size_fails_closed(self):
        with self.assertRaisesRegex(memory.MemoryMeasurementError, "cb mismatch"):
            memory.measure_current_process(
                kernel32=FakeKernel32(), psapi=FakePsapi(wrong_cb=True)
            )

    def test_null_and_out_of_pointer_width_handles_fail_closed(self):
        invalid = [0, 1 << (ctypes.sizeof(ctypes.c_void_p) * 8)]
        for handle in invalid:
            with self.subTest(handle=handle):
                with self.assertRaises(memory.MemoryMeasurementError):
                    memory.measure_current_process(
                        kernel32=FakeKernel32(handle), psapi=FakePsapi()
                    )

    def test_memory_limit_boundary_and_violation(self):
        limit = memory.PEAK_WORKING_SET_LIMIT_BYTES
        self.assertEqual(memory.enforce_peak_working_set(
            memory.ProcessMemorySnapshot(limit, limit, None)), limit)
        with self.assertRaisesRegex(memory.MemoryMeasurementError, "exceeds limit"):
            memory.enforce_peak_working_set(
                memory.ProcessMemorySnapshot(limit + 1, limit, None))

    def test_invalid_snapshot_or_limit_fails_closed(self):
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit):
                with self.assertRaises(memory.MemoryMeasurementError):
                    memory.enforce_peak_working_set(
                        memory.ProcessMemorySnapshot(10, 8, None), limit)
        with self.assertRaises(memory.MemoryMeasurementError):
            memory.enforce_peak_working_set(None)  # type: ignore[arg-type]

    def test_unsupported_os_rejected_without_fallback_metric(self):
        with patch("peak_working_set_v1.os.name", "posix"):
            with self.assertRaisesRegex(memory.MemoryMeasurementError, "unsupported"):
                memory.measure_current_process()

    @unittest.skipUnless(__import__("os").name == "nt", "requires Windows PSAPI")
    def test_real_windows_measurement_is_nonzero_and_ordered(self):
        snapshot = memory.measure_current_process()
        self.assertGreater(snapshot.current_working_set_bytes, 0)
        self.assertGreaterEqual(snapshot.peak_working_set_bytes, snapshot.current_working_set_bytes)
        self.assertLessEqual(
            memory.enforce_peak_working_set(snapshot),
            memory.PEAK_WORKING_SET_LIMIT_BYTES,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
