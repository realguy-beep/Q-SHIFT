# Belief-matching Phase B: BM0 screen (results)

**Pre-registered outcome: STOP.** At d=7, BM0 makes **76** nonzero-q errors against Astar's **55**, so it is about 38% worse. Belief-matching with parallel BP does not close the d=7 gap.

This is development data: re-used saved screen arrays, with small d=7 counts. It is not evidence.

## Execution

- **Protocol:** `SCREEN_PROTOCOL.md`, committed at `1fd226506` before any decode.
- **Run:** 24 chunk jobs, 8 at a time, from 05:41:11Z to 06:02:32Z on 2026-11-17 (21 min). There were no failures and no new samples.
- **Checks:** every chunk's seed matched `SCREEN_SEEDS.json`, the saved Astar counts matched the screen's records, and the BM0 error bits matched their recorded counts.

## Errors (d=7: 150,000 shots per q; d=5: 50,000 per q)

| d | Arm | q=0 | q=0.01 | q=0.02 | Nonzero |
|---:|---|---:|---:|---:|---:|
| 7 | Astar (correlated matching) | 28 | 22 | 33 | **55** |
| 7 | L2 (serial BP+OSD, true q) | 20 | 27 | 30 | 57 |
| 7 | **BM0** | 34 | 33 | 43 | **76** |
| 5 | Astar | 69 | 110 | 107 | 217 |
| 5 | L2 | 31 | 46 | 34 | 80 |
| 5 | **BM0** | 45 | 57 | 52 | **109** |

**Discordance on nonzero-q shots** (shots where only one of the two decoders failed):

| d | BM0 only vs Astar only | BM0 only vs L2 only |
|---:|---:|---:|
| 7 | 49 vs 28 | 48 vs 29 |
| 5 | 47 vs 155 | 50 vs 21 |

**Cost:** 17.4 ms/shot at d=7 and 5.1 ms/shot at d=5, under 8-way contention.

## Findings

1. **d=7: STOP.** BM0 is worse than correlated matching on nonzero shots (76 vs 55) and at q=0 (34 vs 28).
2. **d=5: BM0 beats Astar by 50%** (109 vs 217), which replicates the hyperedge gain. It still falls short of serial BP+OSD (L2: 80). This matches the d=3 ordering: serial is better than parallel, and BP+OSD is better than belief-matching.
3. **The same pattern holds across all three hypergraph-BP approaches at d=7:** BP+OSD with the parallel or serial schedule, and belief-matching with the parallel schedule. Each gives a large gain over correlated matching at d=5, but none beats it at d=7 in this regime.
   - Two things plausibly contribute. Correlated matching's two-pass reweighting already captures most of the hyperedge structure that matters at d=7. And with weight-3 bursts largely harmless at d=7 (V1.4), little headroom remains.
   - This is an interpretation, not a tested claim.
4. **Untested:** serial belief-matching (BM1), the strongest variant at d=3, could not be screened at an affordable cost. The serial BP in ldpc is about 20× slower per iteration (Phase A). The d=7 STOP therefore covers parallel-BP belief-matching only.

## Consequence

Under the plan, Phase C (the frozen d=7 evaluation) does not proceed. Further d=7 work on these arrays would be selection on reused data, and would need a new pre-registration and a fresh hold-out.
