# NS-4A V2 Statistical and Power Assessment

**Scope:** Review of the proposed 64,000-shot selection / 240,000-shot evaluation design. No evaluation outcomes or new samples were accessed or generated.

## Estimand and allocation

For each condition `c` and evaluation root `r`, define

`d[c,r] = (BM errors[c,r] − pooled-fixed PM errors[c,r]) / 4,000`.

The primary estimate is `theta = (1/6) Σ_c (1/10) Σ_r d[c,r]`. The equal condition weighting matches the finite six-cell target, and the same 4,000 evaluation detector/observable rows are scored by every arm. Pairing is at the root and shot level; uncertainty must be computed over roots, not treating all 240,000 shots as independent clusters.

Selection has 8 roots per condition (48 total, 1,333/1,334 shots each). Evaluation has 10 roots per condition (60 total, 4,000 shots each). The six analysis streams are selection-rank bootstrap, primary bootstrap, primary sign-flip, and three distinct secondary sign-flip streams. The seed validator checks the exact roster and uniqueness, but numeric seeds and historical collision evidence are not allocated/available yet. Different numeric seeds alone do not prove statistically independent roots; generation and collision provenance must be frozen.

## Primary interval

The addendum specifies 100,000 stratified paired bootstrap resamples, sampling ten roots with replacement separately within each condition and carrying both decoder outcomes together; condition means are then equally weighted. The two-sided percentile 95% endpoints use NumPy 2.2.6 `quantile(method="linear")`. This is internally aligned with the estimand and preserves the paired root structure.

The limitation is the number of clusters: ten roots per condition is small for a nonparametric cluster bootstrap. If root effects are skewed, heavy-tailed, heterogeneous, or zero-inflated, percentile coverage may be poor; many zero differences can make the bootstrap distribution highly discrete. Increasing bootstrap replicates reduces Monte Carlo error in the quantiles but does not create more independent roots or repair coverage. The prespecified root-level t and leave-one-root-out intervals are useful sensitivity summaries, not guarantees of coverage. No actual root variance or coverage simulation for this specific outcome distribution is available.

Selection and evaluation partitions are disjoint by design. Therefore the primary interval can be interpreted conditionally on the calibration-selected global model. The separate 20,000-replicate selection-rank bootstrap reports ranking instability from the eight selection roots per cell, but its uncertainty is not propagated into the primary interval. The analysis must show both; a stable evaluation contrast against an unstable selected comparator requires especially cautious interpretation.

## Sign-flip and Holm audit

The root-level sign-flip implementation flips each of the 60 condition-root paired differences independently and calculates the equal-condition statistic. It uses 100,000 Monte Carlo assignments, two-sided absolute-statistic extremeness, equality counted as extreme, and the add-one correction. Its stated assumptions are independent root-condition clusters and a symmetric root-level null (or a justified sharp-null exchangeability argument). Decoder arm was not randomized; therefore this is assumption-sensitive sensitivity inference, not a randomization test. Independence, symmetry, and calibration cannot be established before actual roots exist.

The secondary family contains exactly three prespecified contrasts: BM versus selected-DEM ordinary PM; BM versus selected-DEM correlation-enabled PM; and selected PM versus nominal ordinary PM. Holm adjustment is valid only if the three input p-values are valid; it controls familywise error under arbitrary dependence among valid p-values. Because these inputs are sensitivity sign-flip p-values, Holm does not cure their symmetry/exchangeability limitations. The selected model is itself data-selected, so secondary results should remain conditional on selection and labeled exploratory.

The primary endpoint is an interval/feasibility gate, not a confirmatory hypothesis test. The six cell means, the “at least four of six favor BM” gate, root-level plots, and any additional subgroup summaries are exploratory; they must not be promoted as multiplicity-controlled claims. Shot-level McNemar is explicitly descriptive only.

## Practical effect and power

The only numerical effect language in the V2 config is an aspirational 45–50% relative LER reduction; it is expressly not a success threshold. No absolute minimum worthwhile effect or non-inferiority margin is defined. The gate requires a negative primary estimate and a percentile upper endpoint below zero, plus at least four negative cell means. It can therefore pass for a statistically directional but practically trivial effect. It also has no separate formal no-harm bound for the three zero-burst cells; an average can mask a meaningful harm in one of them.

No empirical power estimate is defensible: the V6 readiness benchmark retained no observables or logical labels and computed no LER; hence it provides no paired discordance rate or root-level variance. The V2 sample size was described as bounded feasibility allocation, not a power claim.

For scale illustration only, if root-level paired differences have equal standard deviation `sigma` in every cell and the 60 root-condition units are independent, then `SE(theta) = sigma / sqrt(60)`. A normal-approximation two-sided 5% / 80% power MDE is approximately `(1.96 + 0.84) SE = 0.3616 sigma`:

| Hypothetical root-level SD `sigma` | Approximate MDE |
|---:|---:|
| 0.00025 | 0.000090 |
| 0.00050 | 0.000181 |
| 0.00100 | 0.000362 |
| 0.00200 | 0.000723 |

These are analytic scenarios, not observed variances, formal power for the specified bootstrap gate, or predictions of Q-SHIFT performance. They assume equal variance, independent roots, approximate normality, and no extra selection uncertainty. Root-level heterogeneity or zero inflation can materially reduce power and invalidate the approximation. A second shot-level approximation would require a paired discordance rate that the V6 benchmark deliberately did not measure; none is imputed here.

## Statistical disposition

The estimand, paired root design, equal-cell weighting, separate selection stream, deterministic tie-breaking, and fixed Holm family are coherent for an exploratory finite-set comparison. The proposed root bootstrap and sign-flip are transparently labeled, but sample size and inference are not adequate grounds for confirmatory claims. Before an execution authorization is considered, the protocol owner should explicitly decide whether the aim remains directional feasibility or whether a practical margin and formal power are required. That decision must be prospective and cannot use V2 evaluation labels.
