# Review of proposed 240,000-shot pilot

## Proposal under review

The original NS-0 draft proposes 12 fresh roots in each of two stationary conditions (`p_burst=0` and `.01`), 10,000 paired shots per root: 24 roots and 240,000 paired shot rows. It is a development decoder comparison, not an engineering-only pipeline pilot and not independent confirmation. It does not count the separate detector-only tuning-root data needed to choose the strong static PM profile. With a new tuning allocation, total generated rows exceed 240,000; exact overhead cannot be calculated until tuning root/shot budget is frozen.

The current HAMLD adapter does not preserve the Q-SHIFT decomposed DEM semantics and cannot be executed in the available environment. Therefore the 240,000-shot design is premature. Do not produce roots or sample pending resolution.

## Analytic paired precision scenarios

For an evaluation shot define paired difference `X=I(candidate error)-I(baseline error)`. Let `q=P(X≠0)` be total paired discordance and `δ=E[X]`. Under independent shots within root, `Var(mean X in one root) ≈ [q−δ²]/m`, with `m=10,000`. To reflect root heterogeneity add `τ²`. If two conditions each have 12 independent roots and are equally weighted, approximate `SE(δ̄)=sqrt(q/m+τ²)/sqrt(24)`. The following two-sided normal calculations use alpha .05 and target absolute improvement 0.0002; they are **planning approximations**, not a power guarantee. Root-level t/cluster inference with only 12 roots per condition has less stable tail calibration.

| Paired discordance q | Assumed root SD τ | SE | Approx 95% half-width | Approx 80%-power detectable absolute effect | Approx power for |δ|=.0002 |
|---:|---:|---:|---:|---:|---:|
| .001 | .0000756 | .0000664 | .000130 | .000186 | .854 |
| .0025 | .0000756 | .0001032 | .000202 | .000289 | .491 |
| .01 | .0000756 | .0002047 | .000401 | .000574 | .164 |
| .001 | .0002 | .0000764 | .000150 | .000214 | .745 |
| .0025 | .0002 | .0001099 | .000215 | .000308 | .444 |
| .01 | .0002 | .0002082 | .000408 | .000583 | .161 |

The first τ value (`0.0000756`) is an exploratory historical variance component estimate from Stage 4’s four nonzero strata (7 roots each): pooled over strata, `max(0, sample root-difference variance − q/2500)` with q from Stage 4 paired discordances. This has only 24 historical root effects and is not a reliable universal heterogeneity estimate. `q=.0025` is the observed Stage 4 nonzero paired discordance `(30+145)/70,000`; `.001` and `.01` are explicit lower/higher sensitivity scenarios. Historical Stage 4 nonzero primary difference was `−0.00164286`; using it as the true future effect would produce encouraging arithmetic but would circularly assume the old development effect transports. It must not be treated as prospective power or confirmation.

For comparison, the marginal binomial SE for a single LER near the historical fixed-nominal nonzero rate `506/70,000=.0072286` with 120,000 shots per arm is about `sqrt(2p(1-p)/120000)=0.000345`, but that ignores paired covariance, two conditions, roots and selection. The paired/root calculation above is the more relevant planning approximation.

## Three purposes must stay separate

1. **Engineering feasibility pilot:** small, deterministic/mock pipeline validation; does not need generated decoder outcomes and is the useful next step while HAMLD is blocked.
2. **Development decoder comparison:** fresh tuning roots plus fresh paired evaluation roots; answers whether a compatible decoder has practical headroom; does not confirm superiority.
3. **Independent confirmation:** only after development selection and a frozen confirmatory protocol; untouched data, hypotheses, conditions, inferential plan and independent root source. No confirmation is authorized.

## Resource and decision criteria

No Q-SHIFT HAMLD runtime/RAM number is supportable because its extension did not build and no decoder benchmark was performed. The published paper’s d=3/r=3 speed ratio is not an r=5 Q-SHIFT projection. Before any owner authorization, record build environment, peak RSS, graph/DEM construction, tuning/calibration cost, per-shot p50/p95/p99 latency and total wall time separately. Owner must prespecify practical LER margin and maximum incremental runtime/RAM; neither should be selected after evaluation. Keep matched per-root paired inference and retain unfavorable/failed root results.

**Recommendation:** do not authorize 240,000 shots now. Resolve the deterministic HAMLD input/parser blocker first; then run a deterministic engineering integration check. If a semantics-preserving implementation becomes available, calculate a complete tuning-plus-evaluation budget and seek separate approval for the smallest useful fresh development comparison. No power or improvement claim is made here.
