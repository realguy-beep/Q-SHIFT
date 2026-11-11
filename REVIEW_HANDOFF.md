# Q-SHIFT supervisor review handoff

## Review checkpoint

- PR: [#1 — Strong fixed baselines for synthetic burst noise](https://github.com/realguy-beep/Q-SHIFT/pull/1), base `main`, branch `codex/research-strong-baselines-v1`.
- Supervisor comment: [checkpoint 1, 2026-11-11](https://github.com/realguy-beep/Q-SHIFT/pull/1#issuecomment-6796430085).
- Reviewed source commit: `2dad2f37456886ee32a6b3b1e05511f2ec5df893`.
- Correction implementation commit: `91dddabe5d5ab9ef18791f79d7fba841086f82cb`.
- Scope: correct the prospective pooled-calibration input boundary, preserve and explain V1's deviation, and stop for supervisor review. No sampling or merge is authorized.

## Corrections in this review checkpoint

1. Preserved V1 and added a separately versioned candidate at `outputs/strong_fixed_baselines_v2/`. Its independent template batches alone fit detector profiles. Final calibration enters the pooled estimator as detector matrices, concatenated before estimation; the API rejects condition-tagged tuples. The V2 runner fails closed while `sampling_authorized` is false, before reading a seed inventory or invoking a sampler.
2. Added regression coverage for template-only profile fitting, pooled detector-only estimation, tagged-input rejection, data shape/binary validation, runner call path, disabled sampling, and refusal before inventory/sampler access.
3. Added a prospective plan that requires new independent roots, a pre-sampling source/config/seed freeze, separate selection/validation/evaluation partitions, no-harm and practical-benefit rules, and an independent saved-array audit. It explicitly accounts for information and resource differences: pooled static and per-root adaptive each receive 1.2M calibration detector shots plus the same 60k templates, but aggregate/use information differently; safety-static additionally receives 450k selection plus 450k validation labeled shots.
4. Expanded repository guidance with supervisor checkpoints and a prohibition on merge/auto-merge without explicit authorization.
5. Added `REVIEW_CORRECTION_MANIFEST.json`, which hashes the candidate source/config/docs and references the original V1 freezes/manifests/audit outputs. Manifest SHA-256 for this checkpoint: `0b9fb6c963a784f4d6e12a9d7997e48a60c72bc177f8f10ddf7ae14b235b4686`.

## Reproduction and checks performed

Run from the repository root:

```powershell
python -m unittest outputs.strong_fixed_baselines_v2.test_pooled_calibration_v2 -v
python -m unittest outputs.strong_fixed_baselines_v1.test_experiment -v
python -c "import sys;sys.path.insert(0,'outputs/strong_fixed_baselines_v1');import freeze_pretest; f=freeze_pretest.verify_freeze(); print('verified_files=',len(f))"
python outputs/strong_fixed_baselines_v2/build_review_manifest.py
```

Observed here: V2 regression tests **7/7 passed** (0.263 s); V1 baseline tests **16/16 passed** (1.536 s); V1 V14 freeze verification returned **15 verified file records**. The review manifest builder hashed 10 current source/config/document files and 6 historical references, and confirmed the V1 runner still matches its V14 recorded SHA-256. The recorded manifest hash above is for the generated file at this checkpoint.

The V2 suite uses in-memory/mocked samples and refuses before any sampling. The V1 command is its small existing unit suite, not a new research experiment. No new study sampling, large experiment, raw NPZ replay, sealed-test access, or Stage 5 result access was performed during this review. These local checks are not an independent supervisor replay.

## Historical evidence, deviation, and audit boundary

- V1 files, freezes V1–V14, historical run/recovery data, and post-run reconstruction were not edited. The V1 original runner remains unsuitable for prospective reuse: its final-calibration pathway attached generating-probability tags and passed those tagged batches to profile fitting. That is the disclosed V1 protocol deviation; the preserved runner is not silently repaired or reclassified.
- Historical references and hashes are in `outputs/strong_fixed_baselines_v1/FINAL_EVIDENCE_MANIFEST.json`, `PRETEST_FREEZE_V14.json`, `POSTRUN_RECONSTRUCTION_FREEZE_V1.json`, and `POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json`. The saved-array audit procedure is `POSTRUN_RECONSTRUCTION_PROTOCOL_V1.md`; executable audit/reconstruction sources are `audit_saved_run_reconstruction_v1.py` and `analyze_results_reconstruction_v1.py`.
- The local manifest records hashes for the excluded NPZ evidence and corrected per-shot prediction archives. Those raw files remain local/ignored; this checkpoint did not open, copy, upload, or independently rehash them. The supervisor's review was a source/documentation review, not a replay of the 3.66M-shot evidence.
- The V1 reconstruction remains development evidence after a material implementation deviation. Adaptive-minus-pooled-static was `−0.00002917` absolute LER with descriptive root-bootstrap interval `[−0.00005167, −0.00000750]`, below the `0.0002` practical benchmark. The larger contrast to safety-static reflects that arm's fallback to nominal. Do not claim confirmatory superiority, practical benefit, hardware validity, or general-noise validity.
- The independent Stage 5 audit directory was absent from this clone. Prior documentation says it existed in the earlier workspace; no Stage 5 outcome material was accessed to fill that gap.

## Ready and not ready for review

**Ready:** prospective V2 calibration boundary and tests; correction of the documented V1 code-reuse issue; transparent V1 deviation/result language; disclosed calibration-resource differences; reproducible local unit-test and freeze-verification commands.

**Not ready:** V2 seed-collision clearance, a V2 seed inventory, a V2 pretest freeze, raw V1 array replay in this clone, any V2 performance result, or sampling authorization. Candidate namespace `19,000,000,001` remains a proposal only. Existing Stage 5 material remains sealed.

## Required next action

Stop at PR #1 for the supervisor's next review. Keep the PR open and unmerged; do not enable auto-merge. Do not generate a V2 inventory/freeze or sample the candidate study until a separate review and explicit owner authorization.
