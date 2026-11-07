# Q-SHIFT CNN Stage 2 Results

Development-only results from five independent roots. The independent test remained sealed. Root intervals are descriptive feasibility summaries, not confirmatory tests.

## Aggregate logical errors


| Condition | Decoder | Errors / shots | LER |
|---|---|---:|---:|
| nominal | Nominal fixed PyMatching | 255 / 50000 | 0.005100 |
| nominal | historical_residual_position_cnn | 254 / 50000 | 0.005080 |
| nominal | residual_position_v2 | 255 / 50000 | 0.005100 |
| nominal | factorized_spatiotemporal_residual | 257 / 50000 | 0.005140 |
| synthetic_spatial_burst | Nominal fixed PyMatching | 386 / 50000 | 0.007720 |
| synthetic_spatial_burst | historical_residual_position_cnn | 389 / 50000 | 0.007780 |
| synthetic_spatial_burst | residual_position_v2 | 395 / 50000 | 0.007900 |
| synthetic_spatial_burst | factorized_spatiotemporal_residual | 402 / 50000 | 0.008040 |
| synthetic_spatial_burst | Burst-informed PyMatching (privileged) | 301 / 50000 | 0.006020 |

## Paired comparisons with nominal fixed PyMatching

Differences are candidate LER minus fixed-decoder LER on identical shots. Candidate-only and fixed-only counts are paired shot-level discordances. Intervals are across five independent root-level differences.


| Condition | Candidate | Delta LER | 95% root interval | Candidate-only | Fixed-only | Disagreements | Useful | Harmful |
|---|---|---:|---|---:|---:|---:|---:|---:|
| nominal | historical_residual_position_cnn | -0.000020 | [-7.552890210395551e-05, 3.552890210395576e-05] | 1 | 2 | 3 | 2 | 1 |
| nominal | residual_position_v2 | +0.000000 | [-8.779890330850868e-05, 8.779890330850868e-05] | 1 | 1 | 2 | 1 | 1 |
| nominal | factorized_spatiotemporal_residual | +0.000040 | [-0.0001483076688348439, 0.0002283076688348441] | 7 | 5 | 12 | 5 | 7 |
| synthetic_spatial_burst | historical_residual_position_cnn | +0.000060 | [-0.00016555946662990458, 0.00028555946662990486] | 6 | 3 | 9 | 3 | 6 |
| synthetic_spatial_burst | residual_position_v2 | +0.000180 | [-8.918634023379036e-05, 0.000449186340233791] | 12 | 3 | 15 | 3 | 12 |
| synthetic_spatial_burst | factorized_spatiotemporal_residual | +0.000320 | [-0.00010471443309468284, 0.0007447144330946831] | 23 | 7 | 30 | 7 | 23 |

## Frozen primary endpoint and development gate

Equal-condition root mean ResidualPositionCNNV2 minus fixed PyMatching LER difference: **+0.000090**, descriptive 95% root-level Student-t interval **[-2.941941940499909e-05, 0.0002094194194049994]** (n=5). Favorable roots: 0/5. Condition deltas: {'nominal': 0.0, 'synthetic_spatial_burst': 0.0001800000000000003}. Gate: **FAIL**.

This is a development feasibility gate and does not establish statistical superiority or authorize independent-test access.


## Burst-informed reference

On synthetic-burst shots only, burst-informed minus fixed per-root LER differences are [-0.0008999999999999998, -0.0011999999999999997, -0.0018000000000000004, -0.0033999999999999994, -0.0011999999999999997]; descriptive 95% root interval [-0.0029478568745171523, -0.0004521431254828471]. This reference receives the injected burst specification and is privileged.


## Per-root decoder LER


| Root | Condition | Fixed PyMatching | Historical CNN | V2 CNN | Factorized CNN | Burst-informed PM |
|---|---|---:|---:|---:|---:|---:|
| dev-root-00 | nominal | 0.005900 | 0.005900 | 0.005800 | 0.006200 | n/a |
| dev-root-00 | synthetic_spatial_burst | 0.008100 | 0.008400 | 0.008400 | 0.008900 | 0.007200 |
| dev-root-01 | nominal | 0.005300 | 0.005300 | 0.005300 | 0.005300 | n/a |
| dev-root-01 | synthetic_spatial_burst | 0.006800 | 0.006900 | 0.006800 | 0.007000 | 0.005600 |
| dev-root-02 | nominal | 0.004800 | 0.004700 | 0.004900 | 0.004700 | n/a |
| dev-root-02 | synthetic_spatial_burst | 0.007900 | 0.007700 | 0.007900 | 0.007800 | 0.006100 |
| dev-root-03 | nominal | 0.003600 | 0.003600 | 0.003600 | 0.003600 | n/a |
| dev-root-03 | synthetic_spatial_burst | 0.009600 | 0.009700 | 0.009700 | 0.010100 | 0.006200 |
| dev-root-04 | nominal | 0.005900 | 0.005900 | 0.005900 | 0.005900 | n/a |
| dev-root-04 | synthetic_spatial_burst | 0.006200 | 0.006200 | 0.006700 | 0.006400 | 0.005000 |

Per-root optimizer steps, parameters, checkpoint epoch, calibration threshold/temperature, split-wise residual-positive counts, positive-example reuse ratios, and inference timing are recorded in the independent audit JSON. Class-balanced minibatches reuse rare examples; they do not add unique shots.
