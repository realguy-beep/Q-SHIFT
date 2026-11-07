# Stage 4 Noise Estimation Design

## Estimand and observation boundary

The parameter of interest is the per-round probability `p_burst` for five independent Stim `CORRELATED_ERROR` sites, each applying simultaneous X to data qubits 8 and 10. Base gate and measurement settings remain fixed at the Stage 3 values. The estimator receives a separate calibration batch of 40 detector bits per shot. It never receives observable labels, event-occurrence flags, the generating probability, or evaluation-block detector samples.

## Minimal estimator

The prototype uses 45 binary per-shot features: the 40 detector bits and five pair indicators for joint firing of the graphlike detector pairs `(8,10)`, `(16,18)`, `(24,26)`, `(32,34)`, `(36,38)`. For three profile probabilities, it stores the detector-only mean feature vector. Between adjacent probabilities it linearly interpolates each mean feature. For a new calibration batch it computes the mean feature vector and selects the probability on a fixed 0.00001 grid minimizing featurewise variance-standardized squared distance to the interpolated profile.

This is a method-of-moments/profile-matching estimator, not a likelihood decoder and not an exact posterior. The profile batches are independent. The feasibility pilot fits the profile at p in `{0.002, 0.010, 0.018}` and evaluates estimation at unseen p in `{0.006, 0.014}` using separate random streams. It records detector-only percentile bootstrap intervals from 500 resamples of each calibration batch. These intervals quantify finite calibration-batch variability under the fitted template map only; they do not include template uncertainty fully and are not coverage claims.

## Translating estimates into PyMatching

For each estimated scalar, the code rebuilds the Stage 3 Stim circuit with that value, obtains a DEM with `decompose_errors=True, approximate_disjoint_errors=True`, and constructs `pymatching.Matching.from_detector_error_model(..., enable_correlations=True)`. No free-form CNN feature or weight is passed to PyMatching. The rebuilt object must preserve 40 detectors, one observable, the five burst mechanism records at the requested probability, and valid batch prediction shapes.

## Pilot comparators and fairness

All three arms decode the same paired evaluation detector arrays and are scored against the same observable labels:

1. **Fixed nominal PyMatching:** p=0 burst model. It receives the same detector calibration batch allocation but ignores it.
2. **Detector-estimator-assisted PyMatching:** p is estimated only from the independent calibration detectors; model is rebuilt before evaluation.
3. **Privileged true-p PyMatching:** built with the simulator's true p solely for an upper-reference comparison. The true p is not passed to the estimator.

A fixed p mismatch grid is also scored on those exact samples as an offline sensitivity diagnostic. It is not a selectable deployable policy. Training-profile detector samples, per-root calibration detector samples, and paired evaluation arrays use disjoint seeds and disjoint shots.

## CNN estimator decision

No CNN noise estimator is implemented in this feasibility stage. There is only one scalar probability and its locations/Pauli are fixed by the simulator, so a transparent profile estimator is the appropriate first test. A CNN-estimator arm is considered only if this method has acceptable estimation error yet demonstrably fails to reconstruct decoder-relevant behavior, and the additional model can be trained with an independent monitor partition while receiving the same online calibration information.
