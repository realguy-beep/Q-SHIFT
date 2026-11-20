# Plan: AD2, adaptive decoding when the burst itself changes (development study)

**Status: plan only.** Nothing is built or sampled.

| Approval | Covers |
|---|---|
| "Approve, build it" | code, tests, burst choice, seeds, rehearsal, preflight and freeze |
| "Run AD2" | the single development run |

No seal is opened. RE1's H2, RE2's H3/H4 and the V1.6 d=3 seal stay closed, and AD2 uses only public development bursts.

## Why

**AD1's lesson (`AD1_RESULTS.md`):**
- **Re-estimating a drifting background bought nothing.** A single early estimate (ONCE) was already within 1–6% of the oracle.
- **Adaptation paid when the burst itself changed.** In D3, where a burst switched on and off, AD made 117 errors against ONCE's 156. That schedule was not a pre-registered tracking endpoint.

**RE2's lesson (`RE2_RESULTS.md`):** one flagged estimate decoded with the nominal model cost more errors than the NI floor allowed. In a stream there is a natural cheaper fallback, the last accepted model, and AD2 tests it.

**The question:** when the burst appears, disappears, switches to another location or changes repeatedly, does the rolling-window adaptive decoder:
- clearly beat calibrate-once;
- beat periodic offline recalibration, the honest deployable competitor;
- stay close to the oracle?

AD1's endpoints are not redefined. AD2 is a new study with its own pre-declared endpoints.

## The stream model

As in AD1, except where stated.

| | |
|---|---|
| **Blocks** | **30** per episode (AD1: 24). Noise is constant within a block and changes between blocks according to the schedule |
| **Shots per block** | 2,000 unlabelled detector shots, 250 labelled calibration shots, 1,000 evaluation shots (as AD1) |
| **Window** | the trailing **6 blocks**: 12,000 + 1,500 rows, the validated calibration size |
| **Causality** | block t is decoded only from blocks before t. Blocks 0–5 are warm-up; blocks 6–29 (**24 blocks**) are scored |
| **Burst rate when on** | q = 0.01 (as AD1) |

## Arms (identical evaluation shots)

| Arm | Model and support for block t | Role |
|---|---|---|
| **AD** | AD1's pipeline unchanged: E1T on blocks t−6 … t−1, then the Phase C learner and flip, then BP+OSD. On a flag: nominal, no burst | **candidate (gated)** |
| **AD_LG** | as AD, but on a flag it keeps the **last accepted** model and support (nominal if none yet) | the RE2-motivated fallback (gated as a secondary candidate) |
| **PERIODIC** | the same pipeline re-run only at blocks 6, 12, 18 and 24 on the preceding 6 blocks, then held fixed for 6 blocks | periodic recalibration, the deployable competitor |
| **ONCE** | the same pipeline once on blocks 0–5, then frozen | calibrate-once, today's practice |
| **ORACLE** | BP+OSD on block t's true model and true support | reference ("the same decoder with perfect knowledge of the noise") |
| **AD_M** | correlated matching on AD's model and support (q_dec 0.0025) | deployable matcher (R against the strongest matcher) |
| **A_nominal** | burst-free matching on the nominal model | the standard decoder (R against the standard decoder) |
| **AD_W3** | as AD with a **3-block** window (6,000 + 750 rows) | **descriptive only**: how much faster a shorter window reacts. E1T's flag was not validated at this size, so nothing is gated on it |

**Shared work:** AD, AD_LG and AD_W3 share sampling, and AD and AD_LG share the same estimate on every unflagged window. Identical (model, support) pairs are decoded once and reused, which is exact by construction and checked in the tests.

## Bursts

All are public development bursts from `BRS_BURSTS.json` and `BRT_BURSTS.json`.
- **Excluded:** K, W13 and X13, which AD1 used.
- **Choice:** four bursts, named A–D, are chosen **at build, by a fixed rule written before any AD2 sample.** The rule takes the first public burst in each of the footprint strata ≤ 15, 16–20, 21–25 and ≥ 26 detectors, in label order with BRS before BRT, then assigns them to A–D in footprint order. Every stratum has at least 3 eligible public bursts: footprints 5–30, 16 bursts per file.
- **Recorded:** the choice goes into `AD2_PROTOCOL.md` and the freeze before any study sample.

## Schedules (development values)

Background p 0.003, balanced, unless stated.

| ID | Burst timeline | Tests |
|---|---|---|
| **C0** | A on throughout (static) | control: adapting must not hurt |
| **S1** switch | A in blocks 0–14, then B in 15–29 | one burst replaced by another |
| **S2** intermittent | A on in 6–11, off in 12–17, on in 18–23, off in 24–29 | repeated release and re-acquisition |
| **S3** switch with step | A → C at block 15, **and** p steps 0.0025 → 0.0035 at block 15 | a combined structural and background change |
| **S4** multi-switch | B in 0–9, then C in 10–19, then D in 20–29 | a burst that keeps moving, across footprint sizes |

**Episodes:** 6 per schedule, so 30 in all, with fresh seeds per block. The seeds are screened against every prior inventory, through `RE2_SEEDS.json`.

## Endpoints (development; pre-declared)

Errors are pooled over scored blocks. 95% CIs come from an episode bootstrap, with 20,000 replicates and a one-sided 97.5% bound.

| # | Endpoint | Rule |
|---|---|---|
| E1 | **Adaptive gain** (S1–S4) | upper bound of AD − ONCE below 0, in each of S1–S4 |
| E2 | **Beats periodic recalibration** (S1–S4) | upper bound of AD − PERIODIC below 0. Counted per schedule |
| E3 | **Near-oracle after settling** (S1–S4) | over **settled** blocks (all 6 window blocks in the current burst state), AD's excess over ORACLE is at most 25% of ORACLE's LER (point estimate) |
| E4 | **Acquire and release** | median latency from each change to the first window that learns the new burst exactly (or drops it): ≤ 7 blocks. A 6-block window needs up to 6 |
| E5 | **No harm** (C0) | AD's errors ≤ 1.1 × ONCE's errors + 3 (AD1's rule) |
| E6 | **No mis-learning** | 0 settled windows that accept a wrong class, in any schedule |

**Verdict:**
- **AD2_STRONG:** E1, E3, E4, E5 and E6 pass, **and** E2 passes in at least 3 of S1–S4.
- **AD2_SUPPORTED:** E1, E3, E4, E5 and E6 pass.
- **AD2_PARTIAL:** E1 passes in at least 2 of S1–S4, and E5 and E6 pass.
- **AD2_NOT_SUPPORTED:** otherwise.

**AD_LG, secondary:**
- E1, E3 and E5 are evaluated for AD_LG too.
- The table also reports whether AD_LG − AD has an upper bound below 0 over the transition blocks.
- It cannot change AD's verdict.

**Also reported (descriptive):**
- **The per-block LER curve for every arm**, also exported as `results/ad2/TIMELINE.json` for the project website: per schedule and block, each arm's mean LER and episode range, the true burst state, and AD's learned state.
- **R against the standard decoder** (A_nominal) and against the strongest matcher (AD_M), per schedule and over settled blocks.
- **AD_W3's latency and LER,** against AD.
- **p̂ and b̂ per block,** against the truth.
- **Flag counts,** settled and transition.

## Expected outcomes (stated before any sample, for honesty)

- **E1 is likely to pass.** After a switch, ONCE keeps decoding with a wrong burst for up to 24 blocks. AD1's D3 already showed AD beating ONCE.
- **E2 is genuinely uncertain.** PERIODIC is at most 6 blocks behind, and AD's own lag is up to 6 blocks because of the window. AD2 may well find that per-block adaptation and periodic recalibration are close. That would be reported as found.
- **The windows spanning a change will often be flagged.** AD_LG tests whether holding the last model beats falling back to nominal there. That is not obvious: after a switch, the last model holds the *old* burst.

## Cost

- **Sampling:** 30 episodes × 30 blocks × 3,250 ≈ 2.9 M shots.
- **Decoding:** up to 5 BP+OSD arms (AD, AD_LG, PERIODIC, ONCE, ORACLE), plus AD_W3. Reuse removes most duplicates: on settled blocks AD = AD_LG, and often = PERIODIC.
- **Wall time:** AD1 took 4,522 s for 30 episodes × 18 scored blocks with 3 BP+OSD arms. AD2 is projected at about 2.5–4 h on 8 workers, against a 5 h budget. The preflight from the rehearsal decides.
- **Pre-declared fallback, if over budget:** drop AD_W3 first, then go to 5 episodes per schedule.

## Schedule (fits the 10–15 days available)

| Day | Step | Needs |
|---|---|---|
| 1 | Review this plan | "Approve, build it" (or changes) |
| 2–3 | Build, tests, burst choice, seeds, rehearsal, preflight, freeze | — |
| 3–4 | Single run (about 3 h), analysis twice, recount, `AD2_RESULTS.md` | "Run AD2" |
| 5–7 | Competition results pack (below) | — |
| 8–10 | Website: an adaptive-timeline chart from `TIMELINE.json`, plus a results page | the website's repository or folder |
| 11–15 | Buffer: presentation, rehearsal of answers, fixes | — |

## Competition results pack (after AD2; no new sampling)

Built only from committed, frozen results.

- **One-page plain-language summary:**
  - what the decoder does;
  - the two baselines, stated side by side: the standard decoder (87–98% fewer errors across the 10 frozen gated conditions) and the strongest tuned decoder (57–91%);
  - "matches the same decoder given perfect knowledge of the noise";
  - the sealed-burst result (H3 learned 24/24);
  - AD2's adaptive result;
  - the limits.
- **Figures:**
  1. errors against both baselines, per frozen condition;
  2. learned-burst success: RE1 R6 (0/12) → RE2 H3 (24/24), with RE1's estimator alongside;
  3. the AD2 timeline;
  4. a method diagram;
  5. a limitations panel.
- **Figure script:** a single `make_figures.py`, deterministic, reading only `results/*/ANALYSIS.json` and `TIMELINE.json`.

## Boundaries

- Development evidence at d=5, with weight-3 public development bursts, piecewise-constant noise and simulation only.
- There is no change detector, so the window lag is inherent.
- AD_W3 is descriptive.
- The bursts are public. A sealed adaptive confirmation would be a separate, later study.

## Files (new, in this package)

| File | Purpose |
|---|---|
| `ad2_config.py` | blocks, schedules, burst rule, arms, endpoints |
| `ad2.py` | episode jobs (reusing `ad1_stream`, `ad1.estimate_window`), analyze, timeline export, recount: re-decode episode 0 of each schedule bit-identically |
| `prepare_ad2.py` → `AD2_SEEDS.json` | seeds, screened through `RE2_SEEDS.json` |
| `preflight_ad2.py` → `AD2_PREFLIGHT.json` | preflight |
| `freeze_ad2.py` → `AD2_FREEZE.json` | freeze (`studykit`) |
| `tests/test_ad2.py` | tests |
| `AD2_PROTOCOL.md` | protocol |

`ad1*.py`, `estimate*`, `brt` and the RE1 decoder builders are reused read-only. AD1's frozen files are not modified.

## Verification

**Unit tests:**
- the schedules produce the right per-block truth;
- the windows are causal for AD, AD_LG, AD_W3 and PERIODIC;
- PERIODIC updates only at 6, 12, 18 and 24;
- AD_LG equals AD on every unflagged window, and holds the last accepted model on a flagged one;
- decode reuse is exact;
- the burst rule is deterministic and excludes AD1's bursts;
- the seed screen is collision-free;
- the analysis works on synthetic records (each verdict tier is reachable);
- `TIMELINE.json` has the right schema.

**Rehearsal:** 1 short episode each of C0 and S1 on rehearsal seeds, with 200 evaluation shots per block. Analysis twice to a byte-identical result, and a re-decode.

**After the run:**
- recount;
- `AD2_RESULTS.md`, a DECISION_REPORT addendum, and updates to STATUS and the root index;
- commit. Push only on "Push it".
