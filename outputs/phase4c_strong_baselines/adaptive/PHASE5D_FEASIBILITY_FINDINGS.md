# Phase 5D feasibility findings

Development-only decoder specialization audit; no confirmatory test.

## Decoder disagreement matrix

Entries are paired disagreement shots over 90,000 stationary shots per generating regime.

### data_heavy

| decoder | errors | LER |
| 0 (0.001, 0.001) | 389 | 0.012967 |
| 1 (0.001, 0.003) | 387 | 0.012900 |
| 2 (0.001, 0.006) | 438 | 0.014600 |
| 3 (0.003, 0.001) | 394 | 0.013133 |
| 4 (0.003, 0.003) | 389 | 0.012967 |
| 5 (0.003, 0.006) | 394 | 0.013133 |
| 6 (0.006, 0.001) | 402 | 0.013400 |
| 7 (0.006, 0.003) | 394 | 0.013133 |
| 8 (0.006, 0.006) | 389 | 0.012967 |

| pair | disagreements | rate |
|---|---:|---:|
| 0 vs 1 | 41 | 0.00046 |
| 0 vs 2 | 208 | 0.00231 |
| 0 vs 3 | 178 | 0.00198 |
| 0 vs 4 | 0 | 0.00000 |
| 0 vs 5 | 24 | 0.00027 |
| 0 vs 6 | 237 | 0.00263 |
| 0 vs 7 | 178 | 0.00198 |
| 0 vs 8 | 0 | 0.00000 |
| 1 vs 2 | 167 | 0.00186 |
| 1 vs 3 | 219 | 0.00243 |
| 1 vs 4 | 41 | 0.00046 |
| 1 vs 5 | 17 | 0.00019 |
| 1 vs 6 | 278 | 0.00309 |
| 1 vs 7 | 219 | 0.00243 |
| 1 vs 8 | 41 | 0.00046 |
| 2 vs 3 | 382 | 0.00424 |
| 2 vs 4 | 208 | 0.00231 |
| 2 vs 5 | 184 | 0.00204 |
| 2 vs 6 | 441 | 0.00490 |
| 2 vs 7 | 382 | 0.00424 |
| 2 vs 8 | 208 | 0.00231 |
| 3 vs 4 | 178 | 0.00198 |
| 3 vs 5 | 202 | 0.00224 |
| 3 vs 6 | 59 | 0.00066 |
| 3 vs 7 | 0 | 0.00000 |
| 3 vs 8 | 178 | 0.00198 |
| 4 vs 5 | 24 | 0.00027 |
| 4 vs 6 | 237 | 0.00263 |
| 4 vs 7 | 178 | 0.00198 |
| 4 vs 8 | 0 | 0.00000 |
| 5 vs 6 | 261 | 0.00290 |
| 5 vs 7 | 202 | 0.00224 |
| 5 vs 8 | 24 | 0.00027 |
| 6 vs 7 | 59 | 0.00066 |
| 6 vs 8 | 237 | 0.00263 |
| 7 vs 8 | 178 | 0.00198 |
### nominal

| decoder | errors | LER |
| 0 (0.001, 0.001) | 157 | 0.005233 |
| 1 (0.001, 0.003) | 151 | 0.005033 |
| 2 (0.001, 0.006) | 162 | 0.005400 |
| 3 (0.003, 0.001) | 162 | 0.005400 |
| 4 (0.003, 0.003) | 157 | 0.005233 |
| 5 (0.003, 0.006) | 153 | 0.005100 |
| 6 (0.006, 0.001) | 167 | 0.005567 |
| 7 (0.006, 0.003) | 162 | 0.005400 |
| 8 (0.006, 0.006) | 157 | 0.005233 |

| pair | disagreements | rate |
|---|---:|---:|
| 0 vs 1 | 41 | 0.00046 |
| 0 vs 2 | 208 | 0.00231 |
| 0 vs 3 | 178 | 0.00198 |
| 0 vs 4 | 0 | 0.00000 |
| 0 vs 5 | 24 | 0.00027 |
| 0 vs 6 | 237 | 0.00263 |
| 0 vs 7 | 178 | 0.00198 |
| 0 vs 8 | 0 | 0.00000 |
| 1 vs 2 | 167 | 0.00186 |
| 1 vs 3 | 219 | 0.00243 |
| 1 vs 4 | 41 | 0.00046 |
| 1 vs 5 | 17 | 0.00019 |
| 1 vs 6 | 278 | 0.00309 |
| 1 vs 7 | 219 | 0.00243 |
| 1 vs 8 | 41 | 0.00046 |
| 2 vs 3 | 382 | 0.00424 |
| 2 vs 4 | 208 | 0.00231 |
| 2 vs 5 | 184 | 0.00204 |
| 2 vs 6 | 441 | 0.00490 |
| 2 vs 7 | 382 | 0.00424 |
| 2 vs 8 | 208 | 0.00231 |
| 3 vs 4 | 178 | 0.00198 |
| 3 vs 5 | 202 | 0.00224 |
| 3 vs 6 | 59 | 0.00066 |
| 3 vs 7 | 0 | 0.00000 |
| 3 vs 8 | 178 | 0.00198 |
| 4 vs 5 | 24 | 0.00027 |
| 4 vs 6 | 237 | 0.00263 |
| 4 vs 7 | 178 | 0.00198 |
| 4 vs 8 | 0 | 0.00000 |
| 5 vs 6 | 261 | 0.00290 |
| 5 vs 7 | 202 | 0.00224 |
| 5 vs 8 | 24 | 0.00027 |
| 6 vs 7 | 59 | 0.00066 |
| 6 vs 8 | 237 | 0.00263 |
| 7 vs 8 | 178 | 0.00198 |
### measurement_heavy

| decoder | errors | LER |
| 0 (0.001, 0.001) | 60 | 0.002000 |
| 1 (0.001, 0.003) | 59 | 0.001967 |
| 2 (0.001, 0.006) | 54 | 0.001800 |
| 3 (0.003, 0.001) | 78 | 0.002600 |
| 4 (0.003, 0.003) | 60 | 0.002000 |
| 5 (0.003, 0.006) | 61 | 0.002033 |
| 6 (0.006, 0.001) | 82 | 0.002733 |
| 7 (0.006, 0.003) | 78 | 0.002600 |
| 8 (0.006, 0.006) | 60 | 0.002000 |

| pair | disagreements | rate |
|---|---:|---:|
| 0 vs 1 | 41 | 0.00046 |
| 0 vs 2 | 208 | 0.00231 |
| 0 vs 3 | 178 | 0.00198 |
| 0 vs 4 | 0 | 0.00000 |
| 0 vs 5 | 24 | 0.00027 |
| 0 vs 6 | 237 | 0.00263 |
| 0 vs 7 | 178 | 0.00198 |
| 0 vs 8 | 0 | 0.00000 |
| 1 vs 2 | 167 | 0.00186 |
| 1 vs 3 | 219 | 0.00243 |
| 1 vs 4 | 41 | 0.00046 |
| 1 vs 5 | 17 | 0.00019 |
| 1 vs 6 | 278 | 0.00309 |
| 1 vs 7 | 219 | 0.00243 |
| 1 vs 8 | 41 | 0.00046 |
| 2 vs 3 | 382 | 0.00424 |
| 2 vs 4 | 208 | 0.00231 |
| 2 vs 5 | 184 | 0.00204 |
| 2 vs 6 | 441 | 0.00490 |
| 2 vs 7 | 382 | 0.00424 |
| 2 vs 8 | 208 | 0.00231 |
| 3 vs 4 | 178 | 0.00198 |
| 3 vs 5 | 202 | 0.00224 |
| 3 vs 6 | 59 | 0.00066 |
| 3 vs 7 | 0 | 0.00000 |
| 3 vs 8 | 178 | 0.00198 |
| 4 vs 5 | 24 | 0.00027 |
| 4 vs 6 | 237 | 0.00263 |
| 4 vs 7 | 178 | 0.00198 |
| 4 vs 8 | 0 | 0.00000 |
| 5 vs 6 | 261 | 0.00290 |
| 5 vs 7 | 202 | 0.00224 |
| 5 vs 8 | 24 | 0.00027 |
| 6 vs 7 | 59 | 0.00066 |
| 6 vs 8 | 237 | 0.00263 |
| 7 vs 8 | 178 | 0.00198 |

## Calibration selection and dynamic replication

Best development selections by regime: `{'data_heavy': 7, 'nominal': 1, 'measurement_heavy': 2}`. They were selected from independent 3×5,000-shot batches and evaluated on 3×10,000 new shots per regime. This gives noisy point rankings; uncertainty is limited by only three calibration replicates.

| Schedule | Policy | Mean errors / 12,288 shots | switches | false switches | estimator delay (blocks) | censored |
|---|---|---:|---:|---:|---|---:|
| stationary | ml | 65.8 | 2.25 | 1.00 | [[], [], [], []] | 0 |
| stationary | utility | 64.5 | 2.25 | 1.50 | [[], [], [], []] | 0 |
| stationary | regime_matched | 64.2 | 1.00 | 0.75 | [[], [], [], []] | 0 |
| data_to_measurement | ml | 29.8 | 1.75 | 0.25 | [[1], [1], [1], [1]] | 0 |
| data_to_measurement | utility | 29.8 | 1.50 | 0.00 | [[1], [1], [1], [1]] | 0 |
| data_to_measurement | regime_matched | 28.5 | 2.00 | 1.75 | [[1], [1], [1], [1]] | 0 |
| measurement_to_data | ml | 34.2 | 2.00 | 0.50 | [[1], [1], [1], [1]] | 0 |
| measurement_to_data | utility | 33.8 | 2.00 | 0.25 | [[1], [1], [1], [1]] | 0 |
| measurement_to_data | regime_matched | 33.0 | 2.00 | 1.50 | [[1], [1], [1], [1]] | 0 |
| nominal_measurement_nominal | ml | 17.8 | 1.50 | 0.25 | [[1, 1], [2, 1], [1, 1], [1, 1]] | 0 |
| nominal_measurement_nominal | utility | 17.8 | 0.75 | 0.00 | [[1, 1], [2, 1], [1, 1], [1, 1]] | 0 |
| nominal_measurement_nominal | regime_matched | 17.8 | 3.00 | 1.25 | [[1, 1], [2, 1], [1, 1], [1, 1]] | 0 |
| slow | ml | 86.2 | 3.25 | 0.50 | [[2, 1], [1, 1], [1, 1], [1, 3]] | 0 |
| slow | utility | 84.8 | 3.25 | 0.50 | [[2, 1], [1, 1], [1, 1], [1, 3]] | 0 |
| slow | regime_matched | 87.5 | 3.00 | 2.00 | [[2, 1], [1, 1], [1, 1], [1, 3]] | 0 |
| rapid | ml | 97.5 | 3.50 | 3.50 | [[1, 2, 1, 1, 2, 1, 6, 1, 1, 1, None], [6, 1, 1, 2, 1, 1, 1, 1, 2, 2, 1], [1, 1, 1, 1, 1, 1, 1, 1, 1, 2, None], [1, 1, 1, 1, 1, 2, 2, 1, 1, None, 1]] | 3 |
| rapid | utility | 98.2 | 3.50 | 2.50 | [[1, 2, 1, 1, 2, 1, 6, 1, 1, 1, None], [6, 1, 1, 2, 1, 1, 1, 1, 2, 2, 1], [1, 1, 1, 1, 1, 1, 1, 1, 1, 2, None], [1, 1, 1, 1, 1, 2, 2, 1, 1, None, 1]] | 3 |
| rapid | regime_matched | 87.2 | 12.00 | 9.00 | [[1, 2, 1, 1, 2, 1, 6, 1, 1, 1, None], [6, 1, 1, 2, 1, 1, 1, 1, 2, 2, 1], [1, 1, 1, 1, 1, 1, 1, 1, 1, 2, None], [1, 1, 1, 1, 1, 2, 2, 1, 1, None, 1]] | 3 |
| random | ml | 78.0 | 2.25 | 1.25 | [[1, 2, 3, 1, 1, 3, 1, 1, 1, 1, 1, 1, 4, 2, 2, None], [1, 3, 3, 1, 1, 1, 4, 4, 1, 1, None, 1, 4, 1], [1, 1, 7, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, None], [1, 3, 1, 1, 1, 1, 5, 1, None, 1, 3, 1, 1, 1, None, 1]] | 5 |
| random | utility | 75.8 | 4.00 | 2.50 | [[1, 2, 3, 1, 1, 3, 1, 1, 1, 1, 1, 1, 4, 2, 2, None], [1, 3, 3, 1, 1, 1, 4, 4, 1, 1, None, 1, 4, 1], [1, 1, 7, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, None], [1, 3, 1, 1, 1, 1, 5, 1, None, 1, 3, 1, 1, 1, None, 1]] | 5 |
| random | regime_matched | 75.5 | 15.75 | 12.75 | [[1, 2, 3, 1, 1, 3, 1, 1, 1, 1, 1, 1, 4, 2, 2, None], [1, 3, 3, 1, 1, 1, 4, 4, 1, 1, None, 1, 4, 1], [1, 1, 7, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, None], [1, 3, 1, 1, 1, 1, 5, 1, None, 1, 3, 1, 1, 1, None, 1]] | 5 |

## Interpretation and limitations

Decoder disagreement demonstrates that this bank is not entirely duplicate, but several parameter pairs have identical/near-identical observed behavior and error rankings vary by regime. Regime-matched decoder ID is privileged simulation-state information; it is not the adaptive estimator. Utility policy uses development error rates. Switch penalty and short blocks may suppress changes. Four development repetitions per schedule and 30k stationary shots/regime are feasibility evidence only. Error reduction by switching is schedule-dependent and not statistically confirmatory.

Estimator delay is recorded as blocks until posterior regime classification is correct after a transition; decoder switch delay is available as the selected decoder sequence and switch blocks but is not equivalent to estimator delay. The implementation does not yet estimate false-switch rate against a prespecified null transition hazard, nor compare transition-window error excess to stationary counterfactuals.

Recommendation: improve the measurement and test of specialization before further controller complexity. A larger, blinded development calibration with per-regime paired uncertainty and transition-aware decoder utility is warranted. Do not claim adaptive superiority.
