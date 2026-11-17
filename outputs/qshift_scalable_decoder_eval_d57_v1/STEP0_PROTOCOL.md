# Phase 2 (d=5) Step 0: static prior selection (protocol)

**Committed before any Step 0 decode.** The owner authorized this step on 2026-11-17 ("Approve, run Step 0") in response to `PHASE2_D5_PLAN_DRAFT.md` (`6356d5b9c`). It uses **development data only** and draws no new samples.

## Data

The saved d=5 screen arrays in `work/screen/`:
- `d5_q{0.00,0.01,0.02}_c{0,1}_shots.npz`, which are 6 chunks of 25,000 shots, so 150,000 in total;
- the matching `_errbits.npz` files, which hold the Astar_5 per-shot errors on the same rows.

Before decoding, each chunk's JSON seed is checked against `SCREEN_SEEDS.json`.

## Grid

The candidate is **L2**: ldpc `product_sum`, `serial` schedule, max_iter 50, OSD_CS order 10, via `LdpcBPOSD`. Its DEM is built from `model_v14.build_candidate_circuit(spec, q_dec, scaled_v1)`, with `decompose_errors=False` and `approximate_disjoint_errors=True`.

- **q_dec:** ∈ {0, 0.0025, 0.005, 0.01, 0.02}.
- **The same DEM is used for every condition**, which makes it a static prior.
- **Jobs:** 30 (5 q_dec × 6 chunks), at most 8 at once. Each job writes once and refuses to overwrite.

## Integrity check

When q_dec equals a chunk's true q, the DEM is identical to the one the screen used. So for those 6 jobs, the per-shot errors must equal the screen's saved L2 error bits **bit for bit**. A mismatch is reported as a deviation, and then no selection is made until it is explained.

## Selection rule (fixed now)

- **Nonzero errors:** for each q_dec, E_nz(q_dec) = errors at q = 0.01 plus errors at q = 0.02. Each q has 50,000 shots, so this sum is the equal-weight measure.
- **Eligible:** q_dec values with q=0 errors ≤ 1.10 × Astar_5's q=0 errors on the same rows (69, so the limit is 75).
- **Selected:** the eligible q_dec with the smallest E_nz. Ties go to the smaller q_dec.
- **Fallback:** if none is eligible, take the q_dec with the fewest q=0 errors (ties go to the smaller q_dec) and flag `guard_failed`.

The output is `PHASE2_D5_PRIOR.json`, written once. This is an in-sample selection on development data. The Phase 2 evaluation on fresh seeds is the test.
