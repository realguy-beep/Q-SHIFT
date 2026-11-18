# Decision report: adaptive and broadly robust Q-SHIFT, milestone 0 (2026-11-18)

**Branch:** `codex/qshift-adaptive-robust-v1`, created from `cdbd9d8fb` on `codex/qshift-correlated-decoder-v1-6`.

**Scope of this milestone:**
- audit, design, isolated prototypes, deterministic synthetic tests;
- one diagnostic on existing Stage S **development** arrays.

**What it did not do:**
- no new Stim datasets;
- no Stage E or other frozen evaluation rows read;
- no seals opened;
- no historical file modified;
- no dependency installed.

## 1. What was inspected and verified

- **Records, code and tests** (`BASELINE_AUDIT.md`):
  - the git state;
  - the core registry and controller source;
  - the BP+OSD implementation;
  - the records of every study line (exact d=3, d=5 BP+OSD, robustness, learned support, mismatch, Stage E, d=7, Stage 5, strong fixed, Phase 4, neural);
  - pre-change regression suites.
- **Five record discrepancies** are documented, not resolved by preference. One is a pre-existing hash mismatch in a historical neural-dashboard config that makes one dashboard test error. It is unmodified and needs an owner decision.
- **Literature:** 18 metadata entries verified by web search; the rest are marked as unverified (`LITERATURE_REVIEW.md`).

## 2. What was implemented and tested

Everything is in `outputs/qshift_adaptive_robust_v1/` (new files only).

| File | Purpose | Tests |
|---|---|---|
| `adaptive/estimation.py` | Robust per-class background scale; burst-detector outliers (H-E1) | 5 |
| `adaptive/changepoint.py` | Calibrated two-sided binomial CUSUM (H-E2) | 2 |
| `adaptive/regime.py` | Posterior regime classifier with a deviance-based UNKNOWN (H-E3) | 2 |
| `adaptive/pipeline.py` | Causal controller on the existing `SafeDecoderSelector`; detector-only API | 3 |
| `benchmark/endpoints.py` | Pooled weighted R, root-cluster bootstrap, G_AGG / G_EVERY with Holm, eligibility, power | 6 |
| `benchmark/suite.py` | Draft broad benchmark: dev/val/eval/ood splits, fresh eval geometries | 3 |
| `floor_diagnostic.py` | Background-floor diagnostic on Stage S dev failures | output: `results/floor_diagnostic/` |

**Test results:**
- `python -m unittest discover -s outputs/qshift_adaptive_robust_v1/tests -v`: **21/21 pass**. All inputs are synthetic numpy Bernoulli arrays from literal seeds; no Stim.
- **Regressions after the change** were re-run and are unchanged from the baseline:
  - dashboard: 118/120 pass, with the same 2 pre-existing errors;
  - low-p: 13;
  - mismatch: 6;
  - learned support: 24;
  - robustness: 9;
  - phase4c: 6.

**Floor diagnostic** (`BACKGROUND_ERROR_ANALYSIS.md`), on 56 dev failures:
- BP converged on 20% of failures, against 99.3% of successes.
- **18% of failures are search-limited:** a more likely correct-class error exists.
- **82% are MLE-consistent.**
- Simple search variants fix 3–12 failures each, with 0 breaks in 600 controls. That control sample is far too small to establish safety.

## 3. The strongest defensible research direction

The recommended direction is **attribution-first, strong-comparator adaptive decoding.** Build the deployable Q-SHIFT controller (robust background scale → change detection → calibrated regime/UNKNOWN → hysteretic selection among strong decoders). Evaluate it on the broad benchmark against S\*, the best *deployable static* decoder selected on validation, with Q vs Q0 as the primary adaptiveness test.

The contribution is a credible answer to three questions:
- whether adaptation adds anything beyond hypergraph inference and calibration;
- how much each component contributes (`BASELINE_FAIRNESS.md` ablations);
- whether mismatch-robust support inference fixes the Phase C failure.

## 4. Why it may improve broad-noise performance

1. **Mismatch is the documented failure point of the current learned method.** It causes 0/24 learning when p is lower than assumed and 24/24 false accepts when p is higher. A global mis-scale is separable from a local burst using detector marginals; the synthetic support is in `EstimationTests`. Fixing this turns "works only with an exactly known base model" into "works under ±17% and bias". That is the main robustness gain available.
2. **Temporal change is unhandled by every static arm.** With a step change in the benchmark, a static decoder is mis-specified on one side of the step. CUSUM plus re-selection with hysteresis can recover that, provided the change is detectable within about 10 blocks.
3. **The floor has a fixable part.** About 18% of failures are search-limited and better search removes them. The remaining, larger part needs degeneracy-aware decoding (ensembles or belief-matching).

## 5. Is 95% aggregate reduction feasible?

- **In one favourable regime (d=5, p=0.001): uncertain, near the boundary.**
  - Stage E reached 94.0% [92.3, 95.5] with oracle support.
  - Removing the search-limited share of the floor projects to about 95.0%; the "any variant fix" share projects to about 95.8%.
  - Clearing **G_AGG** (lower bound ≥ 0.95) there would need a true R of about 0.97 and about 500+ comparator failures.
- **Across the proposed broad benchmark: implausible with current methods.**
  - The benchmark keeps p = 0.003 conditions on purpose, and there the historical R is 60–65%, set by the background floor.
  - Pooled weighting by baseline risk makes those conditions dominant.
  - **G_EVERY** (≥ 95% in every eligible condition) is more implausible still.
  - Reaching either gate would require roughly a 10× reduction of BP+OSD's background floor at p = 0.003, and no evidence here suggests that is available. The floor is 82% MLE-consistent, so degeneracy-aware decoding recovers only part of it.
- **What to do with that:** the benchmark is **not** reshaped to make 95% reachable. The 95% gates are reported as pre-specified secondary targets, and the primary claims are H1a and G_ADAPT.

## 6. Main threats to validity

The full list is in `RISK_REGISTER.md`. The main ones:
- **R2:** adaptation adds nothing over a strong static arm (the historical prior).
- **R3/R4:** information leakage or unequal labels.
- **R7:** synthetic tests over-state the prototypes.
- **R8:** undetected breakage from floor variants.
- **R10:** overlap with Bhardwaj et al. 2025 and Takou & Brown 2025.
- **Oracle dependence:** every confirmed d=5 result used the true support or the true base model.

## 7. The smallest discriminating next experiment

**Roadmap step 1, the floor re-decode.** Re-decode all 1.2 M existing Stage S dev shots with two pre-declared variants: min-sum 0.9, and OSD_CS-40 + BP-200.
- **Sampling and cost:** no new sampling; about 30–45 min on 8 workers.
- **The hypotheses it separates:**
  - **H-F1:** the floor is partly search-limited and fixable cheaply. Supported if a variant's net change has a 95% upper bound < 0 with no q=0 harm.
  - **H-F2:** the floor is degeneracy-dominated. Supported otherwise, which redirects effort to ensembles or belief-matching.
- **Why it is the most decision-relevant step:** it decides whether the 95% target is even near-reachable in the favourable regime.

**A close second is roadmap step 2:** test H-E1 on the existing mismatch Phase A dev arrays (`qshift_d5_model_mismatch_v1/work/diag_arrays`, 145 files present).

## 8. Files, commits, commands, approvals

- **Files:** `outputs/qshift_adaptive_robust_v1/`, containing:
  - the 11 documents;
  - `adaptive/`, `benchmark/`, `tests/`;
  - `floor_diagnostic.py`;
  - `results/floor_diagnostic/{FLOOR_DIAG.json, floor_rows.json}`;
  - `README.md`, `.gitignore`.
- **Commit:** the milestone commit on `codex/qshift-adaptive-robust-v1` (see `git log`). The owner authorized the push for this task.
- **Commands to reproduce:**
  - `python -m unittest discover -s outputs/qshift_adaptive_robust_v1/tests -v`
  - `python outputs/qshift_adaptive_robust_v1/floor_diagnostic.py`. This needs the local, git-ignored Stage S dev arrays; it is deterministic and takes 167 s.
- **Approvals required next, each separate:**
  1. "Run floor re-decode" (roadmap step 1): decode only, existing dev arrays.
  2. "Run H-E1 on mismatch dev arrays" (step 2): existing dev arrays.
  3. Dev sampling for the broad benchmark (step 4), which creates a new dataset.
  4. Val sampling and selections (step 5).
  5. Freeze sign-off and sealing of the fresh eval geometries (step 6).
  6. The frozen eval run (step 7) and the OOD run (step 8).
  7. Optionally, a `beliefmatching` dependency install with a pinned-version plan, if step 1 supports H-F2.
  8. An owner decision on the `structured_diagnostic_config.json` hash discrepancy.
- **Not done, by design:** no PR was opened and nothing was merged.

## Addendum (2026-11-18): roadmap step 1 completed

The floor re-decode, pre-registered in `600551456` and reported in `REDECODE_RESULTS.md`, returned **H-F2_FLOOR_DEGENERACY_DOMINATED**.
- **Min-sum 0.9:** net +15 failures [+3, +27] over 1.2 M development shots, which is significantly worse.
- **OSD_CS-40 + BP-200:** net −1 [−9, +7], no detectable effect.

**Effect on §5:** the projected 95.0–95.8% at p = 0.001 is withdrawn. The best figure remains Stage E's 94.0%, and broad-benchmark 95% stays implausible.

**Effect on §7:** the smallest next experiment is now roadmap step 2 (H-E1 on the existing mismatch development arrays). Degeneracy-aware decoding (ensembles or belief-matching) is the only remaining lever on the floor.

## Addendum (2026-11-18): roadmap step 2 (H-E1) completed

The test was pre-registered in `fcd9b8834` and is reported in `HE1_RESULTS.md`. Verdict: **H-E1_PARTIAL**. The unchanged Phase C learner was re-based on a background p estimated from each pool's unlabeled detector rows. The estimate lands within about 1% of the true p.
- **Mlo:** learned pools went from 0/24 to **24/24**.
- **Mhi:** false accepts went from 24/24 to **0/24**, with 24/24 still learned.
- **Control:** unaffected. Its burst-free margin improved (largest Δ fell from 1,544 to 362, against τ = 1,561).
- **Z-bias (Mz):** still fails (0/24). Bias changes the shape of the detector-rate pattern, not only its level, so a bias-aware base model is required.

**Effect on §3–§4.** Mismatch-robust support inference is now the program's strongest development-level result. The next steps are:
- H-E1b: a (p, bias) fit on the existing Mz pools;
- an end-to-end decode check under mismatch, which needs small new development samples;
- a fresh-seed validation screen.
