# Q-SHIFT CNN Architecture Audit — Stage 1

## Scope and evidence reviewed

This audit reads source, frozen protocols, persisted development metrics, and prior audit reports. It does not open any independent-test allocation, train a model, or alter historical files.

Key files reviewed:

- `dashboard/structured_decoder.py` — sparse Stim detector-grid encoding, pooled 3-D CNN, flattened position-preserving CNN, coordinate-channel CNN, and residual XOR helpers.
- `dashboard/structured_training.py` — streaming model fitting, balanced batches, natural-prevalence logit correction, monitor-selected checkpoint restoration, calibration and threshold partitions, and final-development evaluation path.
- `outputs/neural_decoder_diagnostic/autonomous_development/experiment.py` — exact `ResidualPositionCNN` implementation used by the 750K development experiment.
- `outputs/neural_decoder_diagnostic/autonomous_development/PROTOCOL.md`, `config.json`, `ANALYSIS_PLAN.json`, and `FREEZE_FINAL_V3.json` — frozen splits, training budgets, comparisons, and selection rules.
- `outputs/neural_decoder_diagnostic/autonomous_development/run/FINAL_MORNING_REPORT.json` and `.md` — saved per-job and aggregate results for the completed development run.
- `outputs/neural_decoder_diagnostic/root_cause_analysis/ROOT_CAUSE_REPORT.md` and `POSITIONAL_CNN_REPORT.md` — label, imbalance, geometry, threshold, and prior architecture audits.
- `outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/post_run_audit/FINAL_RESEARCH_REPORT_AUDITED.md` — independent residual-sprint recomputation and failed scaling gate.
- `outputs/phase3a_correlated_noise_preflight/CORRELATED_NOISE_HYPOTHESIS.md`, `BASELINE_FAIRNESS_ANALYSIS.md`, `config.json`, and `PHASE3A_FINAL_REPORT.md` — synthetic spatial-burst assumptions and the no-production-sampling status.
- `outputs/phase2b_pauli_bias/noise_model.py` and `outputs/phase3a_correlated_noise_preflight/simulator.py` — actual circuit and correlated-burst construction.

The repository records the 750K autonomous development run as completed: 50/50 model jobs, five roots, and no independent-test access. It also records the 1.665M-shot hybrid residual sprint as failed at controller finalization; its saved scientific evidence was independently audited, and its historical status remains failed. Phase 3A is a deterministic circuit/decoder preflight only, not a neural performance experiment.

## Strongest existing CNN and exact protocol

The strongest recurring CNN is the **`residual_position_cnn`** from `autonomous_development/experiment.py`. Its input is the actual 40-detector sparse `(time=6, y=4, x=4)` grid plus its occupancy mask and the frozen PyMatching logical prediction. It predicts `observable XOR PyMatching_prediction`; the final logical prediction is `PyMatching_prediction XOR thresholded_residual`. This is parity-decoder scoring, not application of a physical correction gate.

The saved job metadata reports **13,429 trainable parameters**. In the 750K experiment it used 10,000 training shots per regime (`x_biased`, `balanced`, `z_biased`), balanced minibatches, batch size 256, AdamW learning rate 0.003 and weight decay 0.0001, StepLR after five epochs with gamma 0.5, at most 10 epochs, and patience 3. The best checkpoint was selected by monitor NLL and restored before probability calibration and threshold selection. Temperature was selected on a separate calibration split; one threshold was selected on a separate threshold-selection split. Five development roots then received one 10,000-shot-per-regime final-development score. No independent test was allocated or accessed.

For the five residual-CNN jobs, final-development counts were **689/150,000 errors (0.4593% LER)** versus frozen PyMatching **653/150,000 (0.4353%)**. There were **49 candidate-only failures and 13 PyMatching-only failures**, a net 36 more residual-CNN errors. The residual network disagreed with PyMatching on only 62/150,000 shots (0.0413%), showing that it mostly copied the strong baseline and its few changed decisions were net harmful. The five-root mean paired effect was +0.024 percentage points, with a reported descriptive 95% root-t interval of −0.00107 to +0.04907 percentage points. This interval is not a confirmatory inference.

The direct position-preserving CNN at 30,000 training shots per regime had 1.0400% mean LER versus 0.4353% for PyMatching. Across the earlier three-root positional diagnostic, flattening substantially improved the CNN over global pooling and a similarly sized pooled control, but still lost to PyMatching. That earlier diagnostic also reused the threshold-selection partition for its displayed thresholded score, making that score selection-biased. The later five-root experiment separated threshold selection from final-development scoring.

## Failure diagnosis

### Confirmed findings

1. **Class imbalance caused an easy collapse mode.** The root-cause audit measured 349/6,000 direct positives (5.82%) and 35/6,000 residual positives (0.58%) in its audited training sample. Early direct models and a pooled CNN often predicted all negative. A dropout-disabled tiny-set check showed that both an MLP and CNN can memorize a balanced set, so the CNN is not categorically unable to learn the label.
2. **Global average pooling discards useful location information in this pilot.** The position-preserving architecture materially improved on the original pooled CNN and a similar-capacity pooled control across the three development roots. This supports position loss as a substantial limitation of that pooled model, but is not a clean causal isolation of pooling.
3. **The later residual CNN learned few decisions beyond PyMatching.** Its 62 changed predictions yielded 13 corrections of baseline failures and 49 new failures. High positive recall alone was not sufficient to lower total logical error.
4. **Weighted BCE score handling required correction.** A prior report thresholded positive-weighted logits as though they were natural posterior probabilities. The later training implementation corrects the odds shift using training prevalence. This is now included as a required audit point for any new training path.
5. **The basic detector, label, geometry, and XOR conventions passed their saved audits.** Stim supplies binary detector and observable arrays; the 40 detector IDs map bijectively to 40 occupied coordinates; residual targets and final XOR correction are aligned.
6. **Decoder copying and weak residual utility are real risks.** The current residual model already receives the PyMatching bit, yet the learned candidate almost always returns the baseline after thresholding. More training alone has not justified a scale-up: the hybrid sprint found no improvement and its conservative gate selected zero corrections.

### Not established

- Calibration quality does not explain away the LER gap. Thresholds and temperature were selected only on development partitions in the later run, but probability calibration is not a guarantee of better decisions.
- Overfitting is not established as the sole failure. The direct position CNN improved with larger nested training budgets in the 750K development study but remained worse than PyMatching. Results also depend on the five-root setup and the simulated distance-3, five-round Z-memory family.
- No evidence says the chosen synthetic burst rate or location represents real hardware. Phase 3A only checks plumbing and graph compatibility.
- No neural or hybrid model has established a statistically reliable advantage over PyMatching.

## Practical conclusion

The rational next architecture test is a **small, paired residual-CNN development preflight**, because the residual CNN is the closest existing model to PyMatching and its failure is specifically a precision/utility problem. A second compact factorized space/time variant is justified as a controlled implementation comparison. Coordinate-channel expansion, more global pooling, and larger unstructured models are not selected: the prior coordinate CNN did not beat the flattened model, while the pooled family was consistently weaker. The new candidates must first pass the isolated shape, seed, parameter, and paired-decoder diagnostics in this versioned directory. Their forward checks are not evidence of learning or improved LER.
