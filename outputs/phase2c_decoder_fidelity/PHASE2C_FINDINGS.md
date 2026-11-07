# Q-SHIFT Phase 2C — Findings and Research Decision

## Result in brief

This exploratory pilot did **not** show that a more channel-faithful decoder improves error correction or makes decoder selection regime-dependent. It did show that a decoder trained directly from the actual categorical Stim channel can produce materially different predictions from the Phase 2B DEM/PyMatching bank. That reference surrogate performed worse, so the experiment cannot attribute the Phase 2B result specifically to DEM approximation error.

## Evidence

We evaluated 120,000 paired held-out samples: 20,000 per memory-basis/regime cell, with four independent 5,000-shot roots per cell. The same detector arrays and logical labels were scored by all candidates. Every stored prediction was independently recomputed and matched exactly.

| Policy | Errors / shots | LER |
|---|---:|---:|
| Phase 2B regime-matched PyMatching | 628 / 120,000 | 0.5233% |
| Phase 2B balanced fixed PyMatching | 683 / 120,000 | 0.5692% |
| Calibration-selected fixed reference forest | 2,579 / 120,000 | 2.1492% |
| Calibration-selected regime-informed reference forest | 2,579 / 120,000 | 2.1492% |

The reference regime-informed minus fixed-reference endpoint was 0.0000 percentage points: the independent calibration selected the same model for every generating regime within each memory basis (Z-memory chose X-trained candidate 0; X-memory chose Z-trained candidate 2). Their held-out predictions were identical, so the paired difference, 95% root-stratified bootstrap interval, and paired sign-flip test were all 0, [0,0], and p=1. This is no evidence of regime-specific utility in the calibrated reference bank.

| Memory | Generating composition | Matched Phase 2B errors | Selected reference errors | Reference-only / matching-only failures |
|---|---|---:|---:|---:|
| Z | X-biased | 167 | 540 | 444 / 71 |
| Z | Balanced | 143 | 456 | 396 / 83 |
| Z | Z-biased | 31 | 163 | 151 / 19 |
| X | X-biased | 21 | 183 | 175 / 13 |
| X | Balanced | 109 | 512 | 459 / 56 |
| X | Z-biased | 157 | 725 | 639 / 71 |

Compared with regime-matched PyMatching, the regime-informed reference produced 2,579 errors versus 628. Paired discordances were 2,264 reference-only errors and 313 PyMatching-only errors (2,577 disagreements); exact shot-level McNemar p = `7.738855561415×10^-364` (the equivalent float underflows). This paired shot test is descriptive and is not a seed-cluster confirmatory inference. The fixed-reference-versus-balanced-PyMatching contrast was 2,579 versus 683, with 2,254 versus 358 discordant errors (exact p = `5.336687518421×10^-335`).

All six reference candidates and all six matching candidates are tabulated by cell in `PILOT_RESULTS.csv`. Pairwise prediction disagreements range from 0.08% to 0.46% within the three Phase 2B matching models, 0.185% to 3.58% within the three reference forests, and 0.85% to 6.18% across matching/reference pairs. The nontrivial cross-family disagreements establish that the approximate DEM and sample-trained surrogate do not always choose the same logical correction; the error counts show that disagreement alone is not improvement.

## Answers to the research questions

1. **Does approximation change predictions?** Yes. Cross-family disagreement reached 6.18%, and the paired selected-reference comparison disagreed on 2,577 of 120,000 shots.
2. **Does the more faithful reference improve correction?** No. Its calibration-selected LER was about 4.1× the regime-matched PyMatching LER in this pilot.
3. **Does selection become regime-dependent?** No. Calibration chose one reference candidate per memory basis, unchanged across all three generating compositions.
4. **Is a new held-out experiment justified?** No. The reference is currently weaker and its probability estimates have visible calibration error. Improve and validate the likelihood estimator on development data first.
5. **Is the adaptive hypothesis settled?** No. This study tests a sample-trained posterior surrogate, not an exact channel likelihood solver. It cannot show that the DEM approximation is harmless or that an exact decoder would fail to specialize. The research hypothesis should be narrowed to “a decoder must be both channel-faithful and demonstrably stronger before adaptation is tested.”

## Decision

Do not run a larger confirmatory or adaptive experiment from this pilot. Retain the general question as open, but do not claim that DEM fidelity is the observed limiting factor. The immediate weakness is the reference estimator's generalization/probability calibration and its inferior logical decisions. Candidate development work could test a circuit-factor-graph likelihood method or improve probability calibration using only new development streams, with a development-only gate requiring performance at least as good as matched PyMatching before proposing a fresh held-out study.

## Limits

Only four roots per cell were run; the work is a bounded simulation pilot. Posterior proper scores do not provide a true full-circuit posterior approximation bound. Regime-informed selection uses known simulated regime labels and is a diagnostic, not a deployable decoder. The custom categorical channel is itself represented exactly by Stim sampling, but Phase 2B's decoder graph uses `approximate_disjoint_errors=True`. No hardware data or hardware integration are involved.

The initial pre-pilot inventory omitted six sklearn forest `random_state` values derived from development seeds. A supplemental audit found no collisions, and these values did not generate circuit samples; the omission is documented in `SEED_COLLISION_AUDIT.md` and `AUXILIARY_RNG_AUDIT.json`.
