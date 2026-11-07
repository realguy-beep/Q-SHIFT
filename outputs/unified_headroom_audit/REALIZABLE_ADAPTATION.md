# Realizable adaptive headroom

## Selection among the existing bank

The central deployability question is not whether candidates disagree, but whether detector information available before choosing a decoder predicts which candidate will have lower future logical error.

- **Phase 2A:** independent calibration selects decoder index 1 globally and for each of the three regimes. The calibrated per-regime policy therefore has exactly the same test predictions as fixed index 1: 4,192 errors/600,000. Test-label retrospective regime best is 4,079, and per-shot hindsight is 2,975; neither is deployable evidence.
- **Phase 2B:** calibration selects one model per memory basis (X index 0; Z index 2) and repeats it for all three regimes. The six-cell primary regime-specific-minus-basis-fixed estimate is exactly zero, CI [0,0], p=1.0. The regime label adds no selected-policy value in this bank.
- **Phase 4A/4B:** detector-marginal calibration improves a measurement-heavy condition over nominal matching, but it is a static fitted decoder; true on-grid model recovery and nominal baseline weakness do not establish causal online selection. Phase 4C later supplies a stronger pooled-fixed baseline.
- **Phase 4C Stage 2:** detector-calibrated versus pooled-fixed equal-regime difference is +0.00001556 LER, 95% root-cluster interval [-0.00004889,+0.00007667], p=.66658. This is no detected benefit. It is not a formal equivalence test; an interval that excludes zero was not required, and practical margins should be interpreted under the frozen plan.
- **Headroom feasibility:** calibration rankings change among some conditions, but selection uncertainty and test utility are inconsistent. The predeclared cross-distance gate failed.

## Detector-based gate and causal policy evidence

The competition-pivot study used leave-one-root-out evaluation on one saved paired dataset (24 roots, 98,304 shots). A confidence/utility gate produced 686 errors versus 681 for pooled fixed; a simple syndrome-likelihood gate produced 684; always-adaptive produced 672. The always-adaptive paired difference is -9 errors (-0.0000916 LER), with 95% root-cluster interval [-0.000417,+0.000234], which includes zero. Only 225/98,304 predictions disagreed (~0.229%). Out-of-root calibration utility AUC was 0.570, syndrome gate AUC 0.464; the gate did not improve the baseline. This is cross-validated exploratory evidence on a single dataset, not an independent confirmatory test.

In the archived prototype dynamic bundle, the chosen decoder is index 1 for every one of 600 blocks. Its adaptive prediction exactly matches pooled fixed; it therefore cannot demonstrate switching benefit. Later corrected Phase 5 development schedules show policy-dependent point differences: some schedules favor static calibration or pooled, and some adaptive results are worse. Small development schedules do not support superiority. Phase 5E saved aggregate totals show ML and utility adaptive errors exactly equal pooled fixed across its four schedules (stationary 42, slow 102, rapid 75, random 79 errors over 9,216 shots each); the hindsight diagnostic is lower, but label-informed.

The online matching-weight feasibility work established that a decoder can be rebuilt from earlier completed data and swapped at block boundaries in a small fixture. However, it did not establish LER improvement against a strong, equally resourced periodic-recalibration policy. Its trigger validation had 2 false-update schedules in 100; the 95% interval (0.24%–7.04%) did not certify a 5% schedule-level rate, and repeated-update behavior remains uncalibrated. The utility pilot was single-distance/basis and inconclusive (effect -0.0000916, 95% CI [-0.000417,+0.000234]).

## Adaptation costs and leakage boundaries

The saved Phase 5 implementations distinguish generating-regime IDs from decoder-grid IDs; the corrected protocol requires using completed prior blocks only. Yet the archived small dynamic results do not jointly establish (a) calibrated detector-to-utility prediction, (b) reliable selection under transition delay, and (c) net advantage after switching/rebuild overhead. Phase 5D/5E are summary-only and have no saved shot arrays for independent shotwise reanalysis. The online study also lacks a matched accounting of syndrome history, estimator calls, graph rebuild CPU/memory, periodic baseline refresh, and activation latency.

## Determination

Existing evidence demonstrates *possible disagreement* and some retrospective complementarity, but not a stable causal mapping from observable-only confidence to future decoder utility. Against the best available fixed comparator, realizable improvement has not been demonstrated. The inference gap is more important than the compute gap: more complicated switching cannot create utility when the candidate bank’s ranking is weak or when observed data do not identify it in time.

