# Plan: frozen evaluation of the mismatch-robust learned-support pipeline (RE1)

**Status: PLAN DRAFT.** Nothing has been built or sampled.

**Approvals still needed, each separately:**
1. "Approve, build it": code, seeds, the sealed hidden burst, tests, rehearsals, preflight and freeze.
2. "Run RE1": the single frozen run.
3. "Open the RE1 seal": access to the hidden support at analysis time.

**Basis (development evidence only):**
- H-E1 and H-E1b: the learner, re-based on estimated (p, b), recovers the burst support under mismatch.
- OG: the continuous fit learns correctly off-grid and flags out-of-family noise.
- E2E: the full pipeline decodes at oracle level under Mlo and Mz.

This study asks whether those findings hold under pre-registration on fresh seeds, at **mismatch values not used in development**, and for a **sealed hidden burst**.

## Question

At d=5, does the deployable pipeline (estimate (p, b) from calibration detectors → learn the burst support → BP+OSD on the estimated model):
- **(a)** decode **no worse than a decoder given the true model and the true support** (non-inferiority), and
- **(b)** beat the **strongest deployable static matcher** with the same information (superiority),

under base-model mismatch, for both a known and a sealed hidden burst?

## Method, fixed exactly as frozen at `fe035cde7`

Nothing in the method is changed after the development results.
- **Estimator:** B2 (`estimate2.fit_b2`).
- **Misspecification flag:** threshold 118.432 (`FLAG_THRESHOLD.json`), valid for 12,000-row pools, which is the calibration size used here.
- **Learner:** the Phase C two-stage learner, τ = 1,561.218.
- **Decoders:** L2 static prior 0.01; Astar q_dec 0.0025.

## Conditions (all fresh values: none was used in dev, OG or E2E)

| ID | True model | Burst | Gated |
|---|---|---|---|
| R1 | p 0.0026, balanced (−13%) | known K (23, 31, 34) | yes |
| R2 | p 0.0034, balanced (+13%) | K | yes |
| R3 | p 0.003, Z-bias 8 | K | yes |
| R4 | p 0.0028, Z-bias 4 | K | yes |
| R5 | p 0.003, balanced (matched control) | K | yes |
| R6 | p 0.0028, Z-bias 4 | **hidden H2 (sealed)** | yes |
| X1 | p 0.003, X-bias 10 (out of family) | K | no: descriptive safety only |

**Hidden burst H2:**
- **Drawing:** drawn at build time with OS entropy (`secrets.randbelow`), the Phase C `c_seal.py` method, over the 1,003 signature classes.
- **Exclusions:** K, Phase C's H (12, 34, 40), the development surrogates M0, M1 and CR, and any support within one qubit of these. This avoids the Phase C caveat that H was a neighbour of M0.
- **Sealing:** only a SHA-256 commitment is committed. The support stays in a git-ignored seal file that the jobs read, and no person or analysis reads it before the run.
- **After the run:** the reveal step needs the owner's "Open the RE1 seal".

## Arms (every arm decodes the same rows)

| Arm | Model and support | Role |
|---|---|---|
| **L2L_R** | BP+OSD on the B2-estimated model, B2-learned support; nominal model and no burst if flagged | candidate |
| **S\*** | the better of {Astar on the estimated model + learned support, Astar on the nominal model + learned support}, chosen **per root** by fewer errors on that root's 1,500 labelled calibration rows | deployable comparator: same information, selection without evaluation data |
| L2s_true | BP+OSD, true model, true support | oracle (non-inferiority reference) |
| Astar_true | correlated matching, true model, true support | oracle reference |
| L2L_N | Phase C pipeline unchanged (nominal) | "before" reference |
| A_nominal | burst-free matching | reference |

**Why S\* is built this way.** In E2E at Mz, correlated matching was worse with the correct biased model (45 errors) than with the nominal one (22). A fixed choice could therefore flatter the candidate. Selecting per root on labelled calibration rows is deployable, uses the same labels the learner's flip stage already uses, and gives the matcher its best case.

## Allocation

- **Each root:**
  - its own calibration pool: 4,000 detector rows + 500 labelled rows per q;
  - then 4,000 evaluation shots per q ∈ {0, 0.01, 0.02}, from separate seeds.
- **Gated conditions:** 12 roots each.
  - That is 48,000 shots per q and **96,000 nonzero-q shots** per condition.
  - Expected nonzero-q errors at p ≈ 0.003, from E2E: L2 about 60, S\* about 180.
- **X1:** 6 roots.
- **Total:** (6 × 12 + 6) roots × 12,000 = **936,000 decoded shots** plus 78 calibration pools.
- **Cost:**
  - 3 BP+OSD arms at about 30 ms/shot give about 84,000 CPU seconds, so about **3.7 h** on 8 workers with a 1.25 contention factor.
  - Hard budget: 5 h, checked by a preflight from a rehearsal.
  - **Pre-declared fallback:** if the preflight exceeds 5 h, L2L_N is dropped from the evaluation shots of conditions R2 and R5, where E2E showed it equal to the oracle. Nothing else changes.

## Endpoints (root-cluster bootstrap, 20,000 replicates; nonzero q pooled)

**Co-primaries per gated condition.** There are 6 conditions × 2 tests, so the one-sided α per test is 0.025 / 12 ≈ 0.0021.
- **NI, non-inferiority to the oracle:** the upper bound of LER(L2L_R) − LER(L2s_true) must be < 0.25 × LER(L2s_true), using the oracle's point estimate.
- **SUP, superiority to S\*:** the upper bound of LER(L2L_R) − LER(S\*) must be < 0.

**Safety at q=0, per gated condition:** the 95th percentile of LER(L2L_R) − LER(A_nominal) must be ≤ 0.05 × LER(A_nominal), or ≤ 0. This is the Phase C rule.

**Secondary (descriptive):**
- support learned exactly, per root, with flag counts;
- repair, L2L_R vs L2L_N, with discordance and an exact McNemar test;
- R vs S\*, with a CI;
- which variant S\* chose in each root;
- p̂ and b̂ against the truth;
- X1's flag rate and its q=0 safety;
- runtime.

**Overall verdict:**
- **CONFIRMED:** all six gated conditions pass NI, SUP and safety.
- **PARTIAL:** some pass all three, and none fails NI or safety in the wrong direction (point estimate beyond the margin).
- **NOT_CONFIRMED:** any condition's NI or safety point estimate lies beyond its margin, or SUP's point estimate is ≥ 0.
- **INCONCLUSIVE:** otherwise.

**What the verdict covers:** the hidden-burst condition R6 is gated like the others. A CONFIRMED verdict therefore requires the hidden burst to be learned and decoded as well.

## Execution

Phase C / Stage E machinery, unchanged in kind:
- the freeze manifest of hashes and `--expected-head`, with each job re-verifying them;
- a clean tree;
- write-once jobs and a single attempt, with a 3,600 s per-job timeout;
- analysis run twice, required to be byte-identical;
- a recount plus a bit-identical re-decode of root 0 for every (condition, arm);
- the run executed from a detached checkout of the freeze commit, as in E2E.

**Rehearsals before the freeze**, on rehearsal seeds and a rehearsal seal (not H2):
- a fake-sampler pass through the pipeline;
- 1 real root per condition at 300 shots per q, which feeds the preflight.

## Claim boundary

A CONFIRMED result supports this statement only: "On fresh seeds at d=5, with calibration of 12,000 unlabelled + 1,500 labelled rows per root, the mismatch-robust pipeline decodes at oracle level (within 25%) and beats the strongest deployable matcher, under ±13% background-p error, Z-bias 4–8, and a combined mismatch, for a known and one sealed hidden weight-3 burst." Even with that verdict:
- this is simulation only;
- it is a single weight-3 burst family;
- the out-of-family noise X1 is safe-fallback only;
- d = 7 is untested;
- R is expected at about 65%, so **this study does not bear on the 95% broad target**.
