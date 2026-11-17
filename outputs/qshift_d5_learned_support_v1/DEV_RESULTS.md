# d=5 learned burst support, Phase B: development gate results

**Decision: STOP.** G2 failed. The pre-registered rule therefore ends the study before Phase C. No frozen evaluation will run on this learner.

- **Protocol:** `DEV_PROTOCOL.md`, pre-registered at `d30c3f72b` before any gate sample.
- **Run:** a single run of 120 pool jobs and 312 Stim sampler calls (720,000 shots), 554 s on 8 workers, all jobs complete.
- **Aggregation:** `gate_aggregate.py` checked every seed against `DEV_SEEDS.json`. Its output is in `DEV_GATE.json`; the per-pool records are in `results/gate_dev/pools/`.

## Gates

| Gate | Rule | Result | Pass |
|---|---|---|---|
| G1 class | every burst ≥ 23/24 | SC 24, CR 24, M0 24, M1 24 | yes |
| G2 q=0 "no burst" | ≥ 22/24 | **9/24** | **no** |
| G3 flip | ≥ 95% of class-correct pools | 100% for all four. For M0 and M1 this came from the labeled L2 stage; for SC and CR it is automatic, since their classes are pure | yes |

## What worked

- **Finding the burst.** Every burst pool found the true class and flip, already at 3,000 shots: SC, CR, M0 and M1 each scored 24/24 at 3k, 6k and 12k.
- **Rate estimates.** The q̂ error against the pooled mean (0.01) was 0.0006–0.0008.
- **The new labeled stage.** It always picked the correct flip, including both cases where the min-weight explanation has the wrong logical effect (M0, M1). In the rehearsal, the error counts it compared were 3 vs 63 and 2 vs 86.
- **Mechanism identity.** Learned supports were the true support (SC, M0, M1), or for CR the representative (16, 18, 25), which has identical burst mechanisms (tested).

## What failed: false bursts on burst-free data

- 15 of the 24 q=0 pools reported a burst, with Δ between 20.9 and 1,060 against the threshold of 19.52.
- The rate was 15/24 at 3k shots, 12/24 at 6k and 15/24 at 12k, so more data did not reduce it.
- Every false pool had q̂ between 0.0005 and 0.0033, and they selected several different classes (0, 362, 750, 826, 897, 900, 949, 989, 1002, …).
- The other 9 pools had Δ = 0 exactly.
- The smallest Δ in any true-burst pool was 7,833.

**Interpretation (a hypothesis, not tested here).** The threshold treats each class's Δ as χ²₁ under the null. That holds only if the parity statistics are independent and the base model is exact. At d=5, the 2,920 parity subsets overlap heavily, and the weighted least-squares fit ignores their covariance, so Δ is not χ²₁-distributed. The base DEM is also built with `approximate_disjoint_errors=True`, which could add a small systematic bias. At d=3, with 15 classes and far fewer subsets, the same rule held (V1.6b G2′ 0.958).

**Not done.** The threshold was not re-tuned on these data. A threshold between about 1,061 and 7,833 would have separated the two groups here, but choosing it from gate data would be tuning on the result. The STOP stands.

## Cost

Mean time per pool, under 8-way contention:
- 1.2–1.5 s for pure-class pools;
- 84–92 s for mixed-class pools, almost all of it the two L2 decodes of the 1,500 labeled shots.

## If the line continues (needs a new pre-registration and owner OK)

These options would each need fresh seeds and a new gate:
- **Null calibration from the known base model.** Simulate burst-free calibration pools from the base circuit to set the acceptance threshold. This uses only knowledge the learner already assumes, the base DEM.
- **A covariance-aware statistic,** such as a generalized least-squares Δ or a parametric bootstrap.

Neither option is authorized, and the existing d=5 claims remain oracle-support results.
