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

## Addendum (2026-11-18): H-E1b completed

The test was pre-registered in `6169c6656` and is reported in `HE1B_RESULTS.md`. Verdict: **H-E1b_SUPPORTED**.

The background p and the bias were fitted jointly from unlabeled detector rows.
- **Mz:** learned pools went from 0/24 to **24/24**, with 0/24 false accepts. b̂ was 10 in all 48 pools, and p̂ was within about 0.2% of the true p.
- **Other conditions:** Mlo, Mhi and the control stayed at 24/24 learned and 0/24 false accepts.

**Caveats:**
- The bias grid contains the true value, so an off-grid test is needed. It requires new development samples.
- p̂ is snapped to the grid, which put the control's largest burst-free Δ back at 1,544, close to τ = 1,561. A continuous p refinement is recommended.
- The decoders under mismatch are untested.

**Standing:** robust support inference is now repaired on development data for every mismatch tested. It is the program's strongest result so far, and it is still development-only.

## Addendum (2026-11-18): OG and E2E development studies completed

Both studies were frozen at `fe035cde7` and run once.

**OG: OG_SUPPORTED** (`OG_RESULTS.md`).
- The continuous (p, bias) learner learns 24/24 with 0/24 false accepts in all 5 in-family conditions whose true values lie off the grid.
- Grid snapping had produced 4–6 false accepts.
- X-bias and measurement-heavy noise are flagged in 48/48 pools each and fall back safely.

**E2E: E2E_SUPPORTED** (`E2E_RESULTS.md`).
- The full pipeline (estimate (p, b) → learn the support → decode) repairs the mismatch failure.
  - Mlo: 153 → 18 nonzero-q errors, against an oracle of 17.
  - Mz: 82 → 2, against an oracle of 2.
- There is no degradation under Mhi or the control.
- R vs matching stays at about 65% at p ≈ 0.003. At Mz, correlated matching is worse with the correct biased model. Against the best matcher present, R ≈ 91% on small counts.

**Standing:**
- **Achieved:** the "exactly known base model" caveat is removed on development data, for scalar p error and Z-bias.
- **Unchanged:** the 95% broad target remains implausible.
- **Next:** a frozen evaluation of the robust pipeline on fresh seeds, plus a wider model family (X-bias, separate measurement p).

## Addendum (2026-11-19): RE1 frozen evaluation completed

The evaluation was frozen at `fe4471fff` and run once: 78/78 jobs in 3.1 h. The analysis is byte-identical across two runs, and the recount and the root-0 re-decode match. The full report is `RE1_RESULTS.md`. Verdict: **NOT_CONFIRMED**.

- **R1–R5 (known burst K): all PASS.** On fresh seeds, at mismatch values never used in development (±13% p, Z-bias 4 and 8, combined), the pipeline decodes at oracle level. It beats the strongest deployable matcher by 59–88%.
- **R6 (sealed hidden burst, Z-bias 4): FAIL_DIRECTION.**
  - All 12 roots were flagged as misspecified: B2 objective 175–227, threshold 118.4.
  - So no burst was learned, and the nominal fallback cannot learn under Z-bias.
  - LER was 35× the oracle's.
- **Diagnosed cause:** the flag and the (p, b) fit were calibrated only on pools with burst K. An unfamiliar burst's detector footprint inflates the objective and biases b̂ (2.8 against a true 4), and a flag switches learning off entirely.
- **X1 (descriptive):** flagged 6/6 as intended. But switching learning off cost 4× against the oracle there, where the nominal learner would have found K.

**Standing:**
- **Supported (frozen):** mismatch-robust decoding for the known burst.
- **Not supported:** the same for an unseen burst.
- **Next:** a burst-robust estimator and flag on development data, then a new frozen run with a new sealed burst. H2 is spent.
- **Unchanged:** the 95% target remains out of reach.

## Addendum (2026-11-19): BRE burst-robust estimation completed

The study was frozen at `d15e5f47e` and run once: 672 pools in 58 min, about 8.6 M detector-only shots. The analysis is byte-identical across two runs, the recount matches, and the replay is bit-identical. The full report is `BRE_RESULTS.md`. Verdict: **BRE_PARTIAL**.

- **BRE-0 census (deterministic):**
  - The earlier development bursts flipped only 10–20 detectors.
  - A 30-detector burst exceeds B2's flag threshold even with no sampling noise, and biases b̂. This explains RE1's R6 failure.
- **Frozen B2 on held-out bursts:**
  - It learns every burst of up to 20 detectors, 60% of 25-detector bursts, and **0%** of 30-detector bursts.
  - It learned 77/120 held-out in-family pools.
- **E1 (one-sided adaptive exclusion):**
  - It learned **240/240** in-family burst pools, with 0 false flags and 0 false accepts.
  - It fails only out of family: under measurement-heavy noise, 3/24 held-out burst-free pools went unflagged and accepted a false burst.
- **E2 and E3 (nominal-learner fallback on a flag):** unsafe. The nominal learner accepted a false burst in 96/96 out-of-family burst-free pools.

**Standing:**
- **Achieved (development):** noise-model estimation and burst learning no longer depend on burst footprint.
- **Not achieved:** a complete pipeline whose flag also catches measurement-heavy misfit.
- **Next:**
  1. E1 plus a structural exclusion check (the excluded set must match a burst class), a post-hoc idea, tested on fresh development data;
  2. then a frozen RE2 with a new sealed burst that excludes every BRE support.
- **Unchanged:** the 95% target remains out of reach.

## Addendum (2026-11-19): BRS structural misfit check completed

The study was frozen at `4967cd7d9` and run once: 512 fresh, fully held-out pools, 6.5 M detector-only shots, in 33 min. The analysis is byte-identical across two runs, the recount matches, and the replay is bit-identical. The full report is `BRS_RESULTS.md`. Verdict: **BRS_NOT_SUPPORTED**, on a single endpoint.

**Before the run:**
- BRS-0, a design check on BRE's arrays, showed that exact shape matching would flag real bursts.
- The owner chose the subset rule. It was recorded as a deviation and fixed before BRS-1.

**What the rule did on fresh bursts:**
- Out-of-family false burst acceptance fell from 16 → 1 (measurement 1.5×), 30 → 0 (2×), 1 → 0 (3×) and 0 → 0 (X-bias).
- In family it learned 126/128 exactly, with 0 false accepts and outcomes identical to E1's.

**What failed:**
- In-family false flags, at 2/32 burst pools under p 0.0036 against an allowance of 1.
- Both came from E1's frozen residual threshold, set at the highest p seen in BRE. The statistic grows with p.

**Standing:**
- **Achieved (development):** footprint-robust estimation (BRE) and structural rejection of out-of-family misfit (BRS).
- **Not achieved:** a frozen pipeline passing all endpoints.
- **Next:**
  1. make E1's statistic scale-free, or drop it in favour of the cap plus the structural rules (post-hoc idea, untested);
  2. a short fresh development run;
  3. then a frozen RE2 with a new sealed burst.
- **Unchanged:** the 95% target remains out of reach.

## Addendum (2026-11-20): BRT threshold-free E1 flag completed

The study was frozen at `de41bf056` and run once: 512 fresh, fully held-out pools, 6.5 M detector-only shots, in 37 min. The analysis is byte-identical across two runs, the recount matches, and the replay is bit-identical. The full report is `BRT_RESULTS.md`. Verdict: **BRT_SUPPORTED**. Every pre-declared endpoint passed.

**What E1T is:** E1's one-sided fit, flagged only by the exclusion cap and the subset-rule shape and consistency checks. It has no residual statistic and no tuned parameter.

**In family** (p 0.0020–0.0040, Z-bias 3–12, all outside earlier ranges):
- 126/128 learned exactly, with 0 false accepts.
- 30-detector bursts were learned 31/32; B2 learned 1/32.
- E1's statistic drifted past its threshold again at p 0.0040. E1 and E1S lost 4–5 bursts there; E1T lost 1.

**Out of family:** false bursts went from 29 → 0 (measurement 2× at high gate p), 13 → 0 (2.5×), 0 → 0 (X-bias 4) and 13 → 1 (1.5×), comparing E1 with E1T.

**Caveat:** the in-family flag margin sits exactly at the 1/32 allowance. A single stray detector over the cutoff breaks the shape match.

**Standing:**
- **Achieved (development, held out):** a footprint- and p-robust estimator that rejects misfit without false bursts. The estimation failure behind RE1's R6 is repaired on development data.
- **Next:** RE2, a frozen decoding evaluation of E1T → learn → BP+OSD, with a new sealed hidden burst. Its exclusion rule must address the depleted pool of large-footprint classes: at most 5 eligible 30-detector classes remain.
- **Unchanged:** the 95% target remains out of reach (R ≈ 59–88%).

## Addendum (2026-11-20): AD1 adaptive decoding under drifting noise completed

The study was frozen at `3a2d0209a` and run once: 30 episodes (5 schedules × 6), 2.34 M sampler shots, in 75 min. The analysis is byte-identical across two runs, the recount matches, and episode 0 of every schedule replays bit-identically. The full report is `AD1_RESULTS.md`. Verdict: **AD1_NOT_SUPPORTED**.

**Why:** all three tracking endpoints (D1 p ramp, D2 Z-bias ramp, D4 p step) failed their second clause, that AD must beat ONCE, the frozen block-6 estimate.
- AD was within 1–6% of ORACLE everywhere, well inside the 25% allowance.
- ONCE was just as close.
- Under these drifts, re-estimating the background bought nothing measurable.

**Passed:**
- **No harm (C0):** 77 vs 74 errors.
- **Burst onset and offset (D3):** median latency 5 and 2.5 blocks, with 0 mis-learned windows.
- **Settled-window flags:** at most 1 per episode.

**Where adaptation paid:** D3, where a burst appears and then disappears. AD made 117 errors against ONCE's 156, with the CI of AD − ONCE wholly below 0. This was not a tracking endpoint, so it does not change the verdict.

**Standing:**
- **Achieved (development):** a causal rolling-window adaptive decoder. It never harmed a static stream and never learned a wrong burst. It acquired and released a transient burst within one window, and stayed near the oracle under every drift tested.
- **Not shown:** a benefit from continuous background re-estimation. The drifts tested (±20% in p, Z-bias 1 → 8) were too mild to hurt a single early estimate.
- **Lesson for the next design (post hoc, untested):**
  - the adaptive value lies in the changing burst support, not the background rate;
  - a follow-up should test larger or structural drift, such as bursts that switch or move, rather than redefining these endpoints.
- **Unchanged:** RE2 with a new sealed burst remains the frozen-evaluation step, and the 95% target remains out of reach.

## Addendum (2026-11-20): RE2 frozen evaluation with two new sealed bursts completed

The study was frozen at `67ed86c6a` and run once, with RE2's own seal opened inside the jobs only: 66 roots, 891,000 calibration and 792,000 evaluation shots, in 93 min. The analysis is byte-identical across two runs. The recount's re-analysis is identical, and root 0 of every condition re-decodes identically. The full report is `RE2_RESULTS.md`. Verdict: **NOT_CONFIRMED** (G1–G4 PASS; G5 FAIL_DIRECTION).

**Why:** in G5 (sealed burst H4), one of 12 roots was flagged by E1T (both S1 and S2) and decoded nominally.
- That root alone made 12 more nonzero-q errors than the oracle, more than the 10-error NI floor. The NI estimate was 1.25e-4 against a 1.04e-4 margin.
- The other 11 G5 roots learned H4 exactly and matched the oracle (18 vs 18).
- Whether the flag was a false alarm cannot be read from the records: the frozen scrub masks class correctness on flagged roots.

**Passed:**
- **Sealed large-footprint burst H3:** learned exactly in 24/24 roots in G3 (R6's base model) and G4, with no flags. L2L_E equalled the oracle (14 vs 14; 100 vs 100). R against S\* was 0.91 and 0.76.
- **RE1's B2 estimator on the same roots:** flagged 6/12 (G3) and 4/12 (G4). G3 errors were 292 against E1T's 14.
- **K (G1, G2):** within 1 error of the oracle.
- **SUP and q=0 safety:** passed in all five gated conditions.

**Standing:**
- **Achieved (frozen, sealed):** E1T repairs RE1's R6 failure mode for a never-seen ≥ 25-detector burst. This is conditional on H3's independence from RE1's H2: 94% under the draw distribution, untested until "Open the RE1 seal".
- **Not achieved:** the full pre-registered claim. The flag → nominal fallback is safe at q = 0, but a single flag costs more than the NI floor at these LERs and root counts.
- **Lesson (post hoc, untested):**
  - the fallback's cost, not the learning rate (59/60 gated roots), now limits the pipeline;
  - a later study could pre-register a cheaper fallback or more roots.
  - These results are not re-scored.
- **Unchanged:** H3, H4 and H2 stay sealed, and the 95% target remains out of reach.

## Addendum (2026-11-20): AD2 adaptive decoding when the burst itself changes completed

The study was frozen at `ccdfbc618` and run once from a detached checkout: 30 episodes (5 schedules × 6), every job returncode 0, in 4.3 h at fallback level 1 (AD_W3 dropped by the preflight's own rule). No seal was read. The analysis is byte-identical across two runs. The recount's re-analysis is identical, and episode 0 of every schedule replays identically (records and decoded error bits). The full report is `AD2_RESULTS.md`. Verdict: **AD2_STRONG** (every endpoint passes; E2 in 4 of 4 changing schedules).

**Errors, blocks 6–29, 144,000 shots per arm (AD / PERIODIC / ONCE / ORACLE):**
- S1 (A → B): 354 / 543 / 1,021 / 157; median latency 4 blocks.
- S2 (A on and off every 6 blocks): 2,048 / 3,515 / 3,478 / 187; median latency 3.5.
- S3 (A → C with p 0.0025 → 0.0035): 323 / 403 / 591 / 188; median latency 5.5.
- S4 (B → C → D): 258 / 332 / 430 / 116; median latency 4.
- C0 (static): 270 / 272 / 273 / 273.

**Standing:**
- **Achieved (development):** when the burst support changes, continuous adaptation beats both a single estimate and scheduled re-estimation, and matches the oracle once settled (settled errors 125 vs 126, 158 vs 153, 62 vs 62). No settled window accepted a wrong burst, and the static stream was not harmed. This answers the question AD1 left open.
- **Not achieved:** near-oracle performance through transitions. AD's excess over the oracle sits in the blocks just after a change, and a burst that toggles every 6 blocks (S2) leaves AD at 11× the oracle's errors.
- **Lesson (post hoc, untested):** the next adaptive gain is faster reaction without false flags. The 3-block window was dropped from AD2 by the preflight, so AD2 says nothing about it. AD2 is not re-scored.
- **Unchanged:** the claim boundary (d=5, public weight-3 bursts, piecewise-constant noise, simulation only), the seals, and the 95% target.

