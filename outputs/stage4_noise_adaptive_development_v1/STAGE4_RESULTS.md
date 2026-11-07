# Stage 4 Development Results

## Aggregate paired evaluation

| Decoder | Logical errors / shots | LER |
|---|---:|---:|
| Fixed nominal PyMatching | 590 / 87,500 | 0.674286% |
| Detector-estimated PyMatching | 474 / 87,500 | 0.541714% |
| Privileged true-probability reference | 476 / 87,500 | 0.544000% |

| Paired measure: estimated vs fixed | Count / estimate |
|---|---:|
| Candidate-only failures | 30 |
| Fixed-only failures | 146 |
| Prediction disagreements | 176 |
| Equal-weight mean nonzero-condition LER difference | -0.164286% |
| Relative reduction vs equal-weight nonzero fixed LER | 22.727% |
| Root-cluster 95% bootstrap CI | [-0.197143%, -0.132857%] |
| Two-sided root sign-flip p | 9.9999e-06 |
| Zero-burst mean difference | -0.005714% |
| Zero-burst one-sided 95% upper bound | +0.000000% |

## Condition results

| Burst p | Shots | Raw observable errors (LER) | Fixed errors (LER) | Estimated errors (LER) | Privileged reference errors (LER) | Est. − fixed [95% root CI] | Estimated-only / fixed-only errors |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.000 | 17,500 | 1073 (6.131429%) | 84 (0.480000%) | 83 (0.474286%) | 84 (0.480000%) | -0.005714% [-0.017143%, +0.000000%] | 0 / 1 |
| 0.004 | 17,500 | 1041 (5.948571%) | 102 (0.582857%) | 94 (0.537143%) | 94 (0.537143%) | -0.045714% [-0.102857%, +0.005714%] | 10 / 18 |
| 0.008 | 17,500 | 1021 (5.834286%) | 111 (0.634286%) | 88 (0.502857%) | 88 (0.502857%) | -0.131429% [-0.188571%, -0.080000%] | 4 / 27 |
| 0.012 | 17,500 | 1106 (6.320000%) | 138 (0.788571%) | 103 (0.588571%) | 105 (0.600000%) | -0.200000% [-0.268571%, -0.131429%] | 6 / 41 |
| 0.016 | 17,500 | 1094 (6.251429%) | 155 (0.885714%) | 106 (0.605714%) | 105 (0.600000%) | -0.280000% [-0.360000%, -0.205714%] | 10 / 59 |

## Estimation and selection diagnostics

Across nonzero conditions, probability-estimation MAE was 0.000934, signed bias +0.000013. Counts within absolute error 0.005 were {"0.004": 7, "0.008": 7, "0.012": 7, "0.016": 7}. The profile-conditional percentile intervals covered the true nonzero p in 26/28 roots; they condition on the fixed profile batches and omit template uncertainty.

Per-root results and paired differences are in `PER_ROOT_RESULTS.csv`; per-condition summaries are in `PER_CONDITION_RESULTS.csv`; calibration estimates/intervals are in `ESTIMATION_DIAGNOSTICS.csv`; root-level paired decoder evidence is in `PAIRED_COMPARISONS.csv`.

## Frozen development gate: PASS

- PASS — nonzero estimation mae
- PASS — nonzero estimation absolute bias
- PASS — at least 5 of 7 estimates within 0.005 per nonzero condition
- PASS — primary equal condition mean at least 0.0002 improvement
- PASS — primary stratified root bootstrap 95ci upper below zero
- PASS — all 4 nonzero condition means favorable
- PASS — no nonzero condition mean harm above 0.0002
- PASS — zero burst one sided root bootstrap 95ci upper within 0.0002
- PASS — median decoder rebuild below 1s
- PASS — peak rss below 2gib

This is not a confirmatory test. The privileged true-probability decoder is a nondeployable reference, not an adaptive arm.

## Interpretation and limitations

The prespecified development gate passed. On the p=0.004 condition, the descriptive root-bootstrap interval includes zero; the four exact condition-level sign-flip tests have Holm-adjusted p-values of 0.375, 0.0625, 0.0625, and 0.0625, so none is individually significant at 0.05 after correction. The primary Monte Carlo p-value is at the 100,000-draw plus-one floor (1/100001), so report it as approximately or at most 1e-5, not with greater precision. Only seven independent roots were run per condition, and the sign-flip test assumes root-effect sign symmetry.

This is development evidence for one synthetic spatial-burst model at distance 3 and five rounds. The profile-conditional parameter intervals omit profile-template uncertainty; Stim's categorical two-qubit DEM conversion remains approximate; the privileged reference receives true p; and no hardware behavior or general adaptive-decoding advantage is established. A fresh, separately frozen independent study is still required.
