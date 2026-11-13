"""Sampler-free diagnostic comparing the V5 ctypes call with the V6 repair."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import sys
import time
from ctypes import wintypes

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "ns4a_v2_integrated_runner_v1"))

from qshift_ns4a_v2_runner.resource_guard_v6 import (
    PROCESS_MEMORY_COUNTERS_EX,
    peak_working_set_bytes,
)


def reproduce_v5_call() -> tuple[bool, str | None, int | None, str, str, str]:
    """Reproduce the old V5 declarations exactly; this performs no sampling."""
    if os.name != "nt":
        return False, "unsupported operating system", None, "unavailable", "unavailable", "unavailable"

    class LegacyCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    counters = LegacyCounters()
    counters.cb = ctypes.sizeof(counters)
    # Deliberately mirrors V5's missing restype/argtypes and default last-error
    # behavior. The API may return FALSE or raise a ctypes conversion error.
    get_current = ctypes.windll.kernel32.GetCurrentProcess
    get_info = ctypes.windll.psapi.GetProcessMemoryInfo
    process = get_current()
    legacy_restype = str(get_current.restype)
    legacy_argtypes = str(get_info.argtypes)
    legacy_info_restype = str(get_info.restype)
    if not get_info(process, ctypes.byref(counters), counters.cb):
        return (False,
                "GetProcessMemoryInfo returned FALSE (V5 did not capture last-error diagnostics).",
                int(process), legacy_restype, legacy_argtypes, legacy_info_restype)
    return True, None, int(process), legacy_restype, legacy_argtypes, legacy_info_restype


def probe_truncated_handle_error(legacy_handle: int | None) -> dict[str, int | bool | str | None]:
    """Query the 32-bit-truncated legacy pseudo-handle with last-error enabled."""
    if os.name != "nt" or legacy_handle is None:
        return {"called": False, "winerror": None, "truncated_handle_hex": None}
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    get_current = kernel32.GetCurrentProcess
    get_current.argtypes = []
    get_current.restype = wintypes.HANDLE
    get_info = psapi.GetProcessMemoryInfo
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
    get_info.restype = wintypes.BOOL
    low32 = int(legacy_handle) & 0xFFFFFFFF
    bad_handle = wintypes.HANDLE(low32)
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(counters)
    ctypes.set_last_error(0)
    success = bool(get_info(bad_handle, ctypes.byref(counters), counters.cb))
    return {
        "called": True,
        "api_succeeded": success,
        "winerror": None if success else int(ctypes.get_last_error()),
        "truncated_handle_hex": f"0x{low32:016x}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hold-seconds", type=float, default=0.0,
                        help="keep process alive briefly for independent PowerShell peak measurement")
    args = parser.parse_args()
    (legacy_ok, legacy_error, legacy_handle, legacy_handle_restype,
     legacy_api_argtypes, legacy_api_restype) = reproduce_v5_call()
    truncated_handle_probe = probe_truncated_handle_error(legacy_handle)
    corrected_peak = peak_working_set_bytes()
    result = {
        "schema": "qshift-windows-memory-diagnostic-v6",
        "pid": os.getpid(),
        "legacy_v5_call_succeeded": legacy_ok,
        "legacy_v5_error": legacy_error,
        "legacy_get_current_process_restype": legacy_handle_restype,
        "legacy_get_process_memory_info_argtypes": legacy_api_argtypes,
        "legacy_get_process_memory_info_restype": legacy_api_restype,
        "legacy_handle_value": legacy_handle,
        "legacy_handle_c_int_bytes": ctypes.sizeof(ctypes.c_int),
        "truncated_handle_probe": truncated_handle_probe,
        "corrected_peak_working_set_bytes": corrected_peak,
        "counter_structure_bytes": ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX),
        "pointer_bytes": ctypes.sizeof(ctypes.c_void_p),
        "handle_bytes": ctypes.sizeof(wintypes.HANDLE),
        "sampler_calls": 0,
        "shots": 0,
    }
    print(json.dumps(result, sort_keys=True), flush=True)
    if args.hold_seconds > 0:
        time.sleep(min(args.hold_seconds, 15.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
