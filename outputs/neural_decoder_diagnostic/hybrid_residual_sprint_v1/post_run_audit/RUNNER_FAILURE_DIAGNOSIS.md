# Runner Failure Diagnosis — Hybrid Residual Sprint v1

## Observed terminal state

The controller's persisted `run/PROGRESS.json` says `failed`, with `current_phase=final_evaluation`, all **30/30 jobs** committed, all five roots trained, and **1,665,000/1,665,000** planned production shots attempted and committed. PID 11656 is no longer running; no `sprint.lock` remains. `run/ERROR.json` contains the complete traceback. `run/CHECKPOINT_MANIFEST.json` is absent.

## Root cause

`run_sprint.py` invokes `verify_results.py` at finalization before it writes the final `PROGRESS.status="completed"`. The verifier's first gate requires exactly that status and raises `AssertionError: Run is not complete: sampling`. The runner wraps the nonzero verifier exit as `RuntimeError("Independent evidence verifier failed ...")` and marks the controller `failed`. This is a lifecycle/finalization ordering defect, not a sampling, training, checkpoint, prediction, or paired-metric failure.

The immutable historical runner verifier also had a separate configuration-key issue discovered during the read-only verification attempt: it referred to `monitor_per_regime_root`, `calibration_per_regime_root`, and `threshold_selection_per_regime_root`, while the frozen configuration uses the corresponding `*_shots_per_regime_root` keys. The audit used a separate copy under `post_run_audit/` with only the finalization-status precondition and these config-key names corrected. The frozen source was not edited.

## Evidence and safe recovery

The saved-evidence inventory passed: 30 checkpoint sets, 30 prediction archives, 135 paired rows, all expected data partition hashes/seed maps, selections, optimizer states, and frozen source hashes. A separate verifier re-decoded the 30 saved PyMatching predictions, recomputed CNN outputs from selected weights, and matched every candidate aggregate and root statistic. It passed with **225,000 final development shots** and `independent_test_access=0`.

An initial post-run audit serializer incorrectly reported 333,000 in one field by dividing all 1,665,000 production shots by five roots. That arithmetic was invalid for the final evaluation partition. The audit-only serializer has been corrected and rerun; the validated count is **15,000 × 5 roots × 3 regimes = 225,000**, now consistent in both fields. No run data or frozen files were changed.

## Recommendation

Do not relaunch/resume the experiment. The scientific calculations are complete and evidence-audited, while the controller's historical status remains failed. Any code repair for future experiments should ensure the verifier accepts a well-defined `finalizing` state (or verifies candidate results before the completed-status commit), fix the config key names, and only then atomically write completion status and the checkpoint manifest. Do not retrofit the original run to say the controller completed.
