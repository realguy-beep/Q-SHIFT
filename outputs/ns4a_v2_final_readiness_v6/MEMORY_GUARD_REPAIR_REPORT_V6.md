# NS-4A V6 Windows memory-guard repair and stopped-attempt recovery

## Decision and scope

V6 repairs only Windows process peak-working-set measurement and prepares one distinct, separately authorized recovery attempt. It preserves the V5 benchmark, six benchmark seeds, protocol, and all scientific settings. No sampling or Stage 5 access was performed. V6 does not itself authorize a benchmark.

## Confirmed V5 failure cause

The V5 `_peak_working_set_bytes()` in `qshift_ns4a_v2_runner/benchmark_v5.py` called `ctypes.windll.kernel32.GetCurrentProcess` and `ctypes.windll.psapi.GetProcessMemoryInfo` without declaring prototypes. The standalone V5-call reproduction on 64-bit Windows reported `GetCurrentProcess.restype = ctypes.c_long` (4 bytes), `GetProcessMemoryInfo.restype = ctypes.c_long`, and `GetProcessMemoryInfo.argtypes = None`. It returned pseudo-handle `-1`; the API returned FALSE. The V5 binding did not use `WinDLL(..., use_last_error=True)`, so that original call did not preserve its Windows error code.

The V5 `PROCESS_MEMORY_COUNTERS_EX` layout itself measured 80 bytes on this 64-bit process and has two DWORD fields followed by nine pointer-sized `SIZE_T` fields. The confirmed defect was the missing pointer-sized function signature, not the structure size. A separate controlled probe passed the zero-extended 32-bit handle `0x00000000ffffffff` using a correctly typed PSAPI signature; Windows returned error 6 (invalid handle), consistent with the truncated pseudo-handle failure.

## V6 correction and independent measurement

`resource_guard_v6.py` loads `kernel32` and `psapi` with `ctypes.WinDLL(..., use_last_error=True)`, declares `GetCurrentProcess.restype = wintypes.HANDLE`, `GetProcessMemoryInfo.argtypes = [HANDLE, POINTER(PROCESS_MEMORY_COUNTERS_EX), DWORD]`, and its `BOOL` return type. It verifies structure size and returned `cb`, rejects invalid handles and zero/inconsistent readings, and includes the actual Windows error code on API failure. Unsupported platforms and measurement failures remain fail-closed.

A held-open diagnostic Python process reported peak working set **17,309,696 bytes**. PowerShell `.NET Process.PeakWorkingSet64` and `Win32_PerfRawData_PerfProc_Process.WorkingSetPeak`, queried for the diagnostic's actual PID, both reported **17,317,888 bytes**; the difference was **8,192 bytes**, below the diagnostic comparison tolerance of 4 MiB. This independent comparison validates the API result; it does not replace the runtime peak-working-set measurement. Structure size was 80 bytes and pointer/HANDLE width was 8 bytes. The diagnostic had zero sampler calls and zero shots.

## Limits and recovery

The original caps remain exactly as frozen: 1 GiB peak working set, 600 seconds, 1 GiB minimum free disk, 128 MiB generated artifacts, 6,000 shots, and six sampler calls. Runtime uses only `PeakWorkingSetSize`; it does not fall back to RSS, virtual memory, or available RAM. The cap is applied to every resource check and final report measurement.

`STOPPED_ATTEMPT_RECORD_V6.json` records the V5 commit, manifest/protocol/inventory identities, old authorization hash, benchmark ID, observed guard failure, zero calls/shots, and empty output directory. V6 verifies the old authorization's digest and verifies that the old V5 run directory still exists and is empty; it never reads that old token as authorization. V6 refuses if the old directory is missing/non-empty or unexpected V5 attempt siblings exist. A V6 attempt uses a distinct output root and a V6 ID; the output root must be absent. No V5 artifacts are rewritten.

The prior V5 authorization cannot authorize V6. A new V6 owner token is required after publication, bound to the final V6 HEAD, V6 manifest, unchanged protocol and seed inventory, and V6 recovery-record hash. The final commit SHA is intentionally absent from the manifest and is bound post-commit by owner authorization.

## Verification

Executed with the pinned environment Python 3.12.10:

- `python -m unittest discover -s outputs/ns4a_v2_final_readiness_v6 -p 'test_*.py' -v` — **18 passed**.
- `python -m py_compile` over the V6 guard, identity validator, benchmark engine, launcher, manifest tools, and diagnostic — **passed**.
- `python outputs/ns4a_v2_final_readiness_v6/diagnose_windows_peak_working_set_v6.py` — legacy failure reproduced; corrected API returned a positive 64-bit peak; zero sampler calls/shots.
- Independent live-process comparison — **PASS** as reported above.
- `python -m py_compile` over all V6 Python implementation, test-support, launcher, manifest, and diagnostic files — **passed**.
- V6 manifest build and independent verification — **PASS**, 89 total rows (73 inherited V5 rows, V5 manifest, and 15 V6 files); final manifest SHA is reported after commit.
- Sampler-free V5-compatible deterministic circuit/DEM preflight previously passed 6 circuits, 6 DEMs, and all 12 candidate rows with zero labels, selections, sampler calls, or shots. V6 itself does not run a production sample path during tests.

Tests cover successful typed API use, API failure with last-error reporting, invalid/zero data, cap equality and exceedance, invalid handles, pointer-width and structure-size handling, malformed returned structure size, unsupported OS, recognition of the empty V5 attempt, rejection of non-empty/extra V5 attempts, old-token hash mismatch, V5-token rejection as V6 authorization, and V6 recovery-record hash binding.

## Evidence and limitations

The original V5 output root contains exactly the recorded child `outputs/ns4a_v2_final_readiness_v5/benchmark_runs/3eb8d077109e8d2a`; it was observed empty with 0 files and 0 bytes. The local V5 token's recorded SHA-256 is `328a384298f4a2f4ca13b81ff683a9ec49dedf8d3edbcd9f11cf826c06eb0947`. The V6 runner and reports do not contain sample arrays or logical outcomes.

The independent check is specific to this Windows 64-bit environment. The 32-bit structure branch is covered by layout logic but was not executed. Failure remains a hard stop on any platform or process where Windows cannot provide a valid peak working-set reading. Full benchmark performance, duration, and memory under decoder workload remain unmeasured. No retry, resume, or second sampling attempt is authorized by this repair.
