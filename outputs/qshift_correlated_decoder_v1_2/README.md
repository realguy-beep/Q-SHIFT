# Q-SHIFT correlated decoder V1.2

V1.2 is a strong-static-baseline evaluation of the V1.1 five-factor decoder. It is development-only and exploratory. Read `EXPERIMENT_PROTOCOL.md` for the design, the decision rule and the evidence boundaries.

## Status

Frozen and ready; **not executed**. Zero V1.2 sampler calls so far. Execution requires the owner's separate sign-off.

## Sampler-free verification

Run from the repository root with Python 3.12.10 and the versions in `config.json`. `<V1>` is the V1 worktree (`qshift-correlated-decoder-feasibility-v1`). `<V1.1 run>` is V1.1's `pilot_runs/attempt_001`; it is local and git-ignored, and is opened read-only.

```powershell
py -3.12 -m unittest discover -s outputs/qshift_correlated_decoder_v1_2/tests -v
py -3.12 outputs/qshift_correlated_decoder_v1_2/rehearsal.py --v1-repo <V1>
py -3.12 outputs/qshift_correlated_decoder_v1_2/run_eval.py --dry-run --expected-head <FROZEN_SHA> --v1-repo <V1>
```

These records were generated once and are frozen; do not regenerate them:
- `prepare_seeds.py` produced `seed_inventory.json` (a test checks it is reproducible).
- `select_static.py --v1-1-run <V1.1 run>` produced `STATIC_SELECTION.json`. It refuses to overwrite an existing selection.
- `preflight.py --v1-repo <V1> --v1-1-run <V1.1 run>` produced `PREFLIGHT.json`.
- `freeze_pretest.py` produced `PRETEST_FREEZE.json`.

## Single evaluation (only after owner sign-off)

```powershell
py -3.12 outputs/qshift_correlated_decoder_v1_2/run_watchdog.py --execute --expected-head <FROZEN_SHA> --v1-repo <V1>
```

This runs the one bounded evaluation of 324,000 new shots in 144 sampler calls, with an 1,800 s cap. It refuses an existing attempt and never resumes or retries. Raw archives go to `pilot_runs/`, which is git-ignored and kept locally.

## Files

| File | Role |
|---|---|
| `contract.py` | Every name shared by runner and analyzer (arms, keys, states, allocation) |
| `multi_prior.py` | Exact shared-residual evaluation of the frozen five-factor decoder at several priors |
| `select_static.py`, `STATIC_SELECTION.json` | Static q selection on V1.1 arrays (Astar 0.005, Bstatic 0.0025) |
| `run_eval.py`, `run_watchdog.py` | Gated runner (`run_pipeline` is shared with the rehearsal) and Windows watchdog |
| `analyze_saved.py` | Independent analyzer; imports no runner code; validates before writing |
| `rehearsal.py` | Fake-sampler end-to-end rehearsal (not evidence) |
| `preflight.py`, `PREFLIGHT.json` | Sampler-free gate checks and runtime projection |
| `DESIGN_PLAN_DRAFT.md` | Approved planning record; superseded by the protocol |
