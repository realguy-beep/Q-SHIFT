# d=5 learned burst support, Phase B2: null-calibrated gate results

**Decision: PASS.** All three gates hold. Phase C, the frozen evaluation, may now be planned. It still needs its own freeze and owner OK, and the hidden-support seal needs explicit authorization.

- **Protocol:** `GATE_B2_PROTOCOL.md`, pre-registered at `8b5416ea8`.
- **Threshold:** τ was committed at `fd42c44c0` before any gate sample was drawn. The gate refuses to run unless `NULL_THRESHOLD.json` is committed and unchanged.
- **Runs:**
  - null calibration: 500 pools, 6,000,000 shots, 86 s;
  - gate: 120 pool jobs, 312 sampler calls, 720,000 shots, 559 s on 8 workers.
- **Checks:** every seed was verified against `B2_SEEDS.json`. Records are in `DEV_GATE_B2.json` and `results/b2_dev/pools/`.

## Null calibration (`NULL_THRESHOLD.json`)

| Quantity | Value |
|---|---:|
| Burst-free pools | 500 × 12,000 shots |
| Pools with T = 0 | 112 |
| Median T | 59.6 |
| 90th / 95th / 99th percentile of T | 457 / 678 / 996 |
| **τ = max T** | **1,561.2** |
| Viability check (0 < τ < 3,000) | passes |

The old analytic threshold of 19.52 sits below the null median. That confirms Phase B's diagnosis: at d=5, Δ is far from χ²₁ under the null.

## Gates

| Gate | Rule | Result | Pass |
|---|---|---|---|
| G1 class | every burst ≥ 23/24 | SC 24, CR 24, M0 24, M1 24 | yes |
| G2 burst-free "no burst" | ≥ 22/24 | **24/24** | yes |
| G3 flip | ≥ 95% of class-correct pools | 100% for all four. For M0 and M1 this comes from the labeled L2 stage; for SC and CR it is automatic, since their classes are pure | yes |

## Descriptive results

- **Smallest true-burst Δ at 12k:** SC 8,518, CR 6,504, M0 9,704, M1 8,548. The smallest is 4.2× τ.
- **Largest burst-free Δ in the gate: 1,543.8, just below τ (99% of it).** The margin is real by construction, since P(T > τ) ≈ 1/501 per pool. Still, the null tail sits close to τ: one burst-free pool in about 500 is expected to raise a false alarm.
- **Learning curve:**
  - class correct at 3k / 6k / 12k: SC 23/24/24, CR 23/24/24, M0 21/24/24, M1 21/24/24;
  - burst-free "no burst" at 3k / 6k / 12k: 24/24/24.
  - τ is calibrated only for 12k, so the 3k and 6k points are descriptive.
- **q̂ error against the pooled mean 0.01:** 0.0006–0.0009.
- **Learned supports** are the true support for SC, M0 and M1. For CR it is the representative (16, 18, 25), which has identical burst mechanisms.
- **Time per pool:** about 1 s for pure classes, 88–90 s for mixed classes.

## Claim boundaries

- Development evidence at d=5, p = 0.003, for four pre-declared weight-3 bursts, with 12,000 detector-only + 1,500 labeled calibration shots.
- τ is calibrated with the **true** base noise model, which is the same assumption the learner makes about the base DEM. Base-model error on a real device would shift the null distribution, and this simulation does not test that.
- The gate measures learning reliability. It is not an evaluation of decoding performance; that is Phase C.
- Phase B (STOP) remains on record. B2 changed only the threshold rule, on fresh seeds.
