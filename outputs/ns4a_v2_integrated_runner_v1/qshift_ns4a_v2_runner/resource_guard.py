"""Conservative wall-clock, RSS, and disk guards used by the runner."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import shutil
import time
from pathlib import Path
from typing import Callable


class ResourceLimitError(RuntimeError):
    """The configured execution limit was exceeded or could not be measured."""


def current_rss_bytes() -> int:
    if hasattr(ctypes, "windll"):
        class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(counters)
        get_current = ctypes.windll.kernel32.GetCurrentProcess
        get_current.restype = wintypes.HANDLE
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
        get_info.restype = wintypes.BOOL
        process = get_current()
        ok = get_info(process, ctypes.byref(counters), counters.cb)
        if not ok:
            raise ResourceLimitError("Windows GetProcessMemoryInfo failed; RSS cannot be enforced.")
        return int(counters.WorkingSetSize)
    try:
        import resource
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value if value > 10_000_000 else value * 1024
    except Exception as exc:
        raise ResourceLimitError("RSS measurement is unavailable; fail closed.") from exc


@dataclass
class ResourceGuard:
    run_directory: Path
    wall_clock_seconds: float = 1_800.0
    peak_rss_bytes: int = 2_147_483_648
    free_disk_reserve_bytes: int = 1_073_741_824
    clock: Callable[[], float] = time.monotonic
    rss_provider: Callable[[], int] = current_rss_bytes
    disk_usage_provider: Callable[[str | Path], Any] = shutil.disk_usage
    epoch_clock: Callable[[], float] = time.time
    deadline_epoch_utc: float | None = None
    started_at: float | None = None

    def start(self) -> None:
        if self.started_at is not None:
            raise ResourceLimitError("Resource guard has already started.")
        self.started_at = self.clock()
        self.check("start")

    def bind_persisted_deadline(self, deadline_epoch_utc: float) -> None:
        if isinstance(deadline_epoch_utc, bool) or not isinstance(deadline_epoch_utc, (int, float)):
            raise ResourceLimitError("Persisted deadline must be an epoch timestamp.")
        if deadline_epoch_utc <= self.epoch_clock():
            raise ResourceLimitError("Persisted whole-run deadline has expired.")
        self.deadline_epoch_utc = float(deadline_epoch_utc)

    def check(self, phase: str) -> dict[str, int | float]:
        if self.started_at is None:
            raise ResourceLimitError("Resource guard must start before use.")
        elapsed = self.clock() - self.started_at
        if elapsed > self.wall_clock_seconds:
            raise ResourceLimitError(f"wall-clock limit exceeded during {phase}.")
        if self.deadline_epoch_utc is not None and self.epoch_clock() >= self.deadline_epoch_utc:
            raise ResourceLimitError(f"persisted whole-run deadline exceeded during {phase}.")
        rss = int(self.rss_provider())
        if rss < 0 or rss > self.peak_rss_bytes:
            raise ResourceLimitError(f"RSS limit exceeded or invalid during {phase}: {rss} bytes.")
        usage = self.disk_usage_provider(self.run_directory)
        free = int(usage.free)
        if free < self.free_disk_reserve_bytes:
            raise ResourceLimitError(f"free-disk reserve violated during {phase}: {free} bytes remain.")
        return {"elapsed_seconds": float(elapsed), "rss_bytes": rss, "free_disk_bytes": free}
