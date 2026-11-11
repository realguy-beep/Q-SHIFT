# Supervisor review corrections v1

This supplement responds to the review on PR #1 at reviewed commit `2dad2f37456886ee32a6b3b1e05511f2ec5df893`. It does not modify the v1 frozen runner, protocol, run archives, post-run reconstruction, or reported results.

## 1. V1 runner is preserved and unsuitable for prospective reuse

In `outputs/strong_fixed_baselines_v1/run_development.py`, the pooled-calibration loop stores `(p, detectors)` at line 385 and passes those tagged batches to `detector_profile_estimator` at line 388. That is the confirmed condition-label leakage into profile fitting. The path is retained as historical evidence; the corrected runner is separately versioned in `outputs/strong_fixed_baselines_v2/run_development_v2.py`.

The v2 runner fits profiles from independent template batches only, keeps final calibration batches as `np.ndarray` detector matrices, concatenates those arrays, and calls the detector-only estimator. The new helper rejects tagged tuples. Regression tests assert the intended fit inputs, pooled detector rows, and rejection behavior. The runner also fails closed while `sampling_authorized` is false; no v2 seed inventory or pre-test freeze currently exists.

## 2. Calibration and selection budgets

Pooled static and per-root adaptive each have 1.2M final calibration detector shots in the v1 study. Pooled static aggregates all 1.2M rows into one estimate; adaptive estimates from 2,000 preceding detector rows per root and can rebuild per root. Both share the 60,000 template shots. Equal total shot count does not make their information access or model-update costs identical.

The safety-constrained fixed baseline also uses 450k selection plus 450k validation shots with observables to choose/validate one grid point; that extra 900k labeled development budget is not given to the deployable detector-only estimators. It is an intentionally strong offline comparator, and the difference is disclosed in `PROSPECTIVE_REPLICATION_PLAN_V1.md`.

## 3. Result language

The protocol-consistent reconstructed adaptive-minus-pooled-static estimate is `−0.00002917` absolute LER, with descriptive 95% root-bootstrap interval `[−0.00005167, −0.00000750]`. Its magnitude is below the `0.0002` practical-benefit benchmark. The larger adaptive-minus-safety-static contrast is not evidence of an advantage over an optimized fixed decoder: that safety-static arm fell back to nominal p=0. No confirmatory superiority, hardware, or general-noise claim is made.

The reconstruction followed a material v1 implementation deviation and used the already sampled development evaluation arrays. It remains a transparent development reconstruction, not a clean prospective execution or independent confirmation.

## 4. Audit scope

The local verification result and 16 tests were reported from the Windows workspace. The supervisor review was a source/documentation review, not a raw-array replay. The NPZ archives and corrected per-shot predictions remain local and ignored; no large raw data or Stage 5 sealed outcome material is added here. The V2 tests use only in-memory fixtures and do not sample.

## 5. Readiness

The corrected estimator boundary is implemented and tested, but V2 is not ready to sample: the fresh seed inventory and prospective pre-test freeze remain absent, sampling is explicitly disabled, and separate owner authorization is required. Do not merge or start another run from this review checkpoint.
