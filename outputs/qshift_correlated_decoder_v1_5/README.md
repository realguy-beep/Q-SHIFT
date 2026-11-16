# Q-SHIFT correlated decoder V1.5

V1.5 is a fresh-seed evaluation of the exact DEM logical-class decoder (V1.4B candidate B) against the best V1.3 decoder and the strongest static matcher. It is development-only. Read `EXPERIMENT_PROTOCOL.md`.

## Status

Frozen and ready; **not executed**. Zero V1.5 sampler calls. Execution requires the owner's separate sign-off.

## Sampler-free verification

Run from the repository root. `<V1>` is the V1 worktree, and `<V1.2 run>` is V1.2's local `pilot_runs/attempt_001`, which serves as the timing fixture.

```powershell
py -3.12 -m unittest discover -s outputs/qshift_correlated_decoder_v1_5/tests -v
py -3.12 outputs/qshift_correlated_decoder_v1_5/run_eval.py --dry-run --expected-head <FROZEN_SHA> --v1-repo <V1>
```

These records were generated once and are frozen:
- `seed_inventory.json`, from `prepare_seeds.py`;
- `PREFLIGHT.json`, from `preflight.py --v1-repo <V1> --v1-2-run <V1.2 run>`;
- `PRETEST_FREEZE.json`, from `freeze_pretest.py`.

## Single evaluation (only after owner sign-off)

```powershell
py -3.12 outputs/qshift_correlated_decoder_v1_5/run_watchdog.py --execute --expected-head <FROZEN_SHA> --v1-repo <V1>
py -3.12 outputs/qshift_correlated_decoder_v1_5/recount_from_scratch.py outputs/qshift_correlated_decoder_v1_5/pilot_runs/attempt_001
py -3.12 outputs/qshift_correlated_decoder_v1_5/posthoc_reference.py outputs/qshift_correlated_decoder_v1_5/pilot_runs/attempt_001 outputs/qshift_correlated_decoder_v1_5/results_v1
```
