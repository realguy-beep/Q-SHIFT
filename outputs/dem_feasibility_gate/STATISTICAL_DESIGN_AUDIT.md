# Statistical design audit of the proposed interaction G

## Coefficients and signs

Use the fixed stratum order:

| s | Condition | Same-name group? | cₛ in I |
|---:|---|---|---:|
| 0 | X-memory / X-biased | yes | +1/2 |
| 1 | X-memory / balanced | no | −1/4 |
| 2 | X-memory / Z-biased | no | −1/4 |
| 3 | Z-memory / X-biased | no | −1/4 |
| 4 | Z-memory / balanced | no | −1/4 |
| 5 | Z-memory / Z-biased | yes | +1/2 |

The coefficients sum to zero. For DEM family m, let `δₛ,m = LERₛ,m(on) − LERₛ,m(off)`, so positive δ means correlated matching is worse. Then `Iₘ = Σₛ cₛ δₛ,m` is the mean δ in the two same-name cells minus the mean δ in the other four. The proposed `G = I_A − I_B` has the correct sign: positive G means the contrast is larger under approximate family A than under B. This is an exploratory/post-pilot interaction, not a new discovery protected from selection.

## Correct paired root-level contrast

For each condition/root, both DEM families must decode the **same** test detector shots and observable labels. Define shot residuals `eₛ,r,m,k,on/off = 1[prediction ≠ observable]`, then:

```text
δₛ,r,m = mean_k(eₛ,r,m,k,on − eₛ,r,m,k,off)
gₛ,r   = δₛ,r,A − δₛ,r,B
G_hat  = Σₛ cₛ mean_r(gₛ,r)
```

This preserves pairing first within each on/off decoder comparison, then across DEM families. The root cluster—not each shot—is the independent sampling unit for the planned seed-level inference. Do not subtract independently computed arm CIs or pair roots across different strata. Resampling must draw root indices independently within each stratum, and reuse each selected index jointly for A/B and off/on.

The pooled index is selected from separate calibration data. A test interval conditional on those frozen model indices does not include calibration-selection uncertainty. If the intended claim is about the full calibration-and-decoding procedure over new calibration runs, calibration roots must also be replicated/resampled as an outer level.

## Sign-flip test assessment

The proposed 100,000-assignment root sign-flip is **not an exact randomization test**. No decoder assignment was randomized; each root is evaluated by both deterministic decoder policies. A sign-flip test on `gₛ,r` needs a symmetry/exchangeability assumption for the root-level contrasts (typically a sharp zero/symmetric null within the fixed strata). The scalar null `G=0` alone permits nonzero stratum effects that cancel under the cₛ weights, so independently flipping every `gₛ,r` generally tests a stronger null than the stated interaction null. Add-one Monte Carlo correction does not fix this assumption.

### Recommended primary inference if a valid B model becomes available

Use a heteroskedastic root-level Welch–Satterthwaite contrast. Let `s²ₛ` be the sample variance of the paired root contrasts `gₛ,r`, and `nₛ` the number of independent roots:

```text
V_hat = Σₛ cₛ² s²ₛ / nₛ
t     = G_hat / sqrt(V_hat)
df    = V_hat² / Σₛ[(cₛ² s²ₛ / nₛ)² / (nₛ − 1)]
```

Report a two-sided t p-value and a 95% interval using this same standard error and Satterthwaite degrees of freedom. Assumptions: independent root clusters within/across the six fixed strata, finite variances, and adequate approximation of the root-mean contrast by a t distribution. With many roots this is more defensible than an unqualified sign-flip. Use a paired, stratum-resampled studentized cluster bootstrap as a predeclared robustness analysis. A root sign-flip may be reported only as a sensitivity analysis with its symmetry assumption stated.

## Power arithmetic and its limits

The prior protocol's variance coefficient `9.776×10⁻⁸` for one family's I is derived from only 12 roots/cell in the approximate-DEM pilot. It is not observed variance for G because no B DEM could be constructed. It also treats the three-model calibration choice as fixed and omits its sampling uncertainty.

If both family-specific I variances equaled this coefficient per root count and covariance were zero, then `Var(G)` would be `2×9.776×10⁻⁸/n`; at n=60, SE≈0.0000571. This generated the previous approximate 94% power for a 0.0002 effect under a normal approximation. But the covariance is **unknown**. If equal family variances had correlation −1, `Var(G)` could be as large as `4×9.776×10⁻⁸/n`; at n=60, SE≈0.0000807 and power for 0.0002 is only about 70%. Under that equal-variance worst-covariance illustration, roughly 103 roots/cell are needed for 90% normal-approximation power; 120 would give margin, but this is not a valid final size because B variance is unknown and 12 pilot roots estimate variance poorly. Positive covariance could reduce variance; larger B variance could increase it.

Therefore the existing 60-root/stratum calculation is a provisional sensitivity calculation, not a reliable power guarantee. If feasibility is restored, estimate paired `gₛ,r` variability on independent calibration/validation streams, freeze the sample size using a prespecified upper variance bound, and do so before any final test labels are accessed. Preserve the 0.0002 practical interaction margin unless the research question is prospectively changed and justified.

## Multiplicity

Keep G as the sole primary interaction test. Treat `I_A`, `I_B`, and per-stratum δ estimates as descriptive with intervals. The six per-stratum A-minus-B contrasts may form one predeclared secondary family with Holm adjustment. Do not promote the same-name subgroup result from the old pilot to a confirmatory claim; it was selected after examining those six conditions.
