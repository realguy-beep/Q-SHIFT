# Phase 2C — Joint estimator design review

**Status:** deterministic population analysis only. No experiment or sampling is authorized. Reviewed Phase 2B commit: `7597510a41be09b6b9c727e7ae6091627011424f`.

## Question and common input

Can the existing 45 detector-only features jointly estimate burst probability `p_b` and measurement-flip probability `p_m` under the current distance-3, five-round rotated Z-memory model? The feature vector is 40 detector bits plus conjunctions `(D8,D10)`, `(D16,D18)`, `(D24,D26)`, `(D32,D34)`, `(D36,D38)`. Every candidate uses only its population mean vector, the same feature order, and the parameter rectangle `p_b∈[0,.020]`, `p_m∈[0,.010]`. No logical observable or label is an estimator input.

Two truth/template regimes are kept distinct:

1. **Exact categorical circuit:** expected features are evaluated under the original independent locations with mutually exclusive Pauli alternatives and independent burst/readout Bernoulli events, using deterministic single-fault masks and exact parity algebra.
2. **Approximate DEM:** templates and their moments are evaluated under Stim's independent error mechanisms from `decompose_errors=True, approximate_disjoint_errors=True`. They are exact for that emitted approximate DEM, not for the original circuit.

Most population comparisons use exact categorical circuit truth, then fit both exact-circuit and DEM templates. This is a deliberate misspecified-template comparison; it does not imply a deployed estimator knows the exact truth model.

## Candidate objectives

All feature scales for diagonal objectives use the existing estimator's population-limit construction at the five burst knots `{0,.005,.010,.015,.020}`, fixed `p_m=.003`: pooled within-feature Bernoulli variance plus between-knot mean variance, floor variance at `1e-6`, then take the square root. Templates are bilinearly interpolated on `p_b` and `p_m` nodes spaced .001. The fitting search uses a .0001 grid, clipped to the declared rectangle; ties choose lower `p_b`, then lower `p_m`.

**A. Existing one-parameter profile.** Fix `p_m=.003`; linearly interpolate the original five burst knots and minimize the mean of 45 squared residuals divided by the squared feature scales. This is the actual `DetectorProfileEstimator` population objective, with the population-limit scales substituted for finite calibration estimates.

**B. Joint standardized distance.** Minimize `Q_B(θ) = (μ̂−g(θ))ᵀ diag(s⁻²)(μ̂−g(θ))`, `θ=(p_b,p_m)`, over the rectangle. This uses the same interpretable diagonal weights as A while freeing measurement probability. It is the preferred simple joint candidate for a later methods study.

**C. Joint generalized least squares.** Minimize `Q_C(θ) = (μ̂−g(θ))ᵀ W (μ̂−g(θ))`. Freeze `W=(Σ_ref+λI)⁻¹` from the feature covariance at `(p_b,p_m)=(.010,.003)`, using the same model family as the templates and `λ=10⁻⁶ λ_max(Σ_ref)`. Covariance is per shot. At the reference its 45 eigenvalues are positive, condition number about **26.74**, and the ridge floor `7.83×10⁻⁸` is below the minimum eigenvalue **.00293**, so the ridge is inactive here. A real finite calibration covariance can be noisy or singular; recompute/freeze regularization from development data before any study and report sensitivity to the floor. Do not use the evaluation mean to update W.

**D. Detector-only model-mismatch diagnostic and conservative fallback.** Under the null profile `p_m=.003`, fit the nuisance burst parameter by minimizing the fixed-reference GLS objective, then compute the minimized 45-feature residual statistic `T=n rᵀΣ_ref⁻¹r`. Under a correct model, fixed known covariance, independent shots and an interior regular one-parameter fit, the asymptotic reference is approximately chi-square with 44 residual degrees of freedom. A provisional 99% threshold is `χ²_(44,.99)=68.71`. If triggered, do not attribute the feature change to burst probability; raise a mismatch alarm and retain the last accepted decoder setting. This guard does not itself estimate the cause or new measurement probability. Its calibration is approximate and is not yet adequate for deployment or a development-study protocol.

## Deterministic population comparison

At nominal `(.008,.003)`, A, B and C all recover `(.008,.003)` on the search grid under exact templates. DEM templates return the same grid point; their minimum standardized score is `1.42×10⁻⁸`, rather than zero, because of the DEM moment approximation.

At exact circuit truth `(.008,.006)`, A estimates burst `.0109` with fixed measurement `.003` (bias `+.0029`, approximately 36% of true burst p); B and C recover `(.008,.006)` with exact templates and with DEM templates at this grid resolution. For fixed burst `.008`, A returns `.0051` when actual `p_m=0`, and `.0148` (`.0149` with DEM templates) when actual `p_m=.010`. The joint candidates recover their tested boundary values. These are deterministic mean fits, not estimates from finite detector histories.

## Decision and scope

Local full-rank evidence supports trying a joint estimator in a separately designed study. It does not establish global identification, finite-sample accuracy, causal tracking under drift, improved graph selection, or lower logical error. Candidate B is simpler and should be the primary experimental candidate; C is a secondary comparison only if finite-sample covariance estimation and regularization are fully prespecified. Candidate D should initially be a fail-safe guard, not a source of automated physical attribution.

The conservative proposed architecture and required owner decisions are in `DEVELOPMENT_PROTOCOL_PROPOSAL.md`. No estimator is yet sufficiently specified, including finite-history alarm calibration and causal update rules, to justify requesting a bounded study without those decisions. No sampling authorization is implied.
