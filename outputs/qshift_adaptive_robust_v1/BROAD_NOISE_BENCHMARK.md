# Broad-noise benchmark (DRAFT design; nothing sampled)

The machine-readable draft is `benchmark/suite.py`. It becomes binding only after it is frozen with hashes and the owner authorizes sampling.

## Design principles

1. **A justified subset, not a Cartesian product.** Each axis is varied one or two at a time around anchor conditions that the historical studies already understand. Two deliberate multi-factor OOD conditions test interaction.
2. **Four disjoint splits, each with its own seed namespace** (`qshift-adaptive-robust-v1:{dev,val,eval,ood}`), collision-screened against every prior inventory before freezing:
   - **dev:** method development. Anything goes, all of it reported.
   - **val:** model selection, threshold and comparator selection (S*), and decoder-variant selection. It is used once per selection decision and logged.
   - **eval:** fresh frozen evaluation. It includes **fresh burst geometries** that do not appear in dev or val (enforced by test), drawn and sealed before the freeze.
   - **ood:** out-of-distribution conditions, never used for any selection: weight-4 bursts, a two-family mixture with bias, mismatch and drift, and an exploratory d=7.
3. **The 95% goal is stated but not engineered.** Eval includes the p = 0.003 conditions where history predicts a cap near 65%. They are **not** removed to make 95% reachable. A pooled 95% verdict must survive them, or the report states that it does not.

## Axes and the conditions that cover them

| Axis | dev | val | eval | ood |
|---|---|---|---|---|
| Distance | 3, 5 | 5 | 3, 5 | 7 (exploratory) |
| Background p | 0.002–0.003 | 0.0015–0.003 | 0.001, 0.002, 0.003 | 0.002–0.003 |
| Burst q | 0, 0.01, 0.02 | 0, 0.02 | 0, 0.01, 0.02 | 0.02 |
| Burst geometry | scaled_v1 | centre_row | fresh A, fresh B (sealed) | weight-4 fresh; two-family mixture |
| Measurement- vs data-heavy | — | measurement-heavy | both | — |
| Biased Pauli | — | z_biased | z_biased | z_biased + mixture |
| Assumed vs true background (mismatch) | 0.83, 1.17 | — | 0.85, 1.20 | 1.1 |
| Temporal change | static | step | step | ramp |

Eval has 10 burst-present conditions (the primary endpoint) and 3 burst-free conditions (the safety endpoint). See `suite.py`.

## Endpoints (computed by `benchmark/endpoints.py`)

- **Primary:** the pooled weighted relative reduction, R_pool = 1 − Σ_c w_c·LER_c(Q) / Σ_c w_c·LER_c(S*).
  - It runs over **eligible** burst-present eval conditions, with equal weights (w_c = 1) and is computed from pooled failures and shots.
  - This deliberately weights by absolute baseline risk: a condition where S* fails often contributes more failures. That is the operationally meaningful aggregate. A mean of per-condition ratios would let a near-zero-risk condition dominate.
- **Reported alongside:**
  - per-condition absolute LER for every arm;
  - per-condition R with CI;
  - **worst-condition R**;
  - **macro-averaged R** (the mean of per-condition R; descriptive only);
  - burst-free safety;
  - latency (CPU ms per shot, median and p99);
  - calibration shots consumed;
  - adaptation delay (blocks from change onset to a switch);
  - recovery time (blocks from a regime's end to the return to fallback).
- **Zero- and near-zero-error handling, frozen before evaluation:**
  - A condition is **eligible** for the R gates only if the *projected* S* failures, from validation-split rates × frozen shots, reach ≥ 30.
  - Ineligible conditions are reported descriptively, with exact Clopper–Pearson LER bounds, and never enter or leave the gate after results are seen.
  - A bootstrap replicate with zero comparator failures is undefined. A bound is reported only if < 1% of replicates are undefined.

## Gates (STATISTICAL_PROTOCOL.md)

- **G_AGG:** the one-sided 97.5% lower bound of R_pool is ≥ 0.95.
- **G_EVERY:** every eligible condition rejects H0: R_c ≤ 0.95 under Holm at overall α = 0.025.
- **G_SAFE:** the burst-free safety criterion holds in all 3 burst-free conditions.
- **G_ADAPT:** Q − Q0 < 0 (lower-is-better) with its 95% upper bound < 0 on the pooled endpoint. This is the adaptiveness ablation.

A point estimate ≥ 0.95 alone **never** establishes success (`test_point_estimate_alone_cannot_pass`).

## Feasibility arithmetic (for planning, not a promise)

**Comparator failures needed to clear 95%.** From `endpoints.required_comparator_failures` (log-ratio delta method, Poisson, at about 50% power):
- if the true R = 0.97, about 500 S* failures are needed in the pooled endpoint (about 15 for Q);
- if the true R = 0.96, about 2,000.

Plan for twice these counts to reach about 80% power.

**Expected pooled R if history transfers.** Using history as priors, R ≈ 0.94 at p = 0.001, about 0.78 at p = 0.002 and about 0.60–0.65 at p = 0.003. The pooled R is then dominated by the higher-risk p = 0.003 conditions, so **G_AGG at 0.95 is implausible** unless the background floor at p = 0.003 falls by an order of magnitude. See `DECISION_REPORT.md` §5.
