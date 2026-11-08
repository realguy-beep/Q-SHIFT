# Prospective Stage 5 secondary-inference method

Created before the new statistical validation. This is a new candidate amendment; it does not change the historical Stage 5 v2 protocol, n=1,210 design validation, or failed Welch/Holm records.

## Failure being repaired

The frozen candidate's one-sided Student-t reference p-values are not valid for all the root-effect shapes used in the design envelope. At n=1,210, complete-null Holm FWER was 9.3815% for right-skew lognormal at 1.5x and 6.84–6.93% for tied/asymmetric roots. Holm controls multiplicity only when its marginal p-values are valid; it cannot repair those anti-conservative inputs. Skewness drives the clearest failure; point masses and ties also invalidate the continuous Student-t reference. Unequal root variances do not alone explain the failures because the problem persists after the per-condition standard-error estimate, and normal/t-family cases mostly passed. The old validation and its independent replay remain untouched.

## Candidate procedure

For each of the four nonzero conditions, let `X_1,...,X_n` be the independent root-level paired LER differences, with `n=1210`. Test the one-sided mean null `H0: E[X] >= 0` against `E[X] < 0` using `T = sqrt(n) * mean(X) / sd(X)`.

The explicitly bounded inferential model is a finite, prespecified **location-scale family** of six centered, unit-variance root-effect distributions: Normal, standardized Student-t(5), standardized Student-t(3), standardized lognormal with log-scale 1, a 65%-zero-inflated Normal, and the frozen 65%-zero/28%-lower/7%-upper tied asymmetric distribution. Each is tested at both historical SD multipliers (1.5x and 2x) and all four historical condition SDs. The test is scale invariant. For a fixed standardized sample, increasing the null mean shifts `T` monotonically to the right, so calibration at mean zero is least favorable for every `E[X] >= 0` in these location-scale families.

Before validation, simulate one million independent `T` statistics from each of the six exact generating families. For each reference CDF `F_s`, construct the upper empirical bound `Fhat_s(t) + epsilon`, capped at one, where `epsilon = sqrt(log(2*6/delta)/(2*M))`, `M=1,000,000`, and `delta=0.001`. This is the two-sided Dvoretzky–Kiefer–Wolfowitz bound with a union bound across six references. Set `p_env(t) = max_s min(1, Fhat_s(t)+epsilon)`, using right-continuous empirical CDFs (`searchsorted(..., side='right')`) so all tied statistics are included conservatively.

On the event that all six DKW bounds hold (probability at least 0.999), each `p_env` is super-uniform for any member of the specified finite family and every nonnegative location shift. Holm step-down at family alpha .05 then controls strong FWER at .05 conditional on that event, under arbitrary dependence among the four tests. Unconditionally the theoretical bound is at most .051. This guarantee is **not distribution-free** and does not cover unmodeled root-effect shapes, dependence among roots, or non-location-scale changes. Such shapes remain a limitation, not something the Monte Carlo validation can prove away.

## Confidence bounds and reporting

For condition-level one-sided upper confidence bounds, invert the same `p_env` test. Use alpha .05/4=.0125 for four simultaneous 95% bounds; report marginal 95% bounds separately as descriptive. The cutoff is the first observed reference statistic where any conservative envelope CDF exceeds alpha; reject only for statistics strictly below that cutoff. Right-continuous CDFs keep a tied atom on the nonrejection side, making inversion conservative. The primary equal-weight endpoint, its existing calibrated confidence procedure, p=0 safety endpoint, and all historical gates remain unchanged.

## Frozen validation design

- 1,210 roots per condition; four nonzero-condition tests; original four Holm comparisons and alpha=.05.
- All six families at both 1.5x and 2x; 200,000 independent Monte Carlo replicates per validation family/scale cell, matching the stronger prior secondary-validation requirement.
- Validate marginal p-value size at all four Holm thresholds with simultaneous one-sided Wilson bounds across 192 cells; retain the historical requirement `upper <= threshold + .002`.
- Validate complete-null FWER and all 14 nonempty proper true-null subsets (1–3 true nulls) under false-null effects −0.0003 and −0.01, plus least-favorable false-null p-values set to zero. This is 516 FWER cells, 200,000 replicates each. Use simultaneous one-sided 95% Wilson upper bounds across all 516 and require each `<= .052`.
- Validate simultaneous one-sided upper-bound coverage across all four conditions for all twelve family/scale cells (each of six root-effect families at both 1.5x and 2x). Use 200,000 replicates per cell; simultaneous Wilson lower bound must be at least .94.
- Report secondary power under all four conditions shifted by −0.0003 and −0.0004, with per-condition Holm rejection rates, any-condition and all-four rejection rates, and Wilson intervals. This is 24 power cells. The historical protocol specifies no separate minimum secondary-power gate; none is added here.
- Use PCG64 seeds in the new `STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json`, disjoint from every recoverable nonsealed Stage 4/5 seed metadata value. Statistical validation streams are never Stage 5 experiment streams.
- Run a separately implemented audit from the frozen seeds and compare all calibrator fingerprints, counts, Wilson bounds and outputs.

## Prespecified decision

The method passes only if all stated marginal-size, complete/partial-null FWER, simultaneous-coverage, reproducibility and integrity criteria pass. Failure means Stage 5 remains NO-GO; do not increase the sample allocation or revise endpoints automatically. Passing establishes readiness only within the stated model envelope and does not authorize Stage 5 sampling.
