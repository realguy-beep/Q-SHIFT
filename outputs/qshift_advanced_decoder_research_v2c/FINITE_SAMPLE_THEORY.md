# Finite detector-history implications

## What the deterministic covariance says

For a single shot let `F∈{0,1}^45` be the fixed feature vector, with exact mean `μ(θ)` and covariance `Σ(θ)` under the exact categorical circuit. For `N` independent, identically distributed shots, `Cov(F̄)=Σ/N` exactly. Phase 2B computes this covariance from parity moments; this is a model-based sampling covariance, not a claim that a finite empirical estimator has been tested.

For a smooth objective with fixed weight matrix `W`, local linearization of a correctly specified joint weighted fit gives the sandwich approximation

`Cov(θ̂) ≈ (1/N) (JᵀWJ)⁻¹ JᵀWΣWJ (JᵀWJ)⁻¹`,

where `J=∂μ/∂θ` at the true point. If `W=Σ⁻¹` were known at truth, this simplifies to `(JᵀΣ⁻¹J)⁻¹/N`. Candidate C instead uses fixed reference covariance at `(.010,.003)`; its reported values use the full sandwich, not the idealized equality. Candidate B uses `W=diag(s⁻²)`. Candidate A is the scalar version with `p_m` fixed. The reported numbers are local asymptotic sensitivities only.

At nominal `(.008,.003)`, `N·Var(p̂_b)` is **.0022688** for A. For B the diagonal coefficients are **.002182** (burst) and **.0002757** (measurement); for C they are **.001804** and **.0002336**. Thus at `N=1,000`, local standard errors are A burst **.001506**; B burst/measurement **.001477/.000525**; C **.001343/.000483**. At `N=10,000`, each is smaller by `√10`. The burst uncertainty at 1,000 is about 18% of `.008`; none of these calculations include model mismatch bias, calibration error, or temporal dependence.

## Why this is not finite-sample estimator accuracy

The delta method assumes the feature mean is near its expectation, the objective is locally quadratic, the minimum is interior, and the template/scale/covariance bundle is fixed and correct. It does not describe boundary clipping, discrete grid selection, multimodal objectives, rare-event/skew effects, finite template estimation, covariance regularization uncertainty, or any temporal autocorrelation. At `p_b=0` or `.020`, ordinary symmetric standard errors are especially inappropriate because estimates are constrained. A finite sample may also yield an estimated feature mean outside the model surface, making a diagnostic fire even when the physical parameter is stationary.

For a stationary sequence with lag covariance matrices `Γ_h=Cov(F_t,F_{t+h})`,

`Cov(F̄_N) = N⁻¹ [Γ_0 + Σ_{h=1}^{N−1}(1−h/N)(Γ_h+Γ_hᵀ)]`.

The current circuit builder specifies independent per-shot noise, but Phase 2C does not model drift within a history, repeated calibration-root effects, correlated readout, or other temporal dependence. Under drift, the history mean may not correspond to any single parameter pair; increasing `N` can then increase lag while increasing bias. No independent-shot formula resolves that issue.

## Calibration and history allocation

The `DetectorProfileEstimator.fit` method estimates means and scales from finite labeled development batches; its `estimate` consumes detector matrices only. Our population calculation substitutes exact template means and population-limit scales. Future implementation will add uncertainty in those templates, and reuse of one shared calibration bundle couples arms and controller windows. That variation is absent from `Σ/N`.

Longer histories reduce independent-shot variance approximately as `1/N`, but increase adaptation latency and mix more pre-change observations into the estimate. Shorter windows increase variance and alarm jitter. No optimal window length follows from the population map. A future development protocol must fix window size, update-block chronology, calibration/template split, minimum history, and how a change resets or weights prior observations before data acquisition.

## Prespecified development diagnostics, not pass criteria

If later authorized, report empirical bias and RMSE by parameter and scenario, boundary-hit fractions, convergence/tie rates, objective gaps versus parameter distance, and intervals calibrated at the independent stream/root level. Compare observed variability with these local analytical coefficients only as a diagnostic. Do not call agreement a power or coverage validation, and do not infer finite-sample decoder benefit from parameter-estimation variance.
