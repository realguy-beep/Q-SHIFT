# Phase A diagnostic results: d=5 learned support under base-model mismatch

**Finding: the Phase C learner is not robust to base-model mismatch.** Under every tested mismatch it fails, in one of two ways:
- if the true background is **lower** than assumed (Mlo, Mz), it never detects the burst;
- if the true background is **higher** than assumed (Mhi), it always "detects" a burst, including when none is present.

These are development data. The method was fixed beforehand and nothing was tuned.

## How the run was done

- The run used `diag.py run` at the pre-registration commit `28e85f8c3`, with `SEEDS.json` committed and the tree clean. The owner authorized it on 2026-11-18.
- It took 290 s on 8 workers and produced 171 write-once records in `results/diag/pools/`. The aggregate is in `DIAG.json`.
- Per condition: 24 burst pools (4,000 + 500 shots per q), 24 burst-free pools of 12,000 rows, and 3 decode roots × 2,000 shots per q.
- In total that is 2.84 M learner shots plus 54,000 decoded shots.

## Learning (τ = 1,561.2, nominal model p = 0.003, balanced)

| Condition | True model | Burst pools: correct / none accepted | Burst-free pools: false accepts | Burst-free T (median / max) | Burst-free residual y: mean / fraction < 0 |
|---|---|---|---|---|---|
| Mlo | p = 0.0025 | **0/24** / 24 | 0/24 | 0 / 0 | +0.037 / 0% |
| Mhi | p = 0.0035 | 24/24 / 0 | **24/24** (7 different classes) | 36,083 / 43,385 (23–28 × τ) | −0.038 / 100% |
| Mz | Z-bias 10 | **0/24** / 24 | 0/24 | 0 / 0 | +0.105 / 0% |

**Mechanism.**
- **The residuals follow the background error.** The learner's residual is `y = log μ − base_log(nominal)`.
  - When the true background makes **fewer** detector flips than assumed (Mlo; and Mz, where X-type errors that the Z-memory detects are rarer), every residual is positive.
  - When it makes **more** (Mhi), every residual is negative.
- **Mlo and Mz:** a burst can only make residuals more negative, so a positive offset of about +0.04 to +0.1 per subset swamps the burst signal. The fitted β is then never negative, Δ = 0, and the learner never accepts a class, even with the burst present at q = 0.02.
- **Mhi:** the background offset itself looks like a burst. All 24 burst-free pools exceed τ by more than 20×.
  - In the burst pools the true class still wins the argmax.
  - However, q̂ is pinned at the 0.02 clip in every pool, so the rate estimate is meaningless.

## Decoding check (6,000 shots per q; errors; nominal-model decoders)

| Condition | Learned support used | q | L2L | L2s (true support) | Astar | A_nominal |
|---|---|---|---|---|---|---|
| Mlo | none (base DEM) | 0 | 3 | 3 | 3 | 3 |
| | | 0.01 | 15 | 3 | 4 | 21 |
| | | 0.02 | 29 | 2 | 10 | 49 |
| Mhi | (23, 31, 34) | 0 | 7 | 7 | 17 | 10 |
| | | 0.01 | 8 | 8 | 20 | 41 |
| | | 0.02 | 7 | 7 | 25 | 82 |
| Mz | none (base DEM) | 0 | 1 | 1 | 1 | 1 |
| | | 0.01 | 16 | 0 | 4 | 14 |
| | | 0.02 | 15 | 0 | 1 | 40 |

Error counts this small give a direction only. Read that way:

- **Where learning fails** (Mlo, Mz), L2L falls back to the burst-free model and is **worse than Astar**: 44 vs 14 and 31 vs 5 at nonzero q.
- **The decoders tolerate the mismatch:** the true-support L2s still beats Astar in every condition (5 vs 14, 15 vs 45, 0 vs 5).
- **Mhi:** the decode check used burst pool 00's learned support, which was correct. In deployment the learner would also add a false burst at q = 0. Phase A did not test the decoding cost of that false burst.

**Cost:** L2 runs at 11–19 ms per shot, in line with Phase C. That projects Phase B to about 3.3 h, as planned.

## What this means for Phase B

The pre-registered plan said Phase B evaluates every condition regardless of Phase A. With these outcomes, however, the result is close to determined:
- in Mlo and Mz, L2L would be base-DEM BP+OSD against true-support Astar, and it loses;
- Phase B would mostly re-measure a known learner failure at a cost of about 3.3 h.

**Owner decision:**
- **(a)** run Phase B as registered and report NOT_ROBUST;
- **(b)** don't run it, and record Phase A as the robustness answer;
- **(c)** start a separate learner-v2 study whose remedy is a nuisance base-scale term fitted jointly with the burst. It would have its own null calibration, gate and frozen run.

**Claim impact.** Phase C's CONFIRMED result stands, but only for a learner with an exactly known base model. A static mismatch of ±17% in p, or an unmodelled Pauli bias, breaks support learning at d=5.
