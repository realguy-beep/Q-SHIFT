# Shared relative-choice classifier for matcher disagreements

## Question

On syndromes where correlated and ordinary PyMatching disagree, can one shared classifier predict whether correlated matching is wrong, then choose the ordinary output only on those flagged cases? This frames the target as relative matcher correctness rather than the absolute logical bit.

## Frozen design

- Six nominal d3 CSS basis/profile conditions; gate/measurement p=.003 and bias ratio 10. Use the existing correlated-vs-ordinary disagreement flag and two matchers.
- Train one shared L2 logistic model on 40 detector bits from flagged cases only. Label each flagged training row `correlated_wrong = (correlated_prediction != observable)`; observables are offline labels. At inference, switch to the ordinary output when the classifier predicts correlated wrong; otherwise retain correlated output. No condition identifier or matcher-output feature enters the classifier.
- 1M train and 1M independent validation samples/condition; 10k preflight/condition. Seeds: preflight 2026118701–8706, training 2026118711–8716, validation 2026118721–8726.
- Compare with correlated matching, the prior shared absolute-bit logistic selector, and prior specialized selectors on the same validation samples. Their coefficients are frozen from existing nominal development fits; no validation outcomes feed training or selection.
- Keep the original advancement gate: >=10% equal-cell macro LER reduction, no cell harmed >5%, total two-matcher-plus-classifier inference <2x.

## Stop rules

Verify circuit geometry/noiselessness, scalar/batch agreement, 40 detector features, one observable, both classes in pooled training labels, and projected train+validation sampling/matching runtime <=300s. No confirmatory/sealed data, no post-validation tuning.
