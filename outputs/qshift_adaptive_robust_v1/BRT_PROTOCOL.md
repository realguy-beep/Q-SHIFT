# BRT: threshold-free E1 flag, a development study (pre-registered)

**Status: frozen** in `BRT_FREEZE.json`, committed before any BRT-1 study sample.

| Approval | Covers | Given |
|---|---|---|
| "Approve, build it" | the build, BRT-0 and the rehearsal | 2026-11-19 |
| "Run BRT" | the single BRT-1 run | not yet |

**Source:** `PLAN_BRT.md` (`88e1dfb11`). Everything in it applies except the deviations below.

## The candidate

**E1T** uses E1's fit, unchanged (BRE). It is flagged if and only if any of the following holds:
- E1 excludes more than 30 detectors (larger than any burst class);
- S1 (shape) fails: X is non-empty and contained in no class detector set;
- S2 (consistency) fails: X is empty but a class was accepted, or the accepted class's set does not contain X.

S1 and S2 are BRS's subset rule. On a flag, no burst.

**There is no residual statistic and no tuned parameter.** The cutoff of +4 was fixed a priori in BRE. The cap of 30 is a code property. S1 and S2 are set logic.

## BRT-0: E1T on existing BRE and BRS data (no sampling; design check, not evidence)

**Source:** `results/brt/BRT0.json`. For BRE, E1 was recomputed from BRE's saved arrays, and every fit reproduced BRE's record exactly. BRS records were read directly.

| Study, condition | E1T burst pools flagged / learned | E1T burst-free flagged / false accepts | E1S, for comparison |
|---|---|---|---|
| BRE, in family (5 × 48) | 1 / 239 (B4: 1) | 0 / 0 | the same |
| BRE, BM and BX | 48 / 0 each | 48 / 0 each | the same |
| BRS S1, S3 and S4 | 0 / 32 | 0 or 1 / 0 | the same |
| **BRS S2 (p 0.0036)** | **1 / 31** | 1 / 0 | **2 / 30**, which was BRS's failure |
| BRS SM2, SM3 and SX | 32 / 0 | 32 / 0 | the same |
| BRS SM15 | 15 / 17 | 21 / 1 | 19 / 13, and 21 / 1 |

**What it shows:** on both earlier studies, E1T would have met every endpoint. That is post-hoc, so BRT-1 is the test.

## Build-time deviations from the plan

1. **E1T lives in a new `estimate5.py`,** rather than being added to `estimate4.py`. This keeps BRS's frozen estimator file and its hash unchanged.
2. **The large-footprint pool is depleted.** After excluding every BRE and BRS class and anything within one qubit of their bursts, only **9** of the 30-detector classes were eligible; BRT uses 4. The stratum class counts were 121, 119, 83 and 9. This constrains RE2's sealed-burst pool. RE2 must either allow re-use of classes that were used only in development, with justification, or accept fewer large-footprint candidates. This is to be decided when RE2 is planned.
3. **Build-time samples, disclosed:** the 3-pool rehearsal on rehearsal seeds only.

## Frozen elements

| Element | Content |
|---|---|
| Arms | **E1T** (the candidate). **E1S** as frozen in BRS. **E1** with the BRE-frozen threshold 2.335. **B2** frozen at 118.432 |
| Bursts | `BRT_BURSTS.json`: X01–X16, 4 per stratum, with footprints 15, 5, 15, 15, 20, 20, 20, 20, 25, 25, 25, 25, 30, 30, 30, 30. None is near any BRE or BRS burst |
| Conditions | **In family:** T1 (p 0.0020), T2 (p 0.0040), T3 (p 0.003, Z-bias 3), T4 (p 0.0033, Z-bias 12). **Out of family, gated:** TM25 (measurement 2.5×), TM2 (gate 0.0036, measurement 2×), TX (X-bias 4). **Out of family, false-accept gate only:** TM15 (measurement 1.5×) |
| Pools | Per condition, 32 burst pools (13,500 rows each) and 32 burst-free pools (12,000 rows). 512 pools in all, about 6.5 M detector-sampler shots |
| Seeds | `BRT_SEEDS.json`: 1,024 study keys and 7 rehearsal keys, screened against 7,152 prior values, BRS included |
| Endpoints (E1T) | As in BRS: learning ≥ 95% overall and ≥ 30/32 per in-family condition; in-family false accepts ≤ 1/32 and false flags ≤ 1/32 (burst and burst-free); TM25, TM2 and TX flag ≥ 30/32 burst pools with ≤ 1/32 false accepts; TM15 false accepts ≤ 1/32; no loss against E1 (≥ E1's count minus 2) |
| Verdict | **BRT_SUPPORTED:** all endpoints pass. **BRT_PARTIAL:** the in-family endpoints pass. **BRT_NOT_SUPPORTED:** otherwise |

## Preflight (`BRT_PREFLIGHT.json`)

- **Inputs:** the slowest rehearsal times, 155 s for a burst pool (T2) and 21 s for a burst-free pool, from 3 concurrent workers.
- **Projection:** 512 pools on 8 workers is about **1.6 h**, or 1.9 h with contention, against the 3 h budget.
- **Caveat:** both BRE and BRS ran at about half their projections.

## Execution (single attempt)

```
git checkout --detach <freeze commit>
cd outputs/qshift_adaptive_robust_v1
python brt.py run eval --expected-head <freeze commit> --workers 8
python brt.py analyze eval <out1>
python brt.py analyze eval <out2>            # byte-identical
python brt.py recount eval <out1>/ANALYSIS.json
git checkout codex/qshift-adaptive-robust-v1   # then commit results
```

The safeguards are as in BRE and BRS.

## Rehearsal (rehearsal seeds; not data)

The rehearsal used 3 pools: T2 with burst X01, a TM2 burst-free pool, and TX with X01.

- **T2/X01** (p 0.0040, above every prior range): p̂ was 0.00404. E1 excluded 9 of the 15 burst detectors, a subset. The class was learned exactly with no flag.
- **TM2 burst-free pool** (misfit at high p): E1's statistic was 2.30, just under the BRE threshold, with 8 exclusions. So E1 alone would have accepted a false class. E1T flagged it on S1 and S2.
- **TX/X01:** 68 exclusions, so flagged.
- **Reproducibility:**
  - the analysis was byte-identical across two runs;
  - the recount re-analysis was identical;
  - all 3 replayed pools were bit-identical.

## Claim boundary

- Development evidence at d=5, with weight-3 bursts and static noise, in simulation.
- Out-of-family noise is detected, not modelled.
- E1T's flag was shaped by BRE and BRS. BRT-1 is its first test on data that informed nothing.
- A supported E1T becomes the RE2 candidate. RE2 needs a new sealed burst; see deviation 2.
