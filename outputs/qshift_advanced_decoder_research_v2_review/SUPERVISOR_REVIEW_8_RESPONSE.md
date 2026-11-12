# Supervisor Review #8 — Correction Response

**Status:** revised review package; no experiment authorized.

**Branch/base reviewed:** `qshift-advanced-research`, `d4cc12b70353c79f30c4219f0ea831c3bcee69c7`.
**Original seven Phase 2 files remain unchanged and historical.** Corrections below are in a separate directory.

## Response by finding

| Finding | Correction in this package | Original document(s) | Effect |
|---|---|---|---|
| Design A had no independent policy-tuning allocation | Add disjoint tuning roots and disjoint detector-only pooled-static calibration roots; evaluation roots are never used to select policies. Recount A/B/C budgets. | `EXPERIMENT_BUDGET_OPTIONS.md`, `PRE_REGISTRATION_DRAFT.md`, `BASELINE_FAIRNESS_MATRIX.md` | Changes budget and data partition; estimand unchanged. |
| Sensitivity table was described too much like power, interval was unspecified, four strata and shared fit randomness were underspecified | Re-derive the four-stratum variance; label z calculations as sensitivity only; define a stratified Welch stream-mean interval and a conservative finite-sample Hoeffding reference; state conditional inference and outer-bundle requirement for unconditional inference. | `STATISTICAL_FEASIBILITY.md`, `PHASE2_RESEARCH_PROTOCOL.md`, `PRE_REGISTRATION_DRAFT.md` | Clarifies analysis and scope of inference; estimand remains equal-weight average over four nonstationary strata. |
| Historical per-stream development evidence was not used | Deterministically reaggregate the saved Pilot 2 result rows for event versus its development-selected static arm: q=31/104,000=0.0002981; conditional stream-variance SE=0.00005723; one-sided Welch upper endpoint=+0.00000888 for a different, restricted four-scenario estimand. This is not confirmation and is not transportable to the detector-only comparator. | `STATISTICAL_FEASIBILITY.md` | Adds a labeled planning reference; no change to proposed estimand. |
| Primary static comparator was underspecified and risked being read as optimal | Specify the equal-weight mixture of four primary schedule strata, detector-only profile fitting, p-grid 0.000 to 0.020 by 0.002, standardized squared profile distance, and lower-p tie-break. Explicitly call it a pooled compromise, not a global optimum. | `BASELINE_FAIRNESS_MATRIX.md`, `PHASE2_RESEARCH_PROTOCOL.md` | Makes comparator operational; estimand unchanged but comparator is now fixed. |
| Cost components and deployment horizon were ambiguous | Give a CPU equation separating per-policy bank build, tuning, calibration, cached construction, update, switching/rebuild and decoding. Provide H=160 and H=1,000 sensitivity points and a proposed all-in CPU guard; owner must freeze H. | `BASELINE_FAIRNESS_MATRIX.md`, `EXPERIMENT_BUDGET_OPTIONS.md`, `PRE_REGISTRATION_DRAFT.md` | Changes operational decision rule, not LER estimand. |
| Detector-only identifiability and mismatch design were unresolved | Bound conclusions to the 45 observed features; propose analytic DEM-derived feature expectations, a two-parameter Jacobian rank/conditioning check, and a separate independent measurement-flip p=.006 vs assumed .003 stress condition at fixed burst p=.008. No sampling performed. | `PHASE2_RESEARCH_PROTOCOL.md`, `SUPERVISOR_REVIEW_REQUEST.md` | Adds structural audit and separate stress stratum; primary estimand unchanged. |
| 0.0002 LER margin lacked justification | State it equals 0.02 percentage points and no utility/cost derivation currently supports that exact value. Show alternatives and z-separation sensitivity; owner must choose a margin before evaluation. | `STATISTICAL_FEASIBILITY.md`, `PRE_REGISTRATION_DRAFT.md`, `SUPERVISOR_REVIEW_REQUEST.md` | Keeps 0.0002 provisional, not endorsed or data-selected; decision rule remains unfrozen. |

## Independently checked arithmetic

The original expected-count table is arithmetically correct for N×p. The design-effect entries and standard errors in the original sensitivity table reproduce to rounding under the stated `q=.006`, `K=4`, equal-S/equal-n approximation. Its `2.4865×SE` column is only a Gaussian separation heuristic; it is not finite-cluster formal power. The prior budget totals were incomplete because tuning was not separated in Design A and pooled-static calibration was omitted from all three designs. The revised totals are 486,000 / 1,406,000 / 10,666,000 unique shots. Raw storage arithmetic reproduces: 10.26M×41=420.66 MB and adding 16 bytes/shot yields 584.82 MB decimal, before overhead.

Historical development computation reads only the already-preserved Pilot 2 `PILOT2_RESULTS.csv` outcome summary and paired contingency columns. It does not read a seed inventory or any protected evaluation source. The results, eligibility limitations, formulas and hashes are recorded in `CORRECTED_STATISTICAL_DESIGN.md` and the source manifest.

## Remaining disagreement / review needed

There is not enough evidence to call 0.0002 an operationally justified effect size, to claim the 45-feature estimator identifies burst probability under measurement mismatch, to establish correlation-aware headroom for this graphlike event, or to make an unconditional-over-calibration claim from one shared tuning/calibration bundle. The proposed Welch interval is implementable but does not guarantee finite-sample coverage under sparse/skewed stream differences; the distribution-free bound is valid but too wide to be useful at proposed budgets. Those are open scientific decisions, not resolved by wording changes.

PR #1, frozen V2.4 files, Stage 4 historical outputs, and the original Phase 2 documents were not modified. No experiment, sampling, training, decoder benchmark, or authorization record was created.
