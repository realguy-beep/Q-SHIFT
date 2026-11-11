# Q-SHIFT supervisor review handoff — V2 checkpoint 2

## Review state

- PR: [#1 — Strong fixed baselines for synthetic burst noise](https://github.com/realguy-beep/Q-SHIFT/pull/1), branch `codex/research-strong-baselines-v1`, base `main`.
- Supervisor review: [Review #2, comment 6796937443](https://github.com/realguy-beep/Q-SHIFT/pull/1#issuecomment-6796937443).
- Source revision reviewed: `5c3aaf48d5807a5dbdb33dc3c6a878c7e496a931`.
- V2 preparation commit: `9b72cb1140b067f6b8bde09f68c725e20f50254f`.
- Scope: V2 runner calibration-boundary test, corrected primary comparison, fairness/leakage review, collision-screened prospective inventory, review-only pre-sampling freeze, and fixture-tested independent audit tooling.
- **No V2 sampling was performed; `sampling_authorized` remains false. No sealed evaluation outcomes were accessed. PR remains unmerged.**

## Changes for Review #2

1. **Calibration integration test.** `run_development_v2.py::run_pooled_calibration_stage` now owns the collection boundary. It passes template `(probability, detector matrix)` batches only to template-profile fitting. It collects the final calibration stream as detector-only matrices, rejects archives containing observable labels, concatenates those matrices, and gives only that detector array to the pooled probability estimator. The mocked integration test exercises the runner orchestration without Stim and checks sampler arguments, fit inputs, estimator inputs, and the pooled matrix. Marker-only/ambiguous commits fail closed before sampling. The full runner still refuses before inventory or sampler access while authorization is false.
2. **Primary comparison.** The primary is now the equal-weight mean over `p > 0` of root-paired `adaptive − pooled detector-calibrated fixed PyMatching` LER. The `−0.0002` practical-benefit boundary is reported as a benchmark; this is a development study, with a descriptive root-stratified bootstrap interval and no confirmatory p-value.
3. **Safety arms.** The zero-burst no-harm selector and its validation fallback to nominal `p=0` remain intact. The safety-constrained static arm is retained as a secondary comparator. It is not substituted for the stronger pooled-fixed primary reference. Final `p=0` effects are reported for deployable arms and cannot alter choices.
4. **Fairness/leakage.** All five arms use identical evaluation detector/observable arrays. Shared independent templates are 60,000 shots. Pooled-fixed and adaptive each receive 1,200,000 final detector-calibration shots in total, but pooled-fixed estimates one global parameter while adaptive estimates per root; equal total shots do not imply equal information aggregation, estimator variance, decoder builds, or compute. The safety-static selector additionally receives 450,000 selection and 450,000 validation labeled shots; that imbalance is disclosed. No evaluation outcomes, generating labels, hidden event flags, or future samples enter deployable calibration or selection.
5. **Seed inventory.** `seed_inventory_v2_r2.json` screens 1,610 unique candidate seeds against 25 hash-verified allowlisted historical metadata sources plus 48 tracked seed inventory/manifest metadata files (29,128 large-integer tokens screened). It reports zero collisions among candidate streams and zero collisions against screened metadata. The 3,660,000-shot allocation is exact. The previous no-sample `seed_inventory_v2.json` remains preserved but is superseded and excluded from historical RNG screening. Historical coverage is explicitly incomplete: undocumented/unrecorded RNG use cannot be ruled out. Regenerating the inventory after the implementation commit produced byte-identical output.
6. **Prospective freeze and independent audit.** `PRETEST_FREEZE_V2.json` binds 20 source/configuration/protocol/test/auditor files and records `PRETEST_FREEZE_REVIEW_ONLY`, `sampling_authorized=false`, and `sampling_performed_at_freeze=false`. `audit_saved_arrays_v2.py` is separate from the runner/reporting code. It verifies committed archive hashes, metadata, detector/observable/prediction shapes, seed/root mapping, independently rebuilds the frozen decoder bank, re-decodes paired stored detector arrays, and reconstructs calibration and aggregate metrics. Fixture tests exercise its validation paths. There is no V2 run to audit yet; a real saved-array replay remains future work after separate authorization.

## Protocol summary

The candidate keeps the frozen distance-3, five-round rotated Z-memory circuit; native parameters and five burst probabilities; five paired decoder arms; 20 selection roots and 20 validation roots per condition; 120 evaluation roots per condition; 2,000 final calibration and 2,500 paired evaluation shots per root; 60,000 template, 450,000 selection, 450,000 validation, 1,200,000 final calibration, and 1,500,000 evaluation shots (3,660,000 total). No circuit, decoder, allocation, or statistical choice was changed during this checkpoint other than correcting the primary comparator to the supervisor-specified pooled-fixed baseline.

The bootstrap resamples independent roots within each nonzero condition and gives each of the four conditions equal weight. It is descriptive and conditional on these conditions; no generalization or statistical-superiority claim follows. The static selector's no-burst rule is based on selection/validation only, with no reselection on evaluation data.

## Reproduction and validation

Run from the repository root:

```powershell
python -m unittest outputs.strong_fixed_baselines_v2.test_pooled_calibration_v2 outputs.strong_fixed_baselines_v2.test_saved_array_audit_v2 outputs.strong_fixed_baselines_v2.test_seed_inventory_v2 -v
python -m unittest outputs.strong_fixed_baselines_v1.test_experiment -v
python -c "import sys;sys.path.insert(0,'outputs/strong_fixed_baselines_v1');import freeze_pretest;f=freeze_pretest.verify_freeze();print('V1 V14 records=',len(f))"
python -m outputs.strong_fixed_baselines_v2.freeze_pretest_v2
python outputs/strong_fixed_baselines_v2/build_review_manifest.py
```

Observed: V2 tests **19/19 passed**; V1 unit tests **16/16 passed**; V1 V14 freeze verified **15 records**; V2 review-only freeze verified **20 hashes**; Python compilation passed for runner, calibration helper, auditor, seed builder, freeze tools, and manifest builder. The mocked integration path did not call Stim sampling. Fixture-only auditor tests passed. The source review manifest hashes 22 current review files and 7 historical references and confirms the V1 runner still matches the V14 hash.

## Key SHA-256 values

- V2 review-only freeze: `820c1f648f7516b82d7f4b3e6dd4c3617909bc9f3c9c5d5d59371f2bf2c06531`
- Final seed inventory r2: `9f38d03d3315bf74e33e2a994446bc1e103b9e08827d8b1cc8553516fbdc72c7`
- V2 config: `8a3a3e2d8fb062852465696aed4601ae19df89708316cdaa51430d1021323860`
- V2 runner: `f55f616ea75aae12162e00b1bd4104a65924b2c3016cc910153e1e3b3564118b`
- Independent saved-array auditor: `0270033c5954e3c84c4a7e63aa26153d5a5fb5c797407591de93eccdcd99f0ec`
- Source review manifest: `e1fc7a07b30b439fd290cff60e1737215a9cee728e59eef68a1188bb3e2acbdf`

The complete 20-file freeze hash inventory is in `outputs/strong_fixed_baselines_v2/PRETEST_FREEZE_V2.json`; per-file metadata-source hashes and collision counts are in `seed_inventory_v2_r2.json` and `SEED_COLLISION_AUDIT_V2.md`.

## Preserved evidence and unresolved limits

- No tracked V1 or Stage 5 evidence path changed. The historical V1 runner remains hash-matched to V14 and its previously documented calibration deviation remains visible; V1 is not silently reclassified. Stage 5 result/outcome files were not accessed; only the specified Stage 5 seed metadata inventory and prior source metadata were used for collision screening.
- The V2 run directory is absent and no V2 arrays, estimates, predictions, or performance results exist. The independent auditor has only been validated on disposable synthetic fixtures, not a real saved run.
- Seed disjointness is verified only against recoverable, hash-verified metadata coverage; unrecorded RNG use is unknowable from these files.
- The plan is development-only and does not establish superiority, practical benefit, or confirmatory power. Resource/information differences remain as disclosed above.
- `sampling_authorized` must remain false until supervisor review and separate explicit owner authorization. Do not merge PR #1 or enable auto-merge.

## Requested next action

Supervisor review of this V2 candidate and its review-only freeze. No experiment launch is requested or authorized by this handoff.
