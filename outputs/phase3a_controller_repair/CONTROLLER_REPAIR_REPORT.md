# Q-SHIFT Controller Repair Report

## Historical diagnosis

The original Phase 4C Stage 2 runner and verifier were inspected but left unchanged. In the hybrid residual sprint, `run_sprint.py` writes `RESULTS.json`, then calls `verify_results.py` (runner lines 1245–1265), and only after the verifier returns does it write `PROGRESS.status="completed"` (line 1265). The frozen verifier checks `PROGRESS.status == "completed"` near its start (line 104). At invocation time the persisted state was still `sampling`, so the verifier raised `AssertionError: Run is not complete: sampling`. The runner then recorded `failed`. This is a finalization-order defect; it is not evidence of a sampling or training failure.

The original sprint remains `failed`, with 30/30 jobs and all expected development artifacts. The existing independent read-only audit remains in `outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/post_run_audit/`; its 292 manifest entries rechecked without mismatch. No historical run status, source, checkpoint, prediction archive, report, or dataset was changed in this phase.

The earlier 750K autonomous development run remains recorded `completed` with 50/50 jobs, five roots, and `independent_test_access=0`. Its 377 run-manifest entries were checked: 376 match; the only discrepancy is `run/controller.stdout.log`, whose manifest hash is the empty-file hash while its current 2,745-byte contents reproduce the completed status JSON with test access 0. This is classified as a post-manifest status stdout artifact. There are no unexplained model, sample, prediction, or checkpoint hash mismatches. The exact hashes and classification are in the Phase 3A preflight record.

## Versioned future-run repair

`finalization_v1.py` is an independent, versioned finalization helper. It does not patch or import either historical runner. Its intended future use is:

1. Freeze the complete expected evidence-file inventory after sampling ends.
2. Atomically write progress state `finalizing` and a SHA-256/byte-count snapshot.
3. Run an independent scientific verifier while status is `finalizing`; the verifier must test data, predictions, aggregates, seeds, and partitions, not require terminal status `completed`.
4. Rehash evidence after verification to detect concurrent writes or corruption.
5. Atomically write the complete evidence manifest, read it back, and verify every entry.
6. Atomically mark progress `completed` only after all checks pass.

The helper resumes an interrupted `finalizing` state only when its stored evidence snapshot exists and every file still matches. If a manifest was already atomically committed, it validates and reuses it. Repeated calls against a completed run validate its manifest and evidence again. Changed files, missing files, malformed manifests, and path traversal fail closed. Writes use a same-directory temporary file, flush plus `fsync`, and `os.replace`.

The caller must enumerate all artifacts that comprise the run; the manifest intentionally does not hash itself. A verifier must be independent of the terminal success flag, but no scientific assertion is removed. The historical verifier's status assertion is preserved as part of the historical source; future verifiers should separate scientific validation from lifecycle-state validation.

## Regression checks

Run:

```powershell
python -m unittest discover -s outputs/phase3a_controller_repair/tests -v
```

Tests cover: verifier invocation during `finalizing`, successful atomic completion and idempotent repeat, recovery from an interrupted finalizing state, fail-closed detection of changed evidence during verification or after interruption, post-completion manifest corruption, missing evidence, and path escape rejection. Results are reported in `PHASE3A_FINAL_REPORT.md`.

## Recovery recommendation

Do not resume or relaunch either historical experiment. The hybrid sprint's scientific evaluation is complete and independently audited, but its operational status must remain `failed`; the absent runner-generated checkpoint manifest should not be fabricated in the historical directory. The separate post-run audit manifest already inventories and hashes the saved evidence. For future runs, use the new finalization helper only after a new runner has been explicitly wired and frozen to call it.
