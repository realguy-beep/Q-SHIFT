# Stage 5 secondary-inference amendment candidate v1

Created prospectively after the failed secondary Welch/Holm design validation and before any Stage 5 sampling. The original Stage 5 v2 protocol, n=1,210 primary design validation, and failed Welch/Holm reports remain unchanged. This file does not authorize sampling.

## Unchanged design

- Endpoint B: equal-weight mean of the four nonzero-condition root-paired adaptive-minus-fixed logical error rate differences.
- Practical boundary −0.0002; planning alternative −0.0003; 1,210 independent roots per each of five conditions; 27,225,000 planned total calibration plus evaluation shots.
- Frozen circuit/noise model, 2,000 detector-only calibration shots/root, 2,500 paired evaluation shots/root, decoder arms, p=0 safety endpoint, all primary critical values, conditions and acceptance rules remain unchanged.
- The selected profile-adaptive PyMatching method remains the Stage 4C refit. No CNN or adaptive controller is added.

## Replaced secondary procedure

The four condition-level one-sided tests retain their root-level mean nulls and Holm family at alpha .05. Only the invalid Student-t reference p-value construction is replaced. The full procedure and proof scope are in `PROSPECTIVE_METHOD.md` and `STATISTICAL_JUSTIFICATION.md`.

The candidate constructs a studentized root-mean statistic and calibrates an upper-envelope CDF across six frozen, centered unit-variance shape families. It adds a six-way Bonferroni DKW upper margin, uses right-continuous CDFs for ties, and applies Holm to four conservative marginal p-values. On the event that the six DKW upper bands hold (probability at least .999), each test is super-uniform under its finite location-scale family for any nonnegative mean; Holm then provides strong FWER control under arbitrary dependence across the four condition tests. The unconditional finite-envelope upper bound is .051. This is not a distribution-free guarantee.

One-sided condition upper confidence bounds invert the same test; Bonferroni alpha .0125 gives simultaneous four-condition 95% coverage. No secondary power threshold is added because none existed in the frozen protocol. The design validation reports per-condition, any-condition and all-four Holm rejection probabilities with Monte Carlo intervals.

## Statistical evidence and limits

The independent design simulation used one million reference statistics per shape and 200,000 root-level replicates for every shape at both variability scales. It covered 192 marginal-size cells, 516 complete/partial-null FWER cells, 12 simultaneous-coverage cells and 24 secondary-power cells. The independent replay and corrected Wilson reporting must pass before this amendment is eligible for Stage 5 readiness.

Inference remains conditional on the six specified location-scale root-effect families and independent sampling of roots within condition. The synthetic design exercise does not establish the actual Stage 5 root-effect distribution. Unmodeled distributions, dependence among roots, and uncertainty in the historical seven-root SD estimates remain limitations.

## Sampling guard

The new runner's `--preflight` path builds circuits/graphs and regenerates the fixed reference CDFs without calling a Stim sampler. Sampling requires both `--run` and `--authorize-stage5-sampling`; readiness, hashes, and preflight are not authorization. Stage 5 evaluation shots generated in this task: zero.
