# BRE results: burst-robust estimation (development study)

**Verdict: BRE_PARTIAL.**
- **E1** (one-sided adaptive exclusion) passes every endpoint except out-of-family. In family it learned **240/240** burst pools exactly, held-out bursts included, with 0 false flags and 0 false accepts.
- **The one failure:** under measurement-heavy noise (BM), 3 of 24 held-out burst-free pools went unflagged and a false burst was accepted. The rule allows at most 1.
- **No arm is chosen** under the pre-declared rule.

| | |
|---|---|
| Freeze | `d15e5f47e` (`BRE_FREEZE.json`, 41 files), run once from a detached checkout of that commit |
| Run | 672/672 pools in a single attempt on 8 workers, 3,486 s (projected 6,825–8,531 s) |
| Samples | 336 × 13,500 + 336 × 12,000 = **8,568,000** detector-sampler shots. Development only, with no decoding |
| Analysis | `results/bre/ANALYSIS.json`, run twice, byte-identical |
| Recount | `results/bre/RECOUNT.json`: the re-analysis is identical, and the first burst pool and first burst-free pool of all 7 conditions replay bit-identically |

## Endpoints (held-out V)

The in-family conditions are B1, B2c, B3, B4 and B5. Each has 24 V burst pools and 24 V burst-free pools.

| Arm | Learned exactly, in family (V) | False flags (burst / burst-free) | False accepts | BX: flagged / false accepts | BM: flagged / false accepts | K and T regression | Passes |
|---|---|---|---|---|---|---|---|
| B2 (frozen) | **77/120** (14–18 per condition) | **6–10** / 0 per condition | 0 | 24/24 / 0 | 24/24 / 0 | T 93/120 | learning ✗, false flag ✗, regression ✗ |
| **E1** | **120/120** | 0 / 0 | 0 | 24/24 / 0 | 24/24 / **3** | K 10/10, T 120/120 | **all except out-of-family** |
| E2 | 119/120 | 0 / 0 | 0 | 24/24 / **24** | 2/24 / **24** | K 10/10, T 118/120 | out-of-family ✗ |
| E3 | 120/120 | 0 / 0 | 0 | 24/24 / **24** | 24/24 / **24** | K 10/10, T 120/120 | out-of-family ✗ |

**Thresholds,** set on in-family T pools only:
- **E1:** mean squared included residual above 2.335, or more than 30 exclusions. The maximum over V in-family pools was 1.92.
- **E2:** 210.6.
- **B2:** the frozen 118.4.

## What the study shows

### 1. RE1's failure mechanism is confirmed on held-out bursts

In-family burst pools, T and V together, by burst footprint:

| Detectors flipped by the burst | Pools | B2 flagged | B2 learned exactly | E1 learned exactly |
|---|---|---|---|---|
| 10 | 30 | 0 | 30 | 30 |
| 15 | 40 | 0 | 40 | 40 |
| 20 | 70 | 0 | 70 | 70 |
| 25 | 50 | 20 | 30 | 50 |
| 30 | 50 | **50** | **0** | **50** |

- **B2 fails exactly where BRE-0 predicted it would:** bursts larger than its 24-detector trim. It never learned a 30-detector burst.
- **The bias estimate tells the same story.** With a 30-detector burst, B2's b̂ averaged 3.16 under B3 (true 4), 7.43 under B4 (true 10) and 4.91 under B5 (true 6). E1's averaged 3.90, 9.59 and 6.07.

### 2. E1 removes the footprint dependence in family

- 240/240 burst pools were learned exactly: all 24 bursts, every condition, T and V alike.
- 0 of 240 burst-free pools had a false accept.
- No in-family burst-free pool excluded any detector. Burst pools excluded at most 30.

### 3. Falling back to the nominal learner (E2, E3) is unsafe

Under both out-of-family models, the nominal learner accepted a false burst in **every** burst-free pool: 96 of 96, T and V together. The flags fired as intended, but the fallback then injected a false burst. In burst pools the fallback does learn the true burst: 48/48 in BX and 34/48 in BM. The rehearsal had previewed this.

### 4. E1's out-of-family weakness: measurement-heavy noise

- **BX (X-bias):** E1 excluded more than 30 detectors in every pool, so all were flagged.
- **BM (measurement p 3×):** E1 excluded 14–41 detectors in burst-free pools. In 8 of 48 pools, 3 of them held out:
  - the exclusions stayed within the 30-detector cap;
  - the remaining misfit fell below the threshold (stat 1.88–2.31 against 2.335);
  - the learner then accepted a false class.

**Post-hoc observation, not a tested fix:** a genuine burst's exclusions are one detector set per round, matching a signature class. BM's exclusions are unstructured. A structural check (the excluded set must match a class's detector set) is a natural candidate for the next study. It was not pre-registered and is not applied here.

## What this changes

- **Supported (development, held-out bursts):** E1 makes noise-model estimation and burst learning independent of burst footprint. It does so across ±13% p error and Z-bias 4–10, where the frozen B2 failed on every 30-detector burst.
- **Not supported:** E1 as a complete pipeline. Its flag misses some measurement-heavy misfit, so the verdict is PARTIAL and no arm is chosen.
- **Next, before any RE2:**
  1. a small development study of E1 plus a structural exclusion check, with BM-type misfit and a fresh hold-out;
  2. then a frozen RE2 with a new sealed burst. It must exclude every BRE support, since this study's bursts are now development data.
- **Unchanged:** this is estimator-level development evidence, not a decoding result. R against matching stays at about 59–88%, and the 95% target is out of reach.
