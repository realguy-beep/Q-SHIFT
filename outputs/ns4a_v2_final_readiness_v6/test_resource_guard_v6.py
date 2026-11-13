from __future__ import annotations

import ctypes
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "ns4a_v2_integrated_runner_v1"))

from qshift_ns4a_v2_runner.resource_guard_v6 import (
    PROCESS_MEMORY_COUNTERS_EX,
    ResourceLimitError,
    enforce_peak_working_set_limit,
    peak_working_set_bytes,
)


class _Function:
    def __init__(self, callback):
        self.callback = callback
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self.callback(*args)


class _FakeApis:
    def __init__(self, *, peak=88_000_000, current=52_000_000, success=True, handle=None,
                 returned_cb=None):
        self.pointer_bytes = ctypes.sizeof(ctypes.c_void_p)
        self.handle = handle if handle is not None else (0x12345678ABCDEF01 if self.pointer_bytes == 8 else 0x1234567)
        self.seen_handle = None
        self.seen_size = None
        self.seen_cb = None
        self.peak = peak
        self.current = current
        self.success = success
        self.returned_cb = returned_cb
        self.kernel = SimpleNamespace(GetCurrentProcess=_Function(lambda: self.handle))

        def get_info(handle, pointer, size):
            self.seen_handle = handle
            self.seen_size = size
            counters = ctypes.cast(pointer, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX)).contents
            self.seen_cb = int(counters.cb)
            counters.PeakWorkingSetSize = self.peak
            counters.WorkingSetSize = self.current
            if self.returned_cb is not None:
                counters.cb = self.returned_cb
            return int(self.success)

        self.psapi = SimpleNamespace(GetProcessMemoryInfo=_Function(get_info))
        self.loaded = []

    def loader(self, name, *, use_last_error):
        self.loaded.append((name, use_last_error))
        return self.kernel if name == "kernel32" else self.psapi


class PeakWorkingSetTests(unittest.TestCase):
    def test_success_uses_typed_handle_and_full_structure(self):
        apis = _FakeApis()
        result = peak_working_set_bytes(os_name="nt", dll_loader=apis.loader, last_error_getter=lambda: 0)
        self.assertEqual(result, apis.peak)
        self.assertEqual(apis.seen_handle, apis.handle)
        self.assertEqual(apis.seen_size, ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX))
        self.assertEqual(apis.seen_cb, ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX))
        self.assertEqual(apis.kernel.GetCurrentProcess.argtypes, [])
        self.assertEqual(apis.kernel.GetCurrentProcess.restype, ctypes.c_void_p)
        self.assertEqual(apis.psapi.GetProcessMemoryInfo.argtypes[0], ctypes.c_void_p)
        self.assertEqual(apis.loaded, [("kernel32", True), ("psapi", True)])

    def test_api_failure_reports_last_error_and_fails_closed(self):
        apis = _FakeApis(success=False)
        with self.assertRaisesRegex(ResourceLimitError, "Windows error 5"):
            peak_working_set_bytes(os_name="nt", dll_loader=apis.loader, last_error_getter=lambda: 5)

    def test_zero_or_invalid_measurement_fails_closed(self):
        for peak, current in ((0, 1), (10, 11)):
            with self.subTest(peak=peak, current=current):
                apis = _FakeApis(peak=peak, current=current)
                with self.assertRaisesRegex(ResourceLimitError, "invalid working-set values"):
                    peak_working_set_bytes(os_name="nt", dll_loader=apis.loader, last_error_getter=lambda: 0)
        with self.assertRaisesRegex(ResourceLimitError, "invalid or zero"):
            enforce_peak_working_set_limit(0, 1_073_741_824)

    def test_peak_over_limit_is_rejected(self):
        with self.assertRaisesRegex(ResourceLimitError, "cap exceeded"):
            enforce_peak_working_set_limit(1_073_741_825, 1_073_741_824)
        self.assertEqual(enforce_peak_working_set_limit(1_073_741_824, 1_073_741_824), 1_073_741_824)

    def test_invalid_handle_is_rejected(self):
        apis = _FakeApis(handle=0)
        with self.assertRaisesRegex(ResourceLimitError, "invalid process handle"):
            peak_working_set_bytes(os_name="nt", dll_loader=apis.loader, last_error_getter=lambda: 0)

    def test_mismatched_returned_structure_size_is_rejected(self):
        apis = _FakeApis(returned_cb=ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX) - 1)
        with self.assertRaisesRegex(ResourceLimitError, "unexpected structure size"):
            peak_working_set_bytes(os_name="nt", dll_loader=apis.loader, last_error_getter=lambda: 0)

    def test_structure_layout_matches_pointer_width(self):
        expected = 2 * ctypes.sizeof(ctypes.c_uint32) + 9 * ctypes.sizeof(ctypes.c_size_t)
        self.assertEqual(ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX), expected)
        self.assertEqual(ctypes.sizeof(ctypes.c_void_p), ctypes.sizeof(ctypes.c_size_t))

    def test_unsupported_operating_system_fails_closed(self):
        with self.assertRaisesRegex(ResourceLimitError, "only on Windows"):
            peak_working_set_bytes(os_name="posix", dll_loader=lambda *a, **k: self.fail("must not load DLL"))


if __name__ == "__main__":
    unittest.main()
