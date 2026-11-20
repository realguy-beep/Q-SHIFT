# BRT results: threshold-free E1 flag (development study)

**Verdict: BRT_SUPPORTED.** E1T passed every pre-declared endpoint on fresh, fully held-out data.

**What E1T is:**
- E1's one-sided adaptive fit;
- a flag made only of the exclusion cap and BRS's subset-rule shape and consistency checks;
- no residual statistic and no tuned parameter.

**What it achieved:**
- **In family:** 126/128 burst pools learned exactly, across p 0.0020–0.0040 and Z-bias 3–12, with no false accepts.
- **Out of family:** no false accepts under measurement 2× (at high gate p), measurement 2.5× or X-bias, and 1 under measurement 1.5×.

It becomes the estimator candidate for RE2.

| | |
|---|---|
| Freeze | `de41bf056` (`BRT_FREEZE.json`, 54 files), run once from a detached checkout of that commit |
| Run | 512/512 pools in a single attempt on 8 workers, 2,217 s (projected 5,603–7,004 s) |
| Samples | 256 × 13,500 + 256 × 12,000 = **6,528,000** detector-sampler shots. Development only, with no decoding |
| Analysis | `results/brt/ANALYSIS.json`, run twice, byte-identical |
| Recount | `results/brt/RECOUNT.json`: the re-analysis is identical, and the first burst pool and first burst-free pool of all 8 conditions replay bit-identically |

All 16 bursts (X01–X16) are new and none is near a BRE or BRS burst. Every pool is held out, and nothing was tuned.

## Results

32 burst pools and 32 burst-free pools per condition. Each cell gives B2 / E1 / E1S / **E1T**.

| Condition | Learned exactly | Burst pools flagged | Burst-free false accepts |
|---|---|---|---|
| T1 (p 0.0020) | 19 / 31 / 31 / **31** | 13 / 1 / 1 / **1** | 0 / 0 / 0 / **0** |
| T2 (p 0.0040) | 25 / 28 / 27 / **31** | 7 / 4 / 5 / **1** | 0 / 0 / 0 / **0** |
| T3 (Z-bias 3) | 22 / 32 / 32 / **32** | 10 / 0 / 0 / **0** | 0 / 0 / 0 / **0** |
| T4 (p 0.0033, Z-bias 12) | 18 / 32 / 32 / **32** | 14 / 0 / 0 / **0** | 0 / 0 / 0 / **0** |
| TM15 (measurement 1.5×) | 10 / 23 / 13 / 19 | 22 / 9 / 19 / 13 | 29 / 13 / 1 / **1** |
| TM2 (gate 0.0036, measurement 2×) | 1 / 6 / 0 / 0 | 31 / 26 / 32 / **32** | 20 / **29** / 0 / **0** |
| TM25 (measurement 2.5×) | 0 / 0 / 0 / 0 | 32 / 32 / 32 / **32** | 1 / **13** / 0 / **0** |
| TX (X-bias 4) | 0 / 0 / 0 / 0 | 32 / 32 / 32 / **32** | 0 / 0 / 0 / **0** |

**E1T endpoints:**

| Endpoint | Result |
|---|---|
| Learning (126/128 = 98.4%; per condition ≥ 30/32) | pass |
| In-family false accepts (0) | pass |
| In-family false flags (at most 1/32 per condition; burst-free 0) | pass |
| TM25, TM2 and TX (32/32 flagged, 0 false accepts) | pass |
| TM15 (1 false accept) | pass |
| No loss against E1 (126 against 123) | pass |

## What the study shows

### 1. The BRS failure mode replicated, and E1T removed it

At p 0.0040, E1's residual statistic exceeded its frozen threshold in 4 pools (maximum 2.54). E1 and E1S therefore flagged 4 and 5 real bursts and learned only 28 and 27. E1T, which has no statistic, learned 31.

### 2. Estimation stays accurate outside every earlier range

| Condition | Mean p̂ | Mean b̂ |
|---|---|---|
| T1 (true p 0.0020) | 0.00201 | — |
| T2 (true p 0.0040) | 0.00403 | — |
| T3 (true bias 3) | — | 2.96 |
| T4 (true p 0.0033, bias 12) | 0.00330 | 11.93 |

E1T learned 30-detector bursts in 31/32 pools. B2 learned 1/32.

### 3. Misfit at high gate p is the case the statistic could not handle

Under TM2, E1 alone accepted a false burst in 29/32 burst-free pools. The structural rules flagged all 32. Under TM25, E1 had 13 false accepts and E1T had 0.

### 4. The margin in family is thin

**What happened:** E1T flagged 1 real burst in T1 and 1 in T2, which exactly meets the allowance of 1/32. In both pools, one detector outside the burst's class crossed the +4 cutoff by chance and was added to the excluded set:
- in the T1 pool this took the count to 31, so both the cap and S1 fired;
- in the T2 pool S1 fired.

**The cost:** 2/128 bursts lost (unlearned, not mis-learned). There were no false accepts.

**What would remove it (post-hoc, untested):** allow one extra detector, for example "X minus at most one detector is contained in a class set". It would have to be weighed against out-of-family sensitivity, and it is not proposed for RE2 without a test.

### 5. Measurement 1.5× is a boundary

The flags are mixed (13/32 burst pools flagged), but false accepts stay at 1. Detecting this condition is not required, because at that level the in-family fit can still decode. Avoiding false bursts is what matters, and E1T does.

## What this changes

- **Supported (development, fresh held-out bursts and widened conditions):** the repaired estimator E1T, with E1's fit plus the cap and the structural rules. It makes burst learning independent of footprint and of p across 0.0020–0.0040 and Z-bias 3–12, and it rejects measurement-heavy and X-bias misfit without false bursts, with no tuned parameter.
- **Next:** RE2, a frozen *decoding* evaluation of the full pipeline (E1T → learn → BP+OSD on the estimated model), with a new sealed hidden burst. This is the first frozen test of the repaired pipeline on an unseen burst.
  - **Constraint:** the large-footprint class pool is depleted. At most 5 eligible 30-detector classes remain after excluding everything near BRE, BRS and BRT bursts: 9 before BRT, minus the 4 it used, minus any near them. RE2's plan must settle the exclusion rule.
- **Unchanged:** this is estimator-level development evidence. R against matching stays at about 59–88%, and the 95% target is out of reach.
