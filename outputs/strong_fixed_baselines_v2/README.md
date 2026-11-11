# Strong fixed-baseline V2 — corrected prospective candidate

This directory contains a corrected, versioned copy of the development runner. It fits detector profiles only from independent template batches and sends final calibration detector matrices, without condition tags, to the pooled estimator. Supervisor checkpoint 2 makes adaptive Q-SHIFT versus pooled-fixed PyMatching the primary comparison while retaining the zero-burst safety gate and safety-constrained static arm.

## Safety status

**No sampling is authorized or enabled.** `experiment_config_v2.json` has `sampling_authorized: false`; `run_development_v2.py` fails closed before loading the seed inventory or reaching a sampler call. The V2 seed inventory and pre-sampling candidate freeze record only metadata and hashes; both preserve sampling as not authorized/performed. The candidate freeze is not permission to sample. Do not change the authorization field. Any future sampling requires a further supervisor review and separate explicit owner authorization.

V1 runner, freezes, run/recovery directories, and post-run reconstruction remain unchanged. V2 uses shared frozen Stim/PyMatching construction primitives but has a separate runner, calibration boundary, config, and tests. No V2 samples exist. No sealed evaluation outcomes were accessed.

## Calibration boundary and arms

1. Fit profiles only from three independent detector-template batches with known template-generation probabilities.
2. Load final calibration as detector matrices only, concatenate them, and estimate one pooled p. The pooled estimator rejects `(probability, detectors)` tuples.
3. Estimate each adaptive root's p from that root's separate 2,000-shot detector-only calibration batch.
4. Apply nominal-fixed, pooled-fixed, safety-constrained static, adaptive, and privileged true-p reference decoders to identical per-root detector/observable evaluation arrays. The privileged reference is nondeployable.

The precise selection, budget, statistical, and leakage rules are in `PROSPECTIVE_REPLICATION_PLAN_V2.md` and `FAIRNESS_AND_LEAKAGE_REVIEW_V2.md`.

## Independent saved-array audit

`INDEPENDENT_AUDIT_PLAN_V2.md` specifies a read-only archive and prediction audit. `audit_saved_arrays_v2.py` does not import the runner or its reporting functions; it independently re-estimates detector profiles, reconstructs selection, verifies archive hashes, rebuilds PyMatching models, re-decodes saved samples, and recomputes paired metrics. Its tests use disposable synthetic archive fixtures only. It must not be pointed at a V2 run until a separately authorized execution exists.

## Collision audit and pre-sampling freeze

`prepare_seed_inventory_v2.py` reads only the fixed, hashed seed-metadata allowlist from the prior audit plus tracked seed inventory/manifest files. It checks a candidate namespace without reading sample archives or outcome arrays. Coverage is limited to recoverable named metadata; undocumented RNG use cannot be ruled out. Exact metadata paths and hashes are stored in `seed_inventory_v2_r2.json`. The earlier `seed_inventory_v2.json` is preserved as a superseded no-sample candidate; it is excluded from historical-seed screening because its streams were never executed.

`PRETEST_FREEZE_V2.json` hashes the final reviewed code, config, seed inventory, analysis plan, and audit source. It is a **review-only freeze** with `sampling_authorized: false` and `sampling_performed_at_freeze: false`. The runner remains disabled.

## Reproduction commands (repository root)

```powershell
python -m unittest outputs.strong_fixed_baselines_v2.test_pooled_calibration_v2 -v
python -m unittest outputs.strong_fixed_baselines_v2.test_saved_array_audit_v2 -v
python -m unittest outputs.strong_fixed_baselines_v2.test_seed_inventory_v2 -v
python -m unittest outputs.strong_fixed_baselines_v1.test_experiment -v
python -m outputs.strong_fixed_baselines_v2.prepare_seed_inventory_v2 --historical-root C:/Users/LENOVO/Documents/Codex/2026-11-03/referenced-chatgpt-conversation-this-is-an
python -m outputs.strong_fixed_baselines_v2.create_pretest_freeze_v2
python -c "import outputs.strong_fixed_baselines_v2.freeze_pretest_v2 as f; print(f.verify_freeze()['freeze_status'])"
```

Unit tests use in-memory arrays, mocked runner dependencies, and temporary fixtures. They do not invoke Stim sampling or read run archives. The seed-preparation command reads only the enumerated seed metadata. The saved-array audit is read-only and requires a completed V2 run, which is absent at this checkpoint.
