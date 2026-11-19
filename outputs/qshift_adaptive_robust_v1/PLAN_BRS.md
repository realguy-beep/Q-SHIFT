# Plan: BRS, a structural misfit check for the E1 estimator (development study)

**Status: plan only.** Nothing is built or sampled.

| Approval | Covers |
|---|---|
| "Approve, build it" | code, tests, the BRS-0 re-analysis of existing BRE arrays (no sampling), seeds, rehearsal, preflight and freeze |
| "Run BRS" | the single fresh development run (BRS-1) |

A frozen RE2 with a new sealed burst would be planned separately, after BRS-1.

## Why

BRE (`BRE_RESULTS.md`, verdict PARTIAL) showed that E1, the one-sided adaptive exclusion fit, makes estimation independent of burst footprint: 240/240 in-family burst pools were learned exactly, with no false flags or false accepts. Its one failure was its flag.

**The failure:** under measurement-heavy noise (BM), E1 excluded 14–41 detectors from burst-free pools, absorbing the misfit. In 8 of 48 pools the rest stayed under the threshold, and the learner accepted a false burst. That makes 3/24 held-out pools against an allowance of 1/24.

**Why a structural check should fix it:**
- A genuine burst's exclusions are exactly the detector set of one signature class. The 1,003 classes all have distinct detector sets.
- In BRE, in-family exclusions were 0 in every burst-free pool and at most 30 in burst pools.
- A misfit's exclusions follow no class pattern.

## The candidate: E1S = E1 plus two structural rules

**The fit is unchanged.** E1S uses E1's fit, cutoff, threshold (2.335, frozen from BRE's tuning pools) and exclusion cap (30). It then adds two rules:

| Rule | A pool is flagged when |
|---|---|
| **S1: shape** | the excluded set X is non-empty and is not the detector set of any signature class |
| **S2: consistency** | the learner's accepted class does not match X. Either X is empty and a class was accepted, or X is a class set and the learner chose a different class |

**On a flag:** no burst (E1's policy). BRE showed that falling back to the nominal learner is unsafe (96/96 false accepts out of family).

**Fixed in advance:**
- **Exact match for S1.** There is no tolerance parameter. BRS-0 below checks whether exact matching is too strict in family. If it is, the build adds one pre-declared alternative, "X within one detector per round of a class set", chosen before BRS-1. No other change is allowed.
- **Nothing else is tuned.** The thresholds come from BRE, so BRS-1 needs no tuning pools and all of it is held out.

## BRS-0: re-analysis of the existing BRE arrays (no sampling)

The BRE pool arrays (672 pools in git-ignored `work/`) are reloaded, and E1S is recomputed on them, deterministically.

**What it reports:**
- how often in-family X equals the true burst's class set;
- whether S1 and S2 flag the 8 BM pools that E1 missed;
- whether S1 and S2 add any false flag in family.

**This is not evidence.** BRE is the data that revealed the problem, so BRS-0 is a design check only. It is reported as such and cannot produce a verdict.

## BRS-1: fresh development run

**Bursts:**
- 16 new held-out bursts, drawn by public seed from the RE1 candidate pool.
- They exclude every BRE support's class, and anything within one qubit of BRE's bursts.
- Stratified by footprint, 4 per stratum: ≤15, 20, 25 and 30 detectors.
- H2 stays sealed and unread, as before.

**Conditions** (new values throughout; the OOF set is widened to probe the flag):

| ID | True base model | Role |
|---|---|---|
| S1 | p 0.0024, balanced | in family |
| S2 | p 0.0036, balanced | in family |
| S3 | p 0.0031, Z-bias 5 | in family |
| S4 | p 0.0027, Z-bias 8 | in family |
| SM3 | measurement p 3× gate p | out of family: BRE's failing case, at new seeds |
| SM2 | measurement p 2× gate p | out of family: milder, harder to flag |
| SM15 | measurement p 1.5× gate p | out of family: boundary (see below) |
| SX | X-bias 6 | out of family |

**SM15 is reported only.** At 1.5× the misfit may be small enough that decoding with the in-family fit is harmless. What matters there is whether false bursts are accepted, so SM15 has a false-accept endpoint but no flag endpoint.

**Pools** use the BRE recipe:
- **Burst pools:** 3 q × (4,000 detector + 500 labelled rows) = 13,500 rows; 16 bursts × 2 pools × 8 conditions = 256.
- **Burst-free pools:** 12,000 rows; 32 per condition = 256.
- **Total:** 512 pools, about 6.5 M cheap detector-sampler shots. There is no decoding.

**Cost:** BRE ran at a median of 19.5 s per pool, so this is about 25–40 min on 8 workers. The preflight confirms it against a 3 h budget.

**Arms,** all on identical pools:
- **E1S:** the candidate.
- **E1:** the BRE arm, unchanged.
- **B2:** the frozen reference.

## Endpoints (all pools are held out; pre-declared)

| Endpoint | E1S must satisfy |
|---|---|
| Learning, in family | ≥ 95% of the 128 in-family burst pools learned exactly, and ≥ 30/32 per condition |
| False accepts, in family | ≤ 1/32 burst-free pools per condition |
| False flags, in family | ≤ 1/32 per condition, for burst pools and for burst-free pools |
| SM3, SM2, SX | burst pools flagged ≥ 30/32; burst-free false accepts ≤ 1/32 |
| SM15 | burst-free false accepts ≤ 1/32 (flags reported only) |
| No loss against E1 | in-family learned-exactly count ≥ E1's minus 2 |

**Verdict:**
- **BRS_SUPPORTED:** E1S passes every endpoint. E1S then becomes the RE2 candidate.
- **BRS_PARTIAL:** E1S passes the in-family endpoints but some out-of-family one fails.
- **BRS_NOT_SUPPORTED:** otherwise.

E1 and B2 are reported alongside for comparison.

## What RE2 would then look like (not part of this approval)

- A frozen decoding evaluation with E1S, on the RE1 template.
- A new sealed hidden burst, drawn to exclude every BRE and BRS support, deliberately including large-footprint (25–30 detector) classes in the candidate pool.
- RE1's conditions, at new values.

RE2 is where a decoding claim for an unseen burst could be made.

## Boundaries

- Development evidence at d=5, with weight-3 bursts and static noise, in simulation.
- Measurement-heavy noise stays **out of family**. E1S only detects it; it does not model it. Extending the model family with a separate measurement p is the alternative fix, and would be its own study.
- The adaptive phase (drift, change detection, bursts that switch on and off) follows RE2.

## Files (new, in this package)

| File | Purpose |
|---|---|
| `brs_config.py` | conditions, bursts, endpoints and the frozen BRE thresholds |
| `estimate3.py` | adds `structural_flags`. Existing functions are unchanged and hash-checked against `BRE_FREEZE.json` |
| `brs0.py` | BRS-0 re-analysis |
| `prepare_brs.py` → `BRS_BURSTS.json`, `BRS_SEEDS.json` | bursts and seeds, screened against every prior inventory, `BRE_SEEDS.json` included |
| `brs.py` | run, analyze, recount |
| `tests/test_brs.py` | tests (see Verification) |
| `freeze_brs.py` → `BRS_FREEZE.json` | freeze |
| `BRS_PROTOCOL.md` | protocol |

**Note:** adding a function to `estimate3.py` changes its hash. BRE's records are unaffected, and the protocol will record both hashes.

## Verification

**Unit tests:**
- S1 on every class's exact detector set gives no flag, and on random sets it flags;
- S2's logic works on synthetic outcomes;
- the burst sets are disjoint from BRE's;
- the seed screen is collision-free;
- the analysis logic works on synthetic records.

**Rehearsal:** 1 pool each for S3, SM2 and SX on rehearsal seeds. Analysis run twice to a byte-identical result, plus a replay.

**After BRS-1:**
- recount;
- `BRS_RESULTS.md` and a DECISION_REPORT addendum;
- commit. Push only on "Push it".
