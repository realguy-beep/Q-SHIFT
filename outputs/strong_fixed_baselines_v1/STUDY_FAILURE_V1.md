# Study failure record v1

## Event

The first authorized development run was started with:

```powershell
python -B outputs/strong_fixed_baselines_v1/run_development.py
```

It exited during the selection phase with `IndexError: list index out of range` at the selection aggregation in `run_development.py`. The failure occurred after all selection and template sampling had been committed, before safety-constrained selection completed, and before validation, held-out-development calibration, or final paired evaluation.

## Confirmed cause

`score_grid_dataset` had used the five generating-condition probabilities to drive the candidate decoder loop. The frozen decoder bank contains nine candidates (`0.000` through `0.016` in `0.002` increments). The runner therefore stored five prediction rows per selection archive and later indexed them as a nine-candidate array. This is an implementation defect, not evidence of a decoder outcome.

## Preserved run state

The original directory `run/` remains unchanged and marked `failed`. Its persisted status says the failure occurred at probability `0.016`, root `19`, with zero final-evaluation shots. Its status counters are stale and report zero sampled partition shots; the independently hash-verified archive audit instead reconstructs 510,000 unique study shots: 60,000 template shots, 200,000 selection-calibration shots, and 250,000 selection-scoring shots.

The run contains 303 NPZ archives: 3 templates, 100 calibration arrays, 100 scoring arrays, and 100 five-row prediction arrays. All 203 raw input archives and commit markers passed hash, seed, shape, and metadata checks. The 100 five-row prediction archives match independent decoding for their five stored rows, but they are invalid for the intended nine-candidate selection analysis and are not reused as valid candidate predictions. The invalid `selection_scores.json`, bad prediction archives, status, logs, and source remain in the original failed directory.

The independent partial audit is `partial_failure_audit/FAILED_RUN_PARTIAL_AUDIT.json` and records the original file hashes. No final-development evaluation archive exists; final-evaluation shots are zero. No Stage 5 or sealed-test data were accessed.

## Recovery boundary

The corrected runner is frozen prospectively in `PRETEST_FREEZE_V7.json`. Continuation is directed to a separate `run_recovery_v2/` directory. Only the 203 independently verified raw input archives (templates, selection calibration, selection scoring) and their commit markers may be copied. Candidate predictions and aggregate scores must be regenerated from the copied scoring detector arrays using all nine candidates. The copied 510,000 shots count once by stream identity; copying is not sampling. Any mismatch, ambiguous target state, lock, or archive/hash discrepancy must fail closed.

No recovery sampling may begin before V7 freeze verification and successful recovery-copy validation. The original failed run is never resumed or rewritten.

## Recovery-copy preflight correction

The first copy-only preflight failed closed before copying any file because the copier normalized audit path keys to `/`, while the Windows audit stored native `\\` separators. Subsequent invocations verified and copied all 203 raw input archives, then failed while looking up the status hash: the audit intentionally stores `status.json` as a short key, unlike archive paths. The copied archives remain hash-identical; no new samples were generated. After V10 fixed that provenance lookup, the corrected runner produced nine-candidate selection prediction archives and then failed while slicing a Python `map` object in selection aggregation (`TypeError: 'map' object is not subscriptable`). No validation or final evaluation streams were sampled and no baseline was selected. The V10 recovery directory remains failed and preserved. Its provenance metadata also names V7 as active even though the copy was made under V10; this label is retained unchanged as a historical metadata deviation. V11 fixes positive-condition iteration and adds a regression test. V12 corrects the active-freeze label for a fresh recovery copy; it does not rewrite the V10 metadata. Unexpected files, incomplete archive/marker pairs, or mismatching hashes still fail closed. The original run and partial audit remain unchanged.

The V12 continuation then failed at a Windows `os.replace` of `status.json` with `PermissionError [WinError 5]`. The runner's failure-status write hit the same denial, leaving the last persisted status as `running`; the process exited, removed its run lock, and left the committed sample archives intact. It had completed all 100 selection roots, all 100 validation roots, and 355 of 600 final calibration archives (710,000 final-calibration shots). No final evaluation archive was generated. This is an observed filesystem replacement failure; antivirus/file-indexer interference or sharing contention are hypotheses, not confirmed causes. V13 adds bounded retry for `PermissionError` to the existing atomic replace operation, without deleting the target or falling back to a non-atomic write. Tests inject both transient and persistent denials.

The next V13 attempt independently audited and re-decoded 4,500,000 selection/validation candidate prediction bits, verified 958 committed archives representing 1,670,000 unique sample shots, and copied them to `run_recovery_v4/`. That run stopped before sampling because immutable JSON resume comparison treated numeric dictionary keys as floats in memory and strings on disk. V14 canonicalizes the proposed JSON record before comparison and adds a regression test. The failed V4 directory is retained; it contains a verified copy of the 1.67M-shot prefix and no new sampling. The next run will use a new target directory and copy only from the V3 audited source.
