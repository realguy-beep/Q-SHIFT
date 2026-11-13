# NS-4A V2 prospective statistical addendum — version 1

**Status: prospective clarification only. Not a freeze and not execution authorization.** This addendum is based on PR #8 commit `7e99b1495dbec401257d85d0436b4c30f25c310f`. It preserves the V2 protocol/configuration and historical evidence unchanged. No numeric production seeds are assigned here.

## Decisions

### Primary interval

- Keep the V2 primary estimand: the equally weighted mean over six conditions of the mean over ten independent evaluation roots of paired `LER(BeliefMatching) − LER(selected pooled-fixed PyMatching)`. Negative values favor BM.
- Use 100,000 root-stratified paired bootstrap replicates. Within each condition, sample its ten root clusters with replacement and retain both decoders' outcomes together for each selected root. Average roots within condition, then give each of six conditions equal weight.
- Report the two-sided percentile 95% interval using NumPy `2.2.6` `numpy.quantile(..., method="linear")` for both endpoints.
- Keep selection-rank uncertainty separate from this evaluation interval. The interval is conditional on the single global candidate selected using the independent selection partition.
- Ten root clusters per condition are few. Percentile coverage may be poor under skew, heterogeneity, or zero-inflated root effects; report root-level data, leave-one-root-out sensitivity, and the labeled root-level t sensitivity interval. No interval is confirmatory.

### Secondary Holm family

The family is exactly these three V2 contrasts:

1. BM versus ordinary PyMatching using the selected DEM.
2. BM versus correlation-enabled PyMatching using the selected DEM.
3. Selected pooled-fixed PyMatching versus nominal ordinary PyMatching.

For each contrast, calculate a root-cluster paired sign-flip Monte Carlo p-value from its own independent analysis stream:

- 100,000 assignments per contrast.
- For every assignment, independently multiply each paired root-condition difference by a Rademacher sign; compute the same equal-condition-weighted statistic.
- Two-sided extremeness is `abs(T_simulated) >= abs(T_observed)`; equality counts as extreme.
- Use add-one correction `(extreme_count + 1) / 100001`.
- Apply Holm to exactly the three raw p-values, with ties ordered by their predeclared family order. Report raw and adjusted values.

The sign-flip procedure assumes independent root-condition clusters and a symmetric root-level null (or a justified sharp-null exchangeability argument). Decoder arm was not randomized. These p-values are assumption-sensitive sensitivity evidence, not a randomized treatment test or confirmatory claim. Zero differences remain zero; if all differences are zero, every assignment is equally extreme and the p-value is 1. Shot-level McNemar remains descriptive only.

### Selection-rank uncertainty

- Use 20,000 bootstrap replicates, resampling the eight selection roots with replacement independently within each of the six selection conditions.
- Every resampled root carries all twelve candidate outcomes together; never resample candidates independently.
- Recompute all twelve equal-condition mean root-LER scores and rank them using the V2 family-major ordering, ordinary mode before correlation-enabled mode. Exact score ties retain that deterministic order.
- Report observed scores, every rank frequency, top-rank frequency, each candidate's frequency of joining a tied best-score set, and the fraction of replicates with any top-score tie.
- Use a separate `selection_rank_bootstrap` stream. Keep ranking uncertainty separate from the primary evaluation interval and do not use evaluation labels to alter selection.

## Preserved V2 design and boundaries

This addendum does not change the six finite, non-factorial noise conditions; the distance-3, five-round, 40-detector, one-observable circuit; the six assumed DEM families; the 12-candidate grid; the five named arms; the equal-condition primary estimand; the 64,000 selection + 240,000 evaluation = 304,000 unique-shot allocation; the finite-grid selection/tie rule; or the exploratory-only progression criteria. The existing review gate remains: integrity/compatibility checks pass, there are no decoder failures, the primary estimate favors BM, the primary bootstrap 95% upper endpoint is below zero, and at least four of six condition means favor BM. A pass only permits requesting review of a larger development protocol; it does not authorize execution, confirmation, or automatic expansion. The proposal remains not authorized, `sampling_authorized=false`, and `sampling_performed=false`.

The V2 disclosure of accidental historical-outcome exposure, reported non-use that cannot be independently certified, and unresolved influence/workspace-isolation risk remains unchanged. This addendum does not repeat exposed values or reclassify the incident. Research Codex remains on HOLD. Stage 5 remains out of scope.

## Seed domains clarified (no allocation)

Required domains are selection roots, evaluation roots, selection-rank bootstrap, primary bootstrap, primary sign-flip sensitivity, and three separate secondary sign-flip domains named for the individual contrast. Every numerical value, if later authorized, must be independently collision-screened and recorded before the final code/config freeze. This document allocates no values and accesses no seed inventory.
