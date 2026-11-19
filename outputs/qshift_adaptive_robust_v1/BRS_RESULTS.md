# BRS results: structural misfit check for E1 (development study)

**Verdict: BRS_NOT_SUPPORTED, by the pre-declared rule.**
- **What failed:** one in-family endpoint, false flags. Under S2 (p 0.0036), 2 of 32 real burst pools were flagged; the rule allows 1.
- **Not the new rule's fault:** both flags came from **E1's own frozen residual threshold** (2.335, set on BRE pools with p ≤ 0.0034), not from the structural rule.
- **What the rule did:** everything it was built for. Out-of-family false accepts fell to 0 under measurement 2×, measurement 3× and X-bias, and to 1 under measurement 1.5×. In family it learned 126/128 with no false accepts.
- **In family, E1S changes nothing downstream:** it gives the same learned outcome as E1 in every one of the 256 pools. Its only extra flags fell on burst-free pools that learn no burst either way. The endpoint, though, is defined on flags, and it fails.

| | |
|---|---|
| Freeze | `4967cd7d9` (`BRS_FREEZE.json`, 50 files), run once from a detached checkout of that commit |
| Run | 512/512 pools in a single attempt on 8 workers, 1,989 s (projected 3,821–4,776 s) |
| Samples | 256 × 13,500 + 256 × 12,000 = **6,528,000** detector-sampler shots. Development only, with no decoding |
| Analysis | `results/brs/ANALYSIS.json`, run twice, byte-identical |
| Recount | `results/brs/RECOUNT.json`: the re-analysis is identical, and the first burst pool and first burst-free pool of all 8 conditions replay bit-identically |

All 16 bursts (W01–W16) are new, and every pool is held out. Thresholds are frozen from BRE.

## Results

32 burst pools and 32 burst-free pools per condition.

| Condition | Arm | Learned exactly | Burst pools flagged | Burst-free false accepts | Burst-free flagged |
|---|---|---|---|---|---|
| S1 (p 0.0024) | B2 / E1 / **E1S** | 22 / 32 / **32** | 10 / 0 / **0** | 0 / 0 / **0** | 0 / 0 / **0** |
| S2 (p 0.0036) | B2 / E1 / **E1S** | 25 / 30 / **30** | 7 / 2 / **2** | 0 / 0 / **0** | 0 / 0 / **1** |
| S3 (Z-bias 5) | B2 / E1 / **E1S** | 22 / 32 / **32** | 10 / 0 / **0** | 0 / 0 / **0** | 0 / 0 / **0** |
| S4 (Z-bias 8) | B2 / E1 / **E1S** | 18 / 32 / **32** | 14 / 0 / **0** | 0 / 0 / **0** | 0 / 0 / **1** |
| SM15 (measurement 1.5×) | B2 / E1 / **E1S** | 12 / 23 / 13 | 20 / 9 / 19 | 30 / **16** / **1** | 0 / 0 / 21 |
| SM2 (measurement 2×) | B2 / E1 / **E1S** | 3 / 12 / 0 | 29 / 20 / **32** | 27 / **30** / **0** | 5 / 2 / **32** |
| SM3 (measurement 3×) | B2 / E1 / **E1S** | 0 / 0 / 0 | 32 / 32 / **32** | 0 / 1 / **0** | 32 / 31 / **32** |
| SX (X-bias 6) | B2 / E1 / **E1S** | 0 / 0 / 0 | 32 / 32 / **32** | 0 / 0 / **0** | 32 / 32 / **32** |

**E1S endpoints:**

| Endpoint | Result |
|---|---|
| Learning (126/128 = 98%; per condition ≥ 30/32) | pass |
| False accepts, in family (0 everywhere) | pass |
| **False flags, in family** | **fail:** S2 has 2/32 burst pools flagged |
| SM3, SM2, SX | pass: 32/32 flagged, 0 false accepts |
| SM15 (1 false accept) | pass |
| No loss against E1 (126 against 126) | pass |

## What the study shows

1. **The structural rule closes E1's out-of-family hole on fresh data.**
   - Under measurement 2×, E1's statistic flagged only 2 of 32 burst-free pools, and the learner then accepted a false burst in **30**. E1S flagged all 32 on shape (S1) and consistency (S2), and accepted none.
   - Under measurement 1.5×, false accepts fell from 16 to 1. That one pool excluded a single detector inside a class's set (`x_class` 363) and so passed both rules.
2. **It cost nothing in family:** 126/128 learned exactly, the same as E1, across all four footprint sizes including 30 detectors.
   - Its 2 extra flags were on burst-free pools (S2 and S4), where one detector crossed +4 by chance and nothing was accepted (rule S2).
   - Both outcomes are "no burst", the same as unflagged. They count as flags but change nothing downstream.
3. **The failing flags come from E1's residual statistic, which drifts with p.**
   - In-family maximum by condition: 1.39 at p 0.0024, **2.75** at p 0.0036, and 1.43 and 1.39 under Z-bias.
   - In BRE the maximum likewise came at the highest p, 2.335 at p 0.0034, and that value became the frozen threshold.
   - So the threshold was set at the edge of the p range seen in tuning. At the higher p used here, 2 burst pools exceeded it. They are also E1's 2 missed bursts, so E1 and E1S share them.
   - The statistic was meant to be about 1 under the correct model. That it grows with p suggests the binomial standardization understates the variance of the pooled mixed-q rates. This is a post-hoc reading and was not tested.
4. **B2 again fails on 30-detector bursts:** 1 of 32 such pools learned across the in-family conditions.

## What this changes

- **Supported (development, fresh held-out bursts):** E1S's structural rules remove false burst acceptance under measurement-heavy and X-bias misfit, at no in-family cost.
- **Not supported:** E1S as frozen, because E1's p-dependent residual threshold falsely flags real bursts just above its tuning range.
- **Candidate fix, post-hoc and untested:** make E1's statistic scale-free. Either standardize with the empirical variance of the pooled rates, or calibrate the threshold as a function of p̂. Alternatively, drop the statistic altogether and rely on the cap plus S1 and S2. In this run S1 and S2 alone flagged every out-of-family burst-free pool in SM2, SM3 and SX. The statistic has to be dropped or replaced together with the 30-detector cap, and that needs a fresh test.
- **Before RE2,** a small fresh development run of the fixed E1S. RE2 then needs a new sealed burst excluding all BRE and BRS supports.
- **Unchanged:** this is estimator-level development evidence, and the 95% target remains out of reach.
