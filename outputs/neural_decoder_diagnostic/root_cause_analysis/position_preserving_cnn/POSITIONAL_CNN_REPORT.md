# Q-SHIFT Position-Preserving CNN Diagnostic

## Decision

**GO for a larger, separately frozen development study of spatially preserving decoders; NO-GO for the prepared 100K run and for any claim of neural superiority.** The results strongly support that global average pooling is a major limitation in this small CNN pilot: position-preserving CNNs were consistently much better than the original pooled CNN on matched samples, including a pooled CNN with a similar parameter count. However, the position CNN did not beat the balanced MLP and all neural models remained worse than frozen PyMatching. The study has only three independent roots, and the reported thresholds were selected on the same validation partition used for the displayed logical-error rates, so those rates are optimistic development metrics.

## Question and implementation

The previous geometry-aware CNN used global average pooling. Pooling combines feature responses across grid locations, which can erase *where* a detector pattern occurred. This diagnostic adds two models while preserving the old CNN: (1) `PositionPreservingConv3DDecoder`, which flattens the 3-D feature map into a compact dense head, and (2) `CoordinateChannelConv3DDecoder`, which supplies normalized time, y, and x detector-coordinate channels alongside syndrome and occupancy channels. Both use the actual Stim mapping `(time=6, y=4, x=4)` with 40 occupied detector sites. A wider pooled CNN is included as a capacity control.

The compared models were the original pooled CNN (8 channels), pooled CNN (16 channels; capacity control), flattened position CNN, coordinate-channel CNN, and the existing direct MLP. Each used either balanced minibatches or weighted BCE. The weighted model logits were corrected by subtracting `log(pos_weight)`; balanced-minibatch logits were shifted back to the natural training prevalence. A temperature grid was fit on a separate validation calibration partition. This calibration correction is not a guarantee of calibrated posterior probabilities.

## Frozen development design

Three independent roots each generated 9,000 training and 9,000 validation shots across X-biased, balanced, and Z-biased regimes: **27,000 training + 27,000 validation shots**, plus 96 noiseless structural-check shots. Every model and training strategy used the same detector, observable, and PyMatching arrays within a root. All model families received the same epoch limit and optimizer-step count within a strategy. Balanced minibatching used twelve full 256-example batches per regime per epoch (3,072 presentations versus 3,000 unique examples; 2.4% oversampling), while weighted BCE traversed the 3,000 unique examples. Validation roots were split into equal monitor, calibration, and threshold-selection partitions. The threshold was selected on the threshold partition and evaluated there as well; therefore thresholded logical-error rates are selection-biased and are presented only as development diagnostics. No test samples were generated or accessed.

The 30 fits completed in **56.1 seconds** on **NVIDIA GeForce RTX 4050 Laptop GPU**. Peak CUDA allocated/reserved memory was 41.2/58.0 MiB; end-of-run host RSS was 1.22 GiB (peak host RSS was not monitored). All 30 fits verified CUDA forward/backward training. The seed inventory reports 312 unique streams and no collisions against 2,076 recoverable historical seed values and the prepared protocol allocation.

### Aggregate paired validation results

LER and recall are equal-regime means over three roots. The 95% intervals are paired root-level t intervals with 2 degrees of freedom; they are descriptive, very low-powered intervals, not confirmatory tests. Candidate-only / PM-only are summed shot-level paired failures across 9,000 matched threshold-partition shots.

| Model | Training | Parameters | LER | PyMatching LER | Neural − PM (95% root CI) | Positive recall | Candidate-only / PM-only |
|---|---|---:|---:|---:|---:|---:|---:|
| pooled cnn8 | balanced | 3,929 | 5.244% | 0.411% | +4.833 pp (+3.519 pp, +6.148 pp) | 8.786% | 447 / 12 |
| pooled cnn8 | weighted BCE | 3,929 | 5.433% | 0.411% | +5.022 pp (+4.614 pp, +5.431 pp) | 4.150% | 464 / 12 |
| pooled cnn16 capacity control | balanced | 14,769 | 3.889% | 0.411% | +3.478 pp (+1.854 pp, +5.101 pp) | 68.903% | 325 / 12 |
| pooled cnn16 capacity control | weighted BCE | 14,769 | 5.167% | 0.411% | +4.756 pp (+4.223 pp, +5.288 pp) | 17.581% | 440 / 12 |
| position flat cnn | balanced | 13,413 | 1.267% | 0.411% | +0.856 pp (+0.511 pp, +1.200 pp) | 83.681% | 87 / 10 |
| position flat cnn | weighted BCE | 13,413 | 1.944% | 0.411% | +1.533 pp (+0.954 pp, +2.113 pp) | 78.811% | 150 / 12 |
| coordinate channel cnn | balanced | 13,737 | 1.689% | 0.411% | +1.278 pp (+0.197 pp, +2.358 pp) | 81.634% | 125 / 10 |
| coordinate channel cnn | weighted BCE | 13,737 | 2.311% | 0.411% | +1.900 pp (+0.389 pp, +3.411 pp) | 68.572% | 183 / 12 |
| balanced mlp | balanced | 13,569 | 1.267% | 0.411% | +0.856 pp (+0.292 pp, +1.419 pp) | 83.302% | 89 / 12 |
| balanced mlp | weighted BCE | 13,569 | 1.600% | 0.411% | +1.189 pp (+0.625 pp, +1.753 pp) | 80.169% | 120 / 13 |

The balanced position CNN matched the balanced MLP on mean LER (1.267%) and was markedly better than the original CNN (5.244%). The coordinate-channel CNN reached 1.689%. PyMatching remained best at 0.411%. For the flattened balanced CNN, paired candidate-only and PM-only failures were 87 and 10; its neural-minus-PM difference was +0.856 percentage points (root t interval +0.511 to +1.200 pp). Thus this diagnostic supports a CNN representation improvement, not an improved decoder over PyMatching.

### Balanced-minibatch results by generating regime

Counts pool the three independent roots (3,000 threshold-partition shots per regime). Confusion is shown as TN/FP/FN/TP for predicting the observable-flip label. `paired-only` counts compare logical failures against PyMatching.

| Model | Regime | Neural LER | Positive recall | TN/FP/FN/TP | Neural-only / PM-only | PM LER |
|---|---|---:|---:|---:|---:|---:|
| pooled cnn8 | x_biased | 7.233% | 10.379% | 2759/6/211/24 | 201 / 3 | 0.633% |
| pooled cnn8 | balanced | 6.000% | 9.525% | 2802/10/170/18 | 175 / 8 | 0.433% |
| pooled cnn8 | z_biased | 2.500% | 6.453% | 2920/2/73/5 | 71 / 1 | 0.167% |
| pooled cnn16 capacity control | x_biased | 4.867% | 70.284% | 2689/76/70/165 | 131 / 4 | 0.633% |
| pooled cnn16 capacity control | balanced | 4.567% | 67.509% | 2736/76/61/127 | 131 / 7 | 0.433% |
| pooled cnn16 capacity control | z_biased | 2.233% | 68.917% | 2879/43/24/54 | 63 / 1 | 0.167% |
| position flat cnn | x_biased | 2.167% | 74.851% | 2759/6/59/176 | 49 / 3 | 0.633% |
| position flat cnn | balanced | 1.333% | 86.094% | 2798/14/26/162 | 32 / 5 | 0.433% |
| position flat cnn | z_biased | 0.300% | 90.098% | 2921/1/8/70 | 6 / 2 | 0.167% |
| coordinate channel cnn | x_biased | 2.633% | 71.858% | 2752/13/66/169 | 63 / 3 | 0.633% |
| coordinate channel cnn | balanced | 1.700% | 82.944% | 2793/19/32/156 | 44 / 6 | 0.433% |
| coordinate channel cnn | z_biased | 0.733% | 90.098% | 2908/14/8/70 | 18 / 1 | 0.167% |
| balanced mlp | x_biased | 2.267% | 74.840% | 2756/9/59/176 | 51 / 2 | 0.633% |
| balanced mlp | balanced | 1.267% | 85.053% | 2802/10/28/160 | 32 / 7 | 0.433% |
| balanced mlp | z_biased | 0.267% | 90.013% | 2922/0/8/70 | 6 / 3 | 0.167% |

Positive recall improved strongly for both position-aware CNNs relative to pooled CNN8. The false-positive cost is visible in the X-biased and balanced conditions. Regime differences should not be generalized beyond these simulated distance-3, five-round Z-memory settings.

### Position versus capacity

The flattened and coordinate-channel models each have parameter counts close to the MLP and the wider pooled control: 13,413; 13,737; 13,569; and 14,769, respectively. The original pooled CNN has 3,929 parameters. Increasing pooled width improved balanced-minibatch LER from 5.244% to 3.889%, but the pooled capacity control remained worse than the flattened CNN. Under balanced minibatches, flattened CNN minus pooled CNN16 was −2.622 pp (root t interval −4.586 to −0.659 pp); coordinate-channel minus pooled CNN16 was −2.200 pp (−4.427 to +0.027 pp). Flattened CNN minus pooled CNN8 was −3.978 pp (−5.367 to −2.589 pp). These comparisons make parameter count alone an unlikely explanation, but do not isolate pooling from all other architectural differences.

The flattened CNN and balanced MLP had essentially identical average LER; per-root flattened-minus-MLP differences were +0.10, −0.13, and +0.03 percentage points. The coordinate-channel model did not improve on the flattened model in this pilot. Explicit coordinates may be redundant when flattening already preserves location.

### Sampling strategy and probability calibration

Balanced minibatches had lower mean threshold-partition LER than weighted BCE for all five model families in these three roots. The weighted approach used the training-only class prevalence to compute `pos_weight`, then applied the appropriate logit offset before temperature calibration. Temperature fitting used only the separate calibration partition. Calibration metrics (Brier score, NLL, and 10-bin ECE) are retained per root in `VERIFIED_RESULTS.json`; root means are summarized below. The threshold partition was then used to choose an LER threshold, so its LER is not an unbiased estimate. Calibration is exploratory and does not justify a probability claim for deployment.

| Model | Training | Brier raw → temp (calibration split) | ECE raw → temp (calibration split) | Temp Brier / ECE (threshold split) |
|---|---|---:|---:|---:|
| pooled cnn8 | balanced | 0.0403 → 0.0402 | 0.0195 → 0.0203 | 0.0423 / 0.0203 |
| pooled cnn8 | weighted BCE | 0.0411 → 0.0411 | 0.0190 → 0.0189 | 0.0435 / 0.0237 |
| pooled cnn16 capacity control | balanced | 0.0299 → 0.0298 | 0.0142 → 0.0146 | 0.0307 / 0.0171 |
| pooled cnn16 capacity control | weighted BCE | 0.0373 → 0.0370 | 0.0148 → 0.0128 | 0.0383 / 0.0148 |
| position flat cnn | balanced | 0.0116 → 0.0115 | 0.0056 → 0.0055 | 0.0120 / 0.0082 |
| position flat cnn | weighted BCE | 0.0162 → 0.0162 | 0.0107 → 0.0106 | 0.0179 / 0.0132 |
| coordinate channel cnn | balanced | 0.0149 → 0.0148 | 0.0072 → 0.0065 | 0.0156 / 0.0093 |
| coordinate channel cnn | weighted BCE | 0.0195 → 0.0194 | 0.0097 → 0.0090 | 0.0207 / 0.0119 |
| balanced mlp | balanced | 0.0108 → 0.0111 | 0.0066 → 0.0090 | 0.0116 / 0.0080 |
| balanced mlp | weighted BCE | 0.0142 → 0.0143 | 0.0088 → 0.0106 | 0.0154 / 0.0110 |

## Root cause assessment

**Supported:** the original pooled CNN’s translation-invariant global pooling is a substantial candidate cause of its poor positive recall in this geometry. The position-aware CNNs improved over both the 8-channel original and the similarly sized 16-channel pooled control on every development root under balanced sampling. Since a similarly parameterized pooled model did not reproduce the improvement, increased parameter count alone is insufficient to explain it.

**Not established:** this is not a clean causal ablation of absolute position alone. The flattened head changes feature interactions as well as retaining coordinates; the coordinate-channel model also changes its input representation. Only three roots were run, threshold selection and displayed LER share one partition, several model/strategy comparisons were made, and no independent test set was opened. No neural model beat PyMatching. The large LER differences versus PM are all in the wrong direction.

## Validation, artifacts, and reproducibility

The Stim geometry and label tests passed; the full dashboard suite passed **47/47** before sampling. A further exact coordinate-ID regression test was added after the run, and the final full suite passed **48/48**. The independent saved-run audit then loaded every best checkpoint, re-evaluated all 30 models, re-selected all temperatures and thresholds from the saved validation partitions, and exactly reproduced 90 model-by-regime prediction arrays and all paired counts. It also checked the saved validation detector/label arrays against each prediction archive. No simulator call was made by the independent audit. The frozen runner's final CSV export had a derived-field naming bug after all results had been saved; `RUNNER_PARTIAL_PER_ROOT.csv` preserves that header-only partial output. The exact frozen runner is retained, and a documented export-only patch fixes future CSV serialization; completed CSVs here were reconstructed independently.

From the repository root, verify the saved run without sampling:

```powershell
python outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/audit_saved_run.py
python -m unittest discover -s dashboard/tests -v
python -m compileall -q dashboard outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn
```

For an exact replay, use a clean copy of the repository with the same relative directory structure; the runner refuses to overwrite its existing frozen output. Replaying the same seed inventory is reproducibility, not an independent replication. The independent test allocation remains sealed.

## Recommendation

**GO** to a larger development-only replication focused on the flattened position-preserving CNN, balanced MLP, and a strict parameter-matched pooled control; include more independent roots and a separate final evaluation partition with thresholds frozen before evaluation. Do not run the prepared 100K training protocol yet. The current evidence indicates position preservation addresses much of the CNN collapse, but does not establish a useful quantum decoder or an advantage over PyMatching.

See `VERIFIED_RESULTS.json`, `per_root_results.csv`, `per_regime_results.csv`, `aggregate_results.csv`, `development_samples.npz`, `predictions_rep*.npz`, and the per-fit checkpoints for complete evidence.
