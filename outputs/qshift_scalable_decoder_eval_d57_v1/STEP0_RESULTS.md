# Phase 2 (d=5) Step 0: static prior selection (results)

**Selected: L2 with a static DEM at q_dec = 0.01.** The q=0 guard passed. This is development data: an in-sample selection on the saved screen arrays, and not evidence.

## Execution

- **Protocol:** `STEP0_PROTOCOL.md`, committed at `f81be21a7` before any decode. The run started from that HEAD (`work/step0_logs/HEAD.txt`).
- **Run:** 30 jobs, 8 at a time, from 02:14:17Z to 03:09:07Z on 2026-11-17 (55 min). There were no failures, and no new samples were drawn.
- **Integrity:**
  - all 6 seeds matched `SCREEN_SEEDS.json`;
  - in all 6 jobs where q_dec equals the chunk's true q, the per-shot errors **reproduce the screen's saved L2 error bits bit for bit**.

## Grid (d=5, 50,000 shots per q; Astar_5: q=0 69, nonzero 217)

| q_dec | q=0 | q=0.01 | q=0.02 | Nonzero | L2-only / Astar-only (nonzero) | ms/shot (8-way) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 31 | 175 | 298 | 473 | 369 / 113 | 44.1 |
| 0.0025 | 31 | 47 | 32 | 79 | 16 / 154 | 30.8 |
| 0.005 | 31 | 47 | 31 | 78 | 16 / 155 | 30.9 |
| **0.01** | **31** | **46** | **31** | **77** | **16 / 156** | **30.3** |
| 0.02 | 33 | 47 | 34 | 81 | 18 / 154 | 27.5 |

## Findings

1. **The prior is not sensitive across 0.0025–0.02.** Nonzero errors range only from 77 to 81, so the choice of 0.01 is close to a tie and carries little selection optimism. A single static prior performs about as well as the true-q oracle (screen L2: 80 nonzero).
2. **A burst-free DEM (q_dec = 0) is much worse at nonzero q** (473 errors vs Astar's 217). BP+OSD needs the burst mechanism in its model. Any positive q_dec in the grid is enough.
3. **Cost:** about 30 ms/shot under 8-way contention. That is about 1.5× the screen's 20 ms estimate, so the Phase 2 runtime projection in the plan (about 1 h) rises to about **1.5–2 h**. The preflight fixes that number before the freeze.

## Next

Freeze Phase 2 with L2s = L2 at q_dec = 0.01, as set out in `PHASE2_D5_PLAN_DRAFT.md`. That means seeds, a hash freeze and rehearsals. Sampling the 600,048 fresh-seed shots needs a separate go-ahead.
