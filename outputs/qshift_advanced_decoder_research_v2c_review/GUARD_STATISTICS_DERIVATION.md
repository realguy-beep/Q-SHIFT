# Candidate D statistic: derivation and operating-characteristic limits

## Five quantities that must stay separate

1. **Population residual** `r=μ_1−g(p̃_b,.003)`: difference between a deterministic truth mean and the fixed-measurement null profile at its fitted burst value.
2. **Population residual energy** `q=rᵀW r`, with `W=(Σ_ref+λI)⁻¹` under the chosen template family. This is a deterministic squared distance per shot.
3. **Population displacement energy** `Nq`. It is the squared whitened mean shift over N shots. It equals a noncentrality parameter only under the covariance/projection assumptions below; it is never a realized test statistic.
4. **Realized statistic** `T=N(F̄−g(p̂_b,.003))ᵀW(F̄−g(p̂_b,.003))`. It is random over finite detector histories. No histories were generated here.
5. **Rejection probability** `P(T>c)`. This needs the distribution of T, including covariance, nuisance fitting, grid selection and calibration uncertainty. It was not measured. The actual operating characteristics remain undetermined.

The legacy Phase 2C field `would_flag_at_provisional_threshold` should be disregarded as a test decision. Corrected result keys use `population_residual_energy_per_shot_discrete_grid`, `lambda_population_energy_N1000_N10000` (a renamed Nq diagnostic, not an asserted noncentral parameter), and `counterfactual_idealized_probabilities`.

## Continuous-fit asymptotic reference

Let `F̄` be the 45-feature sample mean. Suppose for the moment that `√N(F̄−μ)` is asymptotically normal with covariance Σ, W is fixed, the fixed-`p_m` null curve is smooth, and its fitted burst parameter is interior. Let `LᵀL=W`, let `J_b=∂g/∂p_b` at the null fit, and set

`x=L J_b`, `P=I−x(xᵀx)⁻¹xᵀ`.

Then the locally fitted residual statistic is approximately

`T ≈ [P L √N(F̄−μ_0)]ᵀ[P L √N(F̄−μ_0)]`.

The projected space has rank **44** if J_b is nonzero and the fit is a regular continuous one-parameter fit. Under the null, its covariance is `P L Σ_0 Lᵀ P`. A central `χ²_44` reference requires that covariance to be identity on the residual subspace. Under an alternative mean shift, a noncentral `χ²_44(λ)` requires the same identity covariance; then

`λ=N ||P L(μ_1−g(p̃_b,.003))||²`.

If covariance differs from the reference, the limiting statistic is a generalized weighted quadratic form (a sum of eigenvalue-weighted noncentral chi-square components), not a standard noncentral chi-square. The threshold's nominal size and power then do not follow from λ alone.

## What the current fixed grid changes

The Phase 2C implementation searches p_b in increments of **.0001** on a bilinearly interpolated template surface. It does not solve a continuous profile problem. If the grid is held fixed as N grows and the true null p_b is a grid point, the selected nuisance value can lock to that point; conditional on selection, no continuous fitted direction is removed and the quadratic residual has up to **45**, not 44, dimensions. At finite N the selected grid point can switch, yielding a mixture of quadratic forms with different residual means. The `.0001` spacing may be fine relative to some proposed histories, but that does not make the continuous-fit law exact, especially near boundaries or knots. A continuous-refinement analysis would be a different implementation and must be frozen and validated separately.

The 99th-percentile central values are **68.7095** for 44 df and **69.9568** for 45 df. Neither is the calibrated cutoff for the current finite-grid test. Boundary selection, covariance estimation, interpolation knots and finite calibration further change the law.

## Deterministic covariance audit

Phase 2C's exact-categorical Candidate D uses fixed covariance at `(.010,.003)`. The audit computes per-shot covariance from the exact circuit algebra and whitens the truth covariance by the fixed reference covariance. For a continuous local projection:

| Data distribution, exact-categorical reference W | Projected eigenvalue range | Mean | SD before projection |
|---|---:|---:|---:|
| Null `(.008,.003)` | `.8111–1.0020` | `.9827` | `.0588` |
| Measurement mismatch `(.008,.006)` | `.8263–1.7139` | `1.1952` | `.1972` |

The alternative's covariance is materially different from identity after whitening; a standard noncentral chi-square is not justified. Approximate-DEM reference calculations show nearly the same pattern: projected means about `.983` under nominal conditions and `1.195–1.196` under mismatch, with mismatch eigenvalues about `.826–1.714`. The two data-generating distributions remain separately recorded in `guard_distribution_results.json`.

For exact-categorical data against the exact-categorical null profile, discrete-grid population energy per shot is **0** at the nominal point and **.0378253** at mismatch; the corresponding `Nq` is **37.8253** at N=1,000 and **378.253** at N=10,000. Against DEM templates the exact-data mismatch q is **.037999**; DEM data with DEM templates gives **.037848**. These remain deterministic energies.

## Counterfactual distribution-function sensitivity

For scale only, if one additionally assumes identity projected covariance and a continuous nuisance fit, the scipy noncentral-chi-square survival function with df=44, central 99% cutoff 68.7095, and λ from the continuous projection gives:

| Data/template case | N | Counterfactual `P(χ²_44(λ)>68.7095)` |
|---|---:|---:|
| Exact categorical truth, exact templates, `.006` mismatch | 1,000 | `.79787` |
| Exact categorical truth, DEM templates, `.006` mismatch | 1,000 | `.80098` |
| DEM truth, DEM templates, `.006` mismatch | 1,000 | `.79829` |
| Same cases | 10,000 | approximately `1.0` |

These are deterministic distribution-function outputs under counterfactual assumptions, **not theoretical detection probabilities for Candidate D**. Under the null, the same idealized law returns .01 by construction; it does not validate actual size. Because covariance mismatch and fixed-grid selection violate the required law, do not report the table as alarm power, choose N from it, or infer a finite-history decision.

## Determination

Candidate D's actual false-alarm rate, power, threshold and finite-history behavior are **undetermined**. To identify them one would need a fully specified calibration target and an appropriate generalized quadratic-form / grid-selection analysis, plus later independent finite-history validation. This review performs neither stochastic validation nor alarm calibration.
