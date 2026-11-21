# AD3 results: faster reaction to a change (development)

**Verdict: AD3_SUPPORTED.** F1–F4 pass. F5 (median latency ≤ 2 blocks on every changing schedule) passes on S2 only. That is the outcome `AD3_PROTOCOL.md` predicted before any study sample, once the Phase 1 screen had set M = 6.

**In one sentence:** where a known noise state returns (S2), detecting the change and recalling the earlier model cut AD's errors by 23% and halved the median re-learning time from 4 blocks to 2; where the new burst has never been seen, AD3 was identical to AD, as designed.

| | |
|---|---|
| Freeze | `b06349e38` (`AD3_FREEZE.json`, 78 files), run once from a detached checkout of that commit. No seal was read |
| Phase 1 screen | τ = 163.13; 19/20 changes detected on the change block; no 1–3 block window qualified, so M = 6 (`AD3_SCREEN.json`) |
| Run | 30/30 episodes (5 schedules × 6) in a single attempt on 8 workers, 13,735 s (3.8 h; projected 21,290 s); every job returncode 0; level 0 |
| Samples | AD2's stream: per block 2,000 unlabelled + 250 labelled rows and 1,000 evaluation shots; blocks 6–29 scored. Per schedule and arm: 144,000 scored evaluation shots. Fresh seeds; AD2's data not reused |
| Analysis | `results/ad3/ANALYSIS.json` and `results/ad3/TIMELINE.json`, run twice, byte-identical |
| Recount | `results/ad3/RECOUNT.json`: the re-analysis is identical, and episode 0 of all 5 schedules replays identically (records and decoded error bits) |
| Claim boundary | development evidence at d=5, public weight-3 bursts, piecewise-constant noise, simulation only |

## Errors per schedule (blocks 6–29, 6 episodes, 144,000 shots per arm)

| Schedule | What changes | AD3 | AD | PERIODIC | ONCE | ORACLE | A_nominal |
|---|---|---|---|---|---|---|---|
| C0 | nothing (burst A static) | 346 | 346 | 251 | 250 | 253 | 6,928 |
| S1 | A → B at block 15 | 397 | 397 | 668 | 1,006 | 156 | 5,600 |
| **S2** | **A on 6–11 and 18–23, off otherwise** | **1,751** | **2,279** | 3,506 | 3,474 | 178 | 3,575 |
| S3 | A → C at 15, with p 0.0025 → 0.0035 | 312 | 312 | 415 | 613 | 194 | 3,095 |
| S4 | B → C at 10, C → D at 20 | 234 | 234 | 327 | 411 | 98 | 1,253 |

**Arms:** AD3 is AD plus change detection and, within 5 blocks of a detected change, recall of a model learned earlier in the episode. AD is AD2's method, unchanged. PERIODIC, ONCE, ORACLE and A_nominal are as in AD2.

## Endpoints

Bounds are episode-bootstrap, 20,000 replicates, one-sided 97.5%, as differences in LER.

| # | Endpoint | Rule | Result |
|---|---|---|---|
| F1 | S2 faster adaptation | AD3 − AD upper < 0 | −3.67e-3 (upper −1.85e-3) **✓** |
| F2 | no loss on S1, S3, S4 | AD3 − AD point ≤ 0 each | 0, 0, 0 (identical errors) **✓** |
| F3 | no harm when static | C0: AD3 ≤ 1.1 × AD + 3 | 346 ≤ 384 **✓** |
| F4 | safety | 0 mis-learned settled windows | 0 **✓** |
| F5 | latency | median ≤ 2 blocks, each of S1–S4 | S1 4 ✗, **S2 2 ✓**, S3 5 ✗, S4 4 ✗ |

## What the numbers say

- **S2, the case AD3 targeted:**
  - **Errors:** 1,751 against AD's 2,279 (23% fewer). Against the standard decoder, AD3 is 51% lower; AD was 36% lower.
  - **Latency:** median 2 blocks against AD's 4. 10 of 24 changes were re-learned within 1 block, and 14 of 24 within 2.
  - **Detection:** 15 of 24 changes were detected on the change block itself and 18 of 24 within 2 blocks; 2 were never detected.
  - **Why some were missed:** S2's burst A is the smallest (10 detectors). Its on and off changes gave G of about 140–235 against τ = 163, so they sit near the threshold. The late and missed detections were A switching on and off alike.
  - **The other schedules,** whose changes involve the larger bursts B, C and D, were all detected on the change block.
  - **The gap that remains:** AD3 still made 9.8× the oracle's errors (AD 12.8×). The first appearance of A in each episode cannot be recalled, and late detections fall back to AD.
- **S1, S3, S4 (never-seen bursts):** AD3 equalled AD exactly. Changes were detected on the change block in all 24 cases, but with M = 6 no faster route exists for a new burst, so AD3 used AD's estimate.
- **Safety:** no mis-learned settled window, for AD3 or for AD.
- **False detections:** 2 in the 6 C0 episodes. Both were harmless (AD3 recalled the current state or used AD's estimate).

## A finding about AD itself (C0, not an AD3 endpoint)

- **What happened:** in C0, AD and AD3 made 346 errors against ONCE's 250 and ORACLE's 253. In five of the six episodes AD was within 2 errors of ONCE.
- **The cause:** in episode 4, E1T flagged two settled windows (blocks 14 and 15) that had learned the right class. Those blocks were decoded with the nominal model, which cost 96 errors.
- **What it means for AD2:**
  - AD2's verdict stands; it was a single pre-registered run. But this fresh sample shows that AD2's no-harm result (E5: AD ≤ 1.1 × ONCE + 3) is sensitive to rare flags. Here AD would fail it: 346 > 278.
  - This is the same lesson as RE2's G5: a single flag decoded nominally is expensive.
  - **A post hoc, untested fix:** on a flag in a settled stretch, keep the last accepted model, as AD2's AD_LG arm did (it was within a few errors of AD in AD2), or recall the current state's model.
- **None of this is re-scored.**

## Lessons (post hoc, untested)

- **Recall works when states recur.** For the website and the competition, the clean claim is: "when a known noise pattern returns, Q-SHIFT re-adapts in about 1–2 blocks instead of 4".
- **Faster learning of a never-seen burst** needs a window estimator that is reliable on 2–3 blocks. E1T at 4,000–6,000 rows flags too often (screen: 36–68% flags), so this is an estimator problem, not a detection problem: detection was immediate in every new-burst change.
- **The flag fallback** remains the main source of avoidable error in settled stretches.

## Website export

`results/ad3/TIMELINE.json` holds, per schedule and scored block, each arm's mean, minimum and maximum LER over the 6 episodes, the true burst and p, the settled marks, AD3's and AD's learned fractions, and the fraction of episodes with a change detected at that block.

## Files

- `results/ad3/ANALYSIS.json`, `TIMELINE.json`, `RECOUNT.json`, `RUN_STATUS.json`
- `results/ad3/records/*.json` (30 episode records). The decoded-bit archives are not committed; their SHA-256 hashes are in the records.
