# Independent audit — Stage 5 recovery-safety v3.4.3

**Audit result: PASS for the bounded repair primitives and fixture evidence.** The original Stage 5 recovery remains unexecuted and is not authorized by this audit.

## Audit method

`independent_audit_v43.py` is a separate implementation that imports neither `atomic_safety_v43.py` nor `recovery_v43.py`. It independently recalculates SHA-256 values, checks the original preservation inventories, inspects the recovery module's syntax for sampler APIs and label inputs, screens fixture identifiers against the reserved Stage 5 inventory without emitting seed values, and launches the 14-test suite again as a subprocess. The audit JSON records the command, exit code, individual test outcomes, and hash results.

This is an independent scripted audit within the same workspace, not an external human or second-agent review. The code paths and claims were also reviewed directly against the frozen Stage 5 runner and v3.4.2 report.

## Code references reviewed

- `atomic_safety_v43.py:80–133` lock acquisition/release; `:167–202` retry and expected-hash checks; `:205–256` temp/journal/status write; `:259–290` intent replay; `:293–325` archive/sidecar commit; `:328–391` commit verification and interrupted-commit recovery.
- `recovery_v43.py:45–60` provenance gate; `:89–163` root/seed/schema/prediction validation; `:166–230` archive ledger; `:233–261` idempotent count reconstruction; `:264–277` safe status persistence; `:280–341` saved-array completion of an evaluation checkpoint; `:344–452` manifest-verified recovery copy.
- `test_recovery_v43.py:264–293` real status-lock contention; `:307–354` transient and persistent Windows replacement; `:357–396` crash-boundary and old-checkpoint/new-intent recovery; `:214–262` saved evaluation-only recovery and mutation guard; `:79–168` counter, duplicate, seed, sidecar, and prediction checks.
- `independent_audit_v43.py:124–209` freeze/hash-chain checks, no-sampler syntax audit, fixture seed screening, and isolated test rerun.

## Results by requirement

| Requirement | Result | Evidence |
|---|---|---|
| Preserve original run and forensic evidence | **PASS** | All 265/265 entries in `PRE_INVESTIGATION_SHA256.json` and all 56/56 entries in `FORENSIC_MANIFEST.json` match. Historical status remains `worker_failed`. |
| Preserve frozen protocol/source history | **PASS** | v2 53/53, v3.3 13/13, and v3.4.2 14/14 SHA-256 entries independently verified. No scientific source or freeze was changed. |
| Bounded Windows replace retry | **PASS** | A Windows handle that denies delete sharing reproduced replacement denial. One transient WinError 5 recovered within the bounded retries; persistent denial exhausted the retry budget while retaining the old target, exact pending temp, and intent. No permission or security bypass is used. |
| Status writer contention/newer state | **PASS** | Real subprocess holder prevented both competing status writers from entering; target hash remained unchanged. After release one write succeeded. A stale expected hash could not overwrite a newer state. |
| Checkpoint crash/write boundaries | **PASS** | Real subprocesses exited abruptly after temp fsync, intent fsync, archive replace before sidecar, and sidecar replace. Unjournaled temp was rejected; durable intent replay and sidecar reconstruction succeeded; already committed archive was verified. A second test recovered a newer pending checkpoint transition over an older valid checkpoint. |
| Archive-derived counters and duplicate prevention | **PASS** | Fixture archive phases yielded 12 calibration rows, 12 evaluation rows, 24 unique rows, and only one completed root. Repeating reconciliation preserved identical status. Noncanonical duplicate identity, unknown phase, seed collision, orphan temp, and unapplied intent fail closed. |
| Root 124 recovery behavior | **PASS in synthetic fixture; actual root untouched** | A small `evaluation_complete` fixture was completed using saved detector arrays only. The estimator saw calibration detectors; decoder and verifier saw evaluation detectors/predictions only. No sampler API exists. The completion was independently rescored, committed, and idempotent on retry. The actual root's 2,500 saved evaluation rows were not decoded or changed. |
| Separate recovery-copy provenance | **PASS in synthetic fixture; actual copy not made** | Copy validates every source-manifest hash, refuses an existing destination, records all source manifest hashes and copied-file hashes, excludes active ownership files, and leaves source bytes unchanged. Recovery mutations require the provenance marker and an in-directory checkpoint path. |
| No new Stage 5 samples or inference | **PASS** | The recovery module has no Stim import or sampling call; tests use disposable NumPy fixtures. Original hashes still match. No Stage 5 recovery, sampling, prediction decoding, or full-study statistics ran. |
| Independent audit | **PASS with scope limitation** | Audit reran all 14 tests successfully and verified hashes independently. It is not an outside reviewer; full v3.4.2 runner integration remains outstanding. |

## Specific interpretation of the 124th root

The existing forensic evidence establishes that root 123 at probability 0 has a committed `evaluation_complete` archive, containing 2,000 calibration rows and 2,500 evaluation detector/observable rows but no `p_hat` or predictions. It is not a completed decoder comparison. In v3.4.3, the archive ledger counts its saved evaluation rows but does not increment `completed_roots`. A future authorized recovery copy can calculate the frozen detector-only estimate and decode the saved detector batch through explicit callbacks; only a verified `complete` archive is counted as a completed comparison. No samples are regenerated by that function.

The real root was not passed to these callbacks. The recovery function was tested only on a small synthetic archive with unrelated, collision-screened fixture identifiers.

## Residual risks and blockers

1. The historical process holding `status.json` during WinError 5 is still unknown; v3.4.3 addresses the failure mode, not its historical cause.
2. The repair primitives are not integrated into the frozen worker, supervisor, saved-array auditor, two-hour deadline supervisor, aggregate-statistics step, or finalizer. Therefore this PASS does not make the 6,050-root recovery operationally ready.
3. Windows file contents are fsynced, but portable Python directory-entry durability across abrupt power loss is not demonstrated.
4. The recovery-copy test uses a small synthetic manifest. The real 265-entry source has been read-only hash verified but was not copied, reconciled, or modified.
5. Full-scale disk, memory, and two-hour wall-clock behavior was not tested.
6. No external human/second-agent review was available in this execution; the independent audit is code-separated and rerunnable but shares the same workspace.

**Recommendation: NO-GO for authorizing Stage 5 recovery with the current v3.4.3 primitives.** Complete and independently audit a separately versioned integration with the frozen worker/supervisor/auditor/finalizer and full recovery-copy preflight first. The statistical protocol and Stage 5 seed allocation remain untouched. A new explicit recovery authorization is still required after that work.

Machine-readable detail: `INDEPENDENT_AUDIT_V43.json`. Test detail: `TEST_RESULTS_V43.json`.
