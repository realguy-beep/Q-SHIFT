# d=5/d=7 Phase 1 results (development selection and sizing)

This is **development data only**. Astar_d was selected in-sample on these shots, which flatters the baseline. V3.2 used the DEM at the **true** q (a sizing input, privileged).

## Execution

| Item | Value |
|---|---|
| Protocol | `PHASE1_PROTOCOL.md` (`2c79f6ac2`) + Addendum A (`d6eb9f8eb`), both committed before any Phase 1 sample |
| Rehearsal | 2,000 shots per job on separate rehearsal seeds (not Phase 1 data) |
| Run | 6 parallel jobs (PIDs 1034–1039) from HEAD `d6eb9f8eb`; all completed in **5,261 s** (budget 10,800 s) |
| Shots | 900,000 labeled development shots: d=5 3 × 100,000, d=7 3 × 200,000; 6 sampler calls |
| Integrity | All 6 seeds equal `PHASE1_SEEDS.json`; every saved error-bit array reproduces its recorded error count |
| Saved | Per-arm error counts and timings (`results/phase1_json/`), plus bit-packed per-shot error indicators in git-ignored `work/phase1/`. Raw detector arrays were not saved, as pre-registered. |

## Selection (pre-registered rules)

| d | Astar_d | BoffStatic_d prior |
|---:|---|---:|
| 5 | correlated PyMatching, q_dec = 0.0025 | 0.00125 |
| 7 | correlated PyMatching, q_dec = 0.0025 | 0.00125 |

## Error rates (development; per q: d=5 100,000 shots, d=7 200,000)

| d | Arm | q=0 | q=0.01 | q=0.02 | Nonzero |
|---:|---|---:|---:|---:|---:|
| 5 | Astar_5 | 0.142% | 0.149% | 0.186% | 0.168% |
| 5 | A_nominal | 0.116% | 0.466% | 0.821% | 0.644% |
| 5 | **V3.2** | **0.104%** | **0.110%** | **0.102%** | **0.106%** |
| 7 | Astar_7 | 0.016% | 0.015% | 0.016% | 0.0155% |
| 7 | A_nominal | 0.022% | 0.110% | 0.158% | 0.134% |
| 7 | **V3.2** | **0.0235%** | **0.026%** | **0.0345%** | **0.030%** |

**Discordance, V3.2 vs Astar_d** (nonzero q; shots where only one decoder failed):

| | V3.2 only failed | Astar only failed |
|---|---:|---:|
| d=5, q=0.01 | 66 | 105 |
| d=5, q=0.02 | 54 | 138 |
| d=7, q=0.01 | 39 | 17 |
| d=7, q=0.02 | 54 | 17 |

## Findings

1. **d=5:** V3.2 has about 37% lower nonzero LER than the strongest static matcher, and is also lower at q=0. That is consistent with the d=3 hyperedge gain.
2. **d=7: V3.2 is about 2× worse than the strongest static matcher** at every q, and at q=0 it is even slightly worse than plain uncorrelated matching. This is a substantive **negative development result for the V3.2 configuration** (`ldpc` product-sum BP, no damping, 50 iterations, OSD-CS order 10) at d=7. BP rarely converges on real d=7 shots, so the outcome rests on OSD-CS order 10 over 3,700 columns. That search is plausibly too narrow at this size, but the cause is **not yet established**.
3. **Cost** (8 parallel jobs, so contention inflates these): V3.2 is about 4.6 ms/shot at d=5 and about 25 ms/shot at d=7. The five-factor grid is about 2.3–2.6 ms, a matching arm about 3–8 µs, and V3 NumPy at d=5 about 14–17 ms.

## Sizing outcome (pre-registered formula and Addendum A)

N_d = 19,896 per q at d=5 and 406,128 per q at d=7; scale 1.0; V3 included at d=5. That projects 1,350,072 shots and 6,105 s, within the 6 M / 10 h caps. The formula sizes the CI half-width; it doesn't account for the observed sign at d=7.

## Implication

Phase 2 as designed would very likely return **NO-GO at d=7**, and therefore overall NO-GO under the pre-registered rule ("NO-GO if V3.2 is significantly worse than Astar at either distance"). The d=7 problem is in decoder quality, which a confirmation run should not be the place to discover. Because raw Phase 1 detector arrays were not saved, **no alternative decoder configuration can be screened on Phase 1 data**. Any d=7 decoder revision needs new development shots, and that needs owner approval.
