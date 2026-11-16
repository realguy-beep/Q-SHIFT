# V1.4 Phase B headroom gate: results

**Outcome: no cell qualifies. The pre-declared stop rule applies, so no pilot and no frozen evaluation are run from this gate.** These are exploratory development data. They measure ceilings, not decoder performance.

## Execution

- Ran from the clean Phase A commit `89ed5f704aeda2274bd6f2c5273e7582b086f98a`, using `headroom_gate.py --execute`. It sampled 1,080,000 shots: 18 cells × 3 q × 20,000, with seeds from `GATE_SEEDS.json`.
- Decoding was matching only, over the static grid of 9 q values × 2 correlation modes. The five-factor decoder was timed on 200 rows per cell; no error rates are reported from it.
- No raw arrays were saved. Every per-decoder error count is in `HEADROOM_GATE.json`.

## Ceiling table

Definitions:
- floor: the best static matcher's LER at q=0, which equals a burst oracle's LER.
- static: the best static matcher's equal-weight LER at q ∈ {0.01, 0.02}, chosen in-sample.
- ceiling: 1 − floor/static.
- lower: a conservative Clopper–Pearson lower bound on the ceiling. A cell needs lower ≥ 0.97 to qualify.

| d | p | family | floor errors / 20k | static errors / 40k | ceiling | lower |
|---|---|---|---:|---:|---:|---:|
| 3 | 0.001 | scaled_v1 | 14 | 156 | 0.82 | 0.65 |
| 3 | 0.002 | scaled_v1 | 51 | 393 | 0.74 | 0.62 |
| 3 | 0.003 | scaled_v1 | 90 | 555 | 0.68 | 0.57 |
| 5 | 0.001 | scaled_v1 | 1 | 28 | **0.93** | 0.40 |
| 5 | 0.002 | scaled_v1 | 2 | 40 | **0.90** | 0.49 |
| 5 | 0.003 | scaled_v1 | 25 | 67 | 0.25 | <0 |
| 7 | 0.001 | scaled_v1 | 0 | 0 | n/a | n/a |
| 7 | 0.002 | scaled_v1 | 1 | 2 | 0.00 | <0 |
| 7 | 0.003 | scaled_v1 | 2 | 9 | 0.56 | <0 |
| 3–7 | all | centre_row | — | — | ≤ 0.45, or noise | <0.1 |

In the centre_row family the static matcher is within noise of the floor in every cell. Those 2-detector signatures look like an ordinary matching edge, so matching already handles them.

## What this shows

1. **Weight-3 bursts stop dominating at larger distance.** At d=5 and d=7, the best static matcher already corrects most bursts. At d=7 it is within noise of the burst-free floor. Growing the code suppresses burst harm along with background harm, so the hoped-for burst-dominated regime doesn't appear with this burst size.
2. **The highest point ceilings are about 0.90–0.93,** at d=5 with p ≤ 0.002 in the scaled family. Both are below the 0.97 needed for margin, and both rest on 1–2 floor errors and 28–40 static errors, so their lower bounds are 0.40–0.49. Even a perfect burst decoder there would be expected to land near 90%, not reliably at or above it.
3. **The d=3, p=0.003 cell (0.68) agrees with the earlier 64% estimate** from V1.3's own numbers, which is a consistency check on the gate.
4. **The five-factor decoder costs 1.2–3.2 ms per shot** across cells in Python, which would be affordable for a pilot.

## Implication for the 90–95% target

In this noise family (independent weight-3 common-cause bursts, q ≤ 0.02, with the declared burst geometry), a 90–95% reduction against the strongest static matcher can't be demonstrated with margin at any tested d and p. Only a change to the noise model could get there:
- higher burst rate,
- larger burst weight relative to d,
- or bursts aligned with logical-error paths.

That is a scientific scope decision for the owner. The decoder can't change it, and it should not be tuned after seeing these results.
