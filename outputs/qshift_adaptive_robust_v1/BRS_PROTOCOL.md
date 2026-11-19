# BRS: structural misfit check for E1, a development study (pre-registered)

**Status: frozen** in `BRS_FREEZE.json`, committed before any BRS-1 study sample.

| Approval | Covers | Given |
|---|---|---|
| "Approve, build it" | the build, BRS-0 and the rehearsal | 2026-11-19 |
| Owner's choice of the subset rule | deviation 1 below | 2026-11-19 |
| "Run BRS" | the single BRS-1 run | not yet |

**Source:** `PLAN_BRS.md` (`d80cf6554`). Everything in it applies except the deviations below.

## BRS-0: design check on existing BRE arrays (no sampling; not evidence)

**What was run:**
- **`brs0.py` → `results/brs/BRS0.json`:** recomputed E1 on all 672 BRE pools. Every fit reproduced BRE's records exactly, and the excluded set X matched E1's exclusion count in every pool. This run used the plan's **exact** shape rule.
- **`brs0_rules.py` → `results/brs/BRS0_RULES.json`:** compares three shape rules on the same pools, and confirms that the final `estimate4.structural_flags` equals the subset rule in all 672.

**Burst pools flagged** (of 48 per condition), with false accepts on burst-free pools:

| Condition | exact | per-round ±1 (the plan's fallback) | **subset (chosen)** |
|---|---|---|---|
| B1 (p 0.0026) | 16 | 5 | **0** |
| B2c (p 0.0034) | **43** | **19** | **0** |
| B3 (Z-bias 4) | 12 | 1 | **0** |
| B4 (Z-bias 10) | 2 | 1 | 1 |
| B5 (p 0.0028, Z-bias 6) | 2 | 0 | 0 |
| BM (measurement 3×) | 48, 0 false accepts | 48, 0 false accepts | **48, 0 false accepts** (E1 alone had **8**) |
| BX (X-bias 10) | 48, 0 false accepts | 48, 0 false accepts | 48, 0 false accepts |

**Why it is asymmetric:**
- **In family,** E1's excluded set is a *subset* of the true burst's detector set. It misses the burst detectors whose rise falls under the +4 cutoff, which happens more often at higher p. It almost never adds extras: 1 extra detector in 240 pools.
- **Out of family,** misfit always adds at least 7 detectors outside any class's set, and burst-free BM pools add at least 10.

## Build-time deviations from the plan

1. **The shape rule is "subset", chosen by the owner after BRS-0.**
   - **The plan's rule:** exact match, with one pre-declared fallback, ±1 detector per round, and "no other change".
   - **What happened:** BRS-0 showed both would wrongly flag real bursts (43 and 19 of 48 at p 0.0034). The choice went to the owner, who chose the subset rule.
   - **The final rules:**
     - **S1:** X is non-empty and contained in no class detector set.
     - **S2:** either X is empty and a class was accepted, or X is non-empty and the accepted class's set does not contain X (or nothing was accepted).
   - **How it was chosen:** on BRS-0, which uses BRE development data only. BRS-1's bursts, seeds and conditions were fixed before this choice, are not affected by it, and remain a fully held-out test.
2. **The structural rules live in a new `estimate4.py`,** not appended to `estimate3.py`. This keeps BRE's frozen estimator file and its hash unchanged. `estimate4` imports `estimate3` and uses E1 exactly.
3. **X is derived at E1's final fit** as the detectors with standardized residual above +4. The check `set_matches_count` confirms it equals E1's exclusion count, and it held in every BRE pool.
4. **Build-time samples, disclosed:** the 3-pool rehearsal on rehearsal seeds only.

## Frozen elements

| Element | Content |
|---|---|
| Arms | **E1S** (the candidate): E1, plus E1's flag (more than 30 exclusions, or stat > 2.335), plus S1 and S2; on a flag, no burst. **E1:** as in BRE. **B2:** frozen, threshold 118.432 |
| Thresholds | Frozen from BRE's tuning pools (`results/bre/ANALYSIS.json`, checked by a test). Nothing is tuned on BRS-1 |
| Bursts | `BRS_BURSTS.json`: W01–W16, 4 per stratum, with footprints 10, 10, 10, 5, 20, 20, 20, 20, 25, 25, 25, 25, 30, 30, 30, 30. Drawn from the RE1 candidate pool, excluding every BRE class and anything within one qubit of a BRE burst |
| Conditions | **In family:** S1 (p 0.0024), S2 (p 0.0036), S3 (p 0.0031, Z-bias 5), S4 (p 0.0027, Z-bias 8). **Out of family, gated:** SM3 and SM2 (measurement p 3× and 2×), SX (X-bias 6). **Out of family, false-accept gate only:** SM15 (measurement 1.5×) |
| Pools | Per condition, 16 bursts × 2 burst pools (13,500 rows each) and 32 burst-free pools (12,000 rows). 512 pools in all, about 6.5 M detector-sampler shots |
| Seeds | `BRS_SEEDS.json`: 1,024 study keys and 7 rehearsal keys, screened against 6,121 prior values, `BRE_SEEDS.json` included |
| Verdict | **BRS_SUPPORTED:** every endpoint passes. **BRS_PARTIAL:** the in-family endpoints pass. **BRS_NOT_SUPPORTED:** otherwise |

**Endpoints for E1S** (every pool is held out):

| Endpoint | Rule |
|---|---|
| Learning | At least 95% of the 128 in-family burst pools learned exactly, and at least 30/32 per condition |
| False accepts | At most 1/32 per in-family condition |
| False flags | At most 1/32 per in-family condition, for burst pools and for burst-free pools |
| SM3, SM2, SX | Burst pools flagged at least 30/32, with at most 1/32 false accepts on burst-free pools |
| SM15 | At most 1/32 false accepts |
| No loss against E1 | E1S's in-family learned count is at least E1's minus 2 |

## Preflight (`BRS_PREFLIGHT.json`)

- **Inputs:** the slowest rehearsal times, 100 s for a burst pool and 19 s for a burst-free pool, from 3 concurrent workers.
- **Projection:** 512 pools on 8 workers is about **1.1 h**, or 1.3 h with contention, against the 3 h budget.

## Execution (single attempt)

```
git checkout --detach <freeze commit>
cd outputs/qshift_adaptive_robust_v1
python brs.py run eval --expected-head <freeze commit> --workers 8
python brs.py analyze eval <out1>
python brs.py analyze eval <out2>            # byte-identical
python brs.py recount eval <out1>/ANALYSIS.json
git checkout codex/qshift-adaptive-robust-v1   # then commit results
```

The safeguards are BRE's: a clean tree and the expected head, freeze hashes checked per job, write-once records, no retries, and a replay of one burst pool and one burst-free pool per condition.

## Rehearsal (rehearsal seeds; not data)

The rehearsal used 3 pools: S3 with burst W01, an SM2 burst-free pool, and SX with W01.

- **S3/W01:** E1 excluded exactly the 10-detector class set (b̂ 5.22 against a true 5), and the class was learned exactly with no structural flag.
- **SM2 burst-free pool:** this is the targeted case.
  - **E1 alone:** 11 exclusions with stat 1.91, below the threshold, so it would have accepted a false class.
  - **The subset rule:** it flagged the pool on both S1 and S2.
- **SX/W01:** 71 exclusions, so flagged.
- **Reproducibility:**
  - the analysis was byte-identical across two runs;
  - the recount re-analysis was identical;
  - all 3 replayed pools were bit-identical.

## Claim boundary

- Development evidence at d=5, with weight-3 bursts and static noise, in simulation.
- E1S *detects* measurement-heavy misfit; it does not model it.
- The subset rule was chosen on BRE data, so BRS-1 is its first test.
- A supported E1S becomes the RE2 candidate. RE2 needs a new sealed burst that excludes every BRE and BRS support.
