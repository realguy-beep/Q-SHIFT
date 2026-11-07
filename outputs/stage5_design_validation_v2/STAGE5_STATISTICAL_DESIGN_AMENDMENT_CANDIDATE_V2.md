# Stage 5 statistical design amendment candidate v2

**Prospective design review only. Not active protocol and not sampling authorization.** This amendment is separate from, and does not edit or supersede, Stage 5 v2. No Stage 5 evaluation samples or sealed historical test data may be generated/read under this package.

## Endpoint and allocation candidates

Retain Endpoint B: the equal-weight mean of the four nonzero-condition, root-level paired LER differences (profile-adaptive minus fixed nominal) must be below −0.0002. The p=0 stratum remains a separate no-harm safety gate. Each root contributes one paired difference per condition; shots are not independent inferential units.

Compare 578, 640, and 666 roots in each of five conditions, with 2,000 calibration and 2,500 paired evaluation shots per root. Totals are 13,005,000; 14,400,000; and 14,985,000 unique shots. These allocations are design candidates only; the frozen v2 2.5M cap and 100-root runner remain unchanged.

## Candidate inference: scenario-envelope calibrated studentized mean

For each of the four nonzero conditions, compute the sample mean and variance of its root-paired differences. Estimate the target by the equal-weight average of the four condition means. Studentize by the stratified variance estimate \(\widehat V=\sum_j s_j^2/(16n)\). Roots are independent between strata; within-root pairing is retained before aggregation.

Instead of using the previously rejected Welch critical value, use a fixed, allocation-specific one-sided critical value calibrated on a *separate* Monte Carlo stream as the maximum upper-tail critical value over the complete prespecified null envelope. The envelope includes unequal condition variances, 1.5× and 2× root SD, Student-t tails, right skew, point-mass/tied effects, zero inflation, and balanced condition offsets. A separate two-sided critical pair is calibrated for 95% interval coverage. Critical values are frozen before independent validation simulations and before any Stage 5 sample.

This is a model-envelope procedure, not distribution-free inference. Its validity is limited to the simulated envelope. The simulation validation therefore has hard pass/fail rules; no critical value may be tuned on validation results. The rejected Welch method is retained only as a benchmark. Sign-flip is excluded as primary because it assumes sign symmetry. A root-stratified bootstrap-t remains a possible future alternative, but prior evidence did not establish its coverage and nested bootstrap simulation at the required scale is not used as a shortcut here. A Hoeffding bound for root effects in [−1,1] is distribution-free but expected to be far too wide to resolve a 0.0001–0.0002 LER margin at these root counts.

## Prespecified operating-characteristic criteria

Before simulation, the candidate criteria are:

1. For every independently validated primary null scenario at \(\Delta=-0.0002\), the two-sided 95% Wilson upper endpoint for rejection probability must be ≤0.052.
2. The 95% Wilson lower endpoint for one-sided upper-bound coverage at the boundary must be ≥0.94; central 95% interval coverage must also have a Wilson lower endpoint ≥0.94.
3. Use 100,000 calibration simulations and a distinct 100,000 validation simulations for each null-scenario/allocation cell. Power cells use separate 100,000-replicate streams and Wilson intervals.
4. The planning alternative is \(\Delta=-0.0003\), a 0.0001 improvement beyond the practical boundary. Recommend the smallest candidate allocation whose 95% Wilson lower power endpoint is ≥0.80 for every prespecified 1.5×-SD normal, skewed, and tied/zero-inflated scenario. Report 2×-SD sensitivity without treating it as a post-hoc gate.
5. The separate p=0 no-harm boundary is +0.0002. Its null size, upper-bound coverage, and pass probability at true effects 0 and +0.0001 are reported separately; it is a required conjunct for any eventual overall Stage 5 claim.

These thresholds are frozen before the Monte Carlo run. A failed criterion means NO-GO for this candidate; no redesign based on the same validation stream. Monte Carlo intervals quantify simulation error only, not uncertainty in the seven-root variance inputs or model-envelope adequacy.

## Multiplicity and analysis freeze

One primary Endpoint B threshold test is one-sided at alpha=.05. Four nonzero condition-specific secondary tests remain one Holm family. No switching between Endpoints A/B or inference procedures is allowed. If the primary and required p=0 safety gate do not both pass, the overall claim fails. A Stage 5 v3 runner/auditor, if later justified, must freeze the exact critical values and all code before sampling.

## No-sampling boundary

This document authorizes only synthetic statistical design simulations and use of the already completed disposable engineering benchmark. It does not authorize Stim shots under Stage 5, access to any sealed historical test data, or changes to Stage 4C, the website worktree, or v2 artifacts. Any later Stage 5 sampling requires a new versioned runner, auditor, seed inventory, integrity freeze, and separate explicit authorization.
