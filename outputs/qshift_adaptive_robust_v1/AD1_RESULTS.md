# AD1 results: adaptive decoding under drifting noise (development study)

**Verdict: AD1_NOT_SUPPORTED.** All three tracking endpoints failed, so the pre-declared rule gives NOT_SUPPORTED. The other four endpoints passed: no harm, burst onset, burst offset and settled-window flags.

**Why tracking failed:**
- The adaptive decoder tracked well. AD came within 1–6% of the ORACLE LER in D1, D2 and D4, against a 25% allowance.
- The frozen block-6 estimate (ONCE) was just as close. Under these drifts, re-estimating gave no measurable benefit over estimating once.
- The endpoint's second clause needs AD to beat ONCE (upper 97.5% bound of AD − ONCE below 0), so it could not pass.
- The drifts were too mild to hurt a frozen estimate. That is a design finding about the schedules, not a failure of the estimator.

**Where adaptation did matter, in D3 (a burst that appears and then disappears):**
- AD made 117 errors against ONCE's 156, and the 95% CI of AD − ONCE excludes 0.
- AD learned the burst at a median latency of 5 blocks and dropped it at a median of 2.5.
- Nothing was mis-learned.

D3 is not a tracking schedule under the frozen rule, so it does not change the verdict.

| | |
|---|---|
| Freeze | `3a2d0209a` (`AD1_FREEZE.json`, 58 files), run once from a detached checkout of that commit |
| Run | 30/30 episodes in a single attempt on 8 workers, 4,522 s (projected 6,036–7,545 s) |
| Samples | 30 episodes × 24 blocks × 3,250 = **2,340,000** sampler shots. 1,000 evaluation shots × 18 scored blocks per episode, decoded by all 5 arms |
| Analysis | `results/ad1/ANALYSIS.json`, run twice, byte-identical |
| Recount | `results/ad1/RECOUNT.json`: the re-analysis is identical, and episode 0 of all 5 schedules replays bit-identically (records and decoded error bits) |

## Errors per schedule

108,000 scored shots per arm per schedule (6 episodes × 18 blocks × 1,000).

| Schedule | AD | ONCE | ORACLE | AD_M | A_nominal | (AD − ORACLE) / ORACLE | AD − ONCE, upper 97.5% |
|---|---|---|---|---|---|---|---|
| C0 (static) | 77 | 74 | 74 | 191 | 519 | 0.041 | +4.6e-5 |
| D1 (p ramp) | 92 | 90 | 91 | 209 | 545 | 0.011 | +6.5e-5 |
| D2 (Z-bias ramp, X13) | 18 | 21 | 17 | 34 | 52 | 0.059 | +1.9e-5 |
| D3 (W13 on in blocks 8–15) | 117 | 156 | 70 | 222 | 292 | 0.671 | **−2.7e-4** |
| D4 (p step at block 12) | 86 | 84 | 81 | 220 | 592 | 0.062 | +7.4e-5 |

## Endpoints

| Endpoint | Result | Pass |
|---|---|---|
| Tracking D1 | excess 0.011 ≤ 0.25; AD − ONCE upper bound +6.5e-5, not < 0 | no |
| Tracking D2 | excess 0.059; upper bound +1.9e-5 | no |
| Tracking D4 | excess 0.062; upper bound +7.4e-5 | no |
| No harm (C0) | 77 ≤ 1.1 × 74 + 3 = 84.4 | yes |
| Burst onset (D3) | latencies 5, 3, 5, 4, 5, 5 (median 5 ≤ 6); 0 mis-learned windows | yes |
| Burst offset (D3) | latencies 3, 2, 3, 3, 2, 2 (median 2.5 ≤ 6) | yes |
| Settled-window flags | at most 1 per episode everywhere (one in D3 e1, one in D4 e0) | yes |

## What the estimator did

- **p̂ followed the drift.** Each estimate is compared here with the true value averaged over its 6-block window.
  - D1: mean p̂ went from 0.00262 at block 6 to 0.00336 at block 23, against window-average truth of 0.00261 → 0.00335.
  - D4: p̂ went from 0.00252 to 0.00351 across the step, against truth of 0.0025 → 0.0035.
- **b̂ followed the Z-bias ramp in D2:** 1.61 → 6.81, against window-average truth of 1.76 → 6.93.
- **The support was learned exactly** in 108/108 windows in C0, D1 and D2, 107/108 in D4, and 36 burst-on windows in D3. There were no false classes anywhere.
- **Transition windows in D3** were flagged 2–5 times per episode. They were decoded nominally, as designed, and are reported, not gated.
- **R of AD against AD_M (correlated matching on the same model)** was 0.47–0.61.

## Interpretation

- **Achieved (development):**
  - a causal rolling-window adaptive decoder that never harmed a static stream (C0);
  - it never learned a wrong burst;
  - it acquired and released a transient burst within one window length;
  - it kept AD within 6% of the oracle under every smooth or stepped drift tested.
- **Not shown:** that continuous re-estimation beats a single early estimate under smooth background drift. Within ±20% in p and Z-bias 1 → 8, the frozen estimate was already near-oracle. The decoder appears insensitive to background mis-estimation of that size. That is a post-hoc reading and was not tested.
- **The adaptive gain is in the burst structure, not the background rate.** D3 is the only schedule where the decoder's required support changes, and the only one where AD beat ONCE.

## Claim boundary

- Development evidence at d=5, in simulation, with public development bursts.
- Nothing here was evaluated on sealed data.
- No result is used to tune anything, and the endpoints are not redefined post hoc.
