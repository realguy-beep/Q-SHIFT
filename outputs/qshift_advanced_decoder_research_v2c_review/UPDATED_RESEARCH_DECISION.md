# Updated research decision after Phase 2C-R1

## Findings retained

The accepted A/B/C deterministic population comparisons remain valid for their declared template objectives. Candidate B is still the preferred primary estimator design: it is a simpler joint standardized fit and removes the fixed-measurement projection bias at tested population points. Candidate C's covariance advantage remains a local asymptotic result with a fixed covariance reference; it is secondary. Neither joint parameter recovery nor any guard behavior demonstrates decoder benefit or lower LER.

The exact categorical circuit and approximate DEM remain distinct. Phase 2C results are preserved; this review corrects their interpretation without rewriting them.

## Candidate D is not calibrated

`N rᵀW r` is population residual displacement energy for the deterministic mean and selected profile point, not a realized test statistic and not automatically a noncentrality. A central χ² cutoff comparison cannot establish an alarm decision. The regular continuous-fit reference would have 44 residual degrees of freedom only under smooth interior fitting and identity covariance after whitening. Candidate D instead uses a fixed `.0001` grid, fixed reference covariance, and model-dependent covariance. Its finite-sample statistic can have grid-selection mixtures and generalized quadratic-form distributions.

Under the counterfactual identity-covariance, continuous-fit assumptions, the deterministic noncentral-χ² tail at N=1,000 is about `.798` for the `.006` mismatch; this is not an actual detection probability. The exact-categorical projected truth covariance eigenvalues under mismatch span **.826–1.714**, with mean **1.195**, demonstrating that the identity-covariance premise is false. Therefore Candidate D's false-alarm probability, power, cutoff calibration and overall operating characteristics are **undetermined**. Do not label a deterministic energy/cutoff comparison as “flagged” or “not flagged.” Retain D only as a candidate model-adequacy guard for future analysis.

## Model sensitivity changes the readiness decision

Phase 2C holds gate noise fixed at `.003`. A deterministic sensitivity check of the existing balanced categorical gate channels found derivative cosine **.841** between measurement-p and gate-p feature directions. With templates fixed at gate p=.003, exact population truths at gate p=.002 and `.004` were fitted as `(.0083,.0004)` and `(.0077,.0056)` for `(p_b,p_m)`. Thus the two-parameter map's Phase 2B identifiability does not protect against gate-rate misspecification. Additional deterministic nuisance analysis is needed before a finite-history estimator study, especially for gate-rate/bias ranges and exact-circuit versus DEM covariance mismatch.

## Candidate A implementation clarification

Candidate A is a **population-limit counterpart**, not a sampled run of `DetectorProfileEstimator`. It uses the source estimator's five burst knots `{0,.005,.010,.015,.020}`, fixed measurement p `.003`, pooled population-limit feature scales, linear interpolation between those five knots, an inclusive `.00001` burst grid, and bounds `[0,.020]`. The Phase 2C comparison code instead used a `.001` table row and `.0001` fit grid for its A-labeled row. Source-faithful exact-template A estimates are `.01091` under measurement mismatch (vs Phase 2C `.0109`), `.00513` at measurement p=0 (vs `.0051`), and `.01484` at measurement p=.010 (vs `.0148`). DEM-template A estimates are `.01092`, `.00513`, and `.01485`. The earlier values were close but their row was only an approximation. New R1 calculations report both; Phase 2C historical artifacts remain unchanged.

Candidate B/C use `.001` bilinear two-parameter templates and `.0001` fit grid in Phase 2C. Their interpolation, tie-breaking and boundary clipping are design choices, not existing production-estimator behavior. Feature scales come from the five p_b profile knots and population-limit variance. The optimizer chooses the lower p_b then lower p_m on exact score ties; estimates clip to the declared rectangle. Boundary recovery under exact population means does not establish behavior for noisy boundary histories.

## Readiness decision

**NO-GO to request a bounded finite-history study yet.** Candidate B remains the primary design candidate, but the gate-noise assumption is a material unresolved nuisance direction; Candidate D has no calibrated operating characteristics; and the exact-A reproduction gap should be carried into future comparisons. Before a study request, specify: gate-noise/bias treatment; whether p_m is estimated or only tested as mismatch; exact versus DEM template roles; finite history length and causal update rules; a guard statistic/covariance/calibration method that handles grid selection; boundary/out-of-range behavior; and independent calibration/template allocation.

The next permissible work can remain deterministic: map nuisance-augmented exact/DEM feature surfaces and profile collisions over an owner-approved gate/readout uncertainty set, and analytically characterize the finite-grid guard under explicit covariance assumptions. That work is not authorized as sampling. Any study, decoder test or experiment requires separate approval.
