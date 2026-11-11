# Strong fixed-baseline v2 — corrected prospective candidate

This directory contains a corrected, versioned copy of the development runner. It fixes the pooled-static calibration leak from v1 by fitting detector profiles only on the independent template batches and exposing final calibration to the estimator as detector matrices only.

## Safety status

**No sampling is authorized or enabled.** `experiment_config_v2.json` has `sampling_authorized: false`; `run_development_v2.py` fails closed before loading the seed inventory or reaching a sampler call. The v2 seed inventory and pre-test freeze are intentionally absent pending a later protocol/seed audit and review. Do not change the authorization field or create a freeze as a way to start sampling. A future sampling request requires a separately reviewed freeze and explicit authorization.

The v1 runner, all v1 freezes, its run/recovery directories, and the post-run reconstruction are preserved unchanged. V2 imports shared circuit/decoder helpers from v1 but has its own runner, calibration boundary, config, and test. No final-development or Stage 5 labels are read by these tests.

## Correct calibration boundary

1. Read independent template detector arrays, paired only with the fixed template probabilities from the config.
2. Fit detector feature profiles from those template batches.
3. Read final calibration archives into `list[np.ndarray]`; do not attach generating-condition labels to the arrays passed to calibration.
4. Concatenate those detector arrays and estimate one pooled p.
5. Keep the per-root adaptive estimate on the same 2,000-shot detector calibration batch per root; evaluate all decoder arms on identical detector and observable arrays.

`pooled_calibration_v2.py` has separate template-fit and detector-only estimation functions. It rejects tuple inputs to the pooled calibration estimator.

## No-sampling validation command

From the repository root:

```powershell
python -m unittest outputs.strong_fixed_baselines_v2.test_pooled_calibration_v2 -v
```

These tests use only tiny in-memory arrays and mocks. They do not call Stim sampling, open archived run data, or read Stage 5 materials.

The full prospective design, calibration-budget comparison, seed/freeze gates and remaining blockers are documented in `PROSPECTIVE_REPLICATION_PLAN_V1.md`. The code is a correction candidate, not an approved experiment.
