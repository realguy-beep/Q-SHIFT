# Plan: AD3, faster reaction to a change (development study)

**Status: plan only.** Nothing is built or sampled.

| Approval | Covers |
|---|---|
| "Approve, build it" | code, tests, seeds, the calibration screen (Phase 1), the rehearsal, the preflight and the freeze |
| "Run AD3" | the single development run (Phase 2) |

No seal is opened. RE1's H2, RE2's H3/H4 and the V1.6 d=3 seal stay closed. AD3 uses AD2's public bursts A–D and AD2's schedules unchanged.

## Why

**AD2's lesson (`AD2_RESULTS.md`, post hoc):** AD2_STRONG, but almost all of AD's excess over the oracle is in the blocks just after a change.
- **The cause is the window, not the learner.** AD re-estimates from the last 6 blocks, so after a change the window still holds mostly old-burst rows. The new burst is only learned once new rows dominate: a median latency of 3.5–5.5 blocks.
- **The cost is largest when the burst keeps changing.** In S2 (on and off every 6 blocks), AD spends over half of every segment catching up: 2,048 errors against the oracle's 187, and only 42% below the standard decoder.
- **The obvious fix failed.** A plain 3-block window (AD_W3) reacted faster but raised false flags in settled windows in the rehearsal, because E1T was never validated at 6,000 rows.

**The question:** does detecting the change and restarting the window at it, instead of always using the last 6 blocks, cut the transition errors without false alarms and without harming settled or static decoding?

AD2 is not re-scored. AD3 is a new study with fresh seeds and its own pre-declared endpoints. Because AD3's design was motivated by AD2's results, AD2's data is not reused for any AD3 test.

## The method: AD3 (change-aware window)

Everything is AD1/AD2's pipeline (E1T → Phase C learner and flip → BP+OSD), except which blocks the estimate uses.

1. **Change statistic.** After block t−1 arrives, compare its 2,000 unlabelled detector rows with the pooled rows of the current segment (the blocks since the last detected change, up to 6). The statistic is a two-sample test on per-detector firing rates (a binomial log-likelihood-ratio sum over detectors). It uses unlabelled detector data only and costs milliseconds.
2. **Detection.** If the statistic exceeds a threshold τ, a change is declared at block t−1, and the segment restarts there.
3. **Window.** The estimate for block t uses the segment's blocks only, capped at the last 6. With no change detected, this is exactly AD2's 6-block window, so AD3 and AD decode identically in settled and static stretches.
4. **Short segments.** While the segment holds fewer than M blocks, the estimate uses those blocks if E1T accepts it. On a flag, the decoder falls back to a background-only model: E1's p̂ and b̂ on the segment, with no burst. AD2's fallback was the nominal model.

τ and M are fixed by Phase 1, by the rules below, before any study sample.

## Phase 1: calibration screen (no evaluation decoding; separate screen seeds)

This is cheap (about 1 h of compute) and decides τ and M by fixed rules, with no look at decoding errors.

- **τ (false alarms).** Draw 20 static streams, 5 per burst A–D plus none, with 30 blocks each, and compute the statistic between each block and its preceding segment. τ is the smallest value giving **at most 1 false detection per 100 block comparisons**.
- **τ (power, reported only).** On 20 streams with a change at block 15 (A → B, A → none, none → A, B → C, C → D), report the detection rate within 1 and 2 blocks at that τ. If detection within 2 blocks is below 80%, the plan stops and comes back to the owner before any study sample.
- **M (shortest reliable segment).** For window lengths of 1, 2 and 3 blocks, run E1T + learner on 20 static windows per burst A–D. M is the smallest length with **learned-exactly ≥ 95% and false flags ≤ 5%** across bursts. If none qualifies, M = 6 and AD3 reduces to change-reset with a background-only fallback.
- **Records:** the screen's records and its rule outputs are committed in the freeze.

## Phase 2: the study

| | |
|---|---|
| **Stream** | AD2's, unchanged: 30 blocks; per block 2,000 unlabelled + 250 labelled + 1,000 evaluation shots; blocks 6–29 scored; q = 0.01 |
| **Schedules** | AD2's C0, S1, S2, S3, S4, unchanged |
| **Episodes** | 6 per schedule, fresh seeds screened against every prior inventory (through `AD2_SEEDS.json`) |
| **Arms** (identical evaluation shots) | **AD3** (candidate); **AD** (AD2's method, the comparison); ONCE; PERIODIC; ORACLE; A_nominal. Identical (model, support) pairs are decoded once and shared, as in AD2 |
| **Cost** | about AD2's: AD3 needs a second estimate only on post-change blocks. Projected 4–5 h on 8 workers; the preflight checks this against a 6 h budget |

## Endpoints

Bounds are episode-bootstrap, 20,000 replicates, one-sided 97.5%, as differences in LER over scored blocks.

| # | Endpoint | Rule |
|---|---|---|
| F1 | Faster adaptation where it matters | S2: AD3 − AD upper bound < 0 |
| F2 | No loss on the other changing schedules | S1, S3, S4: AD3 − AD point estimate ≤ 0 in each |
| F3 | No harm when static | C0: AD3 ≤ 1.1 × AD + 3 errors |
| F4 | Safety | 0 mis-learned settled windows (AD2's rule) |
| F5 | Latency | median AD3 latency ≤ 2 blocks on each of S1–S4 (AD2's definition) |

**Verdicts:**

| Verdict | Requires |
|---|---|
| AD3_STRONG | F1–F5 |
| AD3_SUPPORTED | F1–F4 |
| AD3_PARTIAL | F1, F3, F4 |
| AD3_NOT_SUPPORTED | otherwise |

**Descriptive (not gated):** AD3's reduction against the standard decoder and its excess over the oracle per schedule; false detections per C0 episode; transition versus settled errors; and the TIMELINE export for the website, in AD2's format.

## Process

As AD2: build with tests (no sampling) → Phase 1 screen → rehearsal (1 episode of C0 and S2, 200 evaluation shots per block) → preflight → freeze → "Run AD3" → analyse twice (byte-identical) → recount and replay → commit → push only on "Push it".

## Rough timing

| Day | Step |
|---|---|
| 1 | build, tests, Phase 1 screen |
| 2 | rehearsal, preflight, freeze; the run overnight (4–5 h) |
| 3 | analysis, recount, results; then the competition figures |

## Claim boundary

Development evidence at d=5, with public weight-3 bursts, piecewise-constant noise and simulation only. AD2's verdict stands whatever AD3 shows.
