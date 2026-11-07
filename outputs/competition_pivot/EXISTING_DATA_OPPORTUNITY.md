# Existing-data opportunity audit

## Evidence reused

The analysis reads only the saved development evidence in outputs/conditional_go_resolution/DEVELOPMENT_RAW_EVIDENCE.npz and UTILITY_PER_ROOT.csv. It does not run Stim, change the saved experiments, or use any Stage 2 held-out labels for policy fitting.

- Circuit: Stim rotated Z-memory, distance 3, five rounds; 40 detectors and one logical observable.
- 24 independent calibration/evaluation roots, eight per generating condition; 1,024 calibration detector shots and 4,096 paired evaluation shots per root.
- Total: 24,576 calibration shots and 98,304 evaluation shots.
- Nine candidate noise-model / PyMatching configurations; decoder selection is recomputed from calibration detector marginals only. Observable labels are omitted from the feature pipeline.
- The source evidence was previously independently checked: template profiles, all 24 choices, all 72 saved decoder prediction arrays, paired errors, and raw detector/observable binary arrays matched. See outputs/conditional_go_resolution/INDEPENDENT_VERIFICATION.json.

## Headroom available to a gate

The calibration-selected candidate and frozen pooled decoder disagree on only **225 / 98,304 = 0.229%** of evaluation shots. Across those differences, the selected candidate is correct while pooled is wrong on 117; the selected candidate is wrong while pooled is correct on 108. Thus the total candidate decoder improves only 9 errors overall (672 vs 681), and even a label-aware per-shot selector could at most exploit those 225 contested predictions. This is a ceiling, not a deployable result.

At root level, the selected candidate had fewer errors than pooled on 15 roots, more on 6, and tied on 3. Root-level observed effects are sparse (one or a few logical events in many roots), so a confidence gate must predict utility with considerable precision before its threshold can be trusted.

## Observable confidence signals tested retrospectively

1. **Calibration confidence:** detector-marginal log-likelihood gap between the best and runner-up bank models, plus selected-minus-pooled score. These are available after the calibration prefix and before the next evaluation block.
2. **Current-shot compatibility:** factorized detector-marginal log-likelihood difference for the current detector vector under selected versus pooled profiles, plus syndrome weight and calibration confidence. This uses only the current detector vector and prior calibration data, not the current logical label.
3. **Decoder disagreement:** available only after both decoders have been run. It is observable but costs an additional decode and identifies only the cases where choosing a different decoder can change the answer.

The calibration-level leave-one-root-out utility model had AUC **0.570** and Brier score **0.2371**, slightly worse than the constant-prevalence Brier score **0.2344**. With a fixed 0.5 equal-cost cutoff it selected the candidate on 21/24 roots and fell back on 3; the resulting evaluation had **686** errors versus **681** for pooled fixed.

The per-shot leave-one-root-out model had AUC **0.464** and Brier **0.2502**, slightly worse than its constant-prevalence baseline **0.2496**. At a 0.5 cutoff it chose candidate on 131/225 disagreement shots and fixed on 94. Candidate choices were harmful on 67 and helpful on 64; fixed fallback avoided 41 candidate harms but missed 53 candidate wins. Overall it produced **684** errors versus **681** pooled.

The simple threshold “use the candidate if its detector-marginal likelihood for this shot exceeds pooled” selected the candidate on all 225 disagreement shots. It therefore reproduced always-adaptive results exactly and created no selective fallback.

These are development-only cross-validation diagnostics, not untouched test estimates. The candidate approach does not meet the requirement for a practically meaningful improvement on independent development roots.
