# Plan: AD1, adaptive decoding under drifting noise (development study)

**Status: plan only.** Nothing is built or sampled.

| Approval | Covers |
|---|---|
| "Approve, build it" | code, tests, seeds, rehearsal, preflight and freeze |
| "Run AD1" | the single development run |

A frozen confirmatory version (RE2-adaptive, with a new sealed burst) would be planned separately, after AD1.

## Why

Every result so far uses a decoder that **calibrates once, then decodes with a fixed model**. BRE, BRS and BRT repaired the one-time estimate: E1T is now burst-footprint- and p-robust and rejects misfit, as development evidence (`BRT_RESULTS.md`). Nothing has yet tested noise that changes during a run, which is what an adaptive decoder is for.

**The question:** when the background noise drifts, steps, or a burst switches on and off, does a pipeline that **re-estimates (E1T) and re-learns on a rolling window** decode close to an oracle that knows the true model at every moment? And how much does calibrate-once lose?

## The stream model

**Blocks:** an episode is a sequence of **24 blocks**. Within a block the true noise is constant, and it changes between blocks according to the schedule.

**Shots per block:**
- 2,000 unlabelled detector shots, used for estimation;
- 250 labelled calibration shots, for the flip stage (like interleaved memory shots with a known prepared state);
- 1,000 evaluation shots, decoded by every arm.

**Window:** the trailing **6 blocks**, giving 12,000 unlabelled and 1,500 labelled rows. That is exactly the calibration size at which τ, E1 and the BRT flag were validated. No new tuning is needed.

**Causality:** block t is decoded using only the windows of blocks before t. Blocks 0–5 are warm-up, and blocks 6–23 (18 blocks) are scored. The adaptive controller in `adaptive/pipeline.py` is not used: its CUSUM change detector failed its gate in Codex's study. A plain rolling window comes first.

## Arms (identical evaluation shots)

| Arm | Model and support used for block t | Role |
|---|---|---|
| **AD** | E1T on the window of blocks t−6 … t−1, then the Phase C learner and flip stage, then BP+OSD on the estimated model. On a flag: the nominal model and no burst | candidate |
| **ONCE** | the same pipeline, run once on blocks 0–5 and then frozen for blocks 6–23 | today's practice |
| **ORACLE** | BP+OSD on block t's **true** model and the true support, when a burst is on | reference |
| **AD_M** | correlated matching on AD's model and support (q_dec 0.0025) | deployable matcher, gives R |
| **A_nominal** | burst-free matching on the nominal model | floor |

## Schedules (development values, not RE1's or RE2's)

The bursts are public development bursts.

| ID | Background | Burst (q = 0.01 when on) | Tests |
|---|---|---|---|
| C0 | p 0.003, balanced, constant | K, on throughout | control: adapting must not hurt |
| D1 | p drifts linearly 0.0025 → 0.0035 over 24 blocks | K, on throughout | slow drift |
| D2 | Z-bias drifts 1 → 8 linearly, p 0.003 | BRT X13 (30 detectors), on throughout | bias drift with a large burst |
| D3 | p 0.003, constant | BRS W13 (30 detectors): off in blocks 0–7, on in 8–15, off in 16–23 | burst onset and offset |
| D4 | p steps 0.0025 → 0.0035 at block 12 | K, on throughout | abrupt change |

**Episodes:** 6 per schedule, so 30 in all. Each episode uses fresh seeds per block.

**Cost:**
- **Sampling:** about 30 × 24 × 3,250 ≈ 2.3 M shots.
- **Decoding:** 3 BP+OSD arms × 1,000 shots × 18 blocks × 30 episodes ≈ 1.6 M BP+OSD decodes at ≤ 30 ms each, plus a re-learn per block.
- **Wall time:** about 3 h on 8 workers (the preflight confirms it), against a 5 h budget.
- **Fallback if the preflight is over budget:** 5 episodes per schedule.

## Endpoints (development; pre-declared)

Errors are pooled over scored blocks within a schedule. 95% CIs come from an episode bootstrap with 20,000 replicates.

| Endpoint | Rule |
|---|---|
| **Tracking** (D1, D2, D4) | AD's excess over ORACLE is at most 25% of ORACLE's LER (point estimate; the CI is reported). **And** AD beats ONCE: the upper bound of AD − ONCE is below 0 |
| **No harm** (C0) | AD's errors ≤ 1.1 × ONCE's errors + 3 |
| **Burst onset** (D3) | median latency ≤ 3 blocks from onset to the first window that learns W13 exactly. No mis-learned class in any scored block |
| **Burst offset** (D3) | median latency ≤ 6 blocks from offset to the first window that drops the burst (the window spans 6 blocks). Excess LER over ORACLE in the off segment is reported |
| **Flags** | in-family schedules: at most 1 flagged window per episode |

**Verdict:**
- **AD1_SUPPORTED:** every endpoint passes.
- **AD1_PARTIAL:** tracking passes in at least 2 of D1, D2 and D4, and no harm passes.
- **AD1_NOT_SUPPORTED:** otherwise.

**Also reported:**
- the per-block LER curves for each arm;
- the per-block p̂ and b̂ against the truth;
- R of AD against AD_M;
- learning outcomes in every window.

## Why this design

- **The window size is fixed at the validated calibration size.** A shorter, faster-tracking window needs its own study, because τ and the flag were validated at 12,000 rows.
- **The ORACLE is the right yardstick.** The question is how much of the true-model performance adaptation recovers, not the gain against matching.
- **AD_M keeps the gain against matching visible,** but it is secondary.
- **ONCE uses exactly the same estimator,** so the comparison isolates adaptation itself.

## Boundaries

- Development evidence at d=5, with weight-3 bursts, piecewise-constant drift, in simulation.
- There is no change detector: the rolling window responds with a lag of up to 6 blocks.
- Out-of-family drift (for example into measurement-heavy noise) is not included; E1T would flag it and fall back.
- Episode counts give development-level precision only.

## Files (new, in this package)

| File | Purpose |
|---|---|
| `ad1_config.py` | schedules, block sizes, arms and endpoints |
| `ad1_stream.py` | per-block true specs and sampling |
| `ad1.py` | episode jobs, analyze, recount: re-decode episode 0 of each schedule bit-identically |
| `prepare_ad1.py` → `AD1_SEEDS.json` | seeds, screened against every prior inventory |
| `preflight_ad1.py` | preflight |
| `freeze_ad1.py` → `AD1_FREEZE.json` | freeze |
| `tests/test_ad1.py` | tests (see Verification) |
| `AD1_PROTOCOL.md` | protocol |

It reuses `estimate3`/`4`/`5`, the Phase C learner and the RE1 decoder builders, all read-only.

## Verification

**Unit tests:**
- the schedule produces the right per-block specs;
- the window is causal: block t never sees blocks ≥ t;
- ONCE equals AD on block 6;
- ORACLE uses the true per-block model;
- the seed screen is collision-free;
- the analysis logic works on synthetic records.

**Rehearsal:** 1 short episode for C0 and D3 on rehearsal seeds, with 200 evaluation shots per block. Analysis run twice to a byte-identical result, plus a re-decode.

**After the run:**
- recount;
- `AD1_RESULTS.md` and a DECISION_REPORT addendum;
- commit. Push only on "Push it".
