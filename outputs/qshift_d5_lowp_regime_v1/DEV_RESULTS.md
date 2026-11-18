# d=5 low-p regime screen, Stage S: development results

**DEVELOPMENT DATA.** These are in-sample selections on small error counts. **Not evidence.**

**Decision (pre-registered rule): PROCEED_TO_STAGE_E_FREEZE.** At L10 the in-sample R is 0.969, which is at least the 0.90 needed to proceed.

## How the run was done

- **Protocol:** `STAGE_S_PROTOCOL.md` at `7fce3fa9f`, with the tree clean and `DEV_SEEDS.json` committed. The owner authorized the run on 2026-11-18 ("Run Stage S").
- **Jobs:** `run_dev.py` ran 6 sample jobs and 18 L2 jobs. All returned rc 0, and all 24 records were written once.
- **Shots:** 1.2 M development shots, 200,000 per (condition, q).
- **Checks:** `dev_aggregate.py` checked every seed against `DEV_SEEDS.json` and every L2 error-bit array against its recorded count. The output is `DEV_SELECTION.json`.

## Selections and headroom

| | L10 (p = 0.001) | L15 (p = 0.0015) |
|---|---|---|
| Astar_C selected | correlated, q_dec 0.0025 | correlated, q_dec 0.0025 |
| Astar errors, q = 0 / 0.01 / 0.02 | 98 / 121 / 134 | 182 / 195 / 193 |
| L2 errors at prior 0.001 / 0.0025 / 0.01, as q0, q1, q2 | 4,4,4 / 3,4,4 / 4,5,4 | 16,12,17 / 16,12,16 / 16,12,17 |
| Selected L2 prior (guard) | 0.001 (passed) | 0.0025 (passed) |
| **In-sample R**, nonzero q | **96.9%** (8 vs 255) | **92.8%** (28 vs 388) |
| L2 q=0 floor / Astar nonzero LER | 0.031 | 0.082 |
| Cap = 1 − floor ratio | 96.9% | 91.8% |
| Discordance at q = 0.01 and 0.02 (L2 only / Astar only) | 2 / 119 and 2 / 132 | 4 / 187 and 9 / 186 |
| L2 ms/shot under 8-way contention | 4.3 | 7.2 |

- **The burst is effectively solved at both p.** L2's error count with the burst equals its burst-free q=0 count: 4/4/4 at L10, 16/12/17 at L15. The remaining errors are background failures.
- **The regime prediction from the plan holds.** At L10 the floor is about 3% of Astar's error rate, so a reduction of about 95–97% is available. At L15 the cap is about 92%.
- **The prior does not matter,** as in Step 0 and Step D: it moves errors by at most 1 at L10.
- **Error counts are small.** L10 rests on 8 L2 errors at nonzero q, so the in-sample R is only a rough guide. The frozen Stage E is the test.

## Stage E sizing (pre-registered rule)

| | L10 | L15 |
|---|---|---|
| Phase 1 formula, N per q | 48,180 | 31,494 |
| N per q to give ≥ 30 L2 errors at nonzero q | **750,000** | **214,296** |
| Projected L2 CPU time (all 3 q) | ≈ 9,700 s | ≈ 4,600 s |

The total is about 2.89 M shots, roughly 30–40 min on 8 workers, well inside the 5 h budget. The Stage E freeze fixes the allocation and requires fresh, screened seeds.

## Next

The next step is to build and freeze Stage E (seeds, run, analysis, recount, preflight, rehearsals) using these selections, with **both** conditions included and the pre-registered target statement (TARGET_MET at R ≥ 0.95, WITH_MARGIN when the lower 95% bound is ≥ 0.95). Sampling needs a separate owner go-ahead.
