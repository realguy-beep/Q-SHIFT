# Q-SHIFT correlated decoder V1.3

V1.3 is a development-only evaluation of the cost-consistent five-factor decoder (residual matching with correlations OFF). It is compared against the strongest static matcher and a mode-switching adaptive matcher. Read `EXPERIMENT_PROTOCOL.md` for the design, the decision rule and the evidence boundaries.

## Status

Frozen and ready; **not executed**. Zero V1.3 sampler calls so far. Execution requires the owner's separate sign-off.

## Sampler-free verification

Run from the repository root with Python 3.12.10 and the versions in `config.json`. `<V1>` is the V1 worktree (`qshift-correlated-decoder-feasibility-v1`), and `<V1.2 run>` is V1.2's local, git-ignored `pilot_runs/attempt_001`.

```powershell
py -3.12 -m unittest discover -s outputs/qshift_correlated_decoder_v1_3/tests -v
py -3.12 outputs/qshift_correlated_decoder_v1_3/rehearsal.py --v1-repo <V1>
py -3.12 outputs/qshift_correlated_decoder_v1_3/run_eval.py --dry-run --expected-head <FROZEN_SHA> --v1-repo <V1>
```

These records were generated once and are frozen; do not regenerate them:
- `seed_inventory.json`, from `prepare_seeds.py`.
- `STATIC_SELECTION.json`, from `select_static.py --v1-2-run <V1.2 run>`, which refuses to overwrite.
- `PREFLIGHT.json`, from `preflight.py --v1-repo <V1> --v1-2-run <V1.2 run>`.
- `PRETEST_FREEZE.json`, from `freeze_pretest.py`.

## Single evaluation (only after owner sign-off)

```powershell
py -3.12 outputs/qshift_correlated_decoder_v1_3/run_watchdog.py --execute --expected-head <FROZEN_SHA> --v1-repo <V1>
py -3.12 outputs/qshift_correlated_decoder_v1_3/recount_from_scratch.py outputs/qshift_correlated_decoder_v1_3/pilot_runs/attempt_001
```

This runs 324,000 new shots in 144 sampler calls, with a 3,000 s cap. It refuses an existing attempt and never resumes or retries. Raw archives stay local in `pilot_runs/`, which is git-ignored.

## Files

| File | Role |
|---|---|
| `contract.py` | Every shared name (arms, keys, comparators, allocation) |
| `multi_prior.py` | Mode-aware exact five-factor decoder (ON = frozen; OFF = cost-consistent) |
| `select_static.py`, `STATIC_SELECTION.json` | Baseline selection on V1.2 arrays |
| `run_eval.py`, `run_watchdog.py` | Gated runner (shared `run_pipeline`) and Windows watchdog |
| `analyze_saved.py` | Independent analyzer; validates before writing; supports re-analysis |
| `rehearsal.py` | Fake-sampler end-to-end rehearsal (not evidence) |
| `recount_from_scratch.py` | Post-run NumPy-only recount, frozen in advance |
| `preflight.py`, `PREFLIGHT.json` | Sampler-free gates and runtime projection |
| `diag_*.py`, `diag_*.json` | Exploratory planning diagnostics (V1.1 data; not evidence) |
| `DESIGN_PLAN_DRAFT.md` | Approved planning record |
