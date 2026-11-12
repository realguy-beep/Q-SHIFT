# Deterministic population comparison

## Setup

Reproduce with `python outputs/qshift_advanced_decoder_research_v2c/joint_estimator_comparison.py`. Stim 1.16.0. It reuses deterministic `p=1` fault signatures from the Phase 2B algebra, computes exact feature expectations, builds the corresponding approximate DEM at the declared parameter nodes, and fits the same 45-feature input. There is no sampler, random-number generator, logical label, decoder, or training step. Exact circuit and DEM data/template sources remain explicitly labeled in results.

Template lattice: `p_b=0:.001:.020`, `p_m=0:.001:.010`; fitting search step `.0001`. Interpolation accuracy was checked at 200 half-cell points. The test scenarios include nominal, measurement mismatch, each parameter edge, and two corners. The fine estimation grid and model-generated templates make this a deterministic algebra check, not an independent sample or out-of-model validation.

## Main estimates (exact categorical truth)

| Population truth `(p_b,p_m)` | A fixed `p_m=.003` | B joint diagonal | C joint GLS |
|---|---|---|---|
| `(.008,.003)` | `(.008,.003)` | `(.008,.003)` | `(.008,.003)` |
| `(.008,.006)` | `(.0109,.003)` | `(.008,.006)` | `(.008,.006)` |
| `(.008,0)` | `(.0051,.003)` | `(.008,0)` | `(.008,0)` |
| `(.008,.010)` | `(.0148,.003)` | `(.008,.010)` | `(.008,.010)` |

Replacing exact templates with approximate-DEM templates gave the same four grid estimates except the high-measurement A estimate was `.0149`. At nominal, the DEM-template mean objective is nonzero (`1.42×10⁻⁸` under diagonal scaling) due to the circuit/DEM difference. At mismatch, the A score is `.0012135` with exact templates (`.0012206` with DEM templates), while B/C fit their matching joint means near zero; this comparison must not be read as a finite-data model-selection guarantee.

## Identifiability, aliases and boundaries

On 231 nodes across the rectangle, the bilinearly interpolated exact-circuit template surface had rank 2 everywhere; minimum smaller singular value **3.14186** and maximum raw condition **4.21821**. For the bilinear DEM template surface: minimum smaller singular value **3.14202**, maximum condition **4.21817**. The lowest singular value and highest condition occurred at `(0,.010)`. This is a finite-grid interpolant check, not an exact derivative at every point. Phase 2B separately reported direct finite-difference rank checks at nominal, mismatch and boundaries. Neither result proves full rank at every continuum point or global injectivity.

Phase 2B's 44-point exact mean collision screen found no duplicate full mean vectors at tolerance `1e-12`. Its nearest pair changing both parameters was `(.018,.006)` versus `(.020,.003)`, standardized RMS distance **.03495**. This grid is coarse and is not a global collision proof. Local runner-up objective gaps on the `.0001` fit lattice are small (for B at mismatch, `1.59×10⁻⁷`); such gaps are expected between neighboring parameter values and depend on grid resolution. They are not evidence of a second distant optimum. Conversely, a grid optimizer can conceal narrow minima, so a future implementation needs continuous/local-refinement checks and explicit edge diagnostics.

A clips estimates to bounds: at true burst p beyond the allowed rectangle or measurement p outside `[0,.010]`, bias is unavoidable and estimates can stick at an edge. Within the tested rectangle the two joint fits returned each tested edge/corner exactly when truth matched a template node. This does not test noisy boundary pile-up.

## Circuit/DEM discrepancy and interpolation

Across 231 matching parameter nodes, maximum absolute feature-mean gap was **3.3116×10⁻⁵**, RMS over node-features **2.1169×10⁻⁵**. At nominal `(p_b=.008,p_m=.003)`: max **3.2720×10⁻⁵**, RMS **2.1360×10⁻⁵**. At mismatch `(.008,.006)`: max **3.2326×10⁻⁵**, RMS **2.1100×10⁻⁵**. The DEM is exact only for Stim's emitted independent-error approximation. A practical estimator trained from DEM templates sees this approximation; it cannot claim exact categorical-circuit moments.

Bilinear interpolation on `.001` nodes, checked at 200 half-cell points, had maximum absolute error **4.870×10⁻⁶** and maximum per-vector feature RMS **1.284×10⁻⁶** for exact circuit; DEM values were nearly identical. This is deterministic interpolation error only. The `.0001` optimizer grid further quantizes the output; smooth local minima, finite template sampling error, numerical precision, and unmodeled mechanisms are not covered by this check.

## Objective degeneracy and overfitting risk

For correctly specified population means, all objectives attain the true parameter by construction. This is a tautological recovery check, not evidence that an empirical estimator will recover it. The mismatch test shows the value of freeing `p_m`; it does not establish that those two physical rates remain separable with finite histories, under temporal drift, or after expanding nuisance channels. Searching 20,301 grid points can itself select noise in empirical data. Any later study must freeze a coarser candidate grid / interpolation scheme, tie-break, boundary reporting, and data separation before acquisition; do not repeatedly refine the grid against evaluation streams.

## Covariance weighting

At nominal truth, the local delta-method covariance coefficients `N·Cov(θ̂)` were:

| Method | Burst variance coefficient | Measurement variance coefficient | Correlation coefficient |
|---|---:|---:|---:|
| B, diagonal standardized joint fit | .002182 | .0002757 | −.00008790 |
| C, fixed-reference GLS | .001804 | .0002336 | −.00001657 |

In this local, correctly specified, known-covariance calculation, C reduces the marginal variance coefficients by about **17.3%** for burst and **15.3%** for measurement relative to B. At `N=1,000`, the corresponding delta-method standard errors are approximately B `.001477/.000525` and C `.001343/.000483` for burst/measurement. At `N=10,000`, divide those by `√10`. These are asymptotic linearization calculations, not finite-sample estimator accuracy or coverage. C's possible gain comes with covariance-model dependence, a fixed reference, matrix conditioning and regularization choices; covariance weighting is not justified as primary until an independently implemented finite-history study demonstrates stable benefit. Prefer B for interpretability.
