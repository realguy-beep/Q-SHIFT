# Prospective clean replication plan v1 — review candidate only

**Status:** candidate protocol; not frozen for sampling, no v2 samples generated, and no sampling authorization.  
**Purpose:** cleanly re-run the strong fixed-baseline comparison with the pooled estimator implementation corrected.  
**Historical boundary:** do not use the v1 final-development outcomes to tune any setting. Do not access Stage 5 evaluation outcomes. The v1 run and reconstruction remain unchanged and are reported separately.

## Hypothesis and scope

The narrow question is whether detector-profile adaptation reduces logical error relative to a single detector-calibrated pooled fixed matcher, while meeting a zero-burst no-harm criterion, under the same five synthetic burst settings. This candidate does not assume an advantage and cannot establish hardware validity or generality beyond this circuit/noise family.

## Method held constant from the v1 written protocol

- Rotated surface-code Z memory, distance 3, five rounds, 40 detectors and one observable.
- Gate and measurement probabilities 0.003; synthetic `CORRELATED_ERROR(p) X8 X10` at each of five measurement boundaries; p values `0, .004, .008, .012, .016`.
- Stim DEM settings remain `decompose_errors=True`, `approximate_disjoint_errors=True`; PyMatching correlation decoding remains enabled.
- Fixed candidate grid `{0,.002,.004,.006,.008,.010,.012,.014,.016}`.
- Static safety selection: among candidates with selection-partition p=0 mean excess LER ≤+0.0002, minimize equal-weight nonzero-condition LER with lower-p tie-break. Validation can accept that one choice only if its one-sided 95% root-bootstrap upper bound for p=0 excess is ≤+0.0002; otherwise fall back to p=0. No validation reselection.
- Keep −0.0002 absolute LER as the separately reported practical-benefit benchmark, not an automatic superiority claim. Keep +0.0002 as the p=0 no-harm benchmark.
- Analysis remains descriptive: paired root-level effects, 100,000 condition-stratified root-bootstrap resamples and 95% percentile intervals; do not report confirmatory p-values from this feasibility study.

## Proposed partitions and fresh streams

The candidate config retains the prior allocation for comparable scope: 60,000 template shots; 450,000 selection; 450,000 validation; 1,200,000 final calibration detectors; and 1,500,000 paired final-development evaluation shots (3.66M unique in total). Use newly generated root/stream seeds, distinct from all prior development allocations. Candidate seed namespace start is 19,000,000,001; the actual inventory is not yet generated or cleared for sampling. Before sampling, a separate seed audit must establish unique roots/streams and collision coverage using only permitted historical metadata. If resolving a collision requires sealed Stage 5 metadata, stop and request a specific access decision rather than opening outcomes.

Templates, selection, validation, calibration and evaluation streams must be disjoint. Each evaluation root's five decoder predictions are produced from the same detector matrix and scored against the same observable array. Final evaluation labels are inaccessible to estimator fitting, threshold/model selection and decoder choice. They may be used only for frozen post-prediction scoring after all arm choices are committed.

## Estimator correction

The v2 runner stores final calibration as detector matrices only. It first fits `DetectorProfileEstimator` from the three independent template batches at p=0, .01 and .02. It then concatenates the 1.2M final calibration detector rows and calls `.estimate` on that matrix. The pooled-estimator function has no condition-label parameter and raises if a condition-tagged tuple is passed. This differs from v1's erroneous `final_cal_batches[(p, detectors)]` profile-fitting call.

The adaptive arm uses the same 1.2M total calibration-shot budget but estimates separately from each root's preceding 2,000 detector rows. Pooled-static sees the full calibration pool jointly and uses one matcher; adaptive sees root-specific subsets and can build a different matcher per root. Both share the same 60,000 template shots. These are equal in total calibration shots but not in information aggregation or number of matchers/rebuilds.

The safety-constrained fixed selector additionally consumes 450,000 selection and 450,000 validation shots with observable labels for model selection and safety checking. That is an extra 900,000 labeled development shots beyond the pooled/adaptive detector calibration budget. It is an intentionally strong offline fixed comparator, not a resource-matched runtime calibration policy. Report this distinction explicitly rather than calling every arm fully equal-resource.

## Baselines and claims

Retain nominal fixed p=0; corrected pooled detector-only static; the safety-constrained static candidate/fallback; per-root detector-profile adaptation; and privileged true-p as a nondeployable diagnostic. A new result is usable only if the new partition is actually generated under the reviewed freeze and independently audited. The present v1 reconstructed outcomes cannot select any parameters for this comparison.

## Before any v2 sampling

The following are prerequisites and are not satisfied by this PR:

1. Supervisor review of this plan and the corrected runner/tests.
2. Complete, collision-screened fresh seed inventory with exact root and stream mapping; the candidate namespace alone is not a seed freeze.
3. A prospective freeze hashing the v2 source, config, noise generator, seed inventory and statistical plan before sampling.
4. Verified sample partition isolation, calibration-only estimator input, selection/validation/evaluation separation, and independent saved-array audit.
5. Separate owner authorization to sample. `experiment_config_v2.json` remains set to `sampling_authorized: false` and `PRETEST_FREEZE_V2.json` is absent.

No experiment is executed by preparing this plan. This package is stopped at the supervisor review checkpoint.
