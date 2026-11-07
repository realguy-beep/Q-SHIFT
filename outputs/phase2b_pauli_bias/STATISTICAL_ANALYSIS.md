# Phase 2B Statistical Analysis

## Frozen inference procedure

Primary estimand: equal-weight average of B−A across six basis-regime cells. The root is the independent unit (20 per cell). Two-sided paired sign-flip Monte Carlo used 100,000 assignments; the stratified percentile bootstrap used 100,000 resamples and a 95% interval. Secondary families were Holm-adjusted at sizes 2, 6, and 12. Exact shot-level McNemar tests are descriptive only.

## Primary

B−A = +0.000000%; 95% CI [+0.000000%, +0.000000%]; p=1. B errors=5,532; A errors=5,532; paired shots=1,200,000.

## By memory basis

| Basis | B−A LER | Root-bootstrap 95% CI | Raw p | Holm p (2) |
|---|---:|---:|---:|---:|
| z | +0.000000% | [+0.000000%, +0.000000%] | 1 | 1 |
| x | +0.000000% | [+0.000000%, +0.000000%] | 1 | 1 |

## By basis and regime

| Basis | Regime | B−A LER | 95% CI | Raw p | Holm p (6) |
|---|---|---:|---:|---:|---:|
| z | x_biased | +0.000000% | [+0.000000%, +0.000000%] | 1 | 1 |
| z | balanced | +0.000000% | [+0.000000%, +0.000000%] | 1 | 1 |
| z | z_biased | +0.000000% | [+0.000000%, +0.000000%] | 1 | 1 |
| x | x_biased | +0.000000% | [+0.000000%, +0.000000%] | 1 | 1 |
| x | balanced | +0.000000% | [+0.000000%, +0.000000%] | 1 | 1 |
| x | z_biased | +0.000000% | [+0.000000%, +0.000000%] | 1 | 1 |

## Alternative bank candidates versus calibration-selected global fixed

| Basis | Regime | Candidate index | Effect LER | Root p | Holm p (12) | Candidate-only / baseline-only shots | McNemar p (descriptive) |
|---|---|---:|---:|---:|---:|---:|---:|
| z | x_biased | 0 | +0.049500% | 0.00116999 | 0.00233998 | 378 / 279 | 0.000128142 |
| z | x_biased | 1 | +0.086500% | 1.99998e-05 | 0.000119999 | 360 / 187 | 1.20805e-13 |
| z | balanced | 0 | +0.160500% | 9.9999e-06 | 0.000119999 | 580 / 259 | 4.67011e-29 |
| z | balanced | 1 | +0.235500% | 9.9999e-06 | 0.000119999 | 597 / 126 | 4.02199e-74 |
| z | z_biased | 0 | +0.052000% | 0.000369996 | 0.00147999 | 208 / 104 | 3.98604e-09 |
| z | z_biased | 1 | +0.101500% | 9.9999e-06 | 0.000119999 | 215 / 12 | 2.85384e-49 |
| x | x_biased | 1 | +0.053500% | 9.9999e-06 | 0.000119999 | 126 / 19 | 1.46797e-20 |
| x | x_biased | 2 | +0.068000% | 9.9999e-06 | 0.000119999 | 170 / 34 | 5.99636e-23 |
| x | balanced | 1 | +0.053500% | 1.99998e-05 | 0.000119999 | 247 / 140 | 5.90264e-08 |
| x | balanced | 2 | +0.089000% | 9.9999e-06 | 0.000119999 | 372 / 194 | 6.30386e-14 |
| x | z_biased | 1 | +0.025500% | 0.000419996 | 0.00147999 | 179 / 128 | 0.00424662 |
| x | z_biased | 2 | +0.008000% | 0.457855 | 0.457855 | 340 / 324 | 0.560523 |

Shotwise intervals and McNemar p-values do not treat 1.2 million shots as independent experimental replicates; primary uncertainty is clustered by independent Stim root.
