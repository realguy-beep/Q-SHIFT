# Post-run protocol-consistent reconstruction v1

## Why this reconstruction is needed

The frozen protocol defines the pooled detector-calibrated static decoder as: fit the detector-feature profiles on the separately generated p={0, 0.01, 0.02} template batches, then estimate one p from the concatenation of the 1.2M held-out-development calibration detector rows. No generating-condition labels, observables, or event flags enter that estimation call.

The executed runner instead called `detector_profile_estimator(final_cal_batches)`, where each final calibration batch was paired with its known generating p. This used the five condition labels to construct profiles and did not follow the frozen pooled-static rule. Its saved p estimate and pooled prediction row are therefore retained as invalid legacy outputs, not silently accepted as the planned arm. An initial independent audit detected the discrepancy before it loaded final evaluation archives or outcomes.

## Frozen reconstruction rule

Before reading final-development observable labels, the reconstruction will:

1. Verify the original `PRETEST_FREEZE_V14.json` source/configuration hashes and the complete sample-archive/commit-marker inventory.
2. Refit the 45-feature detector profile only from the three independent template archives at p=0, 0.01, and 0.02.
3. Estimate a single pooled p from the concatenated 1,200,000 held-out calibration detector rows. The estimator receives only detector rows; its three profile probabilities come only from the independent template-generation settings.
4. Independently rebuild all five prediction arms on the same saved evaluation detector arrays: nominal fixed, reconstructed pooled static, safety-constrained static, per-root adaptive, and privileged true-p reference. The latter remains nondeployable.
5. Verify the original saved prediction rows for all arms other than the invalid legacy pooled row. Separately verify that the legacy pooled row matches its recorded label-conditioned p. Keep both legacy artifacts intact.
6. Score paired XOR residuals only after the reconstruction freeze is written. Use the original descriptive analysis plan: 100,000 condition-stratified root-cluster bootstrap resamples, 95% percentile intervals, no confirmatory p-values, and the p=0 +0.0002 harm benchmark.

This is an explicitly disclosed post-run implementation-deviation reconstruction on the already sampled development evaluation arrays. It is not a clean execution of the original runner and is not confirmatory evidence. No protocol choices may be altered after this freeze; no independent or sealed test data are involved.

## Expected evidence boundary

The reconstructor may read final evaluation detector arrays for decoding. It must not use those observables to estimate p, select a baseline, select seeds, alter thresholds, or change the analysis. Observable labels are used only to compute the predeclared paired error outcomes after all decoder predictions are frozen and saved. The reconstruction is invalid if any archive, prediction, source hash, or stream identity fails its audit.
