# Q-SHIFT Prototype Development Results

Audited independent root-level datasets: **50**; paired evaluation shots: **307,200**. This is development evidence, not confirmatory validation.

## Overall matched-shot outcomes

| Method | Errors | Shots | Logical error rate | Success rate | 95% Wilson interval for LER |
|---|---:|---:|---:|---:|---:|
| identity_no_decode | 19,726 | 307,200 | 6.42122% | 93.57878% | [6.33508%, 6.50845%] |
| pooled_fixed | 1,989 | 307,200 | 0.64746% | 99.35254% | [0.61971%, 0.67645%] |
| nominal_fixed | 1,976 | 307,200 | 0.64323% | 99.35677% | [0.61557%, 0.67212%] |
| adaptive | 1,989 | 307,200 | 0.64746% | 99.35254% | [0.61971%, 0.67645%] |
| regime_informed_diagnostic | 1,989 | 307,200 | 0.64746% | 99.35254% | [0.61971%, 0.67645%] |

The no-decoding baseline predicts no logical flip; its residual error is therefore the sampled observable itself. It is a decoding comparator, not a physical circuit without QEC. The adaptive and regime-informed diagnostics selected the same decoder as the pooled model throughout this run, so their measured results tie the pooled baseline exactly.

## Paired contrasts to pooled fixed

| Comparator | Candidate-only errors | Pooled-only errors | Difference in LER | Exact paired McNemar p | Seed-cluster bootstrap 95% CI |
|---|---:|---:|---:|---:|---:|
| identity_no_decode | 18,589 | 852 | +5.773763% | ~10^-4335 (float underflow) | [+5.693359%, +5.853841%] |
| nominal_fixed | 48 | 61 | -0.004232% | 0.2503 | [-0.011068%, +0.002604%] |
| adaptive | 0 | 0 | +0.000000% | 1 | [+0.000000%, +0.000000%] |
| regime_informed_diagnostic | 0 | 0 | +0.000000% | 1 | [+0.000000%, +0.000000%] |

## Results by generating regime

| Regime | Shots | Identity errors | Pooled errors | Nominal errors | Adaptive errors |
|---|---:|---:|---:|---:|---:|
| data_heavy | 81,920 | 8,575 | 1,174 | 1,157 | 1,174 |
| nominal | 122,880 | 7,498 | 599 | 596 | 599 |
| measurement_heavy | 102,400 | 3,653 | 216 | 223 | 216 |

## Outcomes by schedule

| Schedule | Shots | Identity LER | Pooled LER | Nominal LER | Adaptive LER | Adaptive minus pooled | Replicate paired differences |
|---|---:|---:|---:|---:|---:|---:|---|
| stationary | 61,440 | 5.95540% | 0.48828% | 0.48991% | 0.48828% | +0.00000% | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] |
| data_to_measurement | 61,440 | 7.12891% | 0.79590% | 0.78939% | 0.79590% | +0.00000% | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] |
| measurement_to_data | 61,440 | 6.96615% | 0.84147% | 0.83822% | 0.84147% | +0.00000% | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] |
| nominal_measurement_nominal | 61,440 | 5.24577% | 0.39714% | 0.39225% | 0.39714% | +0.00000% | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] |
| rapid_cycle | 61,440 | 6.80990% | 0.71452% | 0.70638% | 0.71452% | +0.00000% | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] |

## Calibration utility differences against pooled fixed

Calibration-only estimates; intervals are paired, shot-level approximate 95% normal intervals and are descriptive development estimates.

| Regime | Model index | LER | Paired LER difference vs pooled | Approx. 95% interval |
|---|---:|---:|---:|---:|
| data_heavy | 0 | 1.45500% | +0.00500% | [-0.03541%, +0.04541%] |
| data_heavy | 1 | 1.45000% | +0.00000% | [+0.00000%, +0.00000%] |
| data_heavy | 2 | 1.58500% | +0.13500% | [+0.05361%, +0.21639%] |
| data_heavy | 3 | 1.45500% | +0.00500% | [-0.09052%, +0.10052%] |
| data_heavy | 4 | 1.45500% | +0.00500% | [-0.03541%, +0.04541%] |
| data_heavy | 5 | 1.47500% | +0.02500% | [+0.00309%, +0.04691%] |
| data_heavy | 6 | 1.46000% | +0.01000% | [-0.10001%, +0.12001%] |
| data_heavy | 7 | 1.45500% | +0.00500% | [-0.09052%, +0.10052%] |
| data_heavy | 8 | 1.45500% | +0.00500% | [-0.03541%, +0.04541%] |
| nominal | 0 | 0.37500% | +0.01000% | [-0.01772%, +0.03772%] |
| nominal | 1 | 0.36500% | +0.00000% | [+0.00000%, +0.00000%] |
| nominal | 2 | 0.42000% | +0.05500% | [+0.00600%, +0.10400%] |
| nominal | 3 | 0.43000% | +0.06500% | [+0.00703%, +0.12297%] |
| nominal | 4 | 0.37500% | +0.01000% | [-0.01772%, +0.03772%] |
| nominal | 5 | 0.37000% | +0.00500% | [-0.01197%, +0.02197%] |
| nominal | 6 | 0.47000% | +0.10500% | [+0.03641%, +0.17359%] |
| nominal | 7 | 0.43000% | +0.06500% | [+0.00703%, +0.12297%] |
| nominal | 8 | 0.37500% | +0.01000% | [-0.01772%, +0.03772%] |
| measurement_heavy | 0 | 0.19000% | +0.00500% | [-0.00480%, +0.01480%] |
| measurement_heavy | 1 | 0.18500% | +0.00000% | [+0.00000%, +0.00000%] |
| measurement_heavy | 2 | 0.18500% | +0.00000% | [-0.02401%, +0.02401%] |
| measurement_heavy | 3 | 0.22500% | +0.04000% | [-0.00158%, +0.08158%] |
| measurement_heavy | 4 | 0.19000% | +0.00500% | [-0.00480%, +0.01480%] |
| measurement_heavy | 5 | 0.19000% | +0.00500% | [-0.00480%, +0.01480%] |
| measurement_heavy | 6 | 0.26500% | +0.08000% | [+0.03004%, +0.12996%] |
| measurement_heavy | 7 | 0.22500% | +0.04000% | [-0.00158%, +0.08158%] |
| measurement_heavy | 8 | 0.19000% | +0.00500% | [-0.00480%, +0.01480%] |

## Pairwise decoder correction disagreement

Evaluation disagreement-rate matrices in frozen decoder order 0..8; these measure how often two models return different logical corrections, not which is more accurate. The complete long-form table is in `DECODER_DISAGREEMENT_MATRIX.csv`.

**data_heavy** (81,920 paired shots):

```text
0.000% 0.072% 0.408% 0.426% 0.000% 0.052% 0.544% 0.424% 0.000%
0.072% 0.000% 0.336% 0.488% 0.072% 0.020% 0.607% 0.486% 0.072%
0.408% 0.336% 0.000% 0.824% 0.408% 0.355% 0.942% 0.822% 0.408%
0.426% 0.488% 0.824% 0.000% 0.426% 0.474% 0.118% 0.002% 0.426%
0.000% 0.072% 0.408% 0.426% 0.000% 0.052% 0.544% 0.424% 0.000%
0.052% 0.020% 0.355% 0.474% 0.052% 0.000% 0.592% 0.471% 0.052%
0.544% 0.607% 0.942% 0.118% 0.544% 0.592% 0.000% 0.121% 0.544%
0.424% 0.486% 0.822% 0.002% 0.424% 0.471% 0.121% 0.000% 0.424%
0.000% 0.072% 0.408% 0.426% 0.000% 0.052% 0.544% 0.424% 0.000%
```

**nominal** (122,880 paired shots):

```text
0.000% 0.030% 0.154% 0.160% 0.000% 0.018% 0.214% 0.160% 0.000%
0.030% 0.000% 0.124% 0.188% 0.030% 0.012% 0.243% 0.188% 0.030%
0.154% 0.124% 0.000% 0.308% 0.154% 0.136% 0.363% 0.308% 0.154%
0.160% 0.188% 0.308% 0.000% 0.160% 0.176% 0.055% 0.000% 0.160%
0.000% 0.030% 0.154% 0.160% 0.000% 0.018% 0.214% 0.160% 0.000%
0.018% 0.012% 0.136% 0.176% 0.018% 0.000% 0.230% 0.176% 0.018%
0.214% 0.243% 0.363% 0.055% 0.214% 0.230% 0.000% 0.055% 0.214%
0.160% 0.188% 0.308% 0.000% 0.160% 0.176% 0.055% 0.000% 0.160%
0.000% 0.030% 0.154% 0.160% 0.000% 0.018% 0.214% 0.160% 0.000%
```

**measurement_heavy** (102,400 paired shots):

```text
0.000% 0.013% 0.069% 0.075% 0.000% 0.006% 0.102% 0.075% 0.000%
0.013% 0.000% 0.057% 0.088% 0.013% 0.007% 0.114% 0.088% 0.013%
0.069% 0.057% 0.000% 0.143% 0.069% 0.063% 0.167% 0.143% 0.069%
0.075% 0.088% 0.143% 0.000% 0.075% 0.081% 0.026% 0.000% 0.075%
0.000% 0.013% 0.069% 0.075% 0.000% 0.006% 0.102% 0.075% 0.000%
0.006% 0.007% 0.063% 0.081% 0.006% 0.000% 0.107% 0.081% 0.006%
0.102% 0.114% 0.167% 0.026% 0.102% 0.107% 0.000% 0.026% 0.102%
0.075% 0.088% 0.143% 0.000% 0.075% 0.081% 0.026% 0.000% 0.075%
0.000% 0.013% 0.069% 0.075% 0.000% 0.006% 0.102% 0.075% 0.000%
```

## Estimator and runtime

Confusion matrix counts (actual regime rows; estimated regime columns ordered data-heavy, nominal, measurement-heavy), using only blocks with a previous block available:

```text
[[100, 0, 40], [40, 170, 10], [10, 51, 129]]
```

| Schedule | Mean regime accuracy | Estimator transition delays (blocks; null=censored) | Switches | Selection overhead / one fixed decode | Total measured adaptive compute overhead / fixed |
|---|---:|---|---:|---:|---:|
| stationary | 100.0% | [] | 0 | 57.4% | 59.4% |
| data_to_measurement | 90.0% | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | 0 | 53.5% | 46.9% |
| measurement_to_data | 90.9% | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | 0 | 54.4% | 50.9% |
| nominal_measurement_nominal | 81.8% | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | 0 | 67.9% | 64.0% |
| rapid_cycle | 0.0% | [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None] | 0 | 56.8% | 52.5% |

## Findings and limitations

- The calibration table selected pooled decoder index [1, 1, 1] for data-heavy, nominal, and measurement-heavy conditions. Thus this run found no calibration-supported decoder specialization, and the conservative adaptive controller correctly remained at decoder index 1 (pooled fallback).
- The direct detector estimator is reasonably accurate after transitions in long-dwell schedules, but in the rapid cycle it has no completed stable regime block from which to estimate the next state. Classification is not the main blocker here; the calibration data did not identify a better decoder for any of the three regimes.
- The regime-informed diagnostic uses the hidden current generating regime only to pick the calibration-selected decoder and is an optimistic information diagnostic, not a deployable method. It also tied because calibration chose the same model in every regime.
- Each generated Stim circuit has one stationary noise setting throughout its five rounds. Nonstationarity is between batches of independent memory experiments (blocks), not within a single circuit execution. This is a controlled schedule for block-level adaptation and does not establish within-circuit drift handling.
- All policies share the identical detector samples and observable labels. Every stored grid prediction in every root was independently recomputed from its stored detector array and matched exactly.
- This is a bounded, small-code development experiment. The controller utility table is estimated from the same separate calibration shots used to fit detector profiles; evaluation streams and seeds are separate. It is not a confirmatory test, and no hardware was used.
