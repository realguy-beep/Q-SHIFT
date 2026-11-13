# NS-4A Statistical Design

**Proposed only; not frozen or authorized.** No statistical analysis was run for this protocol package.

## Estimand

For evaluation condition `c` and independent root `r`, let `d[c,r] = (errors_BM[c,r] - errors_PooledPM[c,r]) / shots[c,r]`. Negative values favor BeliefMatching. The primary finite-condition estimand is the equal-condition-weighted mean

`theta = (1/6) * sum_c mean_r(d[c,r])`.

This treats each of the six specified strata equally instead of allowing the burst strata or higher-error conditions to dominate through a pooled shot total. Report the absolute difference in LER and relative reduction `(LER_PooledPM - LER_BM) / LER_PooledPM`; report relative reduction as undefined if the pooled comparator has zero errors. The estimand is limited to this finite set of six generator conditions and does not imply performance over a population of hardware devices or noise models.

## Paired outcomes

Each arm decodes identical evaluation detector rows. Per root and condition report:

- `BM_only_failures`: BM predicts the wrong observable while pooled PM is correct.
- `PM_only_failures`: pooled PM is wrong while BM is correct.
- Both wrong, both correct, and total shot count.
- Prediction disagreement count/rate and paired error difference.

The paired shot-level McNemar statistic can be shown descriptively. Its ordinary binomial p-value must not be presented as primary evidence because shots within a root share a generated circuit/noise stream and root is the independent replication unit.

## Primary interval and paired test

Use a **root-stratified paired bootstrap** with 100,000 resamples: within each of the six conditions, sample the 10 evaluation root IDs with replacement; retain each selected root's paired BM/PM counts together; recompute each condition mean and then the equal-weight mean. Report the percentile 95% interval and bootstrap seed from the subsequently collision-screened inventory. Resampling is at root level, not shot level. With only 10 roots per condition, percentile coverage can be poor, especially for skewed/zero-inflated root effects; show the root values, leave-one-root-out sensitivity, and a root-level t interval as a labeled sensitivity analysis. No CI is described as confirmatory.

As a paired test sensitivity, use a two-sided Monte Carlo root-cluster sign-flip test with 100,000 assignments and add-one p-value. Within each condition, independently multiply each root's paired difference by a Rademacher sign, then compute the same equally weighted statistic. This test requires independent roots and a symmetric root-level null distribution (or a justified sharp-null exchangeability argument); there was no randomized assignment of decoder policy, so it is not a randomization test. Inspect root-difference skew, zeros, and condition heterogeneity. If severe asymmetry/zero inflation makes sign symmetry implausible, label its p-value assumption-sensitive and do not make a significance claim; preserve bootstrap/root data as descriptive evidence. Do not substitute a shot-level test.

The six-condition composition is fixed before data collection. The primary test is single and one-sided in the favorable direction only if a one-sided hypothesis is approved in the final freeze; otherwise report a two-sided p-value and two-sided CI. This proposal defaults to two-sided inference, with direction interpreted from the estimate, to avoid directional cherry-picking.

## Multiplicity

One primary contrast: BM versus the selected pooled-fixed PM. No multiplicity correction is needed for that one predeclared contrast, but its status remains exploratory.

Prespecified secondary root-cluster contrasts form a three-test Holm family:

1. BM versus ordinary PM using the selected DEM.
2. BM versus correlation-enabled PM using the selected DEM.
3. Selected pooled-fixed PM versus nominal ordinary PM.

Apply Holm at familywise 0.05 to secondary p-values, while reporting raw and adjusted values. Six per-condition primary contrasts are exploratory; report unadjusted estimates/intervals and a separate Holm-adjusted family of six only if p-values are displayed. No post-hoc subset of conditions is allowed. Candidate selection scores are not confirmatory tests.

## Selection uncertainty and rank stability

The pooled fixed model is selected from eight predeclared configurations using only the 64,000-shot selection partition. Use equally weighted means across the four selection conditions, not a shot-pooled score if condition shot counts differ. Report every candidate's condition and aggregate LER, root-level bootstrap rank frequency, and exact tie-breaking. Use a dedicated selection-rank bootstrap stream, separate from the primary interval and sign-flip streams. If the selected rank is unstable across root resamples, flag the primary “strong baseline” as uncertain. Do not use evaluation labels to replace it. Do not call the lower evaluation LER of an unselected candidate the strongest baseline; such a value would be retrospective and exploratory only.

## Precision sensitivity (not a power claim)

Let `q` be the paired discordance probability, approximately `P(BM wrong, PM right) + P(PM wrong, BM right)`, and let `tau` be the between-root standard deviation of a condition-specific true paired LER difference. Under equal conditions/roots, small effects, independent roots, and binomial within-root variation, an optimistic variance approximation for `theta` is

`Var(theta) ~= tau^2 / (6*10) + q / (6*10*4000)`.

The table gives a normal-approximation 95% half-width for hypothetical values. The proposed 10 roots × 4,000 evaluation shots per condition yields an optimistic half-width about 0.000473 when `q=0.010` and `tau=0.001`; that is the planning rationale for this bounded allocation. Neither `q` nor `tau` is estimated by the five-row fixture. These are sensitivity calculations, not predicted performance, type-I error validation, or a sample-size/power guarantee. With only 10 clusters per condition, small-sample bootstrap/t critical values and skew can make the realized interval wider.

| Hypothetical paired discordance q | Between-root SD tau | Approx. 95% half-width |
|---:|---:|---:|
| 0.001 | 0 | 0.000127 |
| 0.001 | 0.0005 | 0.000179 |
| 0.001 | 0.0010 | 0.000283 |
| 0.005 | 0 | 0.000283 |
| 0.005 | 0.0005 | 0.000310 |
| 0.005 | 0.0010 | 0.000380 |
| 0.010 | 0 | 0.000400 |
| 0.010 | 0.0005 | 0.000420 |
| 0.010 | 0.0010 | 0.000473 |

This approximation omits small-root finite-sample effects, selection uncertainty, root/condition interaction, skew, and zero inflation. Inference must use actual paired root clusters. No 45–50% reduction is presupposed or used as a pass threshold.

## Development-only progression gate

The gate controls whether to **propose** a larger development design, never automatic execution or confirmation. Require: (a) all identity, pairing, alias-safety, seed, and leakage checks pass; (b) no unresolved decoder output failures; (c) primary estimate favors BM; (d) the root-stratified 95% interval's upper endpoint is below zero; and (e) at least four of the six condition-level point estimates favor BM. Otherwise conclude NO-GO or INCONCLUSIVE for scaling and preserve all data. Passing does not establish superiority; a follow-up needs its own approved practical-effect margin, power plan using observed root variability, fresh collision-screened seeds, and explicit authorization. The 45–50% relative reduction remains aspirational only.
