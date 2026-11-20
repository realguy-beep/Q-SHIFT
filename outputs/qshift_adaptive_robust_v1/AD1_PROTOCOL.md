# AD1: adaptive decoding under drifting noise, a development study (pre-registered)

**Status: frozen** in `AD1_FREEZE.json`, committed before any AD1 study sample.

| Approval | Covers | Given |
|---|---|---|
| "Build AD1 first" | the build and the rehearsal | 2026-11-20 |
| Owner's choice of the principled endpoint fix | deviations 1 and 2 below | 2026-11-20 |
| "Run AD1" | the single run | not yet |

**Source:** `PLAN_AD1.md` (`0cd283c44`). Everything in it applies except the deviations below.

## What is run

**Stream:** 5 schedules × 6 episodes × 24 blocks.
- **Per block:** 2,000 unlabelled detector shots, 250 labelled calibration shots and 1,000 evaluation shots, at that block's true model. Bursts have q = 0.01 when on.
- **AD:** for every scored block t (6–23), it uses only blocks t−6 … t−1. Steps:
  1. E1T, the BRT-supported estimator;
  2. the Phase C learner and flip stage;
  3. BP+OSD on the estimated model with the learned support.

  On a flag: the nominal model and no burst.
- **ONCE:** AD's block-6 estimate, frozen.
- **ORACLE:** BP+OSD on block t's true model and support.
- **AD_M:** correlated matching on AD's model.
- **A_nominal:** burst-free matching.

All arms decode identical evaluation shots.

| Schedule | Background | Burst |
|---|---|---|
| C0 | p 0.003 | K (20 detectors), always on |
| D1 | p 0.0025 → 0.0035, linear | K |
| D2 | Z-bias 1 → 8, linear, p 0.003 | BRT X13 (30 detectors) |
| D3 | p 0.003 | BRS W13 (30 detectors), on in blocks 8–15 only |
| D4 | p 0.0025, stepping to 0.0035 at block 12 | K |

## Build-time deviations (owner-approved after the rehearsal; rehearsal seeds, not study data)

1. **Flags are gated only in settled windows.**
   - **What the rehearsal showed:** a window that only partly overlaps a burst (1–4 of 6 blocks) gives E1 a few burst-detector exclusions, but too little signal for the learner to accept. The consistency rule (S2) then flags it, and the decoder uses no burst. That is the safe outcome, identical to an unlearned window.
   - **Why the plan's endpoint cannot pass:** each onset or offset produces about 4 such windows (7 in the rehearsal episode). "At most 1 flagged window per episode" therefore fails by design.
   - **Now:** the endpoint counts flags only in **settled** windows, those with all 6 blocks in one burst state. Transition-window flags are reported, not gated.
2. **Onset limit: 3 → 6 blocks.**
   - **Why:** the plan's 3 was a guess. The rehearsal learned W13 at latency 5, when 5 of the 6 window blocks contained the burst.
   - **The principled limit is the window size:** the burst must be learned by the time the window lies wholly inside the burst.
   - **Unchanged:** the offset limit stays 6. The rehearsal dropped the burst at latency 2.
3. **`ad1_stream.py` is minimal:** per-block truth and sampling only. The episode logic lives in `ad1.py`.
4. **Preflight timing assumption:** L2 decoding at 18.5 ms per shot, measured single-process, × 1.6 for 8-way contention (as observed in RE1).

## Endpoints (development; frozen)

Errors are pooled over scored blocks. CIs come from an episode bootstrap with 20,000 replicates, seeded from `qshift-adaptive-robust-v1:ad1:boot`.

| Endpoint | Rule |
|---|---|
| Tracking (D1, D2, D4) | (AD − ORACLE) / ORACLE ≤ 0.25, **and** the upper 97.5% bound of AD − ONCE is below 0 |
| No harm (C0) | AD errors ≤ 1.1 × ONCE errors + 3 |
| Burst onset (D3) | median latency ≤ 6 blocks to the first window that learns W13 exactly, **and** 0 mis-learned windows (a class accepted that is not the window's true burst) in D3 |
| Burst offset (D3) | median latency ≤ 6 blocks to the first window that drops the burst (no class, or flagged) |
| Flags | at most 1 flagged **settled** window per episode, in every schedule |

**Verdict:**
- **AD1_SUPPORTED:** every endpoint passes.
- **AD1_PARTIAL:** tracking passes in at least 2 of the 3 tracking schedules, and no harm passes.
- **AD1_NOT_SUPPORTED:** otherwise.

**Also reported:** per-block LER curves, per-block p̂ and b̂, R of AD against AD_M, transition flags, and the off-segment excess.

## Seeds (`AD1_SEEDS.json`)

2,160 study keys and 144 rehearsal keys, screened against 8,183 prior values, `BRT_SEEDS.json` included.

## Preflight (`AD1_PREFLIGHT.json`)

- **Inputs:** the slowest rehearsal episode, 230 s at 200 evaluation shots per block, scaled to 1,000 shots per block. An episode is projected at about 1,509 s.
- **Projection:** 30 episodes in 4 waves on 8 workers is about **1.7 h**, or 2.1 h with contention, against the 5 h budget.
- **Consequence:** the fallback (5 episodes per schedule) is not applied.

## Execution (single attempt)

```
git checkout --detach <freeze commit>
cd outputs/qshift_adaptive_robust_v1
python ad1.py run eval --expected-head <freeze commit> --workers 8
python ad1.py analyze eval <out1>
python ad1.py analyze eval <out2>            # byte-identical
python ad1.py recount eval <out1>/ANALYSIS.json
git checkout codex/qshift-adaptive-robust-v1   # then commit results
```

**Safeguards:**
- a clean tree and the expected head, with every frozen hash checked per job;
- write-once records and archives, with no retries;
- the recount re-derives the analysis and replays episode 0 of every schedule bit-identically.

## Rehearsal (rehearsal seeds; not data)

The rehearsal used episode 0 of C0 and D3, at 200 evaluation shots per block.

- **C0:** every window learned K exactly, with no flags. p̂ was 0.00299–0.00305. AD, ONCE and ORACLE made identical errors.
- **D3:**
  - Before onset, no class was accepted (0 false bursts).
  - At onset, the transition windows were flagged (safe). W13 was learned exactly from block 13 (latency 5) and kept through block 17.
  - After offset, the burst was dropped from block 18 (latency 2).
  - Nothing was mis-learned.
- **Reproducibility:**
  - the analysis was byte-identical across two runs, before and after the endpoint change;
  - the recount re-analysis was identical;
  - both replayed episodes were bit-identical.

## Claim boundary

- Development evidence at d=5, with weight-3 bursts and piecewise-constant drift, in simulation.
- The rolling window responds with up to 6 blocks of lag, and there is no change detector.
- The bursts are public development bursts, not sealed.
- A supported result motivates a frozen RE2-adaptive with a new sealed burst.
