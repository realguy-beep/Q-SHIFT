# H-E1b: bias-aware re-basing of the Phase C learner (pre-registered)

**Authorization:** the owner said "Run H-E1b bias fit" on 2026-11-18.

**Commit order:** this protocol and `he1b.py` are committed before the run.

**Checks before the commit:**
- `z_biased` with bias 1 was confirmed to give detector rates identical to `balanced`.
- A synthetic self-check on independent Bernoulli draws from the model's own rate vectors recovered (p, b) = (0.003, 1), (0.0025, 1) and (0.003, 10).
- No study pool was read.

## Question

H-E1 showed that a scalar p̂ repairs p-scale mismatch but not Z-bias (Mz stayed at 0/24). Does fitting the background **p and bias** jointly from unlabeled detector rows repair Mz, without degrading the cases H-E1 already fixed?

## Data

The same 192 development pools as H-E1 (`he1.pools()`), all existing:
- **Mlo, Mhi, Mz:** from mismatch Phase A.
- **CTRL:** matched-model SC and Q0 pools from Phase B2.

There is no sampling.

## Arm B

1. **Fit (p̂, b̂).** Minimize Σ over the 80% smallest standardized squared residuals, summing n·r̂_i·(log r̂_i − log r_i(p, b))². Here r̂_i is the observed rate of detector i and r_i(p, b) is the rate predicted by the `z_biased` base DEM.
   - The fit is over a fixed grid: p in 61 geometric points from 0.0012 to 0.0075; b ∈ {1, 1.5, 2, 3, 4, 5, 7, 10, 15, 20, 30}.
   - It uses the pool's unlabeled detector rows only.
2. **Learn.** Run the unchanged `FastParityLearner` (τ = 1,561.218) and `learn_flip` on the base DEM at (p̂, b̂).

**Disclosure:** the b grid contains the true Mz bias, 10. A grid point at the truth can make recovery look cleaner than a continuous fit would. b̂ is reported in full so this can be judged.

## Decision rule (fixed)

| Condition | Required for a pass |
|---|---|
| Mz | **PASS** if class correct ≥ 20/24 burst pools **and** false accepts ≤ 1/24 burst-free pools |
| Mlo, Mhi, CTRL | **NO_DEGRADATION** if class correct ≥ 22/24 **and** false accepts ≤ 1/24 (H-E1's arm R had 24/24 and 0/24) |

**Overall:**
- **H-E1b_SUPPORTED:** Mz PASS **and** all three others show NO_DEGRADATION.
- **H-E1b_PARTIAL:** exactly one of those two holds.
- **H-E1b_NOT_SUPPORTED:** neither holds.

**Reported:**
- the p̂ and b̂ distributions;
- learned-correct counts;
- the largest burst-free Δ;
- H-E1's arm R side by side.

## Execution

- `python he1b.py run --workers 8` (192 write-once records), then `python he1b.py analyze`, which writes `results/he1b/HE1B.json`. About 3–5 min.
- **Scope:** development evidence for the learner only.
