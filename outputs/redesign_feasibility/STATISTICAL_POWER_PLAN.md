# Statistical power and analysis plan

This plan is prospective. No new data were generated and no sample size has been selected from final outcomes.

## Primary comparison

Use paired root/schedule clusters. For each independent root, generate a prespecified dynamic noise schedule and one held-out detector/observable stream. Score online weights, pooled fixed, nominal fixed, and periodic recalibration on that identical stream. The primary contrast is the schedule-stratified equal-weight mean of `LER_online − LER_pooled_fixed`, including calibration/warm-up and update delays. The critical dynamic-baseline contrast is `LER_online − LER_periodic`; decide before freeze whether this is co-primary (recommended if the intended claim is online cadence value) or a Holm-controlled secondary.

Per-shot discordance and McNemar results are useful conditional on a sampled stream but do not replace root-level inference. Independent roots/schedules are the units for generalization. Keep stationary, abrupt, gradual and randomized schedule strata fixed in advance; do not drop a difficult stratum after inspecting results.

## Practical-effect margin

For initial feasibility planning, reuse the prior headroom study's proposed threshold: a useful gain must be at least **5% relative and 0.0001 absolute LER reduction** against the pooled fixed baseline, and must also beat periodic recalibration. This is a provisional decision threshold, not a result derived by this assessment. If calibration predicts baseline LER too low for the absolute margin to be attainable, stop and rejustify the margin using an explicit application cost before freezing; do not relax it after seeing evaluation outcomes.

## Variance and sample-size selection

1. On independent development roots only, estimate the distribution and variance of root-level paired effects, including between-schedule heterogeneity and the probability of zero-error roots.
2. Preserve root clusters in power simulations; model within-root shot dependence and schedule strata. Do not treat millions of shots from a few roots as millions of independent experimental units.
3. Choose root count and shots/root before final evaluation to achieve at least **80% power** at two-sided `α = 0.05` for the predeclared practical margin on the primary contrast. Use a paired root-cluster sign-flip/permutation test if its exchangeability assumptions hold; use all sign assignments when feasible, otherwise **100,000 Monte Carlo assignments** from a frozen analysis RNG stream. Calculate a **95% root-cluster bootstrap interval with 100,000 resamples**, stratified by the frozen schedule strata and resampling independent roots within strata. If an alternative studentized method is required, specify and validate it before test freeze. Report raw root-level values alongside the interval.
4. Set a maximum shot/root and root count from the compute budget after a measured development benchmark. If the planned design cannot reach 80% power within that cap, do not run an underpowered confirmatory test; report a feasibility no-go or revise the question before a new freeze.

The power calculation must account for schedule-stratification, initialization/warm-up, transition censoring, model-construction time and any multiplicity. Estimate bootstrap/permutation calibration by a separate fixed RNG stream recorded before final sampling. Freeze resample count, seed, test statistic, tie handling, missing-root handling and all endpoints.

## Secondary endpoints and multiplicity

Predeclare a small family: online vs periodic; online vs nominal fixed; online vs privileged regime-informed reference only as descriptive or separately labeled; plus estimator delay and error effects as descriptive. If inferential secondary claims are made, use Holm correction across the exact frozen family. Report raw and adjusted p-values. Do not turn hindsight best-per-root or hidden-regime labels into selectable policies.

## Stopping and interpretation

- If the upper confidence bound is below the negative practical margin, evidence supports a practically meaningful improvement in this tested domain.
- If the interval excludes improvements as large as the margin but includes zero, conclude that a benefit of that size was not supported; do not claim exact equivalence outside the tested conditions.
- If the interval is wide, the result is inconclusive and should not be described as “no effect.”
- If no utility headroom exists during independent calibration, stop before dynamic testing.
- If causal tracking does not beat periodic recalibration, do not claim online cadence value even if both beat a weak nominal decoder.
