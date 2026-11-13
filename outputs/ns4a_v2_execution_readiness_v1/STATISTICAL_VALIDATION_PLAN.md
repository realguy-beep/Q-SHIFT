# Statistical validation plan and pre-freeze issues

This plan preserves V2's proposed estimand and procedures; it does not implement them or change the scientific protocol. The older V1 statistical-design file is retained unchanged but its four-condition/eight-candidate selection section is superseded for V2 by the six-condition/twelve-candidate V2 revision.

## Endpoint and independent unit

For each of the six evaluation conditions `c` and ten independently seeded root clusters `r`, compute paired `d[c,r] = (errors_BM - errors_selected_PM) / 4000`. The primary finite-cell estimand is `theta = (1/6) sum_c mean_r d[c,r]`; negative favors BM. Keep BM and PM predictions paired on identical shot rows. Report per-condition effects, per-root values, discordances, zero-error cells and equal-condition aggregate. Do not use pooled-shot weighting. Relative reduction is undefined if selected-PM errors are zero.

The independent unit is the root-condition cluster; shot-level McNemar may be descriptive only. Selection is performed on independent selection roots. The primary evaluation interval is conditional on the globally selected candidate and does not incorporate finite-grid selection-rank uncertainty; report the separate selection-rank bootstrap alongside it and label baseline selection instability explicitly.

## Required procedures from V2

- **Primary interval:** 100,000 root-stratified paired bootstrap replicates. Within each condition, resample its ten evaluation roots with replacement, keep both decoder outcomes paired for each selected root, compute each condition mean, then the equal-weight mean over six conditions. Use the percentile two-sided 95% interval. Keep actual zero cells as zero; do not add continuity corrections. Resampled zero/identical effects remain ties. The percentile/quantile interpolation convention is not specified in V2 and must be explicitly fixed before the analysis source freeze.
- **Sign-flip sensitivity:** 100,000 two-sided assignments; within every condition independently multiply each root's paired difference by an independent Rademacher sign; calculate the same equal-condition statistic; use add-one p-value. This is not a randomized treatment test. Interpret only with independent roots and a defensible symmetric root-level null; inspect zeros, skew and condition heterogeneity. It is assumption-sensitive with ten roots/condition and zero inflation.
- **Selection-rank bootstrap:** within each of six selection conditions, resample the eight roots with replacement, preserving paired candidate scores on each root; recompute all twelve equal-weight scores and deterministic ranks. Report candidate score distributions and rank frequencies. V2 does not specify the replicate count or seed; both remain unresolved and must be approved before a final freeze.
- **Secondary family:** the three V2 contrasts are BM vs ordinary PM on the selected DEM; BM vs correlation-enabled PM on that DEM; selected fixed PM vs nominal ordinary PM. Apply Holm to three valid p-values and report raw plus adjusted values. V2 does not explicitly identify the inferential procedure that supplies these secondary p-values. Do not silently assume that the primary sign-flip test applies; obtain a written decision before freezing the analyzer.
- **Per-condition exploration:** condition-level estimates and intervals are exploratory. If condition-level p-values are shown, a separate six-test family/correction rule must be predeclared; otherwise do not present unadjusted significance claims.
- **Root sensitivity:** show leave-one-root-out results and a root-level t interval as labeled sensitivity analyses, as V1's statistical specification states and V2 retains. Neither is confirmatory.

## Acceptance tests for later implementation

Use deterministic synthetic count fixtures only in this prepare-only stage (none were generated in this task). Before any actual runner implementation is frozen, tests should verify: paired-root resampling preserves decoder pair identity; equal condition weights despite 1,333/1,334 selection allocation; deterministic ties and stable rank ordering; 0/0 error cells remain zero and relative reduction is undefined at a zero comparator; duplicate roots fail; signs are independently assigned by root-condition; add-one p-values are bounded and deterministic for a fixed seed; Holm monotonicity and family order are correct; bootstrap output has exactly 100,000 replicates; and the independent auditor reproduces the analysis without importing the runner's statistic functions.

The V2 progression gate is an exploratory feasibility screen only: integrity pass, primary point estimate favors BM, the prespecified root-bootstrap 95% upper endpoint below zero, and at least four of six condition means favor BM. Passing only permits a request to review another development protocol; it does not authorize expansion or establish superiority.

## Items requiring explicit pre-freeze resolution

1. Select and record the percentile quantile convention used for both CI endpoints.
2. Specify which valid root-cluster procedure supplies each of the three secondary p-values before Holm correction.
3. Set the selection-rank bootstrap replicate count and tie-frequency reporting rule.
4. Freeze distinct numerical seeds for selection, evaluation, selection-rank bootstrap, primary bootstrap and sign-flip only after the separately authorized collision-screen stage.
5. Confirm that all root IDs are independent cell-root clusters and ensure the resampler/sign-flipper maps one sign or resampled index vector to each paired root cluster, not per shot or decoder.

These are specification gaps identified by inspection; this package does not choose a procedure, allocate seeds, or run statistical simulations.

## Statistical limitations

Ten evaluation roots per cell provide a small number of independent clusters. Percentile-bootstrap coverage may be poor under skew or zero inflation; sign-flip calibration depends on a symmetric null that is not guaranteed by decoder assignment. The estimand is only the equally weighted mean over six selected synthetic cells. The selected baseline is the winner among a finite grid; rank instability can make “strongest fixed” uncertain. These limitations must remain in the final reports even if the screen is favorable.
