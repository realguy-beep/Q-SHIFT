# Belief-matching Phase B: BM0 screen (protocol)

**Committed before any Phase B decode.**

The owner authorized this screen on 2026-11-17 ("Screen BM0 only"), after `PHASE_A_RESULTS.md` showed that the serial variants (BM1–BM3) fail the d=7 cost gate. This screen **amends the variant set** in `DESIGN_PLAN_DRAFT.md`: only BM0 is screened. The selection step is therefore trivial, and the selected variant is BM0. No new samples are drawn.

## Candidate

**BM0**, from `bm.py` `VARIANTS["BM0"]`:
- BP: ldpc product-sum, parallel schedule, max_iter 50, with no converged-BP shortcut;
- DEM: static, from the decomposed DEM at q_dec = 0.01;
- edge rule: the independent-merge rule;
- matcher: uncorrelated PyMatching on the re-weighted graph.

## Data

All data are saved development arrays in `../qshift_scalable_decoder_eval_d57_v1/work/screen/`:
- **d=7:** 18 chunks of 25,000 shots, so 150,000 per q;
- **d=5:** 6 chunks of 25,000 shots, so 50,000 per q.

Each chunk's seed is checked against `SCREEN_SEEDS.json`. The comparators are the saved per-shot error bits on the same rows: **Astar** (correlated PyMatching, q_dec 0.0025) and **L2** (serial BP+OSD at the true q).

## Rule (fixed now; same thresholds as the plan)

- **ADVANCE** to a Phase C plan if both hold:
  1. at d=7, BM0's nonzero errors (q = 0.01 + 0.02) are **below Astar's (55)**, and its q=0 errors are ≤ 1.10 × Astar's (28, so the limit is 30.8);
  2. at d=5, BM0's nonzero errors are below Astar's (217).
- **STOP:** BM0's d=7 nonzero errors are ≥ 55.
- **REVISE:** BM0 beats Astar at d=7, but fails the d=5 check or the q=0 check.

Discordance vs Astar and vs L2, and cost, are reported but play no part in the decision.

## Execution

- **Jobs:** 24, one per chunk, at most 8 at once. Each writes once and refuses to overwrite.
- **Outputs:** per-shot error bits go to git-ignored `work/screen_bm/`, and per-chunk JSON goes to `results/screen_json/`.
- **Expected wall time:** about 40 min (Phase A: 22 ms/shot at d=7 on a single process).

The d=7 counts are small (Astar has 55 nonzero errors), so a pass is a weak signal. That is the reason a frozen Phase C exists.
