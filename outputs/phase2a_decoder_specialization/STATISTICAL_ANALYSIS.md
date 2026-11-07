# Phase 2A statistical analysis

## Procedure

Decoder performance comparisons use 20 independently seeded roots per regime. Each root contains 10,000 paired Stim shots decoded by all nine models. The primary estimates use equal regime weighting. Uncertainty for model differences is resampled at the root level; 24 candidate-by-regime comparisons use paired root sign-flip tests with Holm correction. Wilson intervals and exact shotwise McNemar probabilities are descriptive and do not replace root-level inference. The hindsight oracles are reported separately and never treated as available decoder policies.

## Main headroom comparison

Calibration chose global index 1 and per-regime indices [1, 1, 1]. A had 4,192 errors; B had 4,192. Equal-regime B−A LER difference = +0.000000%; seed-cluster bootstrap 95% CI [+0.000000%, +0.000000%], stratified root sign-flip p=1. Since A and B use the same index in all regimes, their predictions and errors are exactly equal in this experiment.

## Paired bank comparisons vs selected global fixed

| Regime | Candidate | Error delta LER | Candidate-only / baseline-only | Root sign-flip p | Holm p | Root bootstrap 95% CI |
|---|---:|---:|---:|---:|---:|---:|
| data_heavy | 0 | -0.005500% | 73/84 | 0.3559 | 1 | [-0.015500%, +0.004500%] |
| data_heavy | 2 | +0.153500% | 544/237 | 1e-05 | 0.00024 | [+0.124000%, +0.183000%] |
| data_heavy | 3 | -0.037500% | 413/488 | 0.01289 | 0.1933 | [-0.065000%, -0.012500%] |
| data_heavy | 4 | -0.005500% | 73/84 | 0.3559 | 1 | [-0.016000%, +0.004500%] |
| data_heavy | 5 | +0.013000% | 42/16 | 0.00185 | 0.03145 | [+0.006000%, +0.020000%] |
| data_heavy | 6 | -0.010000% | 581/601 | 0.6388 | 1 | [-0.051500%, +0.029000%] |
| data_heavy | 7 | -0.037500% | 413/488 | 0.01289 | 0.1933 | [-0.066000%, -0.012500%] |
| data_heavy | 8 | -0.005500% | 73/84 | 0.3559 | 1 | [-0.016000%, +0.004500%] |
| nominal | 0 | +0.005500% | 35/24 | 0.1428 | 0.9999 | [-0.002000%, +0.012500%] |
| nominal | 2 | +0.032000% | 162/98 | 0.00137 | 0.02603 | [+0.015500%, +0.048500%] |
| nominal | 3 | +0.025000% | 215/165 | 0.0298 | 0.298 | [+0.004500%, +0.045500%] |
| nominal | 4 | +0.005500% | 35/24 | 0.1428 | 0.9999 | [-0.002000%, +0.012500%] |
| nominal | 5 | +0.008500% | 24/7 | 0.00139 | 0.02603 | [+0.003500%, +0.013000%] |
| nominal | 6 | +0.050500% | 297/196 | 0.00022 | 0.0044 | [+0.030000%, +0.070000%] |
| nominal | 7 | +0.025000% | 215/165 | 0.0298 | 0.298 | [+0.005000%, +0.045500%] |
| nominal | 8 | +0.005500% | 35/24 | 0.1428 | 0.9999 | [-0.002500%, +0.012500%] |
| measurement_heavy | 0 | +0.005500% | 15/4 | 0.02126 | 0.2764 | [+0.001000%, +0.010000%] |
| measurement_heavy | 2 | -0.019000% | 29/67 | 0.00826 | 0.1322 | [-0.030500%, -0.007500%] |
| measurement_heavy | 3 | +0.057000% | 142/28 | 1e-05 | 0.00024 | [+0.046000%, +0.068500%] |
| measurement_heavy | 4 | +0.005500% | 15/4 | 0.02126 | 0.2764 | [+0.001488%, +0.010000%] |
| measurement_heavy | 5 | +0.003000% | 8/2 | 0.03946 | 0.3157 | [+0.000500%, +0.005500%] |
| measurement_heavy | 6 | +0.077000% | 185/31 | 1e-05 | 0.00024 | [+0.065500%, +0.088500%] |
| measurement_heavy | 7 | +0.057000% | 142/28 | 1e-05 | 0.00024 | [+0.046000%, +0.068500%] |
| measurement_heavy | 8 | +0.005500% | 15/4 | 0.02126 | 0.2764 | [+0.001500%, +0.010000%] |
