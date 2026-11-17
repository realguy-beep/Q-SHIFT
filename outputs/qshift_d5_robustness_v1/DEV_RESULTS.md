# d=5 robustness, Step D: development selection and sizing (results)

These are **development data**: selections are made in-sample on these shots, and the counts are small. **Not evidence.** Every condition is projected to be powered at the planned N = 200,016 per q.

## Execution

- **Protocol:** `DEV_PROTOCOL.md`, committed at `5a4dfa3af` before any sample. A 300-shot rehearsal on separate seeds passed first.
- **Run:** 9 sample jobs, then 36 L2 jobs, at most 8 at a time, from 06:30:01Z to 07:17:53Z on 2026-11-17 (48 min). All 45 outputs were written, with no failures.
- **Shots:** 270,000 development shots (30,000 per condition and q) in 9 sampler calls, with seeds from `DEV_SEEDS.json`.
- **Checks:** every seed matched `DEV_SEEDS.json`, and every L2 error-bit array matched its recorded count.

## Selections

| Condition | Astar_C (Phase 1 rule) | Astar errors q=0 / 0.01 / 0.02 | Selected L2 prior | Guard |
|---|---|---|---:|---|
| **F2** (centre_row, p=0.003) | correlated, q_dec 0.0175 | 30 / 28 / 32 | 0.01 | passed |
| **P2** (scaled_v1, p=0.002) | correlated, q_dec 0.0025 | 15 / 17 / 33 | 0.0025 | passed |
| **P4** (scaled_v1, p=0.004) | correlated, q_dec 0.0025 | 94 / 106 / 111 | 0.005 | passed |

## L2 prior grid (nonzero errors, q = 0.01 + 0.02; ms/shot under 8-way contention)

| Condition | Astar_C | 0.0025 | 0.005 | 0.01 | 0.02 | ms/shot |
|---|---:|---:|---:|---:|---:|---:|
| F2 | 60 | 54 | 48 | **45** | 47 | 24 |
| P2 | 50 | **12** | 12 | 13 | 15 | 10 |
| P4 | 217 | 95 | **92** | 92 | 93 | 24 |

- **The prior barely matters.** It moves errors by at most 9 within any condition, as in Step 0.
- **In-sample development reductions vs Astar_C:**
  - F2: about 25%. This is the smallest, as predicted: matching already handles 2-detector bursts well.
  - P2: about 76%.
  - P4: about 58%.

  These are optimistic, and the frozen evaluation is the test.

## Sizing (Phase 1 formula; CI half-width ≤ 25% of Astar_C's nonzero LER)

| Condition | Astar_C nonzero LER | N required per q | N planned per q | Powered? |
|---|---:|---:|---:|---|
| F2 | 0.100% | 22,024 | 200,016 | yes |
| P2 | 0.083% | 29,484 | 200,016 | yes |
| P4 | 0.362% | 7,940 | 200,016 | yes |

**Discordance, selected L2 vs Astar_C** (nonzero q; "L2 only failed / Astar only failed"):
- F2: 14 / 29
- P2: 1 / 39
- P4: 39 / 164

## Next

The next step is to build and freeze Step E with these selections, in `DEV_SELECTION.json`, and with fresh screened seeds and rehearsals. Sampling the 1,800,144 evaluation shots needs a separate go-ahead.
