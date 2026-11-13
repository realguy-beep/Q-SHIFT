"""Strict Windows peak-working-set measurement for NS-4A V6.

This reports the OS peak working set (not current RSS, virtual memory, or
available system RAM). API or result failures are fail-closed.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Callable


class ResourceLimitError(RuntimeError):
    """A resource measurement failed or violated the configured limit."""


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
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


def peak_working_set_bytes(
    *,
    os_name: str | None = None,
    dll_loader: Callable[..., object] | None = None,
    last_error_getter: Callable[[], int] | None = None,
) -> int:
    """Return GetProcessMemoryInfo's PeakWorkingSetSize, or fail closed.

    Explicit function prototypes preserve HANDLE width on 64-bit Windows and
    make the structure size passed to PSAPI unambiguous. The optional injection
    points exist only for deterministic unit tests.
    """
    active_os = os.name if os_name is None else os_name
    if active_os != "nt":
        raise ResourceLimitError("peak working-set enforcement is supported only on Windows.")

    loader = dll_loader or getattr(ctypes, "WinDLL", None)
    if loader is None:
        raise ResourceLimitError("Windows DLL loading is unavailable; cannot enforce memory cap.")
    get_error = last_error_getter or getattr(ctypes, "get_last_error", None)
    if get_error is None:
        raise ResourceLimitError("Windows last-error retrieval is unavailable; cannot enforce memory cap.")

    try:
        kernel32 = loader("kernel32", use_last_error=True)
        psapi = loader("psapi", use_last_error=True)
        get_current = getattr(kernel32, "GetCurrentProcess")
        get_current.argtypes = []
        get_current.restype = wintypes.HANDLE

        get_info = getattr(psapi, "GetProcessMemoryInfo")
        get_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
            wintypes.DWORD,
        ]
        get_info.restype = wintypes.BOOL

        process_handle = get_current()
        if not process_handle:
            raise ResourceLimitError("GetCurrentProcess returned an invalid process handle.")

        counters = PROCESS_MEMORY_COUNTERS_EX()
        structure_size = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        counters.cb = structure_size
        ctypes.set_last_error(0)
        ok = get_info(process_handle, ctypes.byref(counters), structure_size)
        if not ok:
            error_code = int(get_error())
            raise ResourceLimitError(
                f"GetProcessMemoryInfo failed (Windows error {error_code})."
            )
        if counters.cb != structure_size:
            raise ResourceLimitError(
                f"GetProcessMemoryInfo returned unexpected structure size {counters.cb}; "
                f"expected {structure_size}."
            )
        peak = int(counters.PeakWorkingSetSize)
        current = int(counters.WorkingSetSize)
        if peak <= 0 or current <= 0 or peak < current:
            raise ResourceLimitError(
                f"GetProcessMemoryInfo returned invalid working-set values "
                f"(peak={peak}, current={current})."
            )
        return peak
    except ResourceLimitError:
        raise
    except Exception as exc:
        raise ResourceLimitError(
            f"Windows peak-working-set measurement failed: {type(exc).__name__}: {exc}"
        ) from exc


def enforce_peak_working_set_limit(peak_bytes: int, maximum_bytes: int) -> int:
    """Reject invalid readings and enforce the unchanged hard cap."""
    if (isinstance(peak_bytes, bool) or not isinstance(peak_bytes, int)
            or peak_bytes <= 0):
        raise ResourceLimitError("peak working-set measurement is invalid or zero.")
    if (isinstance(maximum_bytes, bool) or not isinstance(maximum_bytes, int)
            or maximum_bytes <= 0):
        raise ResourceLimitError("peak working-set limit is invalid.")
    if peak_bytes > maximum_bytes:
        raise ResourceLimitError(
            f"peak working-set cap exceeded: {peak_bytes} > {maximum_bytes} bytes."
        )
    return peak_bytes
