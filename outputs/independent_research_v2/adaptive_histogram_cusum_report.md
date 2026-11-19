# Histogram likelihood CUSUM was fast but switched falsely too often

## Motivation and method

The previous Gaussian-score CUSUM detected X↔Z bias-profile transitions in roughly 27–33 shots, but generated excessive false switches. This screen replaced the Gaussian likelihood with a frozen empirical categorical likelihood over the same detector-only four-feature score. Two 100k nominal calibration streams defined 32 pooled-quantile bins and smoothed profile-specific bin probabilities. The histogram two-sided Page CUSUM used the same `log(200)` threshold and 100-shot initial state as the Gaussian comparators. Test streams included stable profiles and alternating profiles at 1,000-shot dwell, under nominal and doubled measurement noise. Online updates used detector scores only; no logical outcomes were sampled.

## Results

The histogram detector found every transition in both alternating streams. Median delay was 27.5 shots nominal and 19 shots under measurement shift. But stable-profile false switches failed the frozen limits: 33.3 and 41.1 per 100k shots for nominal X/Z profiles, and 45.6 and 170.0 under shifted X/Z profiles. The predeclared limits were 5 and 25 respectively.

The Gaussian heteroscedastic CUSUM had similar nominal false switching (34.4/41.1) and worse shifted Z-profile behavior (292.2/100k). The pooled-variance CUSUM also exceeded limits (25.6/25.6 nominal; 47.8/147.8 shifted). Periodic 100-shot LDA had fewer false switches in these controls: 10.0/2.2 nominal and 4.4/37.8 shifted, with 100-shot transition delay when a switch was needed.

## Decision

Reject this frozen histogram CUSUM for profile adaptation. The empirically estimated likelihood did not fix the false-switch problem, despite its fast response. Do not tune bins or thresholds on these streams. The result is a detector-only simulator study, not logical LER or hardware evidence. No replication was launched because the fixed gate failed.

The run used 200k calibration shots, 80k preflight score samples, and 602k main score samples (882k total). No confirmatory/sealed data were accessed.
