# Detector-only profile change detection and false-switch challenge

## Question

Can an online two-sided CUSUM detect X↔Z bias-profile changes faster than periodic 100-shot LDA recalibration while avoiding excessive false basis switches under stable or measurement-shifted noise?

## Frozen detector

Use the frozen four-feature score and nominal class means/variances from `adaptive_basis_sprt_results.json`. Compare class-specific Gaussian LLR and pooled-variance Gaussian LLR CUSUMs. Initialize basis with a 100-shot frozen LDA mean-sign decision. At each subsequent shot, if state is X, update `Gz=max(0,Gz+LLR)`; if state is Z, update `Gx=max(0,Gx-LLR)`. Switch state when the active statistic reaches `h=log(200)` and reset both statistics. This threshold gives a nominal one-sided likelihood-ratio crossing bound of 0.5% per direction under the correctly specified simple model; report observed false switching instead of assuming the bound transfers to the simulator.

The comparator is periodic non-overlapping 100-shot LDA mean-sign recalibration on the same sequences. Test stable controls and 101-segment alternating X/Z sequences at dwell 1,000 and 10,000 calibration shots, under nominal gate/measurement p=.003/.003 and measurement-shift p=.003/.006. Use 100 independent stable episodes/profile/regime/dwell and 100 true profile transitions/alternating sequence. Preflight uses 10 stable episodes and 20 alternating segments with separate seeds; require source identity, finite scores, and projected main runtime below 300s.

Report stable false switches per 100k calibration shots, initialization errors, transition detection fraction, median/90th-percentile delay, missed transitions, and comparison with periodic LDA. No logical outputs are used. The streams are simulator calibration shots; this is not a logical LER or hardware result. No labels enter the online state update; labels are used only for offline scoring.
