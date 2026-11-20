# PLAN_RE2: frozen evaluation of the E1T pipeline with new sealed hidden bursts (plan only)

**Status:** plan. Nothing is built, drawn, sealed or sampled.

| Approval | Covers |
|---|---|
| "Approve, build it" | the build, the burst draw and seal, the seeds, the rehearsal, the preflight and the freeze |
| The owner's answer to decision D1 below | how RE1's sealed H2 is kept out of the pool |
| "Run RE2" | the single frozen run, with `--open-hidden-seal` |
| "Open the RE2 seal" | publishing the identity of H3 or H4, after the run |

## Why RE2

- **RE1 (`fe4471fff`, NOT_CONFIRMED):**
  - The mismatch-robust pipeline passed every gate for the known burst (R1–R5, 59–88% below the strongest deployable matcher, at oracle level).
  - It failed on the sealed hidden burst (R6). Its estimator (B2) flagged every root, so the burst was never learned.
- **The estimator was rebuilt on development data:**
  - BRE: E1;
  - BRS: E1S;
  - BRT: E1T, which has no residual statistic and no tuned parameter. BRT was SUPPORTED: 126/128 bursts of 5–30 detectors learned exactly, with no in-family false bursts.
- **AD1 changes nothing here.** It tested adaptation, not the estimator.

RE2 is the frozen test that RE1 failed. It asks whether E1T → Phase C learner → BP+OSD learns and decodes **bursts nobody has seen**, under base-model mismatch, at oracle level, and beats the strongest deployable matcher.

## The burst pool (measured at plan time; no sampling)

**Rule:** RE1's candidate pool (`re1_seal.candidate_pool`, 1,998 supports), minus:
- every BRE, BRS and BRT burst class, and K (57 public development bursts);
- any support sharing ≥ 2 qubits with one of those bursts.

Each class is kept once.

**Result:** 182 eligible classes.

| Detector footprint | 5 | 10 | 15 | 20 | 25 | 30 |
|---|---|---|---|---|---|---|
| Eligible classes | 7 | 27 | 42 | 71 | 34 | **1** |
| All classes | 12 | 63 | 190 | 328 | 284 | 126 |

- **30-detector classes are nearly gone.** Only one is eligible, so a draw restricted to them would not be a draw.
- **The ≥ 25-detector stratum still holds 35 classes.** That is where RE1's estimator broke: B2 fails on 25–30-detector footprints, the regime RE1's diagnosis points to.

**Plan:** two sealed bursts, each drawn uniformly by OS entropy within its stratum, one support per class.

| Burst | Stratum | Eligible | Purpose |
|---|---|---|---|
| **H3** | footprint ≥ 25 | 35 | the RE1 failure regime |
| **H4** | footprint ≤ 20 | 147 | a generic unseen burst |

The near-exclusion rule is kept as it is; it is not relaxed to rebuild the 30-detector pool. E1T has no tuned parameter, so the main leakage risk from development bursts is the structural rule's class table, which covers every class anyway. Keeping RE1's rule costs nothing here.

## Decision D1 (the owner's): keeping RE1's H2 out of the pool

- **Why H2 is spent:** BRE, BRS and BRT were designed in response to RE1's R6 diagnosis. That diagnosis concerned H2's footprint behaviour, not its identity.
- **The risk:** if H3 or H4 landed in H2's class, or next to it, RE2 would re-test a burst whose failure shaped the method.
- **Why it isn't negligible:** H2 is large-footprint by that diagnosis, and H3's stratum has only 35 classes.

| Option | What happens | Cost |
|---|---|---|
| **(a) Exclude H2 in-process (recommended)** | `re2_seal.py` opens RE1's seal inside the draw, verifies its commitment, and removes H2's class and every support within one qubit of H2. It prints nothing about H2. The commitment records only a hash of the final pool and the pre-exclusion pool sizes, so the sizes cannot reveal H2's stratum. | It reads sealed data, without publishing it. Needs the owner's explicit OK. |
| (b) Do not read H2 | Draw from the pool as measured, and record the residual risk. If the RE2 seal is opened later and H3 or H4 turns out to be in or next to H2's class, that condition is reported as contaminated and not confirmatory. | No access to sealed data. A real chance of a wasted condition. |

## Conditions

Each condition has 12 roots per gated condition, the same as RE1. Per root:
- 3 q values (0, 0.01, 0.02);
- per q, 12,000 unlabelled + 1,500 labelled calibration rows and 4,000 evaluation shots.

| Cond | True base model | Burst | Gated | Role |
|---|---|---|---|---|
| G1 | p 0.0024 | K | yes | known burst, background p low |
| G2 | p 0.0032, Z-bias 6 | K | yes | known burst, combined mismatch |
| **G3** | **p 0.0028, Z-bias 4** | **H3 (sealed, large)** | **yes** | **R6's exact base model with a new large-footprint burst: the direct re-test** |
| G4 | p 0.0033 | H3 | yes | the large hidden burst at high p, where E1's statistic used to drift |
| G5 | p 0.0026, Z-bias 5 | H4 (sealed, generic) | yes | generic unseen burst under mismatch |
| X2 | p 0.003, X-bias 6 | K | no (6 roots) | out-of-family safe-fallback check, descriptive |

- **G3's exception:** G3 deliberately repeats R6's base model so the two are directly comparable.
- **Every other condition:** its (p, bias) pair differs from every condition in RE1, BRE, BRS, BRT and AD1, asserted by a test.

## Arms

- **L2L_E (the pipeline):**
  1. E1T on the unlabelled rows;
  2. on a flag: the nominal model, otherwise `brt.zspec(p̂, b̂)`;
  3. the Phase C learner and `learn_flip` on the labelled rows;
  4. BP+OSD on the estimated model with the learned support.
- **S\*, the strongest deployable matcher:** chosen per root from {Astar_Em (correlated matching on the estimated model with the learned support), Astar_Nm (nominal model)} by labelled calibration errors. A tie goes to Astar_Em. This is RE1's rule.
- **L2s_true (oracle):** BP+OSD on the true model with the true support.
- **Astar_true and A_nominal:** as in RE1.
- **L2L_B2 (descriptive, G3 and G4 only):** RE1's B2 pipeline, unchanged. It shows on the same shots whether the rebuild is what changed the outcome.

RE1's L2L_N is dropped: RE1 already settled the nominal-learner question.

## Endpoints (gated conditions; all RE1 rules unchanged)

| Endpoint | Rule |
|---|---|
| NI | upper bound of L2L_E − L2s_true < 0.25 × the oracle's nonzero-q LER |
| SUP | upper bound of L2L_E − S\* < 0 |
| Safety (q=0) | p95 of L2L_E − A_nominal ≤ 0, or ≤ max(0.05 × LER_q0(A_nominal), 3 / N_q0) |

- **Statistics:** one-sided bounds at α = 0.025 / (2 × 5), with a root bootstrap of 20,000 replicates seeded from `re2:stats:<cond>`.
- **Verdict (RE1's rule):**
  - **CONFIRMED:** all five gated conditions pass all three endpoints.
  - **NOT_CONFIRMED:** any NI or safety point estimate beyond its margin, or a SUP point estimate ≥ 0.
  - **PARTIAL:** some conditions pass all three, and none fails in the wrong direction.
  - **INCONCLUSIVE:** otherwise.
- **Also reported:**
  - learned-exactly and flag counts per condition (hidden supports recorded as `"SEALED"`);
  - R against S\*;
  - L2L_B2 against L2L_E on G3 and G4;
  - X2's fallback rate.

## Seal handling (as in RE1)

- **`re2_seal.py`:**
  - draws H3 and H4 with `secrets.randbelow`;
  - writes the plaintext (supports and salt) only beside the worktrees, outside git;
  - commits `HIDDEN_COMMITMENT_RE2.json`, which holds a SHA-256 of the canonical plaintext, the exclusion rules, the pool hash and the pre-exclusion pool sizes;
  - refuses to run twice.
- **The rehearsal** uses a public, deterministic rehearsal burst per stratum, which is removed from the pool before the draw.
- **The hidden supports** are read only inside the frozen run (`--open-hidden-seal`), never printed, and stored as `"SEALED"`.

## Seeds, freeze, safeguards

- **Seeds:** `RE2_SEEDS.json`, with keys `re2:<cond>:r<NN>:<cal|eval>:q<i>` and `re2:stats:<cond>`, plus rehearsal keys. They are screened against every prior inventory through `AD1_SEEDS.json`.
- **Freeze:** `RE2_FREEZE.json` via `studykit.write_freeze`. It covers every file the run imports, the seal commitment and the seeds.
- **Run guard:** `studykit.require_frozen_head` in every job. Records and archives are write-once; there are no retries and no seed substitutions.
- **After the run:**
  - the analysis is run twice and must be byte-identical;
  - the recount re-analyses and re-decodes root 0 of every condition end to end, bit-identically.

## Cost (preflight to confirm from the rehearsal)

- **Main arms:** RE1 measured about 47 s fixed and 29.5 ms per BP+OSD arm per shot under contention. With 2 BP+OSD arms over 12,000 shots, a root takes about 755 s.
- **L2L_B2:** adds about 350 s on 24 roots.
- **Run time:** 66 roots on 8 workers in 9 waves is about **2.0 h**, or 2.5 h with a 1.25 factor, against a 5 h budget and a 3,600 s job timeout.
- **Pre-declared fallback** if the preflight exceeds the budget: drop L2L_B2.
- **Sample count:** 66 roots × 3 q × 17,500 = 3.47 M sampler shots.

## Claim boundary

A CONFIRMED verdict would support this, at d=5 in simulation on fresh seeds: the E1T pipeline decodes within 25% of the oracle and beats the strongest deployable matcher, under background p 0.0024–0.0033 and Z-bias 4–6. That holds for the known burst and for two sealed, never-seen weight-3 bursts, one with a large (≥ 25-detector) footprint.

It would not bear on:
- d ≥ 7, or non-synthetic noise;
- bursts of other weights;
- adaptivity;
- the 95% target, since R is expected at about 60–90%.

## Build outline (after "Approve, build it")

1. **Config:** `re2_config.py` holds the conditions, arms, endpoints and keys.
2. **Seal:** `re2_seal.py` holds the pool and the draw, run per D1.
3. **Seeds:** `prepare_re2.py`.
4. **Runner:** `re2.py` (run, analyze, recount). It reuses `re1.decoders` and `re1.predict`, `brt.learn` and `estimate5`.
5. **Preflight and freeze:** `preflight_re2.py` and `freeze_re2.py`, the latter on `studykit`.
6. **Tests:** `tests/test_re2.py` checks the conditions are distinct, the pool rules, seed screening, the seal round trip on a dummy, and the analysis on synthetic records.
7. **Protocol:** a rehearsal on public rehearsal bursts, then the preflight, then `RE2_PROTOCOL.md`, then the freeze commit.
