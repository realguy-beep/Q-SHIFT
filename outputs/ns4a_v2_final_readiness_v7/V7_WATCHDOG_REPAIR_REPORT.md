# Q-SHIFT V7 Watchdog Repair and Validation

## Scope and preservation

This is a separately versioned watchdog engineering package based on repository HEAD `5f0446633091b9671a86341958f4ee5384d9ab55` (branch `codex/ns4a-v2-win-memory-recovery-v6`). It does not edit or call the V6 benchmark launcher, Stim, PyMatching, or any scientific sampling path. The V6 run was not restarted. No PR was merged, no commit was created, and no Stage 5 or sealed outcome was accessed.

The original watchdog remains at `%LOCALAPPDATA%\Temp\qshift_v6_watchdog_81f724ac8bc0497caa703443add07c21\job_watchdog.py`, SHA-256 `8037BB786C789E474C42847513DD5C5C0A69735850632CA1DA4E03C3A7506211`. Its V6 status is preserved as `orphaned_child_failure`; this repair does not revise that historical classification or establish the identity of its residual process.

## Repair

V6 queried `JobObjectBasicAccountingInformation.ActiveProcesses` once after the root process exited and immediately classified any nonzero result as an orphan. V7 instead polls the Job Object PID list (information class `JobObjectBasicProcessIdList`, class value 3) and active count through a default 250 ms grace period. A run is drained only when both are zero. Each observed member is checked with a process handle for Job membership, creation time, liveness, exit code, executable path, and parent PID when available. PID creation-time changes, stale PID observations, inaccessible persistent members, API failures, and inconsistent counts fail closed.

At grace expiry, a confirmed live descendant or unclassified persistent member triggers Job termination. The result remains a failure even if termination drains the Job. Kill-on-close is retained as a final cleanup guarantee. A suspended process that cannot be assigned to the Job is terminated directly by its process handle; it is never resumed first. The overall timer starts before Job creation, accepts at most 600 seconds, and caps the post-root grace and cleanup polling. Status records retain per-poll PID and metadata observations.

The implementation uses explicit `ctypes.WinDLL("kernel32", use_last_error=True)` signatures. `PROCESS_MEMORY_COUNTERS` APIs are not involved. The Job PID-list buffer is dynamically enlarged and `ULONG_PTR` entries use pointer-width storage. The tested Windows 11 x64 structure sizes were: Job basic accounting 48 bytes, extended limit information 144 bytes, and `PROCESSENTRY32W` 568 bytes.

### Exact change from V6

| Area | V6 | V7 |
|---|---|---|
| Post-root observation | One active-process count | Repeated active count plus Job PID list |
| Drain rule | Any nonzero count immediately fails | Requires count and PID list both reach zero during grace |
| Process evidence | No remaining PIDs or identities | PID, creation FILETIME, Job membership, wait state, exit code, image path and parent PID where available |
| Grace/deadline | No grace | Default 250 ms, never beyond 600-second deadline |
| Persistent member | Immediate terminate and orphan status | Live vs inaccessible/unclassified/stale distinction, terminate after grace; forced termination remains failure |
| Setup failure | Assignment failure could leave suspended root outside Job | Direct process-handle termination for an unassigned suspended root |
| Child output | Redirected to run log | Optional append-only stdout/stderr log; CLI requires `--log` |
| Tests | Synthetic no-child cases reproduced false positive | Deterministic state fixtures plus real Python-only Windows subprocess fixtures |

The complete line-by-line unified diff against the preserved original is in [V6_TO_V7_WATCHDOG.diff](V6_TO_V7_WATCHDOG.diff); the original source hash is embedded in the diff header.

## Validation

Environment: Python 3.12.10, Windows 11 x64, 64-bit process handles. Commands run from repository root:

```powershell
python -m py_compile outputs/ns4a_v2_final_readiness_v7/job_watchdog_v7.py outputs/ns4a_v2_final_readiness_v7/test_job_watchdog_v7.py
python outputs/ns4a_v2_final_readiness_v7/test_job_watchdog_v7.py
```

Result: **19 tests passed** in the final run (approximately 1.6 seconds). The tests start only short Python `-c` fixtures or use deterministic fake Job API responses; they do not import the benchmark runner or Stim. They cover immediate exit, a normal short process, child stdout/stderr logging, a parent waiting for a brief child, a child that exits during grace, a persistent child, a deterministic console-host teardown model, inaccessible metadata, PID reuse/stale PID, Job query failure, grace deadline expiry, forced termination with successful cleanup still classified as failure, kill-on-close, assignment failure, timeout-cap enforcement, Win32 structure layout, and unsupported-OS rejection.

The first run after adding child logging had one test error because the kill-on-close fixture still called the revised backend with the old argument count. The fixture was corrected to pass an explicit `None` log path; the final run above passed all 19 tests.

The transient `conhost.exe` case is a deterministic modeled fixture, not a fresh experiment with Windows console-host behavior. Earlier forensic-only synthetic probes observed transient Job membership for a conhost-like process; they did not identify the actual V6 residual.

### Observed synthetic status examples

The saved [synthetic status examples](SYNTHETIC_STATUS_EXAMPLES.json) were produced by fresh Python-only processes:

```json
{"state":"completed","drain":"zero_active_and_zero_job_pids","root_exit_code":0,"kill_on_job_close":true}
{"state":"persistent_live_descendant_terminated","root_exit_code":0,"termination_requested":true,"job_drained_after_termination":true,"root_exit_code_not_reclassified_as_success":true}
```

## Resource enforcement and limits

- **600 seconds:** V7 enforces a monotonic deadline across root execution and post-root drain, and rejects configured values above 600 seconds. The grace cannot extend this deadline.
- **Process-tree ownership:** the root is created suspended, assigned before resume, and the Job uses `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Persistent or uncertain Job members trigger termination.
- **1 GiB working set:** V7 does not claim a hard process-tree memory cap. The existing V6 benchmark checks the runner's reported OS peak working set; this is not Job-level aggregate memory enforcement.
- **128 MiB output and 1 GiB free disk:** these remain V6 runner-level checks. V7 does not replace or weaken them.

Synchronous Win32 API calls and filesystem status writes cannot be asynchronously interrupted by this Python loop. If an OS call or status write itself blocks indefinitely, monotonic polling cannot provide a strict hard real-time bound; an external supervisor remains necessary for that failure mode. Parent PID and image-path fields are diagnostic metadata, not proof of ancestry on their own. Job membership plus process-handle checks drive the decision.

## Independent second-pass review

A separate implementation review inspected the API declarations and structures in `job_watchdog_v7.py` (`WindowsJobBackend` around lines 158–420), PID enumeration and metadata around lines 326–419, drain and termination logic around lines 421–468, and orchestration/deadline logic around lines 469–604. The test review checked the injected-failure cases and real subprocess fixtures in `test_job_watchdog_v7.py` around lines 20–290.

Review findings: **PASS for the targeted post-exit false-positive repair and tested Windows x64 fixtures.** PID reuse and inaccessible metadata do not become success while membership persists; natural drain is required for success; forced termination is never promoted to success; Job close retains kill-on-close; inherited child log handles are closed in the watchdog after resume. The review is an independent second pass by the same engineering agent, not an external reviewer or separate auditor.

Residual limitations: V7 has not been integrated into or authorized to launch a benchmark; the original V6 residual PID remains unknown; the console-host teardown path is modeled rather than reproduced in this V7 test run; and resource caps other than the wall-clock deadline remain enforced by the existing runner/checkpoint logic, not by this watchdog as aggregate Job limits.

## V6 evidence integrity

The original watchdog hash still matches the recorded V6 digest above. The following V6 watchdog evidence hashes also match the previously recorded values: status `E07ECAC82B5DE139084BFAC303984EB375816464CA673518893DB1E560221D66`, stdout `7B2892B8CD4393639143A2409D5604C42F02787C35EEE079498C2AB7A9226136`, empty stderr `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`, and benchmark console log `7B274F992791BF608EF7DDE9B5E9DF6803900BBC4E4A7AFAB95B2CA832632160`.

A read-only sorted path-and-file-hash inventory of the existing `outputs/ns4a_v2_final_readiness_v6/` tree covered 34 files / 162,841 bytes and produced aggregate inventory SHA-256 `E67011491D1EA3F8D4C63856EBC947134F95785A22B15623CE97C8FD8D6DB6DD`. V7 writes were confined to `outputs/ns4a_v2_final_readiness_v7/`; the pre-existing V5/V6 untracked authorization and V6 run-output paths remain present and untouched. The V6 status remains `orphaned_child_failure`.

For Git publication, `core.autocrlf=true` and the repository's text attributes normalize CRLF in the synthetic JSON and unified diff when staged. The pre-stage V7 manifest SHA-256 was `CB1FF790E10444E52A4ECBA1A4D002CA576CC807377C502803F30BB6D97BC9E7`. The staged manifest revision records both the original working-file SHA-256 and the corresponding Git-blob SHA-256 for each artifact; this distinguishes harmless line-ending normalization from content changes and allows post-stage verification. No V6 file or watchdog source was normalized or changed.

## Final disposition

**V7 targeted watchdog engineering validation: PASS.** The one-count false-positive rule is replaced by a bounded Job PID-list drain check with conservative failure handling. This does not authorize V6 rerun, benchmark execution, or the scientific pilot. No Stim sampler was called; **zero additional Stim shots** were generated.
