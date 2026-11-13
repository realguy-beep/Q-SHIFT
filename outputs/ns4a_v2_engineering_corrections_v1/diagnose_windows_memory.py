"""Sampler-free PSAPI versus .NET Get-Process memory cross-check."""
from __future__ import annotations

import json
import subprocess
import sys

from peak_working_set_v1 import measure_current_process


def main() -> int:
    snapshot = measure_current_process()
    ps_command = (
        f"$p=Get-Process -Id {int(__import__('os').getpid())}; "
        "$p.Refresh(); [Console]::WriteLine([string]$p.PeakWorkingSet64); "
        "[Console]::WriteLine([string]$p.WorkingSet64)"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", ps_command],
        capture_output=True, text=True, timeout=10, check=False,
    )
    if result.returncode != 0:
        print(json.dumps({"status": "FAIL", "stderr": result.stderr.strip()}))
        return 1
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 2:
        print(json.dumps({"status": "FAIL", "stdout": result.stdout}))
        return 1
    powershell_peak, powershell_current = map(int, lines)
    agrees = powershell_peak >= snapshot.peak_working_set_bytes
    report = {
        "status": "PASS" if agrees else "FAIL",
        "python_pid": int(__import__("os").getpid()),
        "psapi_peak_working_set_bytes": snapshot.peak_working_set_bytes,
        "psapi_current_working_set_bytes": snapshot.current_working_set_bytes,
        "powershell_peak_working_set64_bytes": powershell_peak,
        "powershell_working_set64_bytes": powershell_current,
        "comparison": "independent high-water observation must be >= earlier PSAPI high-water",
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if agrees else 1


if __name__ == "__main__":
    raise SystemExit(main())
