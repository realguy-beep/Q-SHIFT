# AD2: adaptive decoding when the burst itself changes (development; pre-registered)

**Status: frozen** in `AD2_FREEZE.json`, committed before any AD2 study sample.

| Approval | Covers | Given |
|---|---|---|
| (plan) | `PLAN_AD2.md` (`1fc53f410`) | 2026-11-20 |
| "Approve, build it" | code, tests, burst choice, seeds, rehearsal, preflight and freeze | 2026-11-20 |
| "Run AD2" | the single development run | not yet |

**Source:** `PLAN_AD2.md`. Everything in it applies, except the build-time clarifications below. No seal is read: AD2 uses only public development bursts, and the freeze excludes every seal module and commitment.

## Build-time clarifications

All were found during the build, before any study sample.

1. **E3 is not computable on S2.**
   - A settled block needs block t and its whole 6-block window in one state, which takes 7 equal blocks. S2's on and off segments are 6 blocks each, so S2 has no settled block by construction.
   - E3 (near-oracle after settling) is therefore evaluated on **S1, S3 and S4**, and the core verdict condition uses those three.
   - S2 still counts for E1, E2 and E4. Its schedule is unchanged.
2. **Mis-learning (E6) follows AD1's rule.** It counts a settled window that accepts a wrong class: unflagged, a class learned, and not the window's true class. A missed burst is not a mis-learned class. It shows up in E3 and the latency endpoints instead.
3. **Window truth.** For the learner's correctness record, a window's true burst is the burst of its most recent block, t − 1. That is what an acquisition-latency count needs. Settled windows are unambiguous either way.
4. **Latency definition (E4).**
   - **Changes:** S1 at 15, S2 at 6/12/18/24, S3 at 15, S4 at 10/20.
   - **Latency:** the first block b > c whose window has learned the new burst exactly (acquire), or has dropped the burst by flagging or learning none (release, AD1's rule). The latency is b − c.
   - **No acquisition in the episode:** counted as 99 in the median.
   - **Scoring:** E4 needs each of S1–S4's medians, over all episodes and changes, to be ≤ 7.
5. **The burst rule's result:** A = W01 (10 detectors), B = W05 (20), C = W09 (25), D = W14 (30). A and D share 2 qubits, but S4 uses B → C → D, so A and D never follow each other.
6. **Decoder reuse.** Arms that resolve to the same (model, support) in a block share one decoder and one prediction, so their error bits are identical by construction. The record keeps, per block, which arms equalled AD's model.
7. **Preflight fallback levels:** 0 is as planned; 1 drops AD_W3; 2 also runs 5 episodes per schedule. The lowest level that fits is applied, and the run reads it from `AD2_PREFLIGHT.json`.
8. **The budget was raised from 5 h to 8 h, after the rehearsal and before any study sample.**
   - **Why:** the rehearsal showed per-block re-estimation costs about 75 s, plus about 50 s for AD_W3. The projections were 8.1 h at level 0 and 6.5 h at levels 1 and 2. Level 2 still needs 4 waves on 8 workers. So no pre-declared level fit 5 h.
   - **Options put to the owner:** raise the budget, or cut to 4 episodes.
   - **Decision:** the owner accepted the recommendation on 2026-11-20: keep 6 episodes and raise the budget to 8 h.
   - **Effect:** with the 8 h budget, the preflight applies the pre-declared level 1 (drop AD_W3) by its own rule.
   - **Unchanged:** no endpoint, arm, schedule or method. AD_W3 was descriptive.

## Frozen elements

| Element | Content |
|---|---|
| Method | AD1's `estimate_window`, unchanged: E1T, then the Phase C learner and flip, then BP+OSD via `re1.decoders` and `re1.predict`. The L2 prior is 0.01 and the matcher q_dec 0.0025 |
| Stream | 30 blocks; per block 2,000 unlabelled + 250 labelled + 1,000 evaluation shots (200 in the rehearsal); window 6 blocks (3 for AD_W3); scored blocks 6–29; q = 0.01 |
| Schedules | C0 (A static); S1 (A → B at 15); S2 (A on 6–11 and 18–23); S3 (A → C at 15, with p 0.0025 → 0.0035); S4 (B → C at 10, C → D at 20); background p 0.003 balanced unless stated |
| Arms | AD, AD_LG, PERIODIC (updates at 6/12/18/24), ONCE, ORACLE, AD_M, A_nominal, AD_W3 (descriptive) |
| Endpoints | E1 AD − ONCE upper < 0 (S1–S4); E2 AD − PERIODIC upper < 0 (S1–S4, counted); E3 settled excess over ORACLE ≤ 25% (S1, S3, S4); E4 median latency ≤ 7 (S1–S4); E5 C0 AD ≤ 1.1 × ONCE + 3; E6 0 mis-learned settled windows |
| Verdicts | STRONG (core + E2 in ≥ 3 of 4); SUPPORTED (core = E1 all, E3, E4, E5, E6); PARTIAL (E1 in ≥ 2, E5, E6); NOT_SUPPORTED |
| Statistics | episode bootstrap, 20,000 replicates, seeded from `qshift-adaptive-robust-v1:ad2:boot` + schedule index; one-sided 97.5% bound |
| Seeds | `AD2_SEEDS.json`: 2,700 study keys and 180 rehearsal keys, screened against 10,924 prior values (through `RE2_SEEDS.json`) |
| Website export | `TIMELINE.json`: per schedule and block, each arm's mean, minimum and maximum LER over episodes, the true burst and p, the settled marks, and AD's learned and flagged fractions |

## Preflight (`AD2_PREFLIGHT.json`)

- **Source:** the rehearsal (C0 and S1, 1 episode each, 2 concurrent workers).
- **Method:** non-decode seconds + decode seconds × 5 (1,000 / 200 evaluation shots). Without AD_W3, its measured seconds are subtracted.
- **Per episode:** C0 5,854 s with AD_W3 and 4,672 s without. S1 5,224 s and 4,560 s.
- **Projection** (slowest episode × 4 waves on 8 workers × 1.25):

  | Level | Projection | Fits 8 h |
  |---|---|---|
  | 0 | 29,270 s | no |
  | **1** | **23,360 s (6.5 h)** | **yes** |
  | 2 | 23,360 s | yes |

- **Applied: level 1.** AD_W3 is dropped and 6 episodes per schedule are kept. The worst episode × 1.25 is 5,840 s, against the 9,000 s job timeout.
- **Consequence:** AD_W3 is absent from the study, so nothing about it is reported from AD2. The rehearsal's AD_W3 figures below are rehearsal-only.

## Rehearsal (rehearsal seeds; not data)

- **Run:** 1 episode each of C0 and S1, with 200 evaluation shots per block. The windows and calibration were full size.
- **C0 (static burst A):** AD learned A exactly in 24/24 windows, with no flags and no mis-learning. AD and AD_LG matched ORACLE's error count in every block. ONCE and PERIODIC differed from it in one block, by 1 error.
- **S1 (A → B at block 15):**
  - **Latency:** AD acquired B exactly at block 19, a latency of 4.
  - **Errors in blocks 15–29:** AD 9, PERIODIC 22, ONCE 38, ORACLE 0.
  - **From block 19 on,** AD made 0 errors in every block.
  - **AD_W3** (3-block window) raised 8 flags, 6 of them in windows settled under its own 3-block size, and made more errors than AD. That is consistent with E1T's flag being unvalidated at 6,000 rows.
- **Reproducibility:**
  - the analysis (`ANALYSIS.json` and `TIMELINE.json`) was byte-identical across two runs;
  - the re-analysis was identical, and both episodes replayed bit-identically (records and decoded error bits).
- **Verdicts are meaningless here.** Only 2 of 5 schedules were run, at 200 shots per block, and the rehearsal does not tune anything.

## Execution (single attempt)

```
git checkout --detach <freeze commit>
cd outputs/qshift_adaptive_robust_v1
python ad2.py run eval --expected-head <freeze commit> --workers 8
python ad2.py analyze eval <out1>
python ad2.py analyze eval <out2>            # byte-identical ANALYSIS.json and TIMELINE.json
python ad2.py recount eval <out1>/ANALYSIS.json
git checkout codex/qshift-adaptive-robust-v1   # then commit the results
```

**Safeguards:**
- `studykit.require_frozen_head` runs in the launcher and in every job: expected head, clean tree, every frozen hash.
- `RUN_STATUS.json` refuses a relaunch.
- Records are write-once, with no retries and no seed substitutions.

## Claim boundary

As in `PLAN_AD2.md`: development evidence at d=5, with public weight-3 bursts, piecewise-constant noise and simulation only. AD_W3 is descriptive.
