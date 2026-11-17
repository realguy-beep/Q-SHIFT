# Phase 2, d=5: frozen evaluation results

**Pre-registered decision: GO_d5.** Hypergraph BP+OSD (L2s: serial schedule, with one static prior q_dec = 0.01) has a **64.8% lower** equal-weight nonzero logical error rate than the strongest static matcher (Astar, correlated PyMatching), on 400,032 fresh-seed burst shots. The 95% CI is 61.2–68.4%. It is also 46% lower at q=0, where there are no bursts.

## Execution

- **Freeze:** `FREEZE.json` (26 file hashes) at commit `d22fccf70`. Each job verified HEAD and every hash before sampling, and the run started from a clean tree.
- **Run:** 72 root jobs, 8 at a time, single attempt, from 03:24:11Z to 04:06:53Z on 2026-11-17 (**42.7 min**; projected 86.5 min; budget 180 min).
  - All 72 jobs exited 0, and the longest took 309 s (the timeout was 3,600 s).
  - There were no retries and no seed substitutions.
- **Shots:** 600,048 fresh evaluation shots, 200,016 per q, in 72 stim sampler calls with seeds from `SEEDS.json`.
- **Integrity:**
  - the analyzer checked every seed, every archive's SHA-256, and every recorded per-arm count against the saved predictions;
  - re-analysis into a second folder was **byte-identical** (both `ANALYSIS.json` and `paired_roots.csv`);
  - the independent recount (`recount.py`, `RECOUNT.json`) matched every per-arm, per-q total, and re-decoding root 0 at every q from the saved detectors reproduced **all six arms' predictions bit for bit**.

## Error counts (200,016 shots per q)

| Arm | q=0 | q=0.01 | q=0.02 | Nonzero LER (equal weight) | q=0 LER |
|---|---:|---:|---:|---:|---:|
| Astar (comparator) | 247 | 387 | 386 | 0.193% | 0.124% |
| **L2s (candidate)** | **134** | **149** | **123** | **0.068%** | **0.067%** |
| L2o (true-q prior) | 132 | 149 | 128 | 0.069% | 0.066% |
| L0s (parallel BP) | 226 | 238 | 207 | 0.111% | 0.113% |
| BoffStatic (five-factor) | 240 | 284 | 229 | 0.128% | 0.120% |
| A_nominal | 239 | 1,006 | 1,774 | 0.695% | 0.120% |

On nonzero-q shots where only one of the two decoders failed, **L2s alone failed on 90 shots and Astar alone on 591**.

## Endpoints

All CIs are root-paired bootstraps over 24 roots per q, with 20,000 replicates. Differences are in percentage points of LER.

| Endpoint | Estimate | 95% CI | Result |
|---|---:|---:|---|
| **Co-primary:** L2s − Astar, nonzero | −0.125 pp | [−0.139, −0.111] | **pass** (CI entirely below 0) |
| **Safety:** L2s − Astar at q=0, 95th percentile | −0.045 pp | margin +0.0062 pp | **pass** |
| **Relative reduction R** vs Astar, nonzero | **64.8%** | [61.2%, 68.4%] | reported |
| L2s − Astar at q=0 | −0.057 pp | [−0.070, −0.043] | — |
| L2s − L2o (cost of the static prior) | −0.001 pp | [−0.003, 0.000] | no measurable cost |
| L2s − L0s (serial vs parallel) | −0.043 pp | [−0.051, −0.036] | serial better |
| L2s − BoffStatic | −0.060 pp | [−0.071, −0.050] | — |
| L2s − A_nominal | −0.627 pp | [−0.653, −0.603] | — |

## Findings

1. **The d=5 development gain replicated on fresh seeds without the true-q advantage.** The development estimates were 37% (Phase 1, parallel V3.2) and 63% (screen, L2 with the true q). The frozen result is 64.8%, with a CI that excludes anything below 61%.
2. **Not knowing q costs nothing measurable.** The static prior L2s and the oracle prior L2o are within 0.003 pp of each other at every q.
3. **Most of the gain is not about bursts.** At q=0, with no bursts at all, L2s is still 46% below Astar (134 vs 247 errors). That is the background-hyperedge gain first seen at d=3: BP+OSD decodes the full hypergraph DEM, while matching has to decompose it. At nonzero q the reduction is larger (65%), because the correlated burst is modelled natively.
4. **The serial BP schedule matters.** The parallel schedule (L0s) loses about a third of the gain, consistent with the screen.
5. **Cost:** L2s takes about 15 ms/shot (8-way contention), against about 5 µs for matching, which is roughly 3,000× more. This is an offline/simulation result, not a real-time decoder.

## Claim boundaries

- This is **one d=5, p=0.003 regime, with one synthetic burst mechanism, in simulation only**. There is no hardware data.
- **d=7 is not supported.** The pre-registered d=7 screen returned STOP_d7: the best configuration tied Astar. This d=5 result does not show the method scales.
- The comparator is the strongest *static* matcher available. No mode-switching matcher was built at d=5.
- The candidate's prior was selected on development data (Step 0) and fixed before any evaluation seed was drawn. The protocol records the deviation from the approved design's per-root q̂.
- The 90–95% target was not a pre-registered endpoint of this study, and 64.8% is below it. Reaching 90% here would also require removing most of the background (q=0) errors, which BP+OSD reduces by only about half.
