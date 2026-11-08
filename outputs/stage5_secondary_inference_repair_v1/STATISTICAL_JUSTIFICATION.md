# Statistical justification for the Stage 5 secondary repair

## Why the former procedure failed

The prior condition-level procedure formed four one-sided Student-t/Welch-reference p-values from independent root-level paired logical-error differences, then applied Holm at family alpha 0.05. Holm controls a family only when its input p-values are valid. In 200,000-replicate complete-null checks, the original p-values were anti-conservative for right-skewed lognormal and tied/asymmetric root effects: FWER reached 9.3815% at 1.5x variability and 6.9295% in the tied/asymmetric 2x case, against the frozen 5.2% Monte Carlo upper-bound gate. Independent replay reproduced the failures. The failure is driven by a poor reference distribution for skewed and discrete root-level statistics; Holm cannot correct it. The Student-t reference remains a reasonable exact reference for normal samples, but its use for all listed shapes was unsupported.

## Chosen condition-level procedure

For each of the four nonzero noise conditions, the analysis reduces paired shot-level outcomes to one mean difference per independent root and tests `H0: E[X] >= 0` against `E[X] < 0`. The statistic is `T = sqrt(n) mean(X) / sd(X)`, with `n = 1,210` roots. The inferential scope is explicitly limited to six centered, unit-variance location-scale families: normal, standardized Student-t(5), standardized Student-t(3), standardized lognormal, a 65%-zero-inflated normal, and the specified 65%-zero / 28%-lower / 7%-upper tied asymmetric distribution.

One million independent reference statistics are generated for each family. The candidate p-value is the maximum of the six empirical lower-tail CDFs plus a two-sided DKW upper margin, capped at one. With six references, `M=1,000,000`, and total DKW failure probability `delta=0.001`, `epsilon = sqrt(log(12/delta)/(2M)) = 0.0021671019736932244`. The empirical CDF uses `searchsorted(..., side='right')`, so an atom tied with the observed statistic is included on the conservative side.

For a specified family, the DKW event makes its true CDF no larger than the empirical CDF plus epsilon, uniformly over the statistic. Under a nonnegative location shift, adding the shift increases each sample's studentized mean while leaving the sample standard deviation unchanged. Thus the zero-mean boundary is least favorable for the lower-tail test. Taking the maximum across families gives a conservative p-value for every member of the frozen finite family on that event. Holm then provides strong familywise control at 0.05 under arbitrary dependence among the four tests. Allowing for the DKW failure event gives an unconditional bound of at most 0.051. This is a finite-family guarantee, not a distribution-free guarantee.

The same tests are inverted for condition-level upper confidence bounds. Bonferroni alpha `0.05/4 = 0.0125` gives simultaneous four-condition 95% upper bounds. The primary equal-weight Endpoint B procedure, practical boundary `-0.0002`, planning alternative `-0.0003`, allocation, and separate zero-burst safety endpoint remain unchanged from the historical Stage 5 design.

## Why alternatives were not selected

- The prior Student-t/Welch reference demonstrably fails the frozen size requirement under required skewed and tied distributions.
- A root sign-flip or randomization test would require symmetry/exchangeability assumptions not justified for the root-effect differences, particularly under skew and ties.
- A conventional bootstrap or studentized bootstrap could improve approximation, but its finite-sample tail control for the composite mean null and listed irregular distributions would be an additional unverified assumption. Simulation-only calibration would not establish that property.
- A distribution-free bounded-outcome interval for a root difference in `[-1,1]` is valid but too conservative at `n=1,210` to resolve a `0.0002` practical boundary; it is not a useful replacement at this allocation.

## Limits and safeguards

The guarantee assumes independent roots within each condition and that the root-effect law belongs to one of the six prespecified location-scale families. It does not cover unmodeled shapes, dependent roots, temporal drift across roots, or misspecification of the seven-root historical SD estimates used to set variability scenarios. The Monte Carlo validation checks implementation and operating behavior within the specified families; it cannot prove that actual Stage 5 effects follow them. The procedure is a predeclared secondary analysis, not a way to change the primary endpoint after observing Stage 5 outcomes.
