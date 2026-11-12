# Feature sensitivity and estimator projection

## Scope and definitions

All values below come from deterministic expectations under the existing distance-3, five-round rotated Z-memory circuit, with balanced gate p=.003. The exact model treats each physical noise location as categorical; the independent-mechanism DEM is reported separately. The feature vector is 40 detector bits followed by five detector-pair conjunctions. Derivatives are with respect to burst probability `p_b` and measurement-flip probability `p_m`.

## Local identifiability

At nominal `(p_b,p_m)=(.008,.003)`, the exact categorical model has Jacobian singular values **13.489805, 3.275203**, raw condition **4.118769**, and derivative-column cosine **.443118**. Whitening by the exact single-shot feature covariance gives singular values per square-root shot **65.452409, 23.543997**, condition **2.780004**, covariance rank 45. At mismatch `(.008,.006)`, raw condition is **4.13986** and whitened condition **2.4286**. On the tested four edges of the parameter rectangle, rank remains 2; worst raw condition was **4.1687** at `(.008,.010)`, and worst whitened condition **4.2653** at `(.020,.003)`. The DEM calculation gives nominal raw/whitened conditions **4.118728 / 2.780615** and mismatch **4.139819 / 2.429013**.

These local, finite-point results do not establish global injectivity. The grid scan has 11 burst values `{0,.002,…,.020}` and four measurement values `{0,.003,.006,.010}`: no identical full mean vectors to 1e-12. The nearest distinct-parameter grid pair is `(.018,.006)` vs `(.020,.003)` at standardized RMS distance **.034948**. The scan is a collision screen, not a continuum proof.

## Which features respond

Burst probability has the largest individual local derivatives on D36 (**.9634**), D8/D16/D24/D32 (about **.9630**), and pair-conjunction features 40–44 (about **.933–.956**). Measurement probability has large derivatives on D37 (**4.7271**), D38 (**4.6964**), D39 (**2.9452**) and D36 (**2.8611**). D37 and D39 have zero burst derivative in the tested model. They are useful measurement-sensitive directions that the scalar burst-only profile cannot exploit as a second fitted parameter.

| Exact circuit expectation | p_b=.000, p_m=.003 | p_b=.008, p_m=.003 | p_b=.008, p_m=.006 |
|---|---:|---:|---:|
| D8∧D10 | .00059494 | .00818960 | .00842142 |
| D16∧D18 | .00059494 | .00818960 | .00842142 |
| D24∧D26 | .00059494 | .00818960 | .00842142 |
| D32∧D34 | .00059494 | .00818960 | .00842142 |
| D36∧D38 | .00046819 | .00811712 | .00853794 |

The pairs align with burst sites, but cofire probabilities still depend on measurement noise because other independent faults can flip either member.

## Existing estimator under mismatch

The existing `DetectorProfileEstimator` uses a burst-only profile with assumed `p_m=.003` and knots `0,.005,.010,.015,.020`. Deterministically projecting exact expected features onto that profile gives:

| Generating (p_b,p_m) | Projected p_b | Bias | Mean squared standardized residual | RMS |
|---|---:|---:|---:|---:|
| (.008,.003) | .00800 | .00000 | 0 | 0 |
| (.008,.006) | .01091 | +.00291 | .0012135 | .03483 |

The second row is a model-mismatch stress, not a finite-sample estimator simulation. The approximate DEM projection gives p_b=.01091 and residual .0012143. A small residual does not imply an unbiased parameter estimate: the mismatch moves the mean vector mostly along the burst profile.

## Interpretive boundary

The joint 45-feature mean map is locally identifiable at tested points, while the currently used one-parameter profile is materially biased if measurement p drifts. Whether a joint estimator has useful finite-sample error, stable calibration, or robustness to additional nuisance channels requires a separately approved evaluation. No decoder or sampler was run.
