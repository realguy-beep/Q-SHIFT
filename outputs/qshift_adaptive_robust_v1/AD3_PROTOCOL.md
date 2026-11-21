# AD3: faster reaction to a change (development; pre-registered)

**Status: frozen** in `AD3_FREEZE.json`, committed before any AD3 study sample.

| Approval | Covers | Given |
|---|---|---|
| (plan) | `PLAN_AD3.md` (`31d7dd777`) | 2026-11-21 |
| "Approve, build it" | code, tests, seeds, the Phase 1 screen, the rehearsal, the preflight and the freeze | 2026-11-21 |
| "Run AD3" | the single development run, once frozen | 2026-11-21, given during the build; the run starts only from the frozen commit |

**Source:** `PLAN_AD3.md`. Everything in it applies, except the build-time changes below. No seal is read: AD3 uses AD2's public bursts A–D and AD2's schedules, and the freeze contains no seal module or commitment.

## Build-time changes (written into the code before the Phase 1 screen ran; no study sample)

1. **Fallback in short segments.**
   - **The plan:** after a change, while the segment is shorter than M, or when the segment's estimate is flagged, AD3 would decode with a background-only model (E1's p̂ and b̂ on the segment, no burst).
   - **Built instead:**
     - first, **recall** a model learned earlier in the episode, if its window rows are not rejected against the segment (G ≤ τ, smallest G);
     - otherwise, **AD's own 6-block estimate**, which is AD2's behaviour.
   - **Why:** a background-only model would decode every new burst with no burst at all, which is worse than AD2's stale window. AD's estimate makes AD3 no worse than AD wherever no faster route exists. Recall adds a fast route when a known state returns.
2. **The library.** Every unflagged AD3 estimate whose window lies inside one segment is stored, with its window's detector counts: the latest entry per learned (class, flip), the burst-free state included. Estimates from windows that span a detected change are never stored.
3. **Causality.** The change test for block u runs after block u is decoded. Block t's model uses only blocks before t.
4. **Arms.** AD3, AD, PERIODIC, ONCE, ORACLE and A_nominal, as planned. AD's estimate is shared, so AD, PERIODIC and ONCE are AD2's arms exactly.
5. **Latency (F5).** AD2's definition, applied to AD3's effective estimate. For a recalled model, "learned exactly" means the recalled (class, flip) equals the true class and flip of block t − 1.

## Phase 1 screen (`AD3_SCREEN.json`; screen seeds; 735 s)

| Part | Result | Rule outcome |
|---|---|---|
| τ | 580 static comparisons; median G 118.2, 99th percentile 162.0, max 186.8 | **τ = 163.13** (5 of 580 above) |
| Power | 19/20 changes detected on the change block itself; 1 miss (A → none, detected 11 blocks late). 4 false detections in 280 pre-change comparisons (1.4%) | 95% within 2 blocks ≥ 80%: **no stop** |
| M | learned exactly / flagged over A–D: 1 block 1% / 69%; 2 blocks 25% / 68%; 3 blocks 60% / 36% | **no length qualifies → M = 6** |

**Consequence of M = 6:**
- **No segment estimate is ever used.** AD3 is AD's 6-block window, plus change detection and recall in the 5 blocks after each detected change.
- **A burst AD3 has never seen** (S1, S3 and S4's new bursts) cannot be learned faster than AD learns it. AD3 can only gain where a known state returns: S2's A and its burst-free state.
- **So F5 (median latency ≤ 2 on S1–S4)** is not expected to pass on S1, S3 and S4, and the realistic best verdict is AD3_SUPPORTED. This is stated here, before any study sample. No endpoint is changed.

## Frozen elements

| Element | Content |
|---|---|
| Method | AD2's pipeline (`ad2.estimate` → `ad1.estimate_window`, unchanged), with AD3's window rule above; τ = 163.13 and M = 6 read from `AD3_SCREEN.json` |
| Change statistic | two-sample binomial log-likelihood ratio over the 120 detectors: block u's 2,000 unlabelled rows against the pooled rows of the current segment's blocks before u (at most 6) |
| Stream and schedules | AD2's, unchanged: 30 blocks; per block 2,000 + 250 + 1,000 shots; blocks 6–29 scored; q = 0.01; C0, S1, S2, S3, S4 |
| Episodes | 6 per schedule (the preflight's level 0) |
| Endpoints | F1 S2: AD3 − AD upper bound < 0. F2 S1, S3, S4: AD3 − AD point estimate ≤ 0. F3 C0: AD3 ≤ 1.1 × AD + 3. F4 0 mis-learned settled windows for AD3. F5 median AD3 latency ≤ 2 on each of S1–S4 |
| Verdicts | STRONG (F1–F5), SUPPORTED (F1–F4), PARTIAL (F1, F3, F4), NOT_SUPPORTED |
| Statistics | episode bootstrap, 20,000 replicates, seeded from `qshift-adaptive-robust-v1:ad3:boot` + schedule index; one-sided 97.5% |
| Seeds | `AD3_SEEDS.json`: 2,700 study, 180 rehearsal and 2,280 screen keys, screened against 13,804 prior values (through `AD2_SEEDS.json`) |
| Website export | `TIMELINE.json`, AD2's format, plus AD3's learned and change-detected fractions per block |

## Rehearsal (rehearsal seeds; not data)

- **Run:** 1 episode each of C0 and S2, with 200 evaluation shots per block. The windows and calibration were full size.
- **C0:** no change detected in 28 comparisons (blocks 1–28). AD3 used AD's window in all 24 blocks and was identical to AD (8 errors each).
- **S2:**
  - **Detection:** all four true changes were detected on the change block, plus one false detection (block 23).
  - **Recall:** AD3 recalled the burst-free state at 13 and 25 and burst A at 19. Its latencies were 3, 1, 1, 1, against AD's 3, 3, 4, 4.
  - **Errors:** AD3 40, AD 49, ORACLE 3.
  - **Mis-learning:** none in a settled window.
- **Reproducibility:** the analysis (`ANALYSIS.json` and `TIMELINE.json`) was byte-identical across two runs. The recount's re-analysis was identical, and both episodes replayed bit-identically (records and decoded error bits).
- **Verdicts are meaningless here.** Only 2 of 5 schedules were run, at 200 shots per block, and the rehearsal tunes nothing.

## Preflight (`AD3_PREFLIGHT.json`)

- **Per episode** (non-decode seconds + decode seconds × 5): C0 4,258 s, S2 3,803 s.
- **Projection** (the slowest episode × 4 waves on 8 workers × 1.25): **21,290 s against the 21,600 s budget**, so level 0 (6 episodes) applies. The worst episode × 1.25 is 5,323 s, against the 9,000 s job timeout.

## Execution (single attempt)

```
git checkout --detach <freeze commit>
cd outputs/qshift_adaptive_robust_v1
python ad3.py run eval --expected-head <freeze commit> --workers 8
python ad3.py analyze eval <out1>
python ad3.py analyze eval <out2>            # byte-identical ANALYSIS.json and TIMELINE.json
python ad3.py recount eval <out1>/ANALYSIS.json
git checkout codex/qshift-adaptive-robust-v1   # then commit the results
```

`studykit.require_frozen_head` runs in the launcher and in every job. `RUN_STATUS.json` refuses a relaunch. Records are write-once, with no retries and no seed substitutions.

## Claim boundary

Development evidence at d=5, with public weight-3 bursts, piecewise-constant noise and simulation only. AD2's verdict stands whatever AD3 shows. AD3's design was motivated by AD2's results; AD2's data is not reused.
