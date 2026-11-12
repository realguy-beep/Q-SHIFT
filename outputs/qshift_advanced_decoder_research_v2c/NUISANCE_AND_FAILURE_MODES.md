# Nuisance model and failure modes

## Parameters and assumptions

Do not collapse distinct physical or temporal quantities into one “noise level.”

| Quantity | Current role in model | Identified/varied in this audit? | Limitation |
|---|---|---|---|
| Burst probability `p_b` | Per-round probability of the existing `X8 X10` correlated event, independent at its five insertion locations | Jointly estimated with `p_m` in population fits | A changing average need not represent within-history drift; only this burst mechanism is modeled. |
| Measurement-flip probability `p_m` | Independent readout-flip probability at measurement targets | Jointly estimated in B/C; A fixes it at .003 | Correlated readout, target-specific readout rates and time-varying calibration are absent. |
| Gate-noise assumptions | Fixed balanced Phase 2B channels at gate p=.003, including mutually exclusive Pauli alternatives | Held fixed | Gate probability, Pauli bias and gate-specific inhomogeneity cannot be separated from detector features by this two-parameter fit. |
| Temporal drift | A sequence-level change in `p_b` and/or `p_m` | Not fit in the static population benchmark | A window estimate is a lagged mixture, not an instantaneous value. No trend model is claimed. |
| Correlated readout errors | Not present in the current independent measurement-flip builder | Not modeled | Could mimic pair cofires or other feature changes and invalidate both B/C and the mismatch diagnostic. |

The exact categorical calculation knows the specified physical location probabilities algebraically. An operational estimator does not know the true probabilities; it receives detector features and finite templates. An estimator built from the generated approximate DEM knows the DEM's independent-mechanism probabilities and masks, not the exact mutually exclusive circuit alternatives. The Phase 2B mean gap is small in absolute feature units but nonzero; a fit can still absorb part of model error into parameters.

## Failures the 45 features cannot rule out

- Local rank two in `(p_b,p_m)` does not identify gate p, bias ratio, five separate burst rates, per-round burst dependence, drift rate, or correlated readout parameters.
- Joint fits can return a plausible pair when the true detector mean lies off the two-dimensional model surface. A small objective only means proximity in the chosen weighting, not correctness of physical attribution.
- Covariance GLS depends on the covariance being appropriate to the generating distribution. A fixed nominal covariance can overweight changed or misspecified directions; estimated covariance from short histories can be unstable.
- A detector-only residual alarm may miss low-power mismatch, as it does at history length 1,000 in the approximate calculation; a lenient threshold can also false-alarm under finite data.
- Bound clipping hides out-of-range values. Reporting only the clipped estimate can make an extrapolation look valid.
- The graphlike `X8 X10` detector signature matches a pair feature but does not prove that changing decoder mode, or a more accurate `p_b`, improves logical risk.

## Candidate D guard calculation and caveat

Using the fixed reference covariance and the minimized fixed-`p_m` GLS residual, the mismatch population yields `T/n≈.03783`. With `n=1,000`, `T≈37.83`, below the provisional `χ²_(44,.99)=68.71`; with `n=10,000`, `T≈378.25`, above it. The nominal population has zero residual by construction. Under D's GLS-constrained fit, the mismatch burst estimate is `.0083`, while A's diagonal fixed-`p_m` profile returns `.0109`; the alarm's role is to avoid treating that misspecified profile value as a trusted burst change. These are deterministic mean-score calculations, not validated false-alarm or detection probabilities.

The chi-square reference assumes a correctly specified stationary model, fixed known covariance, independent observations, an interior regular burst fit and a Gaussian approximation to the feature mean. The 45 features are correlated; the implemented statistic minimizes the fixed-`p_m` GLS objective and whitens with covariance at reference `(p_b=.010,p_m=.003)`. Under finite calibration, drift, covariance estimation, a boundary fit or additional nuisance effects, nominal 99% size need not hold. It is therefore a proposed model-adequacy alarm with “hold last accepted graph” fallback, not a calibrated controller. A future study must not treat the `.006` mismatch as the only failure case.

## Proposed deterministic prechecks

Before any future sampling request, evaluate the exact and DEM feature maps over the prespecified rectangle and nuisance perturbations by algebra only; check Jacobian rank/conditioning, profile collisions, boundary saturation, circuit/DEM discrepancy, held-out interpolation error, and robustness to documented gate/readout alternatives. Introduce no new physical mechanism silently: any correlated-readout or time-varying-gate condition must be separately named, specified and approved. These checks cannot replace a future empirical assessment of finite-history alarm rates or decoder outcomes.
