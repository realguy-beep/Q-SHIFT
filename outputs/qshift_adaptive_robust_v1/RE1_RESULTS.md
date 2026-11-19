# RE1 results: frozen evaluation of the mismatch-robust learned-support pipeline

**Verdict: NOT_CONFIRMED.** R1–R5 pass every gate. R6, the sealed hidden burst, fails in direction.

| | |
|---|---|
| Freeze | `fe4471fff` (`RE1_FREEZE.json`, 34 files), run once from a detached checkout of that commit |
| Run | 78/78 jobs, return code 0, single attempt, 8 workers, 11,250 s (3.1 h; preflight 3.1–3.8 h) |
| Shots | 78 roots × 3 q × 4,000 evaluation shots = 936,000, plus 78 × 13,500 calibration rows = 1,053,000 |
| Analysis | `results/re1/ANALYSIS.json`, run twice, byte-identical |
| Recount | `results/re1/RECOUNT.json`: stored counts match the analysis, and the end-to-end re-decode of root 0 is bit-identical in all 7 conditions |
| Seal | H2 was read only inside the run (`--open-hidden-seal`). Nothing here identifies it. Publishing H2 needs "Open the RE1 seal" |

## Gated conditions

Nonzero-q LER pools q = 0.01 and 0.02 over 12 roots (96,000 shots per arm). Bounds are one-sided at α = 0.025/12, root bootstrap, 20,000 replicates.

| Cond | True model | Burst | Learned exactly (R / N) | Flagged | L2L_R | L2s_true (oracle) | S\* | R vs S\* [95% CI] | NI | SUP | Safety q=0 | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | p 0.0026 | K | 12 / 0 | 0 | 3.85e-4 | 3.85e-4 | 1.29e-3 | 70% [58, 81] | pass | pass | pass | **PASS** |
| R2 | p 0.0034 | K | 12 / 12 | 0 | 1.01e-3 | 1.05e-3 | 2.46e-3 | 59% [53, 65] | pass | pass | pass | **PASS** |
| R3 | p 0.003, Z-bias 8 | K | 12 / 0 | 0 | 9.4e-5 | 9.4e-5 | 7.08e-4 | 87% [78, 94] | pass | pass | pass | **PASS** |
| R4 | p 0.0028, Z-bias 4 | K | 12 / 0 | 0 | 1.25e-4 | 1.25e-4 | 1.03e-3 | 88% [79, 94] | pass | pass | pass | **PASS** |
| R5 | p 0.003 (control) | K | 12 / 12 | 0 | 6.77e-4 | 6.88e-4 | 1.80e-3 | 62% [55, 70] | pass | pass | pass | **PASS** |
| R6 | p 0.0028, Z-bias 4 | **H2 (sealed)** | **0 / 0** | **12** | **6.51e-3** | 1.88e-4 | 1.17e-2 | 44% [42, 46] | **fail** | pass | not shown | **FAIL_DIRECTION** |

"Learned exactly R / N": the pipeline's learner on the estimated model / the same learner on the nominal model.

- **R1–R5: the development result replicates on fresh seeds at mismatch values never used in development.** L2L_R matches the true-model, true-support oracle to within a few errors in every condition (discordant with the oracle: 0/0, 0/4, 0/0, 0/0, 0/1). It beats the strongest deployable matcher by 59–88%.
- **The repair is what makes this work.** Under R1, R3 and R4 the nominal-model learner never found the burst (0/12), and L2L_N ran 10–22× worse than L2L_R (one-sided McNemar p ≤ 5e-50). Under R2 and R5 the nominal learner already succeeds, and the two agree.
- **R6 fails.** The pipeline never learned the hidden burst, and its nonzero-q LER is 35× the oracle's: 625 errors against 18. The NI estimate (+6.3e-3) is far above its margin (4.7e-5), so the status is FAIL_DIRECTION by the pre-declared rule, and the overall verdict is NOT_CONFIRMED.
  - SUP still passes, but only because S\* is broken in the same way: with no support learned, correlated matching on the nominal model is worse than plain matching (1.17e-2 against 4.99e-3).
  - Safety at q=0 is not shown: the estimate is −1 error (16 against 17), but the p95 (1.04e-4) exceeds the 3-error floor margin (6.25e-5).

## Why R6 failed (diagnosis from the frozen records; not a new test)

The failure is in the misspecification flag, not in the learner or the decoder.

1. **Every R6 root was flagged.** The B2 objective ranged from 175 to 227 against the threshold of 118.4. Under R4, which has the same true base model with burst K, the objective was about 79 and no root was flagged.
2. **A flagged pool learns no burst, by design** (`DEV2_PROTOCOL.md`). L2L_R therefore decoded on the nominal model with no burst support.
3. **The fallback cannot recover either.** The nominal-model learner fails under Z-bias 4, exactly as in R4 (0/12 there too).
4. **The flag cannot tell an unfamiliar burst from base-model misfit.** The threshold is the largest objective over 192 development pools, whose bursts were all K (`FLAG_THRESHOLD.json`, `he1.py`). H2's detector footprint survives the 20% trim and inflates the objective, which also biases the fit: b̂ = 2.77 ± 0.69 against a true 4, with 3 of 12 roots on the b = 1.5 grid cell.

So the robust fit was validated for a burst it had seen. The trimmed detector-rate objective is not burst-agnostic, and the flag inherits that limitation. Because the flag also disables learning, a false flag is costly.

## X1 (descriptive, X-bias 10, burst K, 6 roots)

- Flagged in 6/6 roots, as intended for out-of-family noise.
- The fallback is safe only in the weak sense: L2L_R decodes with no burst and is 4× worse than the oracle (6.19e-3 against 1.54e-3).
- The nominal learner found K in 6/6 roots here, and L2L_N decoded near the oracle (1.65e-3). Discarding learning entirely on a flag throws this away.
- q=0: L2L_R 46 errors against A_nominal 41, over 24,000 shots. Descriptive only.

## What this changes

- **Supported (frozen, fresh seeds):** for the known burst K, the mismatch-robust pipeline decodes at oracle level under ±13% background-p error, Z-bias 4–8, and a combined mismatch, beating the strongest deployable matcher by 59–88%.
- **Not supported:** the same claim for a hidden burst. The study's pre-registered statement requires both, so it is not made.
- **Diagnosed cause, for a future development study (not a fix applied here):**
  - make the (p, b) fit burst-robust, for example by excluding the top-scoring detectors adaptively, or fitting the burst and the background jointly;
  - recalibrate the flag on pools with varied burst supports;
  - on a flag, still run the nominal-model learner rather than disabling learning.

  Any of these needs new development data and a new frozen evaluation with a new sealed burst. RE1's H2 is now spent and must not be used for development.
- **Unchanged:** R against matching stays at 59–88%, so the 95% target remains out of reach.
