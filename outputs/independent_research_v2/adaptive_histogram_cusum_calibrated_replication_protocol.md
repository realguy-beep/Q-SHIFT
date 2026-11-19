# Independent replication: calibrated histogram CUSUM procedure

Repeat the frozen histogram CUSUM threshold-calibration procedure and gates in `adaptive_histogram_cusum_calibrated_protocol.md`, using fresh calibration and validation score streams. Keep histogram bins/probabilities frozen from the original nominal fit. Re-estimate one global boundary using only calibration streams, then lock it before opening validation. Also report the original first-stream boundary as a secondary frozen-threshold comparator; it cannot affect the replication gate.

- Fresh calibration seeds: 2026122301–2304.
- Fresh validation seeds: 2026122311–2318.
- Same 500 episodes/profile/measurement condition, 1,000-shot dwell, and 101 alternating segments.
- Gate unchanged: all validation stable rates <=5 nominal / <=25 shifted per 100k, >=95% transitions detected, median delay <=100 shots for both measurement conditions.
