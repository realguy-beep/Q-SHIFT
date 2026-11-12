# Statistical Feasibility — Deterministic Sensitivity Analysis

**No stochastic simulation, sampling, or decoder run was performed.** Calculations below are analytical approximations using explicitly labeled planning ranges. Pilot 2 counts and estimates are historical development evidence, not confirmatory evidence and not inputs used as if known future variance.

## Planning reference and expected counts

Pilot 2's historical nominal reference was 478/87,500 = 0.546% LER; Pilot 2 event errors were close in scale to fixed/EWMA, and paired differences were small. These are only rough rate anchors. For an evaluation set of N shots, expected arm counts under assumed LERs 0.003, 0.006 and 0.010 are `N × p`:

| Scored shots in one arm | 0.3% LER | 0.6% LER | 1.0% LER |
|---:|---:|---:|---:|
| 80,000 | 240 | 480 | 800 |
| 200,000 | 600 | 1,200 | 2,000 |
| 900,000 | 2,700 | 5,400 | 9,000 |
| 4,000,000 | 12,000 | 24,000 | 40,000 |

These counts describe an arm's expected errors, not precision of the paired difference. Pairing precision depends on discordance (fraction of shots where two policy losses differ), stream heterogeneity and temporal dependence.

## Paired stream sensitivity model

For paired loss difference `D ∈ {-1,0,1}`, let `q=P(D≠0)` be the discordant-pair rate and let `ρ` be an approximate within-stream intraclass correlation for D. With K=4 equally weighted primary nonstationary strata, S independent streams per stratum and n scored shots per stream, use the design-effect approximation:

`DE = 1 + (n − 1)ρ`

`SE(mean difference) ≈ sqrt(q × DE / (K × S × n))`.

This treats strata as independent and balanced, neglects the usually small squared mean term in Var(D), and approximates dependence by one ICC. It is a sensitivity calculation, not a fitted variance model. Between-stream heterogeneity is represented only indirectly by the assumed ICC; real stream-specific means, unequal variances, event-time effects and nonexchangeable time dependence can produce wider intervals. A confirmatory plan needs empirical stream summaries from authorized development data and a validated analysis method.

For one-sided 5% type-I error and 80% normal-approximation power, the detectable separation beyond the null boundary is `(z.95+z.80)×SE = 2.4865×SE`. To establish the practical claim against margin −0.0002 when the true effect is −0.0004, SE must be at most 0.0000804. A true effect of exactly −0.0002 has no power to clear a strict margin.

### Sensitivity at q=0.006

Table entries show SE, two-sided 95% normal half-width, and 80% detectable separation beyond the practical margin. Values are absolute LER units.

| Streams/stratum × shots/stream | ICC ρ | Design effect | SE | 95% half-width | 80% separation |
|---:|---:|---:|---:|---:|---:|
| 20 × 1,000 | 0 | 1.000 | 0.000274 | 0.000537 | 0.000681 |
| 20 × 1,000 | 0.001 | 1.999 | 0.000387 | 0.000759 | 0.000963 |
| 20 × 1,000 | 0.01 | 10.990 | 0.000908 | 0.001779 | 0.002257 |
| 50 × 2,000 | 0 | 1.000 | 0.000122 | 0.000240 | 0.000305 |
| 50 × 2,000 | 0.001 | 2.999 | 0.000212 | 0.000416 | 0.000527 |
| 50 × 2,000 | 0.01 | 20.990 | 0.000561 | 0.001100 | 0.001395 |
| 500 × 2,000 | 0 | 1.000 | 0.000039 | 0.000076 | 0.000096 |
| 500 × 2,000 | 0.001 | 2.999 | 0.000067 | 0.000131 | 0.000167 |
| 500 × 2,000 | 0.003 | 6.997 | 0.000102 | 0.000201 | 0.000255 |
| 500 × 2,000 | 0.01 | 20.990 | 0.000177 | 0.000348 | 0.000441 |

For q=.002 multiply SE and widths by √(1/3); for q=.012 multiply by √2. At the 20×1,000 design, even the iid q=.006 half-width is 0.000537, already larger than the 0.0002 practical margin. Moderate allocation remains weak when ICC is only .001. The larger candidate reaches the nominal target only for low discordance and modest dependence; at q=.006, ρ=.003, the 80% separation is .000255 and no longer clears the −.0002 margin if true effect is −.0004. At ρ=.01 it is .000441. Therefore “more shots” alone does not assure useful precision; stream count and dependence are decisive.

## Design-level interpretation

- **A, 20 streams × 1,000 scored/stratum:** primary four strata contribute 80,000 scored shots. At q=.006, iid SE≈.000274 and ICC=.001 SE≈.000387. Insufficient for a 0.0002 practical effect; useful only for pipeline and gross-effect feasibility.
- **B, 50 × 2,000:** 400,000 primary scored shots. At q=.006, ICC=.001 gives SE≈.000212; 80% separation≈.000527. Still not well powered around a 0.0002 margin.
- **C, 500 × 2,000:** 4,000,000 primary scored shots. At q=.006, ICC=.001 gives SE≈.000067; nominal 80% separation≈.000167. This barely supports the margin under that assumption, and fails under larger q or ICC. It is not justified until development variance and compute are measured.

## Dependence, pairing, and interval limits

Twenty streams per scenario in Pilot 2 make stream-level bootstrap tails unstable; a percentile bootstrap cannot manufacture independent clusters. Shot-level binomial intervals are inappropriate for policy contrasts when common random numbers and temporal blocks induce pairing and dependence. A paired contingency table is useful descriptively, but the inferential unit is the independent stream/root. Report per-stream paired means, discordance, stream variance, and effective number of clusters. Consider a prespecified studentized cluster bootstrap or randomization-free cluster-robust interval only after method validation; do not use shot resampling.

Equal weighting of scenarios protects the primary estimand from a high-volume/easy scenario dominating. It also means the four scenario estimates, not pooled total shots, determine uncertainty. A separate mismatch stratum is not folded into the primary four.

## Multiplicity and decision feasibility

One primary contrast in ordinary mode avoids mode-selection multiplicity. The correlation-aware contrast and mode interaction, six condition-level contrasts, comparisons to trailing/EWMA/periodic/batch profile, and multiple operational outcomes create a substantial family if all are treated as confirmatory. Keep them secondary and descriptive or freeze hierarchical gates and Holm families before evaluation. If two decoder modes are treated as co-primary, power and multiplicity change and the design must be recalculated; do not select whichever mode looks favorable.

The practical-benefit decision requires the one-sided upper 95% bound to be below −0.0002. The one-sided criterion does not make a design precise; with unknown q and ρ, exact power is unidentifiable. A pilot should estimate these quantities and support a variance-based redesign, not be interpreted as confirmation.
