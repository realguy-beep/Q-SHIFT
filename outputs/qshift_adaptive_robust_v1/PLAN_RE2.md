# PLAN_RE2: frozen evaluation of the E1T pipeline with new sealed hidden bursts (plan only, revision 2)

**Status:** plan. Nothing is built, drawn, sealed or sampled. Revision 2 applies the owner-requested review of revision 1 (`0c68bb5fe`). Its changes are listed at the end.

| Approval | Covers |
|---|---|
| Owner decision, 2026-11-20 | **RE1's H2 seal stays unopened.** RE2 does not read H2 at any stage. |
| "Approve, build it" | the build, the burst draw and seal, the seeds, the rehearsal, the preflight and the freeze |
| "Run RE2" | the single frozen run, with `--open-hidden-seal`, which opens **RE2's** seal only |
| "Open the RE2 seal" | publishing the identity of H3 or H4, after the run |
| "Open the RE1 seal" (if ever given) | also triggers the frozen contamination check in the seal section |

## Why RE2

- **RE1 (`fe4471fff`, NOT_CONFIRMED):** the pipeline passed every gate for the known burst (R1–R5). On the sealed hidden burst (R6), its estimator B2 flagged every root, so the burst was never learned.
- **The estimator was rebuilt on development data:**
  - BRE: E1;
  - BRS: E1S;
  - BRT: E1T, which has no residual statistic and no tuned parameter. BRT was SUPPORTED: 126/128 held-out bursts of 5–30 detectors learned exactly, with no in-family false bursts.

RE2 is the frozen test RE1 failed. It asks whether E1T → Phase C learner → BP+OSD learns and decodes unseen bursts, under base-model mismatch, at oracle level, and beats the strongest deployable matcher.

## Burst pool (measured at plan time from public data only)

**Rule:** RE1's committed candidate pool (`re1_seal.candidate_pool`, 1,998 supports; this function does not read the seal), minus:
- every BRE, BRS and BRT burst class, and K (57 public development bursts);
- any support sharing ≥ 2 qubits with one of those bursts.

Each class is kept once, with its first eligible support as representative. **Result:** 182 classes.

| Detector footprint | 5 | 10 | 15 | 20 | 25 | 30 |
|---|---|---|---|---|---|---|
| Eligible classes | 7 | 27 | 42 | 71 | 34 | 1 |

**Two sealed bursts**, each drawn uniformly by OS entropy within its stratum:

| Burst | Stratum | Eligible | Purpose |
|---|---|---|---|
| **H3** | footprint ≥ 25 | 35 | the RE1 failure regime |
| **H4** | footprint ≤ 20 | 147 | a generic unseen burst |

**Disclosed design input:** the ≥ 25-detector stratum is chosen **because of RE1's published R6 outcome**. RE1's diagnosis is that large footprints break B2, and BRT confirmed B2 fails at 25–30 detectors. This uses an evaluation outcome to design the next test. No RE2 data is used, and the draw is made before any RE2 sample.

**Order of operations at build:**
1. fix one public, deterministic rehearsal burst per stratum: the first class in pool order;
2. remove both rehearsal bursts from the pool;
3. commit the pool hash;
4. then draw.

## H2 stays sealed: contamination risk and how it is handled

- **The risk:** RE2 never reads H2, so it cannot exclude it. If H3 or H4 lands in H2's class, or within one qubit of H2, that burst would partly re-test the burst whose failure shaped the BRE → BRT rebuild.
- **Why the consequence is limited:**
  - No development code read H2 or RE1's per-root records; `re1_seal.open_seal` is called only inside RE1's frozen run.
  - E1T has no fitted parameter.
  - What RE1 shaped is the design emphasis on footprint robustness. That is disclosed above.

**Probability, computed without reading or conditioning on H2:**
- **Prior:** H2 is treated as uniform over RE1's committed pool, which is its true draw distribution.
- **Script:** `re2_overlap.py`, to be committed at build. Its output goes to `results/re2/OVERLAP.json`.

| | H3 | H4 | Either |
|---|---|---|---|
| Same class as H2 | 0.12% | 0.22% | — |
| Same class or within one qubit (uniform prior) | **2.9%** | **3.2%** | **6.0%** |
| Worst case over any possible H2 | 28.6% | 12.9% | 31.5% |

RE1's published diagnosis says H2's footprint is large. Conditioning on that would move the realistic figure toward the worst case. RE2 deliberately does not condition on it.

**Pre-registered handling:**
1. **Deferred check:** `re2_contamination.py` is frozen with RE2. It runs **only if** the owner later says "Open the RE1 seal". It reports, for H3 and for H4, only whether that burst is contaminated, by the rule above.
2. **Pre-declared consequence:**
   - A contaminated burst's conditions (G3 and G4 for H3, G5 for H4) stay reported unchanged, but are relabelled "not independent of RE1".
   - Any confirmatory claim for that burst is withdrawn.
   - The verdict is restated without those conditions, as PARTIAL at best.
3. **Limitation stated in every RE2 report until then:** hidden-burst claims are conditional on H3 and H4 being independent of H2. That probability is 94.0% under the draw distribution, and at least 68.5% in the worst case.

## Conditions

12 roots per gated condition, as in RE1. Per root and per q (0, 0.01, 0.02):
- 4,000 unlabelled + 500 labelled calibration rows, so **12,000 + 1,500 per root**, pooled across q as in RE1;
- 4,000 evaluation shots.

| Cond | True base model | Burst | Gated | Role |
|---|---|---|---|---|
| G1 | p 0.0023 | K | yes | known burst, background p low |
| G2 | p 0.0032, Z-bias 6 | K | yes | known burst, combined mismatch |
| **G3** | **p 0.0028, Z-bias 4** | **H3 (sealed, large)** | **yes** | **R6's exact base model with a new large burst: the direct re-test** |
| G4 | p 0.00335 | H3 | yes | large hidden burst, high p |
| G5 | p 0.0026, Z-bias 5 | H4 (sealed, generic) | yes | generic unseen burst under mismatch |
| X2 | p 0.003, X-bias 8 | K | no (6 roots) | out-of-family safe-fallback check, descriptive |

**Distinctness:**
- G3 repeats R6's base model on purpose.
- Every other (p, bias) pair differs from every fixed condition in DEV2, RE1, BRE, BRS and BRT, and from AD1's C0, D3 and D4 levels. This is asserted by a test.
- AD1's linear ramps pass through intermediate values; the test excludes those from the check.

**Weaker than RE1 (disclosed):** RE1 asserted its mismatch values were never used in development. RE2's values lie inside BRT's development range (p 0.0020–0.0040, Z-bias 3–12), so RE2 claims only distinct exact pairs. The out-of-range claim is not made.

## Arms

**L2L_E (the pipeline):**
1. E1T on the 12,000 unlabelled rows.
2. **If flagged:** the nominal model, **no learning and no burst**, so BP+OSD runs on the nominal base model. This is RE1's rule exactly.
3. **Otherwise:**
   1. model `brt.zspec(p̂, b̂)`;
   2. the Phase C learner and `learn_flip` on the 1,500 labelled rows;
   3. BP+OSD with the learned support.

**The other arms:**
- **S\* (RE1's rule):** chosen per root from {Astar_Em, Astar_Nm}.
  - Astar_Em is correlated matching on L2L_E's model and support.
  - Astar_Nm is correlated matching on the nominal model with the same support.
  - The choice is by errors on the labelled calibration rows; a tie goes to Astar_Em.
- **L2s_true (oracle):** BP+OSD on the true model with the true support.
- **Astar_true and A_nominal:** as in RE1.
- **L2L_B2 (descriptive, G3 and G4 only):** RE1's B2 pipeline, unchanged, on the same shots.
- **Dropped:** L2L_N. RE1 already settled the nominal-learner question.

## Endpoints

| Endpoint | Rule |
|---|---|
| **NI (gated)** | upper bound of L2L_E − L2s_true < **max(0.25 × oracle nonzero-q LER, 10 / N_nz)**, where N_nz = 96,000 pooled nonzero-q shots per arm |
| NI_strict (reported, not gated) | RE1's rule unchanged: upper bound < 0.25 × oracle LER |
| SUP | upper bound of L2L_E − S\* < 0 (RE1, unchanged) |
| Safety (q=0) | p95 of L2L_E − A_nominal ≤ 0, or ≤ max(0.05 × LER_q0(A_nominal), 3 / N_q0) (RE1, unchanged) |

**Statistics:**
- one-sided bounds at α = 0.025 / (2 × 5) = 0.0025;
- a root bootstrap with 20,000 replicates, seeded from `re2:stats:<cond>`;
- the safety percentile is RE1's unadjusted 95th.

**Verdict (RE1's logic):**
- **CONFIRMED:** all five gated conditions pass NI, SUP and safety.
- **NOT_CONFIRMED:** any NI or safety point estimate beyond its margin, or a SUP point estimate ≥ 0.
- **PARTIAL:** some pass all three, and none fails in the wrong direction.
- **INCONCLUSIVE:** otherwise.

### Why the NI floor (new in RE2; the one deliberate change from RE1)

**The problem:** in the low-error Z-biased conditions, 0.25 × the oracle's errors is only about 2.5–4.5 errors in 96,000 shots. A bootstrap check at α = 0.0025 with 12 roots shows that **one root just +2 errors worse than the oracle fails NI**, from ordinary decoder discordance alone. RE1 passed R3 and R4 only because their discordance was exactly 0.

**The floor:** 10 errors, chosen from the same calculation.
- **Tolerated:** one root at +2, or two roots at +1 (bootstrap upper bounds 8 and 6).
- **Still fails:** one root at +3 (upper bound 12), and any unlearned root (about +50, upper bound about 200).

**Precedent:** RE1's safety floor of 3 errors, its deviation 2, made for the same reason.

**What this costs:** the floor binds wherever the oracle makes fewer than 40 errors, which is likely in G2, G3 and G5.
- At RE1 R6's oracle level (18 errors), it admits up to about 55% excess rather than 25%.
- At R4's level (12 errors), it admits about 80%.

So the claim becomes "within 25% of the oracle, or within 10 errors per 96,000 shots". NI_strict and the percentage excess are reported beside it, for comparability with RE1.

## Power (what to expect if E1T works as in BRT)

| Endpoint | Expectation |
|---|---|
| SUP | Near-certain. RE1's R against S\* was 44–88% with tight CIs, and SUP passed even in R6, where nothing was learned. |
| Safety | Passed in all RE1 conditions. No reason to expect a change. |
| NI, known burst (G1, G2) | High. E1T learned K in 108/108 AD1 windows of the same calibration size, and RE1 learned K in 60/60 roots. |
| NI, hidden bursts (G3–G5, 36 roots) | Effectively requires **every root to be learned.** One unlearned root adds about 50 errors, against a margin of about 10. More roots do not fix this: you would need about 400. |

**Hidden-burst odds in numbers:**
- P(all 36 learned) ≈ 0.56 at BRT's 1.6% per-pool failure rate.
- Both BRT failures were at range edges (p 0.0020 and 0.0040). At a more plausible ~0.5% mid-range rate, P ≈ 0.84.

**Overall:** P(CONFIRMED | E1T as in BRT) ≈ 0.5–0.8. This is stated up front. A NOT_CONFIRMED caused by a single unlearned root is reported as exactly that.

## Seal handling (RE2's own seal, as in RE1)

- **`re2_seal.py`:**
  - draws H3 and H4 with `secrets.randbelow` from the committed stratum pools, after the rehearsal bursts are removed;
  - writes the plaintext (supports and salt) only beside the worktrees, outside git;
  - commits `HIDDEN_COMMITMENT_RE2.json`, holding the SHA-256 of the canonical plaintext, the pool hash, the stratum sizes, the rules and the rehearsal supports;
  - refuses to run twice;
  - never reads RE1's seal.
- **In the frozen run:** the hidden supports are read only inside it (`--open-hidden-seal`), never printed, and stored as `"SEALED"`. The analysis reports only learned-exactly and flag counts, and error statistics.

## Seeds, freeze, safeguards

- **Seeds:** `RE2_SEEDS.json`, with keys `re2:<cond>:r<NN>:<cal|eval>:q<i>`, `re2:stats:<cond>` and rehearsal keys. They are screened against every prior inventory through `AD1_SEEDS.json`.
- **Freeze:** `RE2_FREEZE.json` via `studykit.write_freeze`. It covers every file the run imports, `HIDDEN_COMMITMENT_RE2.json`, the seeds, `re2_overlap.py`, `results/re2/OVERLAP.json` and `re2_contamination.py`.
- **Run guard:** `studykit.require_frozen_head` in every job. Records and archives are write-once; there are no retries and no seed substitutions.
- **After the run:**
  - the analysis is run twice and must be byte-identical;
  - the recount re-analyses and re-decodes root 0 of every condition end to end, bit-identically.

## Cost (to be confirmed by the preflight)

- **Samples:** 66 roots × 3 q × (4,500 calibration + 4,000 evaluation) = **1,683,000** sampler shots.
- **Per root:** RE1's measured rates under contention (47 s fixed, 29.5 ms per BP+OSD arm per shot) give, with 2 BP+OSD arms over 12,000 evaluation shots, about 755 s. L2L_B2 adds about 350 s on 24 roots.
- **Run time:** 66 roots on 8 workers in 9 waves is about **2.0 h**, or 2.5 h with a 1.25 factor, against a 5 h budget and a 3,600 s job timeout.
- **Pre-declared fallback** if the preflight exceeds the budget: drop L2L_B2.

## What RE2 can confirm, and what stays unproven

**If every gate passes:** at d=5, in simulation, on fresh seeds, with 12,000 unlabelled + 1,500 labelled calibration rows per root, the E1T pipeline decodes within 25% of the oracle (or within 10 errors per 96,000 shots) and beats the strongest deployable matcher. That holds:
- under background p 0.0023–0.00335 and Z-bias 4–6;
- for the known burst and two sealed, never-seen weight-3 bursts, one with a ≥ 25-detector footprint;
- conditional on H3 and H4 being independent of RE1's H2 (94% under the draw distribution).

**Unproven even then:**
- **Generalization:** a learning rate across unseen bursts in general, since there are 2 bursts and G3 and G4 share H3.
- **Operating range:** mismatch outside the development range; X-bias or measurement-heavy noise (X2 is descriptive only); other burst weights or multiple bursts.
- **Scale:** d ≥ 7, real hardware, and adaptivity (AD1's question).
- **The 95% target:** R is expected at about 60–90%.

## Build outline (after "Approve, build it")

1. **Config:** `re2_config.py` holds the conditions, arms, endpoints and keys.
2. **Pool and seal:** `re2_overlap.py` → `results/re2/OVERLAP.json`; `re2_seal.py` holds the pool and the draw; `re2_contamination.py` holds the deferred check, which is not run.
3. **Seeds:** `prepare_re2.py`.
4. **Runner:** `re2.py` (run, analyze, recount). It reuses `re1.decoders`, `re1.predict`, `brt.learn`, `estimate5` and `estimate2` for L2L_B2.
5. **Preflight and freeze:** `preflight_re2.py` and `freeze_re2.py`, the latter on `studykit`.
6. **Tests:** `tests/test_re2.py` checks:
   - the conditions are distinct;
   - the pool rules and rehearsal removal;
   - that no RE2 code path calls `re1_seal.open_seal`;
   - seed screening;
   - the seal round trip on a dummy;
   - the NI floor and the analysis on synthetic records.
7. **Protocol:** a rehearsal on the public rehearsal bursts, then the preflight, then `RE2_PROTOCOL.md`, then the freeze commit.

## Changes from revision 1 (`0c68bb5fe`), per the owner's review

| # | Change |
|---|---|
| 1 | The H2 exclusion option is removed. **H2 stays sealed.** The contamination probability, the deferred check and the conditional-independence limitation are added. |
| 2 | Calibration size is corrected to 12,000 + 1,500 **per root**, and the sample count to 1.68 M. |
| 3 | G1 moves from p 0.0024 to 0.0023, because 0.0024 duplicated BRS S1. X2 moves from X-bias 6 to 8, because 6 duplicated BRS SX. G4 moves from 0.0033 to 0.00335, away from DEV2's grid value. |
| 4 | Flag handling is spelled out: nominal model, no learning, no burst (RE1's rule). |
| 5 | The weaker independence of the mismatch values (inside BRT's development range) is disclosed. |
| 6 | The design input from RE1's outcome (the stratum choice) is disclosed, and rehearsal bursts are fixed and removed before the draw. |
| 7 | The NI absolute floor of 10 errors is added, with NI_strict reported, and its rationale and cost are stated. |
| 8 | A power section is added: P(CONFIRMED) ≈ 0.5–0.8 even if E1T works as in BRT. |
