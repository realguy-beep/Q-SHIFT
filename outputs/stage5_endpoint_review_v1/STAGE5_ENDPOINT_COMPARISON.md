# Stage 5 endpoint comparison — prospective review v1

**Status: proposed design review only.** This file does not amend or replace the historical Stage 5 candidate or v2 freeze, authorize Stage 5 sampling, or change any saved development evidence. No Stage 5 or sealed-test samples were generated or accessed for this review.

## Common estimand and sampling unit

For each of four nonzero burst-probability strata (j\in\{.004,.008,.012,.016\}), calculate one root-level paired difference

\[
d_{jr}=LER_{adaptive,jr}-LER_{fixed,jr}
\]

from both decoder arms evaluated on the same 2,500 shots. The target is the equal-weight mean across the four stratum means, \(\Delta=\frac14\sum_j E(d_{jr})\). A root—not a shot—is the inferential unit: calibration data select the adaptive decoder for that root, so shots within a root share that calibration/model and are not independent replications. Keep p=0 as a separate safety/no-harm condition.

The saved Stage 4 and Stage 4C development summaries provide seven roots per nonzero stratum each. Using the larger SD per condition gives \(K=\sqrt{\sum_j s_j^2/16}=0.0006429101\), so the planning SE is \(K/\sqrt n=0.0000642910\) at 100 roots per stratum. Those seven-root estimates are very uncertain; this calculation is a scenario, not a power guarantee.

## Endpoint A — improvement over zero

**Primary hypothesis:** one-sided, prespecified \(H_0:\Delta\ge0\) vs \(H_1:\Delta<0\), alpha .05. The practical magnitude −0.0002 is an effect-size benchmark reported with the estimate and interval; it is not this test's null or a pass threshold.

At 100 roots per nonzero stratum and the saved SD scenario, power is about 92.9% for a one-sided 5% test at true \(\Delta=-0.0002\) (about 87.5% for a two-sided 5% sensitivity analysis). However, when the true effect equals −0.0002, the probability that the point estimate is at or below that same value is about 50%. Thus, a zero-null test can show evidence of some improvement while the data remain uncertain about whether the practical benchmark is exceeded. Report the estimate and 95% interval relative to both 0 and −0.0002; do not convert the benchmark into a second hidden gate.

**Strength:** answers the broader scientific question “does the calibrated method improve mean LER at all?” with the current proposed budget plausibly informative under the assumed variance.

**Limitation:** statistical evidence for a tiny improvement can be positive even when it is not practically useful. Wording must distinguish “below zero” from “at least 0.0002 lower.”

## Endpoint B — improvement beyond the practical threshold

**Primary hypothesis:** one-sided, prespecified \(H_0:\Delta\ge-0.0002\) vs \(H_1:\Delta<-0.0002\), alpha .05. A claim of practical improvement requires the one-sided 95% upper confidence limit to be below −0.0002.

This directly tests the benefit that would matter for the project. Power must be specified at a target alternative strictly beyond the boundary: the null boundary itself has rejection probability alpha. At 100 roots per stratum, estimated power is about 46% if true \(\Delta=-0.0003\) (only .0001 beyond the margin), 92.9% at \(-0.0004\), and 99.9% at \(-0.0005\), assuming the development SDs transfer. Under the same assumptions, 80% power for a .0001 gap needs 256 roots/stratum (5.76 million total shots across five strata); 90% needs 354 (7.965 million). The current 2.5-million cap allows 111 roots/stratum and cannot support the .0001-gap target. For a .0002 gap, 64 roots are projected for 80% power and 89 for 90%, but that corresponds to true \(\Delta=-.0004\), twice the margin.

Heterogeneity sensitivity at 100 roots/stratum illustrates the risk: for a true effect −0.0003, power falls from 46.4% at the point SD estimate to 34.4%, 27.2%, and 19.3% when the SD is 1.25×, 1.5×, and 2× larger. For true −0.0004, corresponding power is 92.9%, 80.1%, 66.6%, and 46.4%. Even using all 111 roots allowed by the existing cap, the −0.0003 alternative reaches only about 49.8% power at the nominal SD and 29.0% at 1.5× SD. The sample-size calculations scale approximately with the square of the SD multiplier.

**Strength:** aligns the confirmatory claim with practical utility and prevents “significant but negligible” improvement being called success.

**Limitation:** requires the owner to defend the 0.0002 margin and choose a scientifically plausible planning alternative. Designing only for a large effect (e.g. −0.0004) risks low power for modest-but-real benefits. The seven-root variance estimate and observed between-study SD differences make the current sample-size assurance weak.

## Root pairing, heterogeneity, intervals, and tests

Pair each decoder on exactly the same evaluation samples; form the per-root rate difference before inference. Do not bootstrap shots. The equal-stratum estimator has estimated variance \(\hat V=\frac1{16}\sum_j s_j^2/n_j\). A transparent primary interval/test for the mean is a heteroskedastic Welch–Satterthwaite t procedure applied to the four independent stratum means, with its effective degrees of freedom calculated from the four variance contributions. This explicitly accommodates different root variances by noise stratum and directly targets the equal-weight mean. With about 100 roots/stratum, it is more defensible for a mean than a root sign-flip test whose exactness depends on symmetry. It still relies on independent roots and a large-sample approximation; it is not distribution-free.

Use a **paired, stratum-preserving root bootstrap-t** as the prespecified sensitivity interval: resample complete root differences independently within each p stratum, studentize each replicate, and preserve the equal-stratum weights. Do not resample individual shots. A conventional percentile bootstrap can be reported as a secondary descriptive check, but should not decide success alone. Bootstrap coverage can be poor with few clusters and skew; published cluster-trial simulations caution that the bootstrap is not automatically better than robust mean-based intervals and results depend on cluster count and outcome distribution. That evidence comes from cost outcomes in cluster trials, not QEC, so it motivates checking coverage rather than dictating a method ([Flynn & Peters, 2004](https://pmc.ncbi.nlm.nih.gov/articles/PMC535558/)). If Welch and bootstrap-t materially disagree, label the primary result **inconclusive** and investigate without changing the frozen endpoint.

No empirical 95% coverage study is claimed here. Available planning SDs summarize only seven roots per source cell, too few to establish tail shape or reliable bootstrap coverage. Before a new freeze, simulate operating characteristics (coverage and type-I error) under a prespecified range of root-level normal, skewed, heavy-tailed, and zero-inflated paired-effect distributions, including 1.25×, 1.5×, and 2× SD scenarios. These are design simulations only and must not use Stage 5 outcomes. The final report should retain this limitation even if those simulations support nominal performance.

The current root sign-flip test is not a decoder-arm randomization test because decoder arms are not randomized. Its exact reference distribution requires root effects to be sign-symmetric under the null (or a justified exchangeability construction); zero mean alone does not establish this. Discrete LER differences, many ties, and possible asymmetric root effects make that assumption unverified. Paired sign or signed-rank methods would answer a median/symmetry question, not the desired mean LER contrast. Hutson and Yu discuss the symmetry assumptions and interpretive limits of common paired sign-based tests ([2022, *The American Statistician*](https://doi.org/10.1080/00031305.2022.2110938)).

## Multiplicity and safety

Choose A or B before any Stage 5 data; do not make both co-primary and select whichever passes. Under B, the single threshold test is primary. Under A, the zero test is primary and −0.0002 remains a benchmark. Keep the four condition-specific comparisons in a Holm family for any condition-level inferential claims; all condition point estimates may be displayed, but a consistency gate alone is not evidence of four separate effects. Treat p=0 as a separately predeclared no-harm condition with a one-sided upper limit relative to +0.0002. If overall success requires both primary benefit and p=0 no-harm, the claim is an intersection-union decision: every required component must pass; do not promote any one component alone as overall success. Any additional confirmatory claims need their own multiplicity plan.

## Recommendation

For a project whose claim is that adaptation is **practically useful**, Endpoint B is the more scientifically defensible primary. The current 100-root design is adequate only for a comparatively large effect under the point variance estimate; it is not robustly powered for a modest improvement just beyond the margin. Do not sample under B with the current frozen allocation unless the owner accepts this limitation and the updated decision rule prospectively. A is defensible if the scientific question is explicitly narrowed to any mean improvement, provided claims are restrained and the practical benchmark stays descriptive. Either choice requires an approved, versioned amendment and a new freeze; neither alters the existing v2 protocol by implication.
