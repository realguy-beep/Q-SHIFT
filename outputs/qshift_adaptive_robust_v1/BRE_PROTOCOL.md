# BRE: burst-robust estimation, a development study (pre-registered)

**Status: frozen** in `BRE_FREEZE.json`, committed before any BRE-1 study sample.

| Approval | Covers | Given |
|---|---|---|
| "Approve, build it" | the build, BRE-0 and the rehearsal | 2026-11-19 |
| "Run BRE" | the single BRE-1 sampling run | not yet |

**Source:** `PLAN_BRE.md` (`bbff5861a`). Everything in it applies except the deviations below.

## BRE-0 results (deterministic census; `results/bre/census/CENSUS.json`)

**What was computed:**
- **Supports:** 2,002 (the RE1 candidate pool plus K, M0, M1, CR).
- **Models:** 8 (the 7 BRE conditions plus the nominal model).
- **Per support and model:** exact detector rates at q ∈ {0, 0.01, 0.02}, the expected equal-q-mix calibration pool, and the B2 grid fit on those expected rates (n = 12,000).
- **Refined fits:** B2 and E1 were also refined on a stratified subsample of 40 supports per model.
- **Data:** no sampling; wall time 340 s.
- **What is published:** only aggregates. Per-support rows stay in git-ignored `work/`.

**Findings:**
1. **Footprints are 5–30 detectors, in steps of 5** (one detector set per round). Counts over supports: 5 (72), 10 (233), 15 (469), 20 (625), 25 (484), 30 (119).
2. **The development bursts were all small.** K, M0, M1 and CR flip 20, 15, 20 and 10 detectors. Neither the flag threshold nor any earlier development pool ever saw a 25- or 30-detector burst.
3. **A 30-detector burst always breaks B2.** Its *noise-free* objective is 124–326 across the in-family conditions, above the flag threshold of 118.4 before any sampling noise, which adds about 56 (the development median). A 25-detector burst gives 23–79, so it can be flagged after noise. In B5, where the base model is off-grid, the heuristic cut-off (118.4 − 56) marks 440 of 484 such supports as likely flagged.
4. **The bursts also bias b̂.** Even on exact rates, b̂ ranged down to 3.09 (true 4) in B3, 4.17 (true 10) in B4, and 4.55 (true 6) in B5.
5. **This is consistent with RE1's R6 (objective 175–227, b̂ 2.8 against a true 4).** It suggests R6 was the expected behaviour for a large-footprint burst, not bad luck. No RE1 record was used to reach this.
6. **E1 as first written failed on 2 of 40 B4 supports.** Starting from the biased B2 fit, it locked onto a fixed point with 6 exclusions and b̂ = 5.0. This led to deviation 2.
7. **Final E1 is exact.** On all 200 in-family subsample cases it excluded exactly the burst's detectors, had b̂ within 2% of the truth (40/40 per condition), and left a zero objective. Out of family:
   - **BX:** 71–72 exclusions, above the 30-detector cap, so flagged.
   - **BM:** 14–34 exclusions with an objective up to 487, so flagged by the statistic.

## Build-time deviations from the plan

All were made before any BRE-1 sample.

1. **E1 cutoff fixed a priori** at +4 standard deviations, rather than set on T by a rule. Under the correct model, P(any of 120 detectors exceeds +4) ≈ 0.4%. This removes a tuning degree of freedom.
2. **E1 start (from BRE-0 finding 6).**
   - **What changed:** E1 starts from a one-sided fit that, at every candidate (p, b), drops the 30 largest *positive* standardized residuals. It then iterates the cutoff rule to a fixed point.
   - **Why 30:** it is the largest burst detector set over all signature classes, a property of the code, not a tuned value.
3. **E1 flag.** A pool is flagged if E1 excludes more than 30 detectors (larger than any burst), or if its mean squared included residual exceeds the threshold set on T.
4. **E3 defined precisely:** E1's fit, with E2's on-flag policy (learn on the nominal model). E1 already excludes the burst detectors, so E3 has no separate refit.
5. **Burst-free pools raised to 48 per condition:** pools 0–23 for tuning and 24–47 held out, so that thresholds are never set on the held-out burst-free pools.
   - **Totals:** 672 pools, made of 336 burst pools of 13,500 rows and 336 burst-free pools of 12,000 rows. That is about **8.6 M** detector-sampler shots, against the plan's 504 pools and 6.6 M.
6. **K regression endpoint.** The plan's "24/24 per condition" did not match its own 2 K pools per condition. The endpoint is now: all 10 in-family K pools learned exactly, and at least 95% of all in-family T burst pools learned exactly.
7. **Flags are applied in the analysis.** Each pool's record stores every arm's fit statistic and every learner outcome an arm might need: learning on the nominal, B2, E1 and E2-refit models. The analysis sets thresholds on T pools only, then applies each arm's flag and on-flag policy. Every pool is therefore sampled and learned once, and the arms are compared on identical data.
8. **Burst strata use the class detector-set size.** This equals the census footprint at the 10% threshold, and selection then depends on no census rows.
9. **Build-time samples, disclosed.** During the build I sampled:
   - one 12,000-row prototype pool, with ad-hoc seeds 12345–12347 and burst (9, 34, 38), to check that `fit_masked` reproduces B2 bit for bit;
   - the 3-pool rehearsal on rehearsal seeds.

   Neither is study data. Both use seeds outside `BRE_SEEDS.json`.

## Frozen elements

| Element | Content |
|---|---|
| Arms | **B2:** frozen (`estimate2`, threshold 118.432); on flag, no burst. **E1:** one-sided start, then cutoff 4; on flag, no burst. **E2:** B2, then learn, refit excluding the learned class's detectors, then relearn; on flag, nominal learner. **E3:** E1's fit; on flag, nominal learner |
| Learner | Phase C learner and flip stage, unchanged, τ = 1,561.218 |
| Thresholds | E1 and E2: maximum statistic over **in-family T pools** (T bursts plus burst-free pools 0–23). B2: frozen |
| Bursts | `BRE_BURSTS.json`, drawn by public seed, one support per class, stratified by footprint (≤15 / 20 / 25 / 30). **T:** K (20), M0 (15), M1 (20), CR (10), and T01–T08 (15, 15, 20, 20, 25, 25, 30, 30). **V:** V01–V12, three per stratum (15, 10, 10, 20, 20, 20, 25, 25, 25, 30, 30, 30) |
| Conditions | B1 (p 0.0026), B2c (p 0.0034), B3 (Z-bias 4), B4 (Z-bias 10), B5 (p 0.0028, Z-bias 6), plus out-of-family BX (X-bias 10) and BM (measurement p 3×) |
| Seeds | `BRE_SEEDS.json`: 1,344 study keys and 7 rehearsal keys, screened against 4,770 prior values, `RE1_SEEDS.json` included |
| Endpoints (V, per arm) | See the next table |
| Verdict | **BRE_SUPPORTED:** the first arm in the order E1, E3, E2 that passes every endpoint. **BRE_PARTIAL:** some candidate arm passes the learning and false-accept endpoints. **BRE_NOT_SUPPORTED:** otherwise |

**Endpoints:**

| Endpoint | Rule |
|---|---|
| Learning | At least 95% of in-family V burst pools learned exactly overall, and at least 22/24 per condition |
| False accepts | At most 1/24 V burst-free pools per in-family condition |
| False flags | At most 1/24 per in-family condition, for burst pools and for burst-free pools |
| Out of family | BX and BM flag at least 23/24 V burst pools, with at most 1/24 false accepts on burst-free pools |
| K regression | As in deviation 6 |

## Preflight (`BRE_PREFLIGHT.json`)

- **Inputs:** the slowest rehearsal pool times, 139 s for a burst pool and 24 s for a burst-free pool. These came from 3 concurrent workers.
- **Projection:** 672 pools on 8 workers is about **1.9 h**, or 2.4 h with a 1.25 contention factor, against the 5 h budget.
- **Consequence:** the fallback (drop BM) is not applied.

## Execution (single attempt)

```
git checkout --detach <freeze commit>
cd outputs/qshift_adaptive_robust_v1
python bre.py run eval --expected-head <freeze commit> --workers 8
python bre.py analyze eval <out1>
python bre.py analyze eval <out2>            # byte-identical
python bre.py recount eval <out1>/ANALYSIS.json
git checkout codex/qshift-adaptive-robust-v1   # then commit results
```

**Safeguards:**
- Runs need a clean tree with HEAD equal to the freeze commit. Each job re-verifies every freeze hash.
- `RUN_STATUS.json` refuses a relaunch.
- There are no retries or substitutions.
- The recount re-derives the analysis and replays the first burst pool and the first burst-free pool of every condition; the replay must be bit-identical.

## Rehearsal (rehearsal seeds; not data)

The rehearsal used 3 pools: B3 with K, B4 with M1, and a BX burst-free pool.

**Learning:**
- **B3/K and B4/M1:** every arm learned the burst exactly. The nominal learner did not.
- **B4:** B2's b̂ was 10.6 and E1's was 10.5, against a true 10.
- **BX burst-free pool:** every learner accepted a false class, the nominal one included. E1 excluded 71 detectors and was flagged.

This previews a real risk for the E2 and E3 on-flag policy, which the out-of-family endpoint will test. The rehearsal's verdict is meaningless, since it has no V pools.

**Reproducibility:**
- the analysis was byte-identical across two runs;
- the recount re-analysis was identical;
- all 3 replayed pools were bit-identical.

## Claim boundary

- Development evidence only, at d=5, with weight-3 bursts and static noise, in simulation.
- The V bursts test generalization within development; they do not confirm it.
- H2 (RE1) was not read and could not be excluded from the burst draw. It is spent for confirmatory use.
- A supported arm becomes the candidate for a frozen RE2 with a new sealed burst. RE2 must exclude every BRE support.
