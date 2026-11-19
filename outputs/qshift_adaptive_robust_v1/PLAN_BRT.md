# Plan: BRT, a threshold-free E1 flag (development study)

**Status: plan only.** Nothing is built or sampled.

| Approval | Covers |
|---|---|
| "Approve, build it" | code, tests, the BRT-0 re-analysis of existing BRE and BRS records (no sampling), seeds, rehearsal, preflight and freeze |
| "Run BRT" | the single fresh development run (BRT-1) |

A frozen RE2 with a new sealed burst would be planned separately, after BRT-1.

## Why

BRS (`BRS_RESULTS.md`, NOT_SUPPORTED) showed that the structural rules work. Fresh measurement-heavy and X-bias misfit no longer produces false bursts, and nothing is lost in family.

**The failure:** E1's own residual statistic (mean squared included residual, threshold 2.335) flagged 2/32 real burst pools at p 0.0036.

**The cause:**
- The statistic grows with p. Its in-family maximum went from 1.39 at p 0.0024 to 2.75 at p 0.0036.
- Its threshold was the BRE tuning maximum, which came at the highest p seen there (0.0034).

**Why dropping it might be enough:** no statistic has to replace it. Re-reading the frozen BRS records, a flag made of **only the exclusion cap (more than 30) plus S1 and S2** would have passed every BRS endpoint:

| Condition | Burst pools flagged | Burst-free false accepts |
|---|---|---|
| S2 | 1/32 (31 learned) | 0 |
| S4 | 0/32 | 0 (1 burst-free pool flagged) |
| SM2, SM3, SX | 32/32 | 0 |
| SM15 | 15/32 | 1 |

That check is post-hoc on BRS, so it needs a fresh test.

## The candidate: E1T

- **The fit:** E1, unchanged.
- **The flag:** more than 30 exclusions, OR S1 (shape), OR S2 (consistency), with the subset rule from BRS.
- **On a flag:** no burst.
- **Tuned parameters: none.**
  - The cutoff of 4 was fixed a priori in BRE.
  - The cap of 30 is a property of the code.
  - S1 and S2 are pure set logic.
  - So there is no threshold that can drift with p, and nothing to tune on BRT-1.

**References,** all on the same pools:
- **E1S:** as frozen in BRS. It shows the drift directly.
- **E1:** as in BRE.
- **B2:** frozen.

## BRT-0: re-analysis of existing records (no sampling; design check, not evidence)

E1T is applied to the 672 BRE and 512 BRS records. Those records already contain E1's exclusion count and the BRS structural flags. For BRE, the flags come from the BRS-0 rule comparison on BRE's arrays.

**What it reports:** in-family false flags and learning, and out-of-family flags and false accepts, for every condition. It cannot produce a verdict.

## BRT-1: fresh development run

**Bursts:**
- 16 new held-out bursts, 4 per footprint stratum.
- They exclude every BRE and BRS class, and anything within one qubit of their bursts.
- Public seed. H2 stays sealed and unread.

**Conditions:** they deliberately widen the p range beyond anything seen before, which tests scale-freeness directly.

| ID | True base model | Role |
|---|---|---|
| T1 | p 0.0020, balanced | in family: below every prior study |
| T2 | p 0.0040, balanced | in family: above every prior study |
| T3 | p 0.0030, Z-bias 3 | in family |
| T4 | p 0.0033, Z-bias 12 | in family: combined high p and high bias |
| TM25 | measurement p 2.5× gate p | out of family, gated |
| TM2 | measurement p 2× gate p, gate p 0.0036 | out of family, gated: misfit at high p |
| TX | X-bias 4 | out of family, gated |
| TM15 | measurement p 1.5× gate p | out of family, false-accept gate only |

**Pools** use the BRS recipe: 16 bursts × 2 burst pools (13,500 rows each) plus 32 burst-free pools (12,000 rows), per condition.
- **Total:** 512 pools, about 6.5 M cheap detector-sampler shots. There is no decoding.
- **Cost:** BRS took 33 min, so this should take about 35–60 min on 8 workers, against a 3 h budget.

## Endpoints for E1T (all pools held out; as in BRS)

| Endpoint | Rule |
|---|---|
| Learning | At least 95% of the 128 in-family burst pools learned exactly, and at least 30/32 per condition |
| False accepts, in family | At most 1/32 per condition |
| False flags, in family | At most 1/32 per condition, for burst pools and for burst-free pools |
| TM25, TM2, TX | Burst pools flagged at least 30/32; burst-free false accepts at most 1/32 |
| TM15 | Burst-free false accepts at most 1/32 |
| No loss against E1 | E1T's in-family learned count is at least E1's minus 2 |

**Verdict:**
- **BRT_SUPPORTED:** all endpoints pass. E1T then becomes the RE2 candidate.
- **BRT_PARTIAL:** the in-family endpoints pass.
- **BRT_NOT_SUPPORTED:** otherwise.

## What RE2 would then be (not part of this approval)

- A frozen decoding evaluation of the full pipeline: E1T estimate, then learning, then BP+OSD on the estimated model.
- A new sealed hidden burst, drawn from a pool that excludes every BRE, BRS and BRT support and deliberately includes 25–30-detector classes.
- RE1's design: conditions at new values, and arms including the true-model and true-support oracle and the best deployable matcher.

It would be the first frozen test of the repaired pipeline on an unseen burst.

## Boundaries

- Development evidence at d=5, with weight-3 bursts and static noise, in simulation.
- Out-of-family noise is detected, not modelled.
- Dropping the statistic means that misfit which E1 cannot absorb into burst-shaped exclusions is caught only by the cap and S1. BRT-1's out-of-family conditions, including misfit at high p, test exactly that.

## Files (new, in this package)

| File | Purpose |
|---|---|
| `brt_config.py` | conditions, bursts and endpoints |
| `estimate4.py` | gains `e1t_flag`. Existing functions are unchanged, and BRS's freeze records the previous hash |
| `brt0.py` | BRT-0 re-analysis |
| `prepare_brt.py` → `BRT_BURSTS.json`, `BRT_SEEDS.json` | bursts and seeds, screened against every prior inventory including BRS |
| `brt.py` | run, analyze, recount |
| `tests/test_brt.py` | tests |
| `freeze_brt.py` → `BRT_FREEZE.json` | freeze |
| `BRT_PROTOCOL.md` | protocol |

## Verification

**Unit tests:**
- `e1t_flag` equals the cap OR S1 OR S2;
- the bursts are disjoint from BRE's and BRS's;
- the seed screen is collision-free;
- the analysis logic works on synthetic records.

**Rehearsal:** 1 pool each for T2, TM2 and TX on rehearsal seeds. Analysis run twice to a byte-identical result, plus a replay.

**After BRT-1:**
- recount;
- `BRT_RESULTS.md` and a DECISION_REPORT addendum;
- commit. Push only on "Push it".
