# Independent Stage 5 Statistical and Power Review

## Evidence read

This review reads the prospective Stage 5 candidate protocol/configuration and the available development per-root summaries in `outputs/stage4_noise_adaptive_development_v1/PAIRED_COMPARISONS.csv` and `outputs/stage4c_cnn_noise_estimation_v1/STAGE4C_PER_ROOT.csv`. No Stage 5 or sealed-test sample was opened.

## Estimand and inferential unit

The primary estimand is the equal-weight mean of the four nonzero burst-probability strata of the within-root (profile-adaptive minus fixed nominal) logical-error-rate difference. Each root has 2,500 paired evaluation shots; each condition contributes 100 independent roots. Resampling/sign-flipping roots preserves the within-root pairing and does not pretend the 2,500 shots within a root are independent inferential units.

The point estimate and root-stratified percentile bootstrap CI are well-defined for this estimand. The bootstrap resamples roots independently within each probability, preserving the fixed equal-stratum target. It is not a shot bootstrap. The zero-burst one-sided bound is a separate no-harm check.

## Root sign-flip assumption

The sign-flip procedure is **not** a randomized-treatment test: the two decoder arms are deterministic and were not randomly assigned. It is exact only under the null that independent root-level paired effects are sign-symmetric about zero (or under a suitable exchangeability argument). If root effects have skewness, a point mass at zero, or asymmetric tails, its finite-sample type-I error is not guaranteed. The plus-one Monte Carlo correction and “ties count extreme” rule are correctly conservative for Monte Carlo enumeration, but they do not repair a failed symmetry assumption.

At 100 roots per stratum, the mean's normal approximation may be useful, but it does not make the sign-flip test exact. Report the sign-flip p-value as conditional on sign symmetry; interpret the bootstrap CI and the frozen conjunction gate alongside it. A separate reviewer should approve this inferential framing before samples are authorized. This implementation does not silently replace the frozen test.

## Confidence intervals and multiplicity

The primary 95% percentile CI uses 20,000 stratified root bootstrap replicates. Stage 5 v2 makes the previously implicit random-stream order explicit: one PCG64 generator with seed `4240001001`; draw `(20,000,100)` root indices for p=.004, then .008, .012, .016, combine the four bootstrap means with equal weights, then draw `(20,000,100)` indices for p=0 and use its 95th percentile as the one-sided upper harm bound. This is a prospective computational clarification, not a change to the estimand.

The four nonzero condition sign-flip p-values form one secondary family and are Holm-adjusted. Holm controls familywise error under arbitrary dependence if each raw test is valid. The primary endpoint is separate and predeclared. The success gate requires all four condition point estimates to be favorable, but does not require all four Holm-adjusted tests to be significant; therefore condition-level superiority claims must not be inferred from the gate alone.

The sign-flip RNG is PCG64 seed `4240001002`, with 100,000 assignments for primary first, then each condition ascending. Each assignment flips every root independently within its condition; the equal-condition primary statistic equals the mean over all 400 nonzero-condition root effects because the strata have equal sizes. Count absolute-statistic ties as extreme and use `(extreme+1)/(assignments+1)`.

## Independent power-input recomputation

The values in the prior candidate protocol are the maximum sample SD by condition between (i) Stage 4 development profile-minus-fixed root LERs and (ii) Stage 4C profile-minus-fixed root LERs:

| Burst probability | Stage 4 development SD | Stage 4C SD | Conservative SD used |
|---:|---:|---:|---:|
| .004 | 0.0008141604 | 0.0004535574 | 0.0008141604 |
| .008 | 0.0007904188 | 0.0009641182 | 0.0009641182 |
| .012 | 0.0010327956 | 0.0010690449 | 0.0010690449 |
| .016 | 0.0011313708 | 0.0019692880 | 0.0019692880 |

The SDs were recalculated from 7 per-root differences in each development condition. The implied SE of the equal-stratum mean at 100 roots/condition is `sqrt(sum(sd_i^2)/4^2/100) = 0.00006429`, which verifies the candidate's rounded `0.0000643`.

Under a Gaussian root-effect planning approximation, a true effect of −0.0002 gives about 87.5% probability of a two-sided 5% test rejecting zero. However, the frozen point-estimate gate `estimate <= −0.0002` has exactly 50% probability at an alternative equal to its boundary; thus the conjunction gate cannot have 87.5% power at that boundary and is at most 50% before the favorable-strata requirement. A planning alternative of −0.0005 clears the point threshold by about 4.67 aggregate SEs, but this relies on SDs estimated from only seven roots and assumes independent roots, stable variance, approximately symmetric effects, and no material calibration/evaluation-root dependence.

The planning SD does not explicitly account for the extra binomial Monte Carlo variation from 2,500 shots per root; the observed root-level SDs already include that variation, but transfer from 7-root development cells to the new allocation is uncertain. No formal power guarantee follows. The p=0 no-harm bound is also sensitive to its true root-level variability; prior zero-burst candidate/fixed predictions were mostly identical, but Stage 5 p=0 calibration may still yield nonzero decoder differences.

## Conclusion

The proposed 2.25-million-shot allocation is numerically correct and computationally plausible within the 2.5-million shot cap. The stated power summary is accurate for the primary null-rejection component but overstates what can be inferred about power for the complete conjunction gate unless that distinction is kept explicit. Root sign symmetry is a substantive assumption, not a randomization guarantee. These issues are recorded as **pre-sampling review conditions**; no Stage 5 data have been generated.
