# Phase 2C-R1 — Candidate D statistical correction

**Review checkpoint:** `a5e6a86b24affc355169dbbf188e3ee1e247b1e7`, branch `qshift-advanced-research`. **No experiment or sampling is authorized.** This is a narrowly scoped correction package; the published Phase 2C package is preserved unchanged.

## Correction

Phase 2C's Candidate D output called `N rᵀΣ_ref⁻¹r` a population noncentrality approximation, then compared it to the central `χ²_(44,.99)` cutoff in a `would_flag_at_provisional_threshold` field. That comparison was not a realized test decision and did not establish rejection probability. This review removes that decision framing from the corrected calculation. The historical Phase 2C JSON still contains the old field for provenance; do not interpret it as a simulated or observed alarm.

The corrected outputs distinguish:

- **Population residual energy per shot:** `q=rᵀW r`, a deterministic squared distance of the expected feature mean from the fitted fixed-measurement profile.
- **Population residual energy at N shots:** `Nq`. It is only the mean displacement contribution to a quadratic statistic. It is not a random statistic and is not itself a noncentrality unless the relevant covariance and projection assumptions hold.
- **Realized statistic:** `T=N(F̄−g(p̂_b,.003))ᵀW(F̄−g(p̂_b,.003))`, which depends on an unobserved finite detector history. No realized statistic was generated in this audit.
- **Central-null cutoff:** the 99th percentile is **68.7095** for `χ²_44` under a continuous, regular one-parameter fit with correct whitened covariance, versus **69.9568** for `χ²_45` if the parameter is fixed at a grid point and no continuous degree of freedom is removed. Neither is established as the actual finite-grid test cutoff.
- **Theoretical detection probability:** it requires the realized-statistic distribution under the alternative. It is not obtained by asking whether `Nq` is above or below a cutoff.

## Corrected assessment

Under the *counterfactual* assumptions of a continuous interior nuisance fit, identity covariance after whitening, Gaussian feature means, and the Phase 2C residual energy as a valid noncentrality, `ncx2.sf(χ²_(44,.99),44,λ)` gives a sensitivity calculation of about **.798** for N=1,000 and approximately **1.0** at N=10,000 for exact categorical truth `(.008,.006)` against the fixed `.003` measurement profile. The corresponding DEM-template sensitivity is about **.795** and approximately **1.0**. These are explicitly counterfactual model calculations, not alarm power or operating characteristics.

Those assumptions do not hold exactly for Candidate D as implemented. At the nominal null, the whitened projected truth covariance eigenvalues range **.811–1.002**, with mean **.983**. At measurement mismatch they range **.826–1.714**, mean **1.195**. Thus the statistic is generally a generalized quadratic form, not a central/noncentral chi-square with identity covariance. In addition, Phase 2C estimates burst p on a fixed `.0001` grid using interpolated templates. Its finite-sample estimator is discrete, with neighbor switching; the regular continuous nuisance-fit degrees-of-freedom argument is not an exact representation. At asymptotically very large N with a fixed grid, the fit can lock to a grid node and remove no smooth degree of freedom. At finite N, the distribution can be a mixture over selected grid points.

**Conclusion:** the actual size, power, and alarm operating characteristics of Candidate D are **undetermined**. The published `would_flag_at_provisional_threshold` values must not be used. No alarm/pass decision is inferred from the deterministic calculations.

## Other required review points

- Candidate A is the **population-limit counterpart** of the sampled `DetectorProfileEstimator`, not a sampled implementation. It uses population profile means/scales in place of finite calibration batches.
- Candidate A's Phase 2C comparison row did not exactly reproduce its source search: it used the joint-table `.001` interpolation nodes and `.0001` search increment, whereas `DetectorProfileEstimator` uses five burst knots `{0,.005,.010,.015,.020}` with linear interpolation and `GRID_STEP=.00001`. The mismatch estimates `.0109` and `.01091` were close, but the earlier row is now identified as an approximation. R1 recalculates a source-faithful population-limit A and preserves the published Phase 2C artifact unchanged.
- Candidate B remains the preferred simple primary estimator. Candidate C's covariance claims remain local, asymptotic sandwich calculations only.
- Gate noise was fixed at `.003` in Phase 2C. Deterministic variation of the *existing* balanced categorical gate rate shows a nuisance direction that can strongly shift the joint fit; details are in `MODEL_SENSITIVITY_REVIEW.md`.
- A joint parameter fit is not a decoder-performance result. No logical outcomes or decoder behavior were evaluated.

## Preservation and integrity

The new review directory includes the deterministic covariance audit code and results. It does not modify Phase 2C, Phase 1/2/2A/2B, V2.4, main, other branches, or PR #1. No sampler, stochastic experiment, training, protected evaluation data or new seed inventory was used. Source and file hashes, ancestry and privacy results will be recorded in `SOURCE_MANIFEST.json` and verified before publication.
