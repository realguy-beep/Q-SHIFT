# d=7 decoder-configuration screen: results

**Pre-registered outcome: STOP_d7.** No candidate configuration has fewer d=7 nonzero errors than the strongest static matcher. The best candidate (L2, serial schedule) **ties** it.

This is development data: an in-sample screen with small d=7 counts. It is not evidence.

## Execution

- **Protocol:** `SCREEN_PROTOCOL.md`, committed at `5659e20f1` before any sample.
- **Rehearsal:** one 1,000-shot d=7 chunk on rehearsal seeds.
- **Run:** 24 chunks, 12 at a time, from HEAD recorded in `work/screen_logs/HEAD.txt`. Started 2026-11-16T13:22:44Z and finished by 16:16:54Z (**2 h 54 m**, within the 4 h budget). There were no failures.
- **Shots:** 600,000 fresh dev shots (d=7 450,000; d=5 150,000) in 24 calls. Detectors and observables are saved bit-packed in git-ignored `work/screen/`.
- **Integrity:** the aggregator checked every chunk's seed against `SCREEN_SEEDS.json` and every error-bit array against its recorded count.

## d=7 (150,000 shots per q)

| Arm | q=0 | Nonzero (q=0.01 + 0.02) | Cand-only / Astar-only (nonzero) | ms/shot (12-way contention) |
|---|---:|---:|---:|---:|
| **Astar** | 28 | **55** | — | 0.02 |
| A_nominal | 40 | 381 | — | 0.01 |
| L0: product-sum, parallel, OSD-CS 10 (= V3.2) | 43 | 89 | 61 / 27 | 29.6 |
| L1: min-sum 0.625, parallel, OSD-CS 10 | 38 | 75 | 46 / 26 | 35.6 |
| **L2: product-sum, serial, OSD-CS 10** | **20** | **57** | 31 / 29 | 128.9 |
| L3: min-sum 0.625, parallel, OSD-CS 30 | 35 | 70 | 43 / 28 | 26.8 |
| N3: NumPy V3, damped (24,000-row subsample, all q) | 22 errors on its subsample, vs Astar 10 | — | — | 87.4 |

**Selection:** L2 has the fewest nonzero errors among the candidates. **Criterion 1 fails:** 57 is not below 55. Its q=0 count (20 vs 28) would have passed.

## d=5 no-regression check (50,000 shots per q)

| Arm | q=0 | Nonzero | Cand-only / Astar-only |
|---|---:|---:|---:|
| Astar | 69 | 217 | — |
| L0 | 53 | 123 | 58 / 152 |
| L1 | 35 | 102 | 41 / 156 |
| **L2** | **31** | **80** | 18 / 155 |
| L3 | 32 | 91 | 29 / 155 |

Criterion 2 (d=5) passes for every candidate. L2 is about 63% below Astar on these fresh shots (80 vs 217).

## Findings

1. **The BP schedule was the main d=7 problem.** Switching from parallel (flooding) to serial BP brought BP+OSD from about 1.6× Astar's errors (L0: 89 vs 55) to a tie (57 vs 55), and below Astar at q=0 (20 vs 28). Min-sum and a deeper OSD order helped less.
2. **No configuration demonstrates an advantage over the strongest matcher at d=7** in this screen, and the best one costs about 6,000× more than matching. Combined with V1.4's finding that weight-3 bursts become nearly harmless at d=7, the remaining d=7 headroom for hypergraph BP+OSD over correlated matching appears small in this regime.
3. **d=5 shows a large, consistent BP+OSD advantage,** replicated on fresh development data: every configuration beats Astar by 43–63% nonzero, and is also lower at q=0. Serial L2 is best at d=5 as well.
4. **N3** (the damped NumPy V3) did worse than the L candidates at d=7 on its subsample, so damping alone is not the fix.

## Consequence (protocol)

STOP_d7 means the BP+OSD family in these configurations is not competitive with correlated matching at d=7 under this noise model. A **d=5-only Phase 2** is the remaining evaluation option, and it needs a separate owner decision. Further d=7 tuning on these saved arrays would be selection on the same data, and would need a new pre-registration plus a fresh hold-out.
