# Stage 5 Recovery Safety v3.4.3 — Prospective Operational Protocol

## Scope and boundary

This is a separately versioned filesystem and recovery-safety implementation based on commit `8c06750808582137f6a81e2170ad702a552594fb`. It does not replace or edit v3.4.2, the frozen Stage 5 protocol, its seed allocation, decoder settings, Endpoint B, the zero-noise no-harm gate, or secondary inference rules. It does not authorize recovery or sampling. All executable tests use temporary synthetic NumPy fixtures and benchmark-only seed identifiers.

The failed production directory remains the immutable source of the forensic record. A future recovery must first verify every file in the supplied source inventory, create a previously absent destination outside the original run, copy only the status and committed root archives/sidecars, omit active ownership files, and record source inventory and per-file hashes in `RECOVERY_PROVENANCE.json`. Mutating recovery APIs refuse directories without this provenance marker.

## Windows replacement and persistence

`atomic_safety_v43.py` uses a per-target OS file lock, an expected-old SHA-256 compare-and-swap, a fsynced temporary file, and a small write-intent journal containing the target/temp paths and payload hash. The temporary file contains the exact intended bytes. Windows errors 5, 32, and 33 receive at most six attempts with a fixed bounded backoff; all time spent consumes the caller's monotonic deadline. Persistent failure leaves the old destination untouched and preserves the temp and journal. The code neither changes permissions nor disables sharing checks.

Recovery may replay one unambiguous pending intent only if the target still has the exact expected-old hash and the pending temp has the intended hash. If the temp is absent, altered, or a newer/unknown target exists, recovery fails closed. Multiple pending intents are ambiguous and rejected. The applied marker makes replay idempotent. NPZ archives and their commit sidecars are separate compare-and-swap writes; a sidecar is accepted only when it names the exact archive SHA-256.

## Archive-derived state

`recovery_v43.py` reconstructs counters as assignments from a ledger of committed and validated archives. It checks canonical condition/root filenames, explicit expected calibration/evaluation seed mappings, seed uniqueness, checkpoint phase, exact array schemas and dimensions, binary labels/detectors/predictions, and commit-sidecar hashes. A `calibration_complete` archive contributes calibration rows. An `evaluation_complete` archive contributes both saved streams but is not a completed decoder comparison. Only a `complete` archive with independently recomputed predictions increments `completed_roots`.

An in-flight calibration or evaluation stream without the matching durable checkpoint blocks reconstruction. Orphan v3.4.3 temp files and unapplied write intents also block counting until resolved. Status fields are replaced from ledger totals and never incremented from stale counters. Applying the same ledger twice produces the same counters and reconciliation record.

## In-flight evaluation-complete root

The bounded `complete_evaluation_checkpoint` function has no sampler argument. It accepts a detector-only estimator that receives only saved calibration detector rows, and decoder callbacks that receive the resulting estimate and saved evaluation detector rows. Observable labels are preserved in the archive but are not passed to the estimator, decoder, or prediction verifier. Predictions are independently verified before the result archive is committed and read back. The function reports zero additional samples and reuses the saved calibration/evaluation row counts.

The real 124th archive was read only for metadata/schema confirmation during implementation; no recovery function was invoked on it. The implementation tests use a small synthetic `evaluation_complete` archive with unrelated benchmark identifiers. It does not import or call Stim's sampler, the Stage 5 runner, or Stage 5 statistical analysis.

## Test plan and measured status

The Windows suite uses disposable temporary directories and real child processes. It covers status write-lock contention, compare-and-swap protection against newer state, transient WinError 5 retry, persistent `CreateFileW` denial without payload loss, crashes before and after durable write intent, crash after archive replacement before sidecar, crash after sidecar replacement, recovery from an `evaluation_complete` checkpoint, duplicate/noncanonical root rejection, copy provenance/source immutability, idempotent counters, unresolved sampler/checkpoint fail-closed behavior, and rejection of mutation in an unmarked original directory.

Commands and observed outcomes are recorded in `REPRODUCE_V43.md`, `TEST_RESULTS_V43.json`, and `INDEPENDENT_AUDIT_V43.md` after the final test run.

## Platform and integration limits

- Windows file contents are flushed with `fsync`; portable Python does not provide directory-entry `fsync` here, so sudden power-loss durability is not proven.
- Replacement errors are retried; failures while creating the temp or journal fail immediately and preserve the original target.
- The historical trigger for WinError 5 remains unknown; an incompatible sharing handle reproduced the mechanism but did not identify the original process.
- This is a separately versioned recovery primitive set, not an integrated replacement for the v3.4.2 worker/supervisor/auditor/finalizer. No full 6,050-root workflow, two-hour recovery deadline, full-study audit/finalization, or full-scale resource behavior is certified by these bounded tests.
- A future recovery still requires a separate explicit authorization. This work did not execute it.
