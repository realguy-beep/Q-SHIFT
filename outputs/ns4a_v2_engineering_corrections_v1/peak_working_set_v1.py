"""Fail-closed Windows per-process peak working-set measurement.

This module does not change the historical V2 runner. It defines the intended
process high-water metric for a separately reviewed V2 source revision.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from typing import Any


PEAK_WORKING_SET_LIMIT_BYTES = 2_147_483_648


class MemoryMeasurementError(RuntimeError):
    """The configured process memory metric is invalid or unavailable."""


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    """Windows PSAPI structure using SIZE_T fields at native pointer width."""

    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


@dataclass(frozen=True)
class ProcessMemorySnapshot:
    """Two distinct PSAPI values from one process."""

    peak_working_set_bytes: int
    current_working_set_bytes: int
    process_id: int | None


def _api_pair() -> tuple[Any, Any]:
    if os.name != "nt":
        raise MemoryMeasurementError("Windows process working-set measurement is unsupported on this OS.")
    try:
        return (
            ctypes.WinDLL("kernel32", use_last_error=True),
            ctypes.WinDLL("psapi", use_last_error=True),
        )
    except Exception as exc:
        raise MemoryMeasurementError("Windows kernel32/psapi bindings are unavailable.") from exc


def _handle_integer(handle: Any) -> int:
    """Validate a pointer-width HANDLE without truncating a 64-bit value.

    GetCurrentProcess returns the documented pseudo-handle (HANDLE)-1. It is
    valid here; null and positive values outside pointer width are rejected.
    """
    if isinstance(handle, bool):
        raise MemoryMeasurementError("GetCurrentProcess returned an invalid boolean handle.")
    if isinstance(handle, int):
        value = handle
    elif isinstance(handle, ctypes.c_void_p):
        value = handle.value
        if value is None:
            raise MemoryMeasurementError("GetCurrentProcess returned a null handle.")
    else:
        try:
            value = ctypes.cast(handle, ctypes.c_void_p).value
        except Exception as exc:
            raise MemoryMeasurementError("GetCurrentProcess returned an invalid HANDLE value.") from exc
        if value is None:
            raise MemoryMeasurementError("GetCurrentProcess returned a null handle.")
    value = int(value)
    max_pointer = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
    if value == 0 or value < -1 or value > max_pointer:
        raise MemoryMeasurementError("GetCurrentProcess returned a HANDLE outside pointer width.")
    return value


def _declare(kernel32: Any, psapi: Any) -> None:
    try:
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    except Exception as exc:
        raise MemoryMeasurementError("Could not declare the Windows memory API signatures.") from exc


def measure_current_process(*, kernel32: Any = None, psapi: Any = None) -> ProcessMemorySnapshot:
    """Measure current-process peak and current working set using PSAPI.

    PeakWorkingSetSize is a per-process high-water mark. This does not measure
    aggregate Job Object/process-tree memory or install a hard limit.
    """
    if kernel32 is None or psapi is None:
        kernel32, psapi = _api_pair()
    _declare(kernel32, psapi)
    try:
        handle = kernel32.GetCurrentProcess()
        handle_value = _handle_integer(handle)
    except MemoryMeasurementError:
        raise
    except Exception as exc:
        raise MemoryMeasurementError("GetCurrentProcess failed.") from exc

    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    try:
        ok = psapi.GetProcessMemoryInfo(
            wintypes.HANDLE(handle_value),
            ctypes.byref(counters),
            ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX),
        )
    except Exception as exc:
        raise MemoryMeasurementError("GetProcessMemoryInfo call failed.") from exc
    if not ok:
        try:
            error_code = ctypes.get_last_error()
        except Exception:
            error_code = None
        raise MemoryMeasurementError(
            f"GetProcessMemoryInfo returned failure (last_error={error_code})."
        )

    expected_size = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    if int(counters.cb) != expected_size:
        raise MemoryMeasurementError(
            f"PROCESS_MEMORY_COUNTERS_EX.cb mismatch: {counters.cb} != {expected_size}."
        )
    peak = int(counters.PeakWorkingSetSize)
    current = int(counters.WorkingSetSize)
    if current <= 0 or peak <= 0 or peak < current:
        raise MemoryMeasurementError(
            f"Invalid working-set readings: peak={peak}, current={current}."
        )
    return ProcessMemorySnapshot(
        peak_working_set_bytes=peak,
        current_working_set_bytes=current,
        process_id=os.getpid(),
    )


def enforce_peak_working_set(
    snapshot: ProcessMemorySnapshot,
    limit_bytes: int = PEAK_WORKING_SET_LIMIT_BYTES,
) -> int:
    """Return the process peak when compliant, otherwise fail closed."""
    if isinstance(limit_bytes, bool) or type(limit_bytes) is not int or limit_bytes <= 0:
        raise MemoryMeasurementError("Peak working-set limit must be a positive integer.")
    if not isinstance(snapshot, ProcessMemorySnapshot):
        raise MemoryMeasurementError("Peak memory snapshot is missing or has an invalid type.")
    peak = snapshot.peak_working_set_bytes
    if type(peak) is not int or peak <= 0:
        raise MemoryMeasurementError("Peak working-set measurement is invalid.")
    if peak > limit_bytes:
        raise MemoryMeasurementError(
            f"Process peak working set exceeds limit: {peak} > {limit_bytes} bytes."
        )
    return peak
