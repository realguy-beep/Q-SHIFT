# Prospectively calibrate a histogram CUSUM false-alarm boundary

## Motivation

The fixed `log(200)` histogram CUSUM detected changes quickly but exceeded stable false-switch limits. This follow-up keeps the histogram bins and likelihoods fixed and asks whether a single empirically calibrated threshold can meet the false-switch targets without exceeding the 100-shot median-delay limit.

## Frozen design

- Reuse the prior frozen 32-bin histogram probabilities, fitted only on nominal calibration scores. Do not change bins or probabilities.
- Estimate one global threshold from fresh stable calibration streams: 500 independent 1,000-shot episodes for each of X/Z profile × nominal/doubled measurement p. Choose the smallest threshold at or above `log(200)` whose observed false-switch rates meet <=5/100k nominal and <=25/100k shifted in every calibration stratum. Search by deterministic bisection; no validation streams enter threshold selection.
- Freeze that threshold and evaluate on fresh stable streams of the same sizes plus independent 101-segment alternating streams at 1,000-shot dwell, nominal and doubled measurement p.
- Compare with fixed `log(200)` Gaussian CUSUMs and periodic 100-shot LDA on the same streams.

## Advancement gate

Require the fixed threshold to exist, all independent stable validation rates to meet 5/25 false switches per 100k, >=95% transitions detected, and median transition delay <=100 shots under both measurement conditions. If calibration cannot find a threshold by h=100, do not open validation. No further threshold changes on validation. Detector-only development study; no logical outcomes or hardware evidence.

Seeds: calibration 2026122201–2204; validation stable/alternating streams 2026122211–2218. Each stage uses new streams, independent of the earlier histogram screen.
