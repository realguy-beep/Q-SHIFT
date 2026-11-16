# d=7 decoder-configuration screen (development; protocol)

**Committed before any screen sample.** The owner authorized "Fix d=7 decoder first" on 2026-11-16 in response to `PHASE1_RESULTS.md`: V3.2 was about 2× worse than Astar_7 at d=7. This is **development data**, used to choose a BP+OSD configuration for Phase 2. It is never reused for evaluation.

## Sampling (fresh seeds, `SCREEN_SEEDS.json`)

- **Circuit:** the same as Phase 1 (`model_v14`, rounds 5, p = 0.003, scaled_v1 burst, q ∈ {0, 0.01, 0.02}).
- **d=7:** 150,000 shots per q (450,000 in total) in 6 chunks of 25,000 per q, giving 18 sampler calls.
- **d=5** (no-regression check): 50,000 shots per q (150,000) in 2 chunks of 25,000 per q, giving 6 calls.
- **In total:** 600,000 shots in 24 calls. Detectors and observables are **saved bit-packed** in git-ignored `work/screen/` for later re-decoding without resampling.

## Decoders (all on identical rows; every DEM at the true q, as in Phase 1)

| ID | Configuration | Role |
|---|---|---|
| Astar | Phase 1 selected: correlated PyMatching, q_dec = 0.0025 | comparator |
| A_nominal | PyMatching, burst-free DEM, correlations OFF | reference |
| **L0** | ldpc product_sum, parallel, max_iter 50, OSD_CS order 10 (= V3.2) | candidate |
| **L1** | ldpc minimum_sum, ms_scaling 0.625, parallel, max_iter 50, OSD_CS 10 | candidate |
| **L2** | ldpc product_sum, serial schedule, max_iter 50, OSD_CS 10 | candidate |
| **L3** | ldpc minimum_sum, ms_scaling 0.625, parallel, max_iter 50, OSD_CS order **30** | candidate |
| N3 | V3 NumPy (damped 0.5), OSD-CS 10, on the first 4,000 shots per chunk | diagnostic only, not selectable |

## Selection rule (fixed now)

- **Selected candidate:** among L0–L3, the one with the fewest d=7 nonzero-q errors (q = 0.01 and 0.02, all 300,000 nonzero shots). Ties go to the lower ID.
- **ADVANCE** to a Phase 2 re-plan if **both** hold:
  1. the selected candidate's d=7 nonzero errors are **below** Astar's on the same shots, and its d=7 q=0 errors are no more than 1.10 × Astar's;
  2. at d=5, the selected candidate's nonzero errors are **below** Astar_5's on the d=5 screen shots.
- **STOP (d=7):** no L candidate has fewer d=7 nonzero errors than Astar. The BP+OSD family in these configurations is then not competitive at d=7. Phase 2 could proceed as a d=5-only study, which needs a separate owner decision.
- **REVISE:** some candidate beats Astar at d=7, but the selected one fails the d=5 or q=0 check.

Reported but with no decision role:
- discordance for each candidate vs Astar;
- N3 vs the L candidates on N3's subsample;
- per-configuration cost.

The d=7 counts are small (Astar is about 0.0155%, so roughly 45 nonzero errors expected), so the screen is **noisy**, and selecting in-sample on it is optimistic. Phase 2 must re-establish any gain on fresh seeds.

## Execution controls

- **Rehearsal:** one d=7 chunk of 1,000 shots on rehearsal seeds, writing to a separate folder, to check correctness and measure cost.
- **Run:** 24 chunk jobs in parallel, at most 12 at once. Each writes once and refuses to overwrite. No retry or seed substitution.
- **Wall-time budget:** 4 h, with a monitored background run.
