# Model-sensitivity review

## Gate noise is a fixed assumption, not an estimated quantity

Phase 2C holds balanced categorical gate-noise probability at `.003`. Its two-parameter map therefore asks whether burst p and measurement p are locally distinguished **conditional on that gate model**. It says nothing about whether gate p is known accurately. The review varied only the existing balanced one- and two-qubit categorical channel rates, preserving the circuit, fault alternatives, detector masks, burst mechanism and measurement channel.

At baseline `p_b=.008`, `p_m=.003`, `p_gate=.003`, the exact categorical 45×3 local mean Jacobian for `(p_b,p_m,p_gate)` had singular values **47.139, 7.132, 3.228** (condition **14.60**). Derivative-column cosines were burst/measurement **.443**, burst/gate **.321**, measurement/gate **.841**. The three local directions are linearly independent at this point but measurement and gate changes are strongly aligned. Rank three is not evidence that a finite detector history estimates all three accurately.

Templates remained at gate p=.003. Deterministic exact-categorical population truth at nominal burst/readout settings produced:

| Actual balanced gate p | Fit with fixed-gate exact templates `(p_b,p_m)` | Fit with fixed-gate DEM templates `(p_b,p_m)` |
|---:|---:|---:|
| `.002` | `(.0083,.0004)` | `(.0083,.0004)` |
| `.003` | `(.0080,.0030)` | `(.0080,.0030)` |
| `.004` | `(.0077,.0056)` | `(.0077,.0056)` |

Thus modest gate-rate mismatch is largely absorbed as a measurement-rate change in this population fit, with a smaller burst shift. This is a deterministic confounding example, not an estimate from sampled shots. At gate p `.002/.004`, exact-categorical and generated DEM truth feature means differ by max `1.480×10⁻⁵ / 5.717×10⁻⁵`, respectively (RMS `9.663×10⁻⁶ / 3.731×10⁻⁵`).

## Other nuisance directions

- **Gate p and Pauli bias:** the fitted model fixes the balanced channel proportions and bias. A total-rate change can mimic readout shifts as above; changes in composition or location-specific gate rates may create feature directions not represented by either p parameter.
- **Temporal drift:** a chronological mean over a window can combine multiple burst and measurement regimes. That average need not lie on the stationary two-parameter surface. The static population fit cannot identify change time, direction or rate.
- **Correlated readout:** not present in the current builder. Such errors could alter single-detector and pair-cofire features in ways that resemble burst and gate shifts. No correlated-readout mechanism was introduced for this audit.
- **Burst heterogeneity:** the current model uses one common burst probability with independent events at five sites. Site-specific rates, within-round dependence or a different correlated Pauli pattern are outside the two-parameter identification claim.

The **exact categorical circuit** calculations use mutually exclusive alternatives at each gate location and independent burst/readout locations. The **approximate DEM** calculations treat Stim's converted error mechanisms as independent. Results and covariance spectra are separated by data and template family in `guard_distribution_results.json`; a small mean difference does not establish distributional equivalence.

## Required deterministic work before any finite-history study

At minimum, a future protocol-design review should: (1) define an owner-justified gate-rate/bias uncertainty set; (2) compute exact categorical and DEM feature maps and Jacobians across that set; (3) test whether nuisance-augmented maps lose rank or approach cross-parameter profile collisions; (4) quantify approximation discrepancy in means and covariances over that set; (5) specify which nuisance parameters are fixed, jointly estimated or only guarded; (6) define a named correlated-readout stress only if the physical mechanism and probabilities are explicitly supplied; and (7) freeze temporal-change scenarios separately from stationary model checks. These deterministic checks precede, but do not substitute for, any separately approved finite-sample assessment.
