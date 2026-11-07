# Q-SHIFT Neural Decoder Collapse: Root-Cause Report

## Decision

**NO-GO for the proposed supervised 100K run.** The labels, Stim/PyMatching alignment, and actual detector-coordinate mapping are valid. Class imbalance and short training contribute to collapse, and a balanced-batch MLP learns useful positive recall on development data. However, even the best new candidate has higher logical error than frozen PyMatching. The CNN still fails to generalize positive corrections on the fresh multi-regime validation stream. No test data were generated or opened.

## Audit of the previous run

The three circuit conditions share one rotated Z-memory circuit structure: distance 3, five rounds, 40 detector bits, and one observable. Stim returns detector samples with shape `(shots, 40)` and the observable flip with shape `(shots,)`; `sample()` checks these shapes and binary values. The no-noise circuit returns zero detectors and zero observable flips. The implemented logical error is `prediction XOR observable`; the residual target is `PyMatching_prediction XOR observable`, and its correction is XORed with the PyMatching bit. Fresh deterministic tests now check these conventions and alignment directly.

The previous run's saved validation data were independently re-counted from all 24 NPZ batches and matched its JSON totals exactly: identity **156/3,000**, PyMatching **11/3,000**, direct MLP **156/3,000**, unweighted CNN **156/3,000**, weighted CNN **183/3,000 at threshold 0.50**, and residual MLP **11/3,000**. The residual network's predictions equal PyMatching on all 3,000 shots. The previous `FINAL_MANIFEST.json` matched all 71 listed files at the start of this audit; a later, documented calibration-code correction changes the current training-source hash. Historical results, checkpoints, and their manifest were not overwritten.

The previous training target prevalence was **349/6,000 (5.82%)** for direct prediction and **35/6,000 (0.58%)** for residual correction. On validation, direct target positives were 156/3,000 and residual positives were 11/3,000. For direct MLP and unweighted CNN, every selected-threshold validation prediction was negative. At threshold 0.50 the weighted CNN predicted positive on 33/3,000 shots, correctly on 3; it had 30 false positives and 153 false negatives. Its selected threshold 0.75 produced zero positive predictions.

### Confirmed causes and limits

| Finding | Evidence | Interpretation |
|---|---|---|
| Severe class imbalance | 5.82% direct and 0.58% residual training prevalence | The all-negative classifier receives strong support from the majority class, especially for residual training. |
| Insufficient optimization in the original run | Only two epochs; best checkpoints were epoch 2 for MLP/unweighted CNN/residual and epoch 1 for weighted CNN | The 256-shot tiny-set CNN needed the higher tested learning rate to memorize both classes. This supports learning-rate/optimization sensitivity, not proof that longer training will generalize. |
| Weighted-score calibration bug | Positive-weight BCE's ideal logit is `natural_posterior_logit + log(pos_weight)` | The old report thresholded weighted scores at 0.25/0.50/0.75 as if they were natural posterior probabilities. With the old weight near 16.2, threshold 0.50 corresponds roughly to the natural class prevalence; the natural-posterior 0.50 threshold is near 0.94 in weighted-score space. Old weighted probability calibration metrics therefore were not natural-posterior calibration estimates. |
| Label/circuit error not found | Stim shapes, binary labels, no-noise behavior, XOR convention, paired PyMatching decoding all pass | Label polarity does not explain the collapse. |
| Detector geometry not found to be corrupt | Actual Stim coordinates map the 40 detector IDs bijectively to a sparse `(time=6, y=4, x=4)` tensor with 40 occupied cells | The earlier unit test used a synthetic `(5,1,8)` layout and did not test the actual circuit. A regression test now covers the real geometry. |
| Exact feature ambiguity is small in this sample | In fresh 9,000-shot training data, 1,134 unique syndromes; 9 syndrome vectors had both labels (67 rows); best deterministic lookup accuracy on this finite sample is 99.90% | Conflicts are real and will grow with data, but do not explain the observed 5% all-negative error rate. This is a finite training-sample bound, not an achievable generalization guarantee. |

The previous saved model probability histograms were also reproduced. Direct MLP placed 2,829/3,000 scores in `[0,0.1)`, 162 in `[0.1,0.2)`, and 9 in `[0.2,0.3)`. The unweighted CNN placed all 3,000 below 0.1. Weighted CNN placed 2,967 in `[0.4,0.5)` and 33 in `[0.5,0.6)`; these weighted scores require logit correction before posterior interpretation. Direct MLP's average positive-class saved-score log loss was about 2.37 versus 0.061 on negatives; unweighted CNN was about 3.09 versus 0.047. The output-layer bias alone was not strongly negative (direct −0.032; unweighted CNN +0.054; weighted CNN +0.145), so the collapse is not explained by a single output bias.

At the saved best checkpoints, positive-only gradient norms exceeded negative-only norms (direct MLP 3.12 vs 0.229; unweighted CNN 7.87 vs 0.376; residual MLP 9.17 vs 0.063, using up to 256 examples per class). This does not negate imbalance: positive samples are rare in ordinary batches, especially for the residual target. Gradient norms were recomputed on the new development training samples and are diagnostic summaries, not training-history measurements.

## Bounded development diagnostics

### Fixed-set memorization

The deterministic, dropout-disabled 256-shot balanced subset contained 128 positive and 128 negative detector patterns. One duplicate pattern had conflicting labels, giving a finite-subset deterministic accuracy ceiling of **255/256 (99.61%)**. With AdamW and BCE, the MLP reached 255/256 at both tested learning rates (0.001 and 0.01). The CNN reached 221/256 (86.3%) at 0.001 and **254/256 (99.22%)** at 0.01, with both-class recalls 98.44% and 100%. Thus the CNN can represent and optimize the target on a small fixed set; the prior collapse is not an absolute inability to learn either class.

A separate 16-positive/240-negative memorization control showed the expected interaction: at LR 0.001 the unweighted CNN predicted all negative (0% positive recall), while weighted BCE reached 100% positive recall but made 9 false positives. At LR 0.01 the unweighted CNN reached 93.75% positive recall. These are in-sample memorization diagnostics only.

### Fresh paired multi-regime development comparison

New independent development streams generated 9,000 training and 4,500 validation shots (3,000/1,500 per regime). All strategies used the same samples within each split. Training was limited to 15 epochs; checkpoints were selected by corrected validation log loss, then thresholds were selected on the same development validation stream. A 5,000-resample regime-stratified **shot** bootstrap is reported below for description only. It does not provide independent-root uncertainty because only one validation seed stream per regime was run. The exact shot-level McNemar values are not confirmatory and are not evidence of generalization.

| Model / training strategy | Train shots per regime | Selected validation LER | PyMatching LER | Candidate-only / PyMatching-only failures | Paired shot-bootstrap 95% CI for LER difference |
|---|---:|---:|---:|---:|---:|
| MLP, natural unweighted | 3,000 | 2.64% | 0.53% | 107 / 12 | +1.67 to +2.60 percentage points |
| MLP, natural weighted | 3,000 | 2.60% | 0.53% | 102 / 9 | +1.62 to +2.53 pp |
| MLP, balanced minibatches | 3,000 | **1.78%** | 0.53% | **66 / 10** | **+0.89 to +1.64 pp** |
| CNN, natural unweighted | 3,000 | 5.44% | 0.53% | 232 / 11 | +4.24 to +5.58 pp |
| CNN, natural weighted | 3,000 | 5.42% | 0.53% | 231 / 11 | +4.22 to +5.56 pp |
| CNN, balanced minibatches | 3,000 | 5.42% | 0.53% | 231 / 11 | +4.24 to +5.56 pp |

The best result, balanced MLP at 3,000 training shots per regime, made **80/4,500** errors versus PyMatching's **24/4,500**. It predicted corrections on 5.93% of X-biased, 5.73% of balanced, and 2.73% of Z-biased validation shots; positive recall was 71.8%, 78.3%, and 90.9%. Per-regime MLP errors versus PyMatching were X-biased 41 vs 13, balanced 34 vs 6, and Z-biased 5 vs 5. The paired difference was **+1.244 percentage points** (neural minus PyMatching), with 66 neural-only and 10 PyMatching-only failures. The reported shot-level McNemar p-value is 2.96×10⁻¹¹, but selection and evaluation share a single validation stream and multiple development policies were compared. Treat the result as clear development underperformance, not as an independent inferential test.

Increasing training from 1,500 to 3,000 shots per regime and using balanced batches lowered MLP validation LER from 2.51% to 1.78%, but did not close the gap to PyMatching. The CNN's balanced-batch positive recall remained under 8% at the selected thresholds. A CNN that can memorize 256 examples but still collapses on fresh validation suggests a generalization/representation or optimization issue beyond class prevalence alone. Loss of absolute spatial information from global average pooling is a plausible hypothesis, not a confirmed cause.

## Code correction and safeguards

The worker now subtracts `log(pos_weight)` from logits before probability calibration, validation loss/thresholding, and reporting for positive-weighted BCE models. The saved best-model artifact records its training positive weight. This is the exact ideal correction for the weighted-BCE odds shift under a correctly specified, optimized model; it is not a calibration guarantee. Tests verify the algebra and the inference path. The old result files were preserved and not rewritten.

Balanced minibatches are evaluated only in the bounded diagnostic script. They are **not** the default in the 100K worker: the exploratory MLP improvement still loses to PyMatching, and introducing a different sampling protocol into the prepared 100K experiment would require a new pre-run protocol and seed freeze. Regime identity is simulator metadata, not a runtime detector input; no regime-conditioned model was trained.

## Test and evidence status

- `python -m unittest discover -s dashboard/tests -v`: **45 passed** after the calibration and real-geometry regression tests were added.
- `python -m compileall -q dashboard outputs/neural_decoder_diagnostic/root_cause_analysis`: **passed**.
- `node --check dashboard/static/app.js`: **passed**.
- Prior artifact hashes: **71/71 matched before the documented source correction**. A post-correction audit finds **69/71 unchanged**; the only changed entries are `dashboard/structured_training.py` and its direct regression test. All historical results, datasets, and checkpoints retain their old hashes.
- Fresh diagnostic: **13,500** train/validation samples, plus 96 noiseless structure-check shots; GPU RTX 4050, 65.5 seconds end-to-end, peak RSS 1.57 GB, peak CUDA allocated 25.4 MB.
- Fresh seed screen: **122 unique proposed RNG values; zero overlaps** with 2,076 recoverable historical seed values, the prior 81-value development allocation, or the 397-value prepared 100K inventory.
- Held-out test samples: **0 generated or accessed**. No 100K, overnight, or large-scale job was started.

## Recommendation

Keep PyMatching as the default. Do not authorize 100K yet. Before reconsidering, implement a separately frozen development protocol with multiple independent train/validation roots, the corrected weighted-score treatment, a balanced-sampling option, and a CNN that retains absolute detector position (or a non-convolutional spatial baseline). Require a practical validation gain over PyMatching across roots before any held-out study. The current evidence shows that neural learning is possible, but not that it improves decoding.
