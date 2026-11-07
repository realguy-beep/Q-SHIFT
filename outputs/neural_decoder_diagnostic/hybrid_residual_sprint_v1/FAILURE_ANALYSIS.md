# Residual-decoder failure analysis (pre-sprint)

**Status:** completed before any new sprint sampling. This report uses only the
already saved Phase 2B and 750,000-shot development evidence. It is diagnostic,
not a new evaluation and is not used to tune the new sprint's model or threshold.

## Evidence reviewed

- `outputs/neural_decoder_diagnostic/autonomous_development/run/FINAL_MORNING_REPORT.md`
- `outputs/neural_decoder_diagnostic/autonomous_development/run/FINAL_MORNING_REPORT.json`
- The 50 saved model result records and 50 prediction archives under the same
  completed run; archived test access is recorded as zero.
- `outputs/neural_decoder_diagnostic/root_cause_analysis/ROOT_CAUSE_REPORT.md`
- `outputs/neural_decoder_diagnostic/root_cause_analysis/REPRODUCE.md`
- `outputs/neural_decoder_diagnostic/root_cause_analysis/SAVED_EVIDENCE_RECOMPUTATION.json`
- Existing residual model and training/calibration implementation in
  `outputs/neural_decoder_diagnostic/autonomous_development/experiment.py`.

The prior report lists the residual model at 0.45933% LER versus 0.43533% for
PyMatching on 150,000 paired final-development shots (five roots, three
regimes, 10,000 shots per regime/root). This is development evidence only.
The independent test remains sealed and is not part of this sprint.

## Paired failure mechanism

For the saved residual predictions, PyMatching made 653 errors. At the saved
threshold of 0.50, the residual network proposed 62 parity flips: 13 changed a
PyMatching error into a correct logical prediction, and 49 changed a correct
prediction into an error. The hybrid therefore added 36 errors relative to
PyMatching (49 minus 13). Residual-target prevalence in the old training data
was about 0.4–0.5% per root, so useful examples were scarce.

The saved probability ranking contains a possible signal (reported old-run
development AUC 0.941), but at the frozen threshold its precision was only
13/62 = 21.0% and recall was 13/653 = 2.0%. This combination indicates that
ranking and probability/decision calibration are separate concerns. It does
not prove a reliable tail threshold exists. The old evaluation partition is
not reused to select one.

## Confirmed observations versus hypotheses

**Confirmed:** the target is `observable XOR PyMatching_prediction`; inference
applies `PyMatching_prediction XOR predicted_residual`. The saved prediction
arrays were independently rescored, are paired with the stored observable
labels, and preserve the frozen PyMatching comparator. The residual class is
rare. The saved model's selected threshold produced more harmful than helpful
corrections.

**Not established:** whether the dominant issue is posterior miscalibration,
finite positive-example count, regime pooling, model representation, or
optimization. The old data do not support a causal explanation by syndrome
structure: there were only 13 helpful corrections. Regime-specific counts are
also too sparse to justify a regime-specific threshold. A high AUC on the old
development partition is exploratory and cannot be used as new-sprint model
selection evidence.

## Prospective response

The new development sprint keeps the position-preserving residual CNN and
PyMatching reference. It separates monitor, probability calibration,
threshold selection, and final development evaluation streams. It compares
the established balanced-minibatch objective with a natural-prevalence,
positive-weighted objective whose ideal weighted-logit shift is removed before
calibration. A confidence-gated policy is selected only from its own
threshold-selection split, requires a multiplicity-adjusted one-sided lower
precision bound above 0.5, and otherwise falls back to exact PyMatching. No
old-run threshold, probability, or final-evaluation outcome is used to set
these rules.

## Limitations

Five new root clusters support only a bounded development/feasibility study.
Shot-level intervals will not be presented as independent-root uncertainty.
Even a favorable development difference will not establish neural superiority
or authorize access to the independent test. The strongest justified next
step will be decided from root-level paired outcomes, positive-example counts,
calibration stability, and resource cost.
