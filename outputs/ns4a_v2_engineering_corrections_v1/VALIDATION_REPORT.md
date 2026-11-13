# NS-4A V2 Engineering Corrections — Validation Report

## Scope

Base commit: f7f0fc167960e9499e40785a9b2262295bfecabc

This package addresses only the deadline-supervisor and memory-measurement
items in the readiness review. The runner, resource-guard implementation,
scientific protocol/configuration, allocations, hypotheses, seeds, V7 source,
and historical reports were not modified. The supervisor was tested only with
deterministic fake Job APIs and disposable Python child processes. No Stim
module is imported, and no sampler or scientific workload is invoked.

## Implemented checks

| Requirement | Result | Evidence |
|---|---|---|
| Natural root and Job-tree drain | PASS | Real Windows Python child fixtures; completion requires zero active count and zero Job PIDs |
| Persistent descendant handling | PASS | Real descendant survives grace, is identified and terminated; final state remains failure |
| Failed Job accounting/PID queries | PASS | Deterministic injected API failures request fail-closed cleanup |
| Deadline expiry | PASS | Fake monotonic clock expires during drain grace; real blocking fixtures expire while the parent remains responsive |
| Late native wait observation | PASS | Synthetic backend returns root completion after deadline; supervisor does not report success |
| Synthetic sampling/analysis failure | PASS | Python-only labeled stages exit nonzero; supervisor reports root_failed |
| Synthetic archive/finalization interruption | PASS | Disposable partial-file fixture remains uncommitted when the child fails or is terminated; final path is absent |
| Forced termination | PASS | Job drain after forced termination is never promoted to completed |
| Kill-on-close and handle cleanup | PASS | Real Windows Job Object test confirms root and descendant exit after Job close |
| Repeated invocation | PASS | Three separate real Python-only Jobs complete and close independently |
| Write-once status | PASS | Existing status is not overwritten |
| Memory API signatures/layout/handle | PASS | Deterministic tests validate pointer-width HANDLE, pseudo-handle preservation, typed PSAPI args/result, cb size, and native SIZE_T layout |
| Memory failures and limit | PASS | API failure, invalid values/handle/structure, unsupported OS, exact 2-GiB boundary, and one-byte-over cases |
| No sampling dependency | PASS | AST test finds no Stim imports, compile_detector_sampler calls, or sample calls in this package |
| Historical V6/V7 integrity | PASS for this task's writes | Test computes read-only SHA-256 inventories for both directories before/after a synthetic child run and finds them unchanged |

## Commands and results

From the repository root, using Python 3.12.10 on Windows:

    python -m py_compile outputs/ns4a_v2_engineering_corrections_v1/v2_job_supervisor_v1.py outputs/ns4a_v2_engineering_corrections_v1/peak_working_set_v1.py outputs/ns4a_v2_engineering_corrections_v1/diagnose_windows_memory.py outputs/ns4a_v2_engineering_corrections_v1/verify_source_manifest.py outputs/ns4a_v2_engineering_corrections_v1/tests/test_v2_job_supervisor_v1.py outputs/ns4a_v2_engineering_corrections_v1/tests/test_peak_working_set_v1.py outputs/ns4a_v2_engineering_corrections_v1/tests/synthetic_pipeline_worker.py
    python -m unittest discover -s outputs/ns4a_v2_engineering_corrections_v1/tests -p "test_*.py" -v
    python outputs/ns4a_v2_engineering_corrections_v1/diagnose_windows_memory.py
    python outputs/ns4a_v2_final_readiness_v7/test_job_watchdog_v7.py
    python outputs/ns4a_v2_engineering_corrections_v1/verify_source_manifest.py

The final engineering-corrections run passed 38 tests in 8.166 seconds. The
original V7 suite passed 19 tests in 1.278 seconds and its committed files
remained read-only. All subprocess fixtures are Python-only and
temporary-directory scoped.
The package source-manifest verifier passed for 10 package files and 15
read-only source references. The original V7 manifest's five artifact rows
also matched their recorded working-tree or normalized-byte SHA-256 values.

## Native Windows memory diagnostic

The diagnostic called the new PSAPI provider in a Python process, then asked
PowerShell/.NET Get-Process to query the same PID. The earlier PSAPI peak was
17,514,496 bytes and the later independent PeakWorkingSet64 value was
17,838,080 bytes. PSAPI's current value at its snapshot was 17,514,496 bytes;
the later PowerShell current value was 17,838,080 bytes. The later high-water
value being at least the earlier one is the expected relationship; the
different instantaneous current values reflect separate observation times.
This was a small API correctness check, not an experiment resource benchmark.

## Historical-directory preservation check

An independent before/after SHA-256 inventory around the final engineering
test run matched exactly: V6 directory, 13 visible files / 58,094 bytes /
aggregate d88fb4602b07bf3afd4f31c749e7f45af79d0680c1aa13a0b9157eaebaaa533c;
V7 directory, 7 visible files / 144,189 bytes /
aggregate 585207e2d8ea261f815891a79a7b1c4395e09973441d0d82e5cf9f623aeb020b.
The V6 visible inventory is smaller than the earlier V7 report's recorded
34-file / 162,841-byte inventory (aggregate
E67011491D1EA3F8D4C63856EBC947134F95785A22B15623CE97C8FD8D6DB6DD), so that
full earlier local inventory is not reproduced in this clean branch worktree.
This task did not recover the absent files or rewrite the historical record.

The V7 tree count includes one ignored Python bytecode cache generated when
the unchanged V7 test module was run. Its source, test, manifest, reports, and
tracked evidence hashes still match. A cleanup request for that exact cache
was rejected by local command policy; it remains untracked, is excluded from
the package, and was not staged or committed. No other V6/V7 path changed
during the measured final test run.

## Initial test-harness correction

The first run had fixture-only errors: several new real-process assertions
referenced helpers scoped to another unittest class, and a 350-ms timeout
expired during process startup before the phase marker was written. Those
tests did not pass. The helpers were scoped correctly and the disposable
startup window was lengthened while the child still blocks well beyond the
deadline. The final run passed the complete suite. No production code or
historical evidence was implicated by the initial fixture failures.

## Remaining readiness blockers

This package is not a readiness authorization. The correction does not create
numeric production seeds, resolve the historical outcome-exposure/influence
limitation, recover the absent V6 benchmark report, establish full-workload
runtime, close statistical-power questions, wire the supervisor into the
runner, or bind the new source into a final execution identity. The historical
V2 status remains CORRECTIONS_REQUIRED and no sampling is authorized.
