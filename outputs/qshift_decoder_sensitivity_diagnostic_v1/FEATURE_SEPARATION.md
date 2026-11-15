# Feature separation and estimator diagnosis

## Question and method

The detector-only estimator's training shots and simulator-parameter targets are in the 5,000-row training partition. Estimator errors below are evaluated on the separate 50-batch calibration partition (five conditions, ten roots, 500 rows per root). The 40-feature representation is the detector-bit marginal vector. The 45-feature representation appends one binary cofire feature for each detector pair derived from the deterministic burst DEM. Feature scaling is fitted on training data only; calibration data are never used to fit or tune coefficients.

Each condition summary is the mean over ten root-specific batch values. Intervals are unadjusted two-sided Student-t intervals over roots (df=9). The intervals assume independent roots, are descriptive at this small root count, and are not simultaneous intervals. Feature-by-feature tests and multiplicity-adjusted claims were not part of this diagnostic.

## Detector-marginal signal

The mean of the 40 detector marginal rates averaged over detector positions is 0.02748, 0.02736, 0.02859, 0.02977 and 0.03106 for `p=0, 0.004, 0.008, 0.012, 0.016`, respectively. The aggregate response spans only about 0.00358 over a 0.016 parameter range, and individual detector rates vary substantially across space. This representation carries some condition information, but the overall marginal level is weak and includes background detector activity from the rest of the circuit noise.

## Pair-cofire separation

The five pair features are `(D8,D10)`, `(D16,D18)`, `(D24,D26)`, `(D32,D34)`, and `(D36,D38)`. They come from the five pairwise burst signatures in the deterministic DEM; their exact mapping is also recorded in `feature_pair_map.json`.

| Pair cofire rate | `p=0` | `p=0.004` | `p=0.008` | `p=0.012` | `p=0.016` |
|---|---:|---:|---:|---:|---:|
| D8 & D10 | 0.0008 [0.00006, 0.00154] | 0.0042 [0.00249, 0.00591] | 0.0098 [0.00784, 0.01176] | 0.0140 [0.01176, 0.01624] | 0.0186 [0.01407, 0.02313] |
| D16 & D18 | 0.0012 [0.00020, 0.00220] | 0.0040 [0.00098, 0.00702] | 0.0070 [0.00506, 0.00894] | 0.0128 [0.00874, 0.01686] | 0.0142 [0.01108, 0.01732] |
| D24 & D26 | 0.0006 [-0.00009, 0.00129] | 0.0044 [0.00155, 0.00725] | 0.0074 [0.00358, 0.01122] | 0.0104 [0.00704, 0.01376] | 0.0156 [0.01224, 0.01896] |
| D32 & D34 | 0.0006 [-0.00009, 0.00129] | 0.0044 [0.00164, 0.00716] | 0.0074 [0.00516, 0.00964] | 0.0132 [0.01057, 0.01583] | 0.0154 [0.01287, 0.01793] |
| D36 & D38 | 0.0002 [-0.00025, 0.00065] | 0.0036 [0.00212, 0.00508] | 0.0068 [0.00454, 0.00906] | 0.0104 [0.00840, 0.01240] | 0.0180 [0.01477, 0.02123] |

Entries are mean cofire rates [95% root-level t interval]. A few low-rate intervals extend slightly below zero because these are unconstrained t intervals. All five means rise substantially from `p=0.008` to `0.016`; the nonzero baseline at `p=0` (0.0002–0.0012) also shows why the raw pair rate is not itself an unbiased estimate of burst `p`. The calibration partitions therefore contain direct, interpretable burst information, although the intervals overlap for some adjacent low-probability conditions.

## Estimation error and scaling

| Representation / fit | Overall calibration MAE | Overall calibration RMSE | Mean `p_hat` at p=0 | Mean `p_hat` at p=0.016 | Endpoint range of mean `p_hat` |
|---|---:|---:|---:|---:|---:|
| 40 marginals, frozen alpha=10 | 0.004765 | 0.005610 | 0.007950 | 0.008081 | 0.000131 |
| 45 features, alpha=10 diagnostic | 0.004709 | 0.005541 | 0.007856 | 0.008185 | 0.000329 |
| 45 features, training-only batch-CV alpha=0.01 | 0.004709 | 0.005540 | 0.007855 | 0.008185 | 0.000330 |

The five added features modestly reduce MAE by about 1.16% relative to the frozen 40-feature fit, but their endpoint estimate range is only about 2.1% of the true 0.016 range. The 40-feature endpoint range is about 0.8% of that true range. At `p=0` the 40-feature model overestimates by about 0.00795; at `p=0.016` it underestimates by about 0.00792. Similar errors remain for 45 features. The near-zero aggregate bias is cancellation across the balanced grid, not evidence of condition-wise calibration.

Standardization is applied to each feature before ridge fitting, so a simple unit mismatch between marginals and cofires is not the explanation. Row-wise training CV favors `alpha=1000`, while training-only CV that scores held-out batch means favors `alpha=0.01`. But the batch-CV selected fit barely differs from alpha=10 on the independent calibration set. Thus the row-wise objective does over-shrink for the batch-mean target, but correcting that choice does not solve the collapse.

Using deterministic evenly spaced subsets from each saved calibration batch, increasing the number of rows from 50 to 500 changes 40-feature MAE from 0.004774 to 0.004765 and 45-feature MAE from 0.004727 to 0.004709. This argues against calibration volume alone as the dominant cause within the tested range. It is not an independent resampling study, and it does not establish the sample size needed for another estimator.

## Interpretation

The evidence does not support “no observable burst signal”: the pair cofiring rates carry a clear condition trend. The failure is more specific: the frozen per-shot linear ridge model, trained on only 1,000 shots per setting with one scalar target repeated per shot, largely maps each 500-shot root batch back to the balanced-grid prior near `p=0.008`. The five direct pair indicators help only slightly under the same regression strategy. A targeted sufficient-statistic or likelihood estimator could plausibly estimate `p` better, but this feature finding alone says nothing about logical-error improvement. The matching decision-sensitivity result is the stricter bottleneck for this setting.
