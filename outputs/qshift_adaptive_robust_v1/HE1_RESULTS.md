# Roadmap step 2 / H-E1 results: mismatch-robust burst-support learning

**Verdict:** **H-E1_PARTIAL**, under the rule pre-registered in `HE1_PROTOCOL.md` (commit `fcd9b8834`).

- Re-basing the unchanged Phase C learner on a background p estimated from the pool's own unlabeled detector rows **fully repairs both p-scale mismatches**.
- It **does not repair Z-biased noise**.
- The matched-model control is unaffected.

These are development data only. The result justifies a fresh-seed validation screen. It is not a confirmatory robustness claim.

## How the run was done

| Item | Detail |
|---|---|
| Authorization | Owner, 2026-11-18 ("Run H-E1 test"). Code and protocol committed at `fcd9b8834` before the run |
| Disclosed peek | One smoke-test pool (Mlo burst 00) before the commit; nothing changed afterwards |
| Command | `python he1.py run --workers 8`: 192/192 write-once pool records, 130 s wall time |
| Data | No sampling. Existing mismatch Phase A pools, plus Phase B2 matched-model development pools as the control |
| Identity check | Arm N reproduced every recorded Phase A selection (class and Δ) for Mlo, Mhi and Mz |
| Analysis | `python he1.py analyze`, run twice; `HE1.json` byte-identical |

## Results

Arm N is Phase C unchanged. Arm R is re-based on p̂. Every burst-pool count is out of 24, and so is every burst-free count.

| Condition | True model | p̂ (mean ± SD) | N: class correct | R: class correct | R: learned correct (class + flip) | N: false accepts | R: false accepts | R: max burst-free Δ (τ = 1,561) | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Mlo | p = 0.0025 | 0.002525 ± 0.000030 | 0 | **24** | **24** | 0 | 0 | 645 | **PASS** |
| Mhi | p = 0.0035 | 0.003532 ± 0.000043 | 24 | **24** | **24** | **24** | **0** | 403 | **PASS** |
| Mz | p = 0.003, Z-bias 10 | 0.00225 ± 0.00018 (balanced proxy) | 0 | **0** | 0 | 0 | 0 | 0 | **FAIL** |
| CTRL (matched) | p = 0.003 | 0.003025 ± 0.000035 | 24 | 24 | 24 | 0 | 0 | 362 (N: 1,544) | **CONTROL_OK** |

## Interpretation

1. **A global background mis-scale is separable from a local burst and correctable from detector data alone.**
   - The robust p̂ is within about 1% of the true p.
   - It is slightly high in burst pools, because the burst adds detection events that the trim does not fully remove.
   - With the base re-fitted:
     - Mlo goes from 0/24 to 24/24 learned;
     - Mhi goes from 24/24 false accepts to 0/24, and still learns 24/24.
   - This confirms the Phase A mechanism (a uniform residual offset) and removes the "exactly known base p" caveat for scalar p errors of ±17%.
2. **The matched-model control improved its safety margin.** The largest burst-free Δ fell from 1,544 (just under τ = 1,561) to 362. The nominal arm's near-threshold control pool was itself partly a background-fluctuation effect. Absorbing that fluctuation into p̂ also reduces false-accept risk when the model is correct.
3. **Bias is not a scale error.**
   - Under Z-bias the detector-rate pattern changes shape, not just level, so a single balanced p̂ cannot remove the residual structure.
   - Δ stays at 0 in every pool: after re-basing, the fitted burst coefficient β is still ≥ 0 for every class.
   - p̂ is also 5× noisier than under the scale mismatches, consistent with model misspecification.
   - **A bias-aware base model is needed:** at least a two-parameter (p, bias) fit, or per-detector-class scales mapped to error types (`ADAPTIVE_ARCHITECTURE.md`, identifiability limit 3).
   - A practical safeguard is to flag misspecification (p̂ variance, or a residual deviance test) and fall back.

## What this does and does not establish

- **Established (development):** the learner component is robust to ±17% uniform background error, at d=5, with the known burst, from 12,000 unlabeled rows per pool.
- **Not established:**
  - **end-to-end decoding** under mismatch with the re-based model, where the decoders also use p̂;
  - **fresh seeds**;
  - **other burst supports**;
  - **non-uniform drift**;
  - **any form of bias**.

## Next steps (each needs an owner OK)

1. **H-E1b, bias-aware re-basing.** Fit (p, bias) on the same Mz development pools. A two-dimensional grid over `CodeSpec(regime="z_biased", bias_ratio=b)`, matched on per-class detector rates. Development only, about 5 min.
2. **End-to-end decode check.** Decode the Phase A decode-root design with the re-based model for both the learner and the decoders (L2L, Astar) on the Mlo and Mhi conditions. This needs **new development samples**, because Phase A's decode-root arrays were not saved. The cost is small: about 54k shots.
3. **Fresh-seed validation screen** of the robust learner across the benchmark's mismatch conditions, before any freeze.
