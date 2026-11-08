# Stage 5 recovery-safety repair v3.4.4

**Scope:** Windows filesystem safety and recovery-copy integration only.
**Recommendation:** **NO-GO for authorizing the full Stage 5 recovery at this time.**
**Stage 5 recovery/sampling executed:** No.

## What changed

This revision integrates the previously isolated bounded-retry and archive-ledger routines into a copy-only recovery service and a separately gated continuation runner.

- `atomic_safety_v44.py` preserves exact pending payload bytes, journals each compare-and-swap write, retries only transient Windows replace errors 5/32/33 with bounded backoff, and rejects changed targets or ambiguous intents.
- `recovery_service_v44.py` verifies the 265-file forensic inventory, checks source ownership locks without rewriting source lock/owner files, copies only status plus committed root archives/sidecars into a new provenance-marked directory, reconstructs counters from archive phases, repairs only a uniquely journaled archive/marker transition, and finishes an `evaluation_complete` checkpoint using its saved arrays.
- `worker_recovery_v44.py` delegates scientific behavior to the unchanged frozen runner after saved-array reconciliation. Writes go through the v4.4 journaled CAS routines and remain inside the recovery copy.
- `recovery_runner_v44.py`, `audit_saved_run_v44.py`, and `finalize_v44.py` provide a recovery-copy-only path behind a separate explicit authorization flag. The runner rejects the original source path and the auditor now checks each archived calibration/evaluation seed against the frozen inventory.
- The finalizer includes the recovery provenance and journal hashes in its finalization manifest.

The 124th archive is root `p=0.000`, root index `123`, phase `evaluation_complete`. The forensic evidence says its 2,000 calibration rows and 2,500 paired evaluation rows are committed, while `p_hat` and decoder predictions are absent. The service's saved-array path recomputes `p_hat` from calibration detectors, decodes evaluation detectors, validates all three prediction arms, then atomically commits the completed archive. It receives no sampler and never passes observables to the estimator or decoder. The actual root was not opened or changed in this task.

## Validation

Windows 11, Python 3.12.10:

- v3.4.4 integration tests: **6/6 passed**. They use only deterministic NumPy benchmark fixtures and synthetic source inventories. They cover copy provenance, reconstruction from archive counts, saved `evaluation_complete` completion, idempotent replay, interrupted archive/sidecar commit recovery, root duplication rejection, tamper rejection, and refusal to write to the original source.
- v3.4.2 process-ownership regressions: **8/8 applicable tests passed**, including real Windows subprocess supervisor-death phases, live lock contention, child deadline, and benchmark crash recovery. The old ninth test was excluded in the audited runner because it asserts the historical failed-run directory is absent; that assertion contradicts the preservation requirement.
- Frozen v3.4.4 no-sampling preflight: **PASS**. It verified 53 Stage 5 frozen hashes, 14 inherited v3.4.2 safety hashes, 265 original-run inventory entries, source state `worker_failed`, and absent recovery destination.
- Independent audit: **PASS WITH DEVIATION**. It rechecked v3.4.4/v2/v3.3/v3.4.2 hashes, all 265 original files and 56 forensic entries before and after disposable tests, and confirmed that no Stage 5 recovery or sampling occurred.
- Existing v3.4.3 independent audit record: **PASS** (read-only in this audit). Its prior Windows suite covered persistent replace denial, bounded retry, CAS contention, crash points, duplicate roots, and saved-array recovery.

Exact commands and per-command output are recorded in `INDEPENDENT_AUDIT_V44.json` and `REPRODUCE_V44.md`.

## Integrity deviation discovered during this task

The full legacy command `python outputs/stage5_execution_safety_v3_4_2/run_tests_v4.py` was invoked before noticing that its test `test_frozen_hashes_and_stage5_boundary` requires the original Stage 5 run directory not to exist. Eight tests passed; that one environment-specific assertion failed because preserving the `worker_failed` run is mandatory. The legacy runner then rewrote its untracked `SAFETY_TEST_RESULTS_V4.json`.

The tracked v3.4.2 evidence manifest records the original raw-result SHA-256 as `d191d48d999bf169cbcaa5a9e42fb604e8241f387bee84e19c598402dc319a4c`; the current local raw-result file hashes to `3d0aa61720a2f7258da661d48163d02bdaba3cc3e22457c97799c69c30b3f64c`. The original bytes could not be recovered from the repository. The tracked summary and all 14 frozen v3.4.2 source/configuration hashes still match. This deviation is preserved and disclosed in the independent audit; the altered legacy raw-result file is not included in the v3.4.4 commit.

## Decision and limits

The core safety repair is implemented and the synthetic tests pass, but the overall recommendation remains **NO-GO** for the full 27.225-million-shot recovery. No production recovery copy was created; no actual checkpoint was decoded; no Stage 5 statistical result was computed; no Stage 5 shots were generated. Full-scale throughput, disk headroom, power-loss durability on Windows, and actual antivirus/ACL behavior remain unverified. The local v3.4.2 raw-result hash deviation also prevents an unqualified preservation claim.

The original `worker_failed` directory remains read-only and its 265 inventory files match their recorded hashes. Any future recovery requires separate owner authorization, restoration or disposition of the v3.4.2 raw-report discrepancy, and an additional full-size resource preflight.
