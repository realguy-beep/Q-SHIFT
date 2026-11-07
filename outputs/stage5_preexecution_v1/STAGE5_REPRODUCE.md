# Reproduction and Safe Readiness Checks

Run from the repository root with the installed project Python environment.

```powershell
python -m unittest outputs.stage5_preexecution_v1.tests.test_stage5_preflight -v
python -m outputs.stage5_preexecution_v1.stage5_preflight
python -m outputs.stage5_preexecution_v1.review_power
python -m outputs.stage5_preexecution_v1.freeze_stage5
python -m outputs.stage5_preexecution_v1.stage5_runner --preflight
```

These commands validate code, seed inventory, source/configuration hashes, circuit/DEM/graph structure, and deterministic non-sampled fixtures. They do not call Stim sampling. The `stage5_runner --preflight` check requires the pre-test freeze and never samples.

The saved-array auditor is a future read-only operation and will require all 500 final root files:

```powershell
python -m outputs.stage5_preexecution_v1.stage5_saved_array_audit outputs/stage5_preexecution_v1/run/roots --output outputs/stage5_preexecution_v1/run/INDEPENDENT_AUDIT.json
```

**Do not run sampling as part of pre-execution readiness.** The guarded command is documented for a later, separately authorized execution only:

```powershell
python -m outputs.stage5_preexecution_v1.stage5_runner --run --authorize-stage5-sampling
```

Normal readiness work has no need to run that command. No output from tests or preflight should be interpreted as Stage 5 performance evidence.
