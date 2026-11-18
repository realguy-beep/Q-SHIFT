# Independent validation extension for sequential detector calibration

The first 1,000-window/profile screen had SPRT point errors of 39/1000 and 35/1000; the X-biased exact 95% interval extended above 5%. Freeze the Gaussian score means/variances, LDA parameters, and Wald threshold from `adaptive_basis_sprt_results.json`. Test only a fresh validation stream, with 2,500 independent 500-shot windows per profile, new seeds 2026115401/5402, and the same matched 25/100/500-shot LDA prefix comparators. No training parameters may be refit.

Before the full extension, run 500 windows/profile with seeds 2026115391/5392 to verify source construction, finite scores, and runtime; require projected validation <300s. The extension advances only if each SPRT profile error's exact two-sided 95% upper bound is <=5% and mean shots consumed is below 25. This is a development replication of calibration performance, still not an LER, hardware, or change-point result. Total new unique samples are preflight plus 2.5M main shots.

## Retrospective comparator check

After the primary screen, add a stronger matched fixed-budget comparator: apply the same frozen class-conditional Gaussian score likelihood ratio to the first 25/100/500 samples, without sequential stopping. Recompute this comparator on the exact same saved-seed validation streams. This is a retrospective fairness check, not a change to the primary gate; label it exploratory and count no additional unique samples. Any adoption claim requires a prospective new stream comparing SPRT with this fixed-budget likelihood rule.
