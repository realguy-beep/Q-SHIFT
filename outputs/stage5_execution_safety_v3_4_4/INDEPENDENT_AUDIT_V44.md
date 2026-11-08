# Independent audit — Stage 5 recovery-safety v3.4.4

**Result: PASS WITH DEVIATION for the new recovery-copy code; NO-GO for full recovery authorization.**

## Checks

| Area | Result | Evidence |
|---|---|---|
| v3.4.4 source/config freeze | PASS | 12/12 frozen source hashes matched `SAFETY_FREEZE_V44.json`. |
| Stage 5 frozen protocol | PASS | 53/53 hashes matched; Endpoint B and all scientific parameters remain unmodified. |
| v3.3 and v3.4.2 inherited safety sources | PASS | 13/13 and 14/14 hashes matched. |
| Original failed-run evidence | PASS | 265/265 entries matched before and after audit execution. No source files were written. |
| Forensic evidence | PASS | 56/56 manifest entries matched before and after execution. |
| Recovery-copy code tests | PASS | 6/6 tests passed on synthetic arrays. A saved evaluation-complete fixture was finished with zero new samples and repeated idempotently. |
| Process/ownership failure injection | PASS | 8/8 applicable v3.4.2 Windows subprocess regressions passed. The omitted test asserts the original failed-run directory is absent, which is not valid for this project state. |
| No-sampling preflight | PASS | `worker_failed` source state confirmed; the dedicated recovery directory was absent; no recovery or sampling call was made. |
| Legacy v3.4.2 raw test-result artifact | **FAIL / local deviation** | The old result file hash in its evidence manifest no longer matches; see below. |
| Full production recovery | NOT RUN | Explicitly prohibited in this task and remains separately gated. |

## Integrity deviation

The legacy full test command was run once. Its only failing test expects the real failed-run directory not to exist. The runner also rewrote the untracked v3.4.2 `SAFETY_TEST_RESULTS_V4.json` before this was recognized. The original hash recorded by `SAFETY_EVIDENCE_MANIFEST_V4_2.json` is `d191d48d999bf169cbcaa5a9e42fb604e8241f387bee84e19c598402dc319a4c`; current local hash is `3d0aa61720a2f7258da661d48163d02bdaba3cc3e22457c97799c69c30b3f64c`. The original bytes were not recoverable. The file was not staged or committed; the tracked summary and frozen source hashes remain valid.

The audit script does not import `recovery_service_v44.py`, `recovery_core_v44.py`, or `atomic_safety_v44.py`. It independently recomputes manifest hashes, then launches the fixture suite, the applicable Windows process regressions, and the read-only preflight as separate processes. Detailed child output is saved in `INDEPENDENT_AUDIT_V44.json`.

## Recommendation

Do not authorize the full Stage 5 recovery yet. The new recovery-copy mechanics pass bounded fixture tests, but they have not been exercised against a production recovery copy or at full scale, and the local legacy raw-report discrepancy remains unresolved. No endpoint statistics were calculated and the incomplete 124th root remains incomplete in the original run.
