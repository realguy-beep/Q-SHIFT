# H-E1b results: bias-aware re-basing of the Phase C learner

**Verdict: H-E1b_SUPPORTED**, under the rule pre-registered in `HE1B_PROTOCOL.md` (commit `6169c6656`).
- A joint (p, bias) fit from each pool's unlabeled detector rows repairs Z-biased noise.
- The same fit keeps the p-scale repairs and the matched-model control intact.

This is development data only. Two caveats follow below.

## How the run was done

| Item | Detail |
|---|---|
| Authorization | Owner, 2026-11-18 ("Run H-E1b bias fit"); code and protocol committed at `6169c6656` first |
| Peek before the run | None. Pre-commit checks used synthetic draws from model rates only |
| Command | `python he1b.py run --workers 8`: 192/192 write-once records in 60 s |
| Data | Existing H-E1 pools, no sampling |
| Analysis | `python he1b.py analyze`, run twice; `HE1B.json` byte-identical |

## Results

Arm B is the bias-aware fit. H-E1 arm R is the earlier scalar-p fit, shown for comparison. Burst pools and burst-free pools are each out of 24.

| Condition | True model | p̂ mean ± SD | b̂ (48 pools) | B: class correct | B: learned (class + flip) | B: false accepts | B: max burst-free Δ (τ = 1,561) | H-E1 R: class / false accepts | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Mlo | p 0.0025, balanced | 0.0025009 ± 0.0000222 | 1 in all 48 | 24 | 24 | 0 | 1,021 | 24 / 0 | NO_DEGRADATION |
| Mhi | p 0.0035, balanced | 0.0034974 ± 0.0000348 | 1 in all 48 | 24 | 24 | 0 | 916 | 24 / 0 | NO_DEGRADATION |
| **Mz** | p 0.003, Z-bias 10 | 0.0030059 ± 0.0000351 | **10 in all 48** | **24** | **24** | **0** | 517 | **0** / 0 | **PASS** |
| CTRL | p 0.003, balanced | 0.0030001 ± 0.0000189 | 1 in all 48 | 24 | 24 | 0 | **1,544** | 24 / 0 | NO_DEGRADATION |

Phase C as is (arm N, from H-E1) had: Mlo 0/24 learned; Mhi 24/24 false accepts; Mz 0/24 learned.

## Interpretation

1. **Bias is identifiable from detector data, given a model family that contains it.** The 120 detectors cover both X- and Z-type stabilizers, and Z-bias changes their rates differently: the ratio to balanced ranges from 0.43 to 1.10. The trimmed fit picks the correct bias in every pool and recovers p within about 0.2%. On the re-based model the unchanged learner then learns the burst in 24/24 pools, against 0/24 before.
2. **Together with H-E1:** at d=5 with the known burst, the learned-support method now works on development data when the true background is any of these:
   - 17% below the assumed p;
   - 17% above the assumed p;
   - Z-biased with bias 10;
   - matched to the model.

   In every case the learner knows only its model *family*, not the true parameters.

## Caveats (stated, not hidden)

1. **The grid contains the truth.** The b grid includes 10 and the p grid includes values within 3% of every true p. Exact recovery (b̂ = 10 in all 48 Mz pools) is therefore partly a property of the grid. **The next test must use a bias value off the grid** (for example 6 or 12) and a p between grid points. That needs new development samples.
2. **Grid quantization removed H-E1's safety margin on the control.**
   - The p grid passes within 0.02% of 0.003, so the control's p̂ is effectively the nominal value. The control's largest burst-free Δ is back to **1,544, which is 98.9% of τ**. It is the same pool that sat close to the threshold under the nominal learner.
   - H-E1's continuous p̂ had brought it down to 362. The verdict is unaffected (0/24 false accepts), but the margin is thin.
   - **Recommended fix, which must be pre-declared before it is used:** refine p continuously within the chosen b̂, using H-E1's 1-D root, instead of snapping p to the grid.
3. **The model family is assumed.** The fit chooses within `{balanced/z_biased} × p`. X-bias, non-uniform bias, measurement-vs-gate mismatch, drift and crosstalk are not in the family. The fit objective (its residual after trimming) is recorded per pool as `fit_objective` and could serve as a misspecification flag. Nothing here calibrates it.
4. **Learner only.** Decoders under mismatch were not tested. That needs the end-to-end decode check, which requires new development samples.

## Next steps (each needs an owner OK)

1. **Off-grid validation screen (new development samples, small).**
   - Draw fresh pools with biases 6 and 12, p values 0.0027 and 0.0033, an X-bias case, and a measurement-heavy case.
   - Use continuous p refinement, pre-declared.
   - Measure learning accuracy, false accepts and the fit-objective flag.
2. **End-to-end decode check under mismatch.** Re-based learner plus decoders (L2L, Astar on the estimated model), on Mlo, Mhi and Mz decode roots. About 54k new development shots.
3. Only after both: fold the re-basing step into the adaptive controller's estimation stage and the broad benchmark's validation split.
