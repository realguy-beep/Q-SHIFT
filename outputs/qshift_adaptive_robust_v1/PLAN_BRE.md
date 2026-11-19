# Plan: burst-robust estimation (BRE), a development study

**Status: plan only.** Nothing is built or sampled.

| Approval | Covers |
|---|---|
| "Approve, build it" | code, tests, the deterministic census (BRE-0), seeds, rehearsal, preflight and freeze |
| "Run BRE" | the single development sampling run (BRE-1) |

A later frozen evaluation (RE2, with a new sealed burst) would be planned separately, and only if BRE-1 supports it.

## Why

RE1 (`RE1_RESULTS.md`) passed for the known burst K and failed for the sealed hidden burst H2.

**The failure chain:**
1. **Flag.** H2's detector footprint inflated the trimmed B2 objective (175–227 against a threshold of 118.4), so all 12 roots were flagged.
2. **No learning.** A flag switches learning off.
3. **No recovery.** The nominal fallback cannot learn under Z-bias, so nothing recovered.

**Root cause.** Both the fit and the flag were validated only on pools whose burst was K (`FLAG_THRESHOLD.json`: 192 pools). The fixed 20% symmetric trim (24 of 120 detectors) is not burst-agnostic.

**The question:** can the (p, b) estimate and the flag be made robust to *which* burst is present, without losing what RE1 confirmed for K?

## Data discipline

- **RE1 is not used.** No RE1 sample, record or objective value is used to choose anything here. RE1 enters only as the motivating failure.
- **H2 stays sealed.** It is not read. This has a consequence: the development burst set cannot be screened against H2, so a development support could coincide with it. H2 is spent for confirmatory use anyway, and any RE2 needs a new sealed burst drawn to exclude every BRE support. This is disclosed rather than worked around.
- **Fresh seeds.** All seeds are new (`bre:*`), screened against every prior inventory, `RE1_SEEDS.json` included.

## BRE-0: deterministic footprint census (no sampling)

For each weight-3 support in the `CLASSES_D5` candidate pool, plus K, M0, M1 and CR, and for each BRE noise condition below:
- compute exact detector rates of the burst circuit at q ∈ {0, 0.01, 0.02} with `he1.detector_rates`, and form the expected calibration pool (equal q mix);
- run the B2 fit on these *expected* rates, with n = 12,000 used for the weights;
- record the footprint size (detectors raised by more than 10% at q = 0.02), the expected objective, b̂ and p̂.

**What it tells us:**
- whether RE1's failure is typical or rare across bursts (the fraction of supports with expected objective > 118.4);
- whether the 24-detector trim is the binding constraint;
- which candidate estimators remove the dependence, before any sampling.

**Reporting:** only aggregated distributions are published (quantiles, flag fractions, and footprint against objective). Per-support values stay in git-ignored `work/`, so the census cannot be matched against RE1's published R6 objectives to narrow down H2.

**Cost:** about 2,000 supports × 7 conditions × 3 q of DEM rate evaluations, plus fits. CPU only, under 1 h.

## Candidate estimators and policies (fixed before BRE-1)

All candidates are detector-only and use no labels or q values. Labels come in only at the unchanged flip stage.

| Arm | Fit | On flag |
|---|---|---|
| **B2** (frozen baseline) | as in RE1 | no burst |
| **E1** one-sided adaptive trim | drop only detectors with *positive* standardized residual above a robust cutoff (median + c·MAD, iterated to a fixed point); a burst only raises rates | as B2 |
| **E2** learn-then-refit | B2 fit → learner on the fit (run even if flagged) → if a class is accepted, refit (p, b) with that support's detectors excluded → relearn once | learn on the nominal model |
| **E3** = E1 + E2 policy | E1 fit, then E2's refit and policy | learn on the nominal model |

**Fixed in advance:**
- the cutoff constant c in E1;
- the flag thresholds for each arm.

Both are set on the **tuning** burst set only (see below), by a written rule. The flag threshold is the maximum objective over in-family tuning pools, as before, but now over varied bursts.

**τ and the learner stay unchanged.** Each candidate is a change to the estimator and the flag policy only.

## BRE-1: development sampling

**Bursts** (selected by public seed, and disclosed):
- **Tuning set T:** K, M0, M1, CR, plus 8 random eligible supports.
- **Held-out set V:** 12 further random eligible supports. V is used only for the verdict, never for c or the thresholds.
- **Selection rule:** supports are drawn stratified by BRE-0 footprint size, so that large-footprint bursts like the one RE1 found are represented. No per-support RE1 information is used.

**Conditions:**

| ID | True base model | Role |
|---|---|---|
| B1 | p 0.0026, balanced | in family |
| B2c | p 0.0034, balanced | in family |
| B3 | p 0.003, Z-bias 4 | in family |
| B4 | p 0.003, Z-bias 10 | in family |
| B5 | p 0.0028, Z-bias 6 | in family, combined |
| BX | p 0.003, X-bias 10 | out of family: must flag; checks the on-flag policy |
| BM | measurement p 3× gate p | out of family: must flag |

The values are deliberately not RE1's.

**Pools** use the RE1 calibration recipe: 3 q × (4,000 detector + 500 labelled rows) = 13,500 rows.
- **Burst pools:** 24 bursts × 7 conditions × 2 pools = 336.
- **Burst-free (q = 0 only) pools:** 7 × 24 = 168.
- **Total:** 504 pools, about 6.6 M cheap detector-sampler shots (336 × 13,500 + 168 × 12,000). There is no evaluation decoding: RE1 showed that an exactly learned support decodes at oracle level.

**Execution:** every arm runs on the same pools, with a single attempt, write-once records, a freeze, and `--expected-head` and hash checks, as in OG and E2E.

**Cost:** about 504 pools × 4 arms × 40–50 s ÷ 8 workers ≈ 3 h. The preflight confirms this against a 5 h budget. If it exceeds that, the pre-declared fallback is to drop BM.

## Endpoints (development; pre-declared)

Per arm, on **held-out V** bursts:

| Endpoint | Pass rule |
|---|---|
| Learned exactly, in-family burst pools | ≥ 95% overall, and ≥ 22/24 in each in-family condition |
| False accepts, in-family burst-free pools | ≤ 1/24 per condition |
| False flags, in-family | ≤ 1/24 per condition (burst and burst-free pools separately) |
| Out-of-family BX and BM | flag ≥ 23/24; on-flag false accepts at q = 0 ≤ 1/24 |
| No regression on K | learned exactly 24/24 per in-family condition |

**Also reported:**
- the T-set results;
- the error distribution of b̂ and p̂ against footprint size;
- learning under the on-flag policy in BX (RE1's X1 suggested the nominal learner finds K there).

**Verdict:**
- **BRE_SUPPORTED:** at least one candidate arm passes every endpoint on V. If several pass, the pre-declared preference order is E1, then E3, then E2, simplest first.
- **BRE_PARTIAL:** some endpoints pass.
- **BRE_NOT_SUPPORTED:** otherwise.

A supported arm becomes the candidate for RE2. It is not a confirmed result.

## Boundaries

- Development evidence only.
- d=5, weight-3 bursts, simulation.
- Static noise only. The adaptive phase (drift, change detection, on/off bursts) comes after this and reuses the chosen estimator.
- The held-out V set gives within-development generalization, not confirmation.

## Files (new, in this package)

| File | Purpose |
|---|---|
| `bre_config.py` | conditions, arms, bursts and endpoints |
| `bre_census.py` | BRE-0 |
| `estimate3.py` | E1 and E2 estimators; B2 imported unchanged from `estimate2.py` |
| `prepare_bre.py` → `BRE_SEEDS.json`, `BRE_BURSTS.json` | seeds and the published burst sets |
| `bre.py` | run, analyze, recount |
| `tests/test_bre.py` | tests (see Verification) |
| `freeze_bre.py` → `BRE_FREEZE.json` | freeze |
| `BRE_PROTOCOL.md` | protocol |

`estimate2.py`, `re1*.py` and every RE1 file are unchanged.

## Verification

**Unit tests:**
- E1 equals B2 when no residual exceeds the cutoff;
- E2 with no accepted class equals B2;
- the seed screen is collision-free;
- the V set is disjoint from T and from every excluded class;
- the analysis decision logic works on synthetic records.

**Rehearsal:** 1 pool per condition and kind on rehearsal seeds, end to end, with analysis run twice to a byte-identical result.

**After BRE-1:**
- recount;
- `BRE_RESULTS.md` and a DECISION_REPORT addendum;
- commit. Push only on "Push it".
