# AD2 results: adaptive decoding when the burst itself changes (development)

**Verdict: AD2_STRONG.** Every pre-registered endpoint passed: E1–E4 on every schedule they apply to, E5 and E6. E2 (beating a scheduled re-estimate) passed in 4 of 4 changing schedules, against the 3 that STRONG needs.

**In one sentence:** when the burst switches, appears or moves, the adaptive decoder re-learns it within a median of 3.5–5.5 blocks, cuts errors by 40–65% against a single estimate and by 20–42% against re-estimating every 6 blocks, and once settled it matches the oracle decoder that is told the true noise.

| | |
|---|---|
| Freeze | `ccdfbc618` (`AD2_FREEZE.json`, 65 files), run once from a detached checkout of that commit. No seal was read |
| Run | 30/30 episodes (5 schedules × 6) in a single attempt on 8 workers, 15,643 s (4.3 h; projected 23,360 s); every job returncode 0. Fallback level 1 (AD_W3 dropped), applied by the preflight's own rule |
| Samples | per block, 2,000 unlabelled + 250 labelled calibration rows and 1,000 evaluation shots; 30 blocks per episode, blocks 6–29 scored. Per schedule and arm: 144,000 scored evaluation shots |
| Analysis | `results/ad2/ANALYSIS.json` and `results/ad2/TIMELINE.json`, run twice, byte-identical |
| Recount | `results/ad2/RECOUNT.json`: the re-analysis is identical, and episode 0 of all 5 schedules replays identically (records and decoded error bits) |
| Claim boundary | development evidence at d=5, public weight-3 bursts, piecewise-constant noise, simulation only |

## Errors per schedule (blocks 6–29, 6 episodes, 144,000 shots per arm)

| Schedule | What changes | AD | AD_LG | PERIODIC | ONCE | ORACLE | AD_M | A_nominal |
|---|---|---|---|---|---|---|---|---|
| C0 | nothing (burst A static) | 270 | 270 | 272 | 273 | 273 | 520 | 7,030 |
| S1 | A → B at block 15 | 354 | 351 | 543 | 1,021 | 157 | 1,180 | 5,692 |
| S2 | A on 6–11 and 18–23, off otherwise | 2,048 | 2,050 | 3,515 | 3,478 | 187 | 2,133 | 3,556 |
| S3 | A → C at 15, with p 0.0025 → 0.0035 | 323 | 329 | 403 | 591 | 188 | 445 | 3,110 |
| S4 | B → C at 10, C → D at 20 | 258 | 257 | 332 | 430 | 116 | 422 | 1,350 |

**Arms:** AD re-estimates from the last 6 blocks before every block and decodes nominally on a flag. AD_LG keeps the last good model on a flag. PERIODIC re-estimates at blocks 6, 12, 18 and 24. ONCE estimates once at block 6. ORACLE is the same BP+OSD decoder given the true model of each block. AD_M is the strongest matcher fed AD's base model. A_nominal is the standard decoder with the nominal model.

## Endpoints

Bounds are episode-bootstrap, 20,000 replicates, one-sided 97.5%, as differences in LER.

| Endpoint | Rule | C0 | S1 | S2 | S3 | S4 |
|---|---|---|---|---|---|---|
| E1 AD − ONCE | upper < 0 | | −4.24e-3 ✓ | −9.15e-3 ✓ | −1.42e-3 ✓ | −9.79e-4 ✓ |
| E2 AD − PERIODIC | upper < 0 (counted) | | −5.00e-4 ✓ | −9.42e-3 ✓ | −2.92e-4 ✓ | −4.03e-4 ✓ |
| E3 settled excess over ORACLE | ≤ 25% | | −0.8% ✓ | (none settled) | +3.3% ✓ | 0.0% ✓ |
| E4 median latency | ≤ 7 blocks | | 4 ✓ | 3.5 ✓ | 5.5 ✓ | 4 ✓ |
| E5 no harm when static | AD ≤ 1.1 × ONCE + 3 | 270 ≤ 303 ✓ | | | | |
| E6 mis-learned settled windows | 0 | 0 | 0 | 0 | 0 | 0 |

## What the numbers say

- **After a change, AD catches up and then equals the oracle.** In settled blocks, AD made 125 errors against ORACLE's 126 (S1), 158 against 153 (S3) and 62 against 62 (S4). In C0 it made 270 against 273.
- **Reductions against the alternatives** (all scored blocks):

  | | S1 | S2 | S3 | S4 |
  |---|---|---|---|---|
  | vs ONCE | 65% | 41% | 45% | 40% |
  | vs PERIODIC | 35% | 42% | 20% | 22% |
  | vs A_nominal | 94% | 42% | 90% | 81% |

- **Latency:** S1 acquired B in 3–4 blocks in every episode. S2 acquired A in 3–4 blocks and released it in 3–4. S3 acquired C in 4–6. S4 acquired each new burst in 4–5.
- **No wrong burst was ever accepted** in a settled window (E6). One settled window in S3 (episode 2) was flagged and decoded nominally; that is a cost, not a mis-learning.
- **AD_LG** (last good model on a flag) was within a few errors of AD everywhere. It beat AD on transitions only in S1 (descriptive, not an endpoint).

## Where the remaining gap is

- **Almost all of AD's excess over the oracle is in the transition blocks**, while the window still holds the old burst. In S1, transition blocks cost AD 229 errors against ORACLE's 31; settled blocks cost 125 against 126.
- **S2 is the hard case.** Its burst switches every 6 blocks, so with a 6-block window and a 3–4 block latency, AD spends over half of every segment catching up. AD still beat ONCE and PERIODIC by about 41%, but it made 11× the oracle's errors and only 42% fewer than the standard decoder. A shorter window would react faster, but the rehearsal's 3-block arm raised false flags; AD_W3 was dropped from the study by the preflight, so AD2 says nothing about it.
- These observations are post hoc and descriptive. They do not change the verdict.

## Website export

`results/ad2/TIMELINE.json` holds, per schedule and scored block, each arm's mean, minimum and maximum LER over the 6 episodes, the true burst and p, the settled marks, and AD's learned and flagged fractions. It is the source for a live "burst changes → decoder adapts" chart.

## Files

- `results/ad2/ANALYSIS.json`, `TIMELINE.json`, `RECOUNT.json`, `RUN_STATUS.json`
- `results/ad2/records/*.json` (30 episode records). The decoded-bit archives are not committed; their SHA-256 hashes are in the records.
