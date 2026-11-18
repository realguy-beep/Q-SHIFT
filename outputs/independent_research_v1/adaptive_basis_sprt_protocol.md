# Sequential detector-only X/Z profile calibration

## Question and hypothesis

Can a sequential probability ratio test (SPRT) on the already frozen four detector-rate features identify the sign of a stable X/Z bias direction with at most 5% profile-selection errors while consuming fewer than 25 calibration shots on average? Prior Q-SHIFT studies used fixed 25/100/500-shot feature averages; they did not test early stopping.

## Frozen protocol

Use d3/five-round Z-memory calibration circuits under the existing X-biased and Z-biased profiles at gate/measurement p=.003 and bias ratio 10. Keep the existing LDA weights and intercept from `bias_identification_results.json`; do not retrain or use logical observables. Transform each shot's four detector-rate features to its fixed scalar LDA score. From a separate labeled training stream of 50,000 shots/profile, fit Gaussian score means and variances. For an independent validation stream, group shots into 1,000 windows/profile, each with a maximum of 500 samples. Accumulate the Gaussian log-likelihood ratio (Z-biased vs X-biased) sequentially; stop when it crosses the symmetric Wald threshold `log(19)`, corresponding to nominal 5% false-alarm/miss targets, or at 500 shots. At the cap, select by the accumulated likelihood ratio sign.

Compare on the exact same validation windows against the frozen LDA sign on prefixes of 25, 100, and 500 shots. Report profile-specific selection errors with exact binomial intervals and mean/median calibration shots consumed. Preflight uses 100 windows/profile and 10,000 training shots/profile at separate seeds; advance only if source/circuit/features are valid, projected full run is below 300 seconds, and no stream or seed is reused. Main uses the fixed full budgets above.

## Advancement and interpretation

The candidate advances to an LER/throughput projection only if both profile error rates are <=5% and mean SPRT consumption is below 25 shots. This is a detector-calibration development study under two simulator profiles, not a measured change-point detector, hardware drift result, or claim about arbitrary logical states. Calibration cost is counted in circuit shots; no calibration data or observables are oracle inputs at operation.
