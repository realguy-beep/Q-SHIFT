# Q-SHIFT decoder sensitivity and identifiability diagnostic

## Finding

The zero-gain result is consistent with two bottlenecks, with decoder decision sensitivity the decisive one. The 40-marginal ridge profile is nearly a constant estimate near the balanced-grid mean. Adding the five detector-pair cofire features reveals condition-level signal, but barely improves the frozen calibration error. More importantly, the estimated-profile matcher makes no prediction changes relative to the pooled matcher on the saved evaluation detector rows. A true-​parameter matcher changes only 10 of 80,000 nonzero-condition predictions. Thus a better estimator of this same scalar burst probability has little opportunity to change logical predictions under this matching representation on these samples.

This is a detector-only mechanism diagnosis consistent with the previously reported zero improvement. This report does **not** recompute or validate any logical-error rate, because evaluation observable labels were not loaded.

## Scope and partitions

- Source reference: `3a3f1dd2a14769dea645045c2be4acc8c1ecf739`.
- Training: 5,000 detector rows (1,000 for each of five configured burst probabilities) and the corresponding simulator-parameter targets. These are the only labels used to fit or cross-validate the diagnostic estimators.
- Calibration: 50 disjoint batches, each 500 detector rows, across ten roots and five conditions. Their known generating probabilities are used only to calculate estimation error and condition-level summaries.
- Evaluation: 100,000 saved rows, 20,000 per condition. The diagnostic opens only the `detectors` member of each evaluation archive; it never requests `observables` and does not use logical outcomes for any selection or inference.
- Circuit/DEM construction is deterministic. No Stim sampler API was called; the recorded sampler-call count is zero.

## Estimator results

The frozen 40-feature estimator uses standardized detector bits, ridge `alpha=10`, an intercept, and output clipping to `[0, 0.016]`. The 45-feature diagnostic appends the five DEM-derived pair-cofire indicators. It uses the same training and calibration partitions.

| True burst probability | 40-feature mean estimate (root-level 95% CI) | 40-feature MAE (root-level 95% CI) | 45-feature mean estimate (root-level 95% CI) | 45-feature MAE (root-level 95% CI) |
|---:|---:|---:|---:|---:|
| 0.000 | 0.007950 [0.007931, 0.007969] | 0.007950 [0.007931, 0.007969] | 0.007856 [0.007835, 0.007876] | 0.007856 [0.007835, 0.007876] |
| 0.004 | 0.007964 [0.007945, 0.007982] | 0.003964 [0.003945, 0.003982] | 0.007920 [0.007889, 0.007950] | 0.003920 [0.003889, 0.003950] |
| 0.008 | 0.007990 [0.007967, 0.008014] | 0.000028 [0.000016, 0.000040] | 0.007999 [0.007963, 0.008035] | 0.000041 [0.000024, 0.000059] |
| 0.012 | 0.008036 [0.008016, 0.008055] | 0.003964 [0.003945, 0.003984] | 0.008085 [0.008055, 0.008115] | 0.003915 [0.003885, 0.003945] |
| 0.016 | 0.008081 [0.008061, 0.008102] | 0.007919 [0.007898, 0.007939] | 0.008185 [0.008150, 0.008220] | 0.007815 [0.007780, 0.007850] |

Intervals are two-sided Student-t intervals over the ten calibration roots (9 degrees of freedom). The MAE intervals apply the same calculation to the ten root-level absolute errors. They are descriptive, conditional on treating roots as independent, and unadjusted across conditions/features; ten roots are too few to support strong asymptotic claims.

Across all 50 calibration batches, the frozen 40-feature estimator has MAE `0.004765` and RMSE `0.005610`. The 45-feature estimator has MAE `0.004709` and RMSE `0.005541`: a 1.16% relative MAE reduction and 1.23% relative RMSE reduction. A constant estimate of `0.008` on this equally weighted five-condition grid has MAE `0.004800` and RMSE `0.005657`; the 45-feature estimator therefore improves only modestly over that constant reference. Overall bias is near zero because overestimates at low `p` cancel underestimates at high `p`; it must not be mistaken for calibration accuracy.

Training-only row-wise five-fold CV chose `alpha=1000` for both feature sets, while batch-mean CV chose `alpha=0.01`. Batch-mean CV was designed to match the calibration estimand. Using its selected alpha barely changed external calibration MAE/RMSE from `alpha=10` (45 features: MAE `0.0047093`, RMSE `0.0055404`). This makes severe regularization a secondary contributor, not the main explanation. Details and the feature evidence are in [FEATURE_SEPARATION.md](FEATURE_SEPARATION.md).

## Decoder results without labels

The pooled estimate reconstructed from the detector-only calibration batches is `0.008004311733110277`. The per-root 40-feature profile predictions were compared with that pooled matcher on the same saved evaluation detector rows. They changed **0 of 100,000** predictions. Reconstructed true-`p` matchers changed 3/20,000 at `p=0`, 5/20,000 at `p=0.004`, 0/20,000 at `p=0.008`, 4/20,000 at `p=0.012`, and 1/20,000 at `p=0.016`.

Across the 80,000 nonzero-condition rows, the true-`p` arm differs on 10 rows (fraction `0.000125`). Without labels, this gives only a mechanical bound: changing at most 10 predictions can change the nonzero pooled error count by at most 10, or the LER by at most `0.000125` on these exact rows. It does not establish the direction or actual LER effect. The graph shows the five burst-edge weights do change with `p`; the selected predictions almost never change. See [DECODER_DECISION_SENSITIVITY.md](DECODER_DECISION_SENSITIVITY.md).

## Diagnosis and limitation

The balanced training grid gives the ridge model an intercept of `0.008`. On calibration, both models remain close to that value at every condition. The direct pair features are measurably informative, so the failure is not absence of all detector signal. The current linear, per-shot regression does not translate that signal into a useful per-batch estimate. Increasing the batch subset from 50 to 500 rows barely changes MAE (`0.004774` to `0.004765` for 40 features; `0.004727` to `0.004709` for 45), so the tested range does not support “calibration count alone” as the explanation. These nested deterministic subsets are not independent sample-size experiments.

Even perfect scalar `p` inference has little decision leverage in this fixed graph-matching family on these data: the oracle disagreement fraction is only `0.0125%` over nonzero rows. That makes decoder sensitivity the limiting factor for a material LER gain from scalar probability adaptation. The diagnostic cannot show whether a different decoder family would help; that requires a separately specified, independently evaluated study.

## Reproduction and evidence

From the repository root, with Python 3.12.10, NumPy 2.5.3, Stim 1.16.0 and PyMatching 2.4.0:

```powershell
python -m unittest discover -s outputs/qshift_decoder_sensitivity_diagnostic_v1/tests -v
python outputs/qshift_decoder_sensitivity_diagnostic_v1/diagnostic.py --sample-root <local-V1.1-saved-samples-directory>
python outputs/qshift_decoder_sensitivity_diagnostic_v1/build_manifest.py
```

The runner writes `diagnostic_results_v1_4.json`. It records hashes of canonical training/calibration arrays and of each condition's concatenated evaluation detector rows, not raw archives. The full input sample directory is local and ignored; no data archives, seeds, labels, or absolute machine paths are included. Four earlier diagnostic JSON iterations remain untouched locally and are excluded by the directory-local `.gitignore`; v1.4 is the published canonical output. The JSON flags `sampling_api_calls=0` and `evaluation_observable_members_loaded=false`.
