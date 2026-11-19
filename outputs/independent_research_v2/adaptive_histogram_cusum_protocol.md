# Detector-only histogram likelihood CUSUM after Gaussian false alarms

## Question

A prior Gaussian-score CUSUM detected profile changes quickly but exceeded its false-switch target. Can a frozen categorical likelihood ratio over the same detector-only score reduce false switching while retaining useful change delay, without using logical outcomes online?

## Frozen method and comparator

- Use the existing frozen four-feature detector-only LDA score for X-biased vs Z-biased profile selection on Z-memory d3 circuits.
- Train a two-profile histogram likelihood model from 100,000 nominal p_meas=.003 scores/profile. Define 32 pooled-score quantile bins (collapse duplicate edges) and estimate profile-specific bin probabilities with Jeffreys 0.5 pseudocounts. Freeze bins and probabilities.
- Use two-sided Page CUSUM with threshold log(200), the same first-100-shot mean-sign initialization, and the same reset behavior as the prior Gaussian CUSUM. No detector labels or logical outcomes enter online updates.
- Compare on identical streams with class-specific Gaussian CUSUM, pooled-variance Gaussian CUSUM, and periodic nonoverlapping 100-shot LDA.
- Test stable 1,000-shot episodes under nominal and doubled-measurement p (.003 and .006), plus 101-segment alternating profiles at 1,000-shot dwell under each measurement rate.

## Gates and resources

Preflight uses 10 stable episodes/profile and 20 alternating segments, distinct seeds, source-builder identity, finite score, and runtime projection <=300 seconds. Advancement requires <=5 false switches per 100k shots in nominal stable controls, <=25/100k under measurement shift, >=95% of transitions detected within dwell, median delay <=100 shots, and no source or finite-score failures. This is an independent development screen, not a logical LER or hardware result. No threshold tuning or model refit is allowed on validation streams.

Seeds: calibration 2026122101–2102; preflight score streams 2026122111–2126; validation streams 2026122131–2138.
