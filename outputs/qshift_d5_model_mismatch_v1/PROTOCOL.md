# d=5 learned-support decoding under base-noise-model mismatch

**Status:** Phase A diagnostic pre-registered. It is committed before any study sample.
- **Authorized:** the owner approved the plan on 2026-11-17. That covers building the package; sampling is not yet authorized.
- **Needs a separate owner go-ahead:** Phase A sampling, and then the Phase B freeze and run.

## Question

Phase C (`9de6536b9`, CONFIRMED) found that L2 BP+OSD with a **learned** burst support beats correlated PyMatching given the true support, by 59.8% for the known burst.

That result assumed the learner, τ and every decoder use the **true** base noise model. This study asks whether the advantage survives when the data come from a different base model than the one all of them assume.

## Conditions

All conditions use d=5, 5 rounds, `model_v14`, the known burst scaled_v1 (23, 31, 34), and q ∈ {0, 0.01, 0.02}.

| ID | True model (sampler only) | Assumed model (learner and all decoders) |
|---|---|---|
| Mlo | gate and measurement p = 0.0025, balanced (−17%) | p = 0.003, balanced |
| Mhi | gate and measurement p = 0.0035, balanced (+17%) | same |
| Mz | p = 0.003, `z_biased`, bias ratio 10 | same |

## Fixed method (unchanged from Phase C; nothing is tunable)

- **Learner:** `FastParityLearner` on the nominal base DEM, with τ = 1,561.218 (`NULL_THRESHOLD.json`) and `learn_flip` at prior 0.01.
- **Decoders:** Phase C's `c_job.decode_all`, which builds every decoder from the nominal spec:
  - L2L / L2s: ldpc serial BP+OSD, static prior 0.01;
  - Astar / Astar_L: correlated PyMatching, q_dec 0.0025;
  - A_nominal.
- **Tests:** `job.py` changes only the sampler. The tests pin that its nominal-spec sampler is bit-identical to Phase C's, that `decode_all` *is* Phase C's function, and that each true-model circuit differs from nominal only in noise parameters.

## Phase A: development diagnostic (`diag.py`; informational)

- **Seeds:** `SEEDS.json` → `diag_seeds`, 315 keys in namespace `qshift-d5-model-mismatch-A-diag-2026-11-17`.
  - They are screened against 2,690 prior values, including every learned-support seed file.
  - `diag.py run` refuses to start unless `SEEDS.json` is committed and unchanged.
- **Per condition:**
  - **24 burst pools:** the calibration recipe, 4,000 detector rows plus 500 labeled rows per q, with the detector-row labels discarded unread. Each pool records the class and flip and whether they are correct.
  - **24 burst-free pools of 12,000 rows,** the size τ was calibrated at. Each records whether a burst was falsely accepted, the T statistic, and the nominal-model residuals (mean y, mean z).
  - **3 decode roots × 2,000 shots per q** on all five arms. These use the learned support of that condition's **burst pool 00**, declared here before sampling, or the base DEM if nothing was learned.
- **Total:** 72 burst pools and 72 burst-free pools (2.84 M cheap shots) plus 54,000 decoded shots. Expected well under 1 h on 8 workers.
- **Output:** `results/diag/pools/*.json`, then `diag.py aggregate` → `DIAG.json`, and a write-up in `DIAG_RESULTS.md`. Arrays go in the git-ignored `work/`.
- **No pass/fail gate.** No method parameter can be changed in response to Phase A. Phase A informs the owner's decision to freeze Phase B and gives the cost estimate.
  - If a condition learns badly, Phase B still evaluates it, because the end-to-end effect is the question.
  - Any learner remedy, such as a base-scale nuisance parameter, would be a separate study with its own gate.

## Phase B: frozen evaluation (planned here; frozen after Phase A with a separate sign-off)

- **Calibration:** one calibration job per condition, using the Phase C recipe and `seeds` → `d5mm:B:cal:*`.
- **Roots:** 24 roots × 8,334 shots per (condition, q), for 1,800,288 shots in total.
- **Arms:** as Phase C, all on the nominal model.
- **Per condition:**
  - co-primary L2L − Astar, equal-weight over nonzero q, using the 95% CI;
  - q=0 safety as in Phase C;
  - non-inferiority of L2L vs L2s, with margin 0.25 × LER(L2s);
  - R reported.
- **Overall verdict:** Bonferroni with α = 0.05/3.
  - ROBUST if every condition is GO, passes the Bonferroni CI and passes safety;
  - NOT_ROBUST if any condition is NO-GO;
  - PARTIAL or INCONCLUSIVE otherwise, using Phase C's logic.
- **Execution:** Phase C's controls apply: freeze hashes, HEAD gate, write-once, single attempt, byte-identical re-analysis, recount and root-0 re-decode.

## Claim boundaries

- d=5, the known weight-3 burst, three static mismatches, simulation only. Drift, crosstalk and leakage are untested.
- Both decoders are mismatched equally. The study measures whether the *relative* advantage survives.
- There is one learning draw per condition in Phase B.
- The d=7 STOP stands.
