# Sequential profile calibration under measurement-noise composition shift

## Question

Does the nominal p=.003 Gaussian score SPRT retain X/Z profile-selection accuracy when measurement-error probability rises to .006 while gate noise remains p=.003 and the 10:1 bias direction is unchanged?

## Frozen method

Keep the exact nominal LDA weights/intercept, fitted Gaussian score means/variances, Wald threshold log(19), and 500-shot cap from `adaptive_basis_sprt_results.json`. Use d3/five-round Z-memory detector-only calibration circuits, X-biased and Z-biased ratio10 profiles, gate_p=.003, measurement_p=.006. Compare SPRT with frozen LDA and Gaussian-LLR prefix decisions at 25/100/500 shots. Do not retrain or use observables. Preflight uses 100 independent 500-shot windows/profile, seeds 2026115901/5902; require source builder identity, finite scores, and projected full validation under 300s. Main uses 1,000 independent 500-shot windows/profile, seeds 2026115911/5912.

Report profile-specific classification errors with exact 95% binomial intervals, mean/median shots, and shifted score mean/variance. Advance to an end-to-end LER test only if both 95% upper error bounds are <=5% and mean shots remain below 25. This tests one controlled composition shift; it does not establish general model robustness or hardware validity.
