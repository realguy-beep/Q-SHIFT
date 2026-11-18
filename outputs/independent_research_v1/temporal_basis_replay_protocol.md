# Exploratory temporal replay of detector-only basis selection

## Question and scope

Does periodically recalibrating the frozen d=3 detector-only X/Z selector retain an operational advantage when bias direction alternates? This is a model-based replay of existing independent calibration and logical windows, not a new circuit experiment. It uses the 25/100/500-shot classifier confusion counts and per-window logical failure arrays already saved by the end-to-end and calibration-cost screens. The classifier, decoder, profiles, and error-rate estimates are not refit.

## Replay design

- Distances/resources stay at d=3, 5 rounds, p=.003, with X/Z profiles at bias ratios 2, 5, and 10.
- Hidden profile alternates deterministically with equal dwell in logical blocks of 100 shots. Test dwell lengths are 1, 10, 100, and 1,000 blocks (100 through 100,000 logical shots).
- Calibration uses a frozen prefix of 25, 100, or 500 detector-only shots. The resulting basis choice is held for K blocks; K is 1, 10, 100, or 1,000. At each scheduled calibration, the current profile's measured confusion rate is applied. A switch between calibration times leaves the previous choice active until the next scheduled check.
- Point estimates of per-profile/basis LER come from the existing independent 100,000 logical outcomes/profile/basis. Calibration and logical data were independent in the source experiment.
- Compare to the better of static-X and static-Z under the equal-duration alternating profile. Report both LER per logical attempt and correct logical outputs per total circuit shot, charging C calibration shots per update and assuming calibration shots yield no useful output. This assumption is explicit; a different task may allow useful output during calibration.
- Replay horizon is 10,000,000 logical attempts with updates at t=0 and then every K blocks. Results are plug-in projections from one synthetic stationary model family. They are exploratory and do not establish device drift, causal change-point performance, or long-run stationarity.

## Validation and stopping

Before reporting the replay, assert that the source JSONs are present, sample totals/shapes match the declared 1,000 calibration windows and 1,000 logical batches, and the expected LER reconstructed from observed 500-shot confusion rates and independent basis-specific logical LERs agrees with the saved primary policy LER within 0.0004. No new stochastic samples are generated. No confirmatory evaluation is accessed. Preserve all schedules, confusion inputs, and point-estimate outputs.
