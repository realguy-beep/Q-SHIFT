# Stage 4C — Statistical Comparison

**Primary:** CNN-assisted minus Stage4B-profile-assisted PyMatching, equal-weight mean over p=0.004,0.008,0.012,0.016.
Effect=+0.00004286; 95% stratified root-bootstrap CI [+0.00000000, +0.00012857]; sign-flip p=1.
Resampling unit: independent root, with seven roots resampled within each p stratum. No shot-level bootstrap.

| p | CNN − profile ΔLER | 95% root bootstrap CI | Candidate-only | Profile-only | Prediction disagreements |
|---:|---:|---|---:|---:|---:|
| 0.000 | +0.005714% | [+0.000000%, +0.017143%] | 1 | 0 | 1 |
| 0.004 | +0.017143% | [+0.000000%, +0.051429%] | 4 | 1 | 5 |
| 0.008 | +0.000000% | [+0.000000%, +0.000000%] | 0 | 0 | 0 |
| 0.012 | +0.000000% | [+0.000000%, +0.000000%] | 0 | 0 | 0 |
| 0.016 | +0.000000% | [+0.000000%, +0.000000%] | 0 | 0 | 0 |

## Prespecified secondary family (Holm adjusted)

| Comparison | Raw two-sided sign-flip p | Holm adjusted p |
|---|---:|---:|
| cnn minus fixed | 0.000309997 | 0.000929991 |
| cnn minus ridge | 0.249428 | 0.498855 |
| ridge minus profile | 0.498385 | 0.498855 |

Condition-specific intervals are descriptive and not individually confirmatory. Primary sign-flip inference assumes independent roots and approximate symmetry of root-level paired effects under its null.
