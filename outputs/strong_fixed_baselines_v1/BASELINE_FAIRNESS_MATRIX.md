# Baseline fairness matrix — v1

| Arm | Model information | Runtime/test input | Training or calibration information | Status |
|---|---|---|---|---|
| Nominal fixed PyMatching | p=0 DEM | Same evaluation detectors as every arm | Frozen physical-noise assumptions; no test-time calibration | Deployable fixed reference |
| Pooled detector-calibrated static | One p estimate from pooled final calibration detector rows | One matcher reused for every evaluation condition | Same total 1.2M calibration detector shots available to adaptive, pooled once; no labels/condition tags enter estimator | Deployable after an offline calibration period; mixture-sensitive |
| Safety-constrained optimized static | One p selected from fixed grid | One matcher reused for every evaluation condition | Selection/validation development labels allowed; separate from final development evaluation | Strong offline fixed comparator; selection budget disclosed |
| Q-SHIFT profile adaptive | Per-root p̂ from profile-marginal discrepancy | One matcher per root, selected from that root's prior calibration batch; same eval arrays | Independent profile templates plus 2,000 calibration detector shots per final root | Deployable under the tested calibration protocol |
| Privileged true-p reference | Generating p | Same evaluation detector arrays | Hidden p used only to build this reference and for offline stratification | Nondeployable diagnostic; not an optimal-decoder bound |

All arms see the exact same evaluation detector rows and observable labels are read only for post-prediction scoring. The final pooled static arm and adaptive arm share the same calibration samples: pooled static uses them collectively; adaptive estimates each root separately. Thus total shot budget is matched, while information aggregation is deliberately different. The safety-optimized static arm has an additional, explicitly reported development-label selection budget; this makes it a strong fixed reference rather than a runtime-matched online method.

The oracle and the detector-only arms are not given equivalent runtime information; the oracle is not used for deployment claims. No candidate is described as “strongest possible.” The fixed grid is finite, and this study cannot rule out better static priors or decoder families.
