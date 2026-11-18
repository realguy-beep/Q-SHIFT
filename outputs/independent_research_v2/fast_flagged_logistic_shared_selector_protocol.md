# One shared selector across six known d3 conditions

## Question

Can a single flagged-syndrome L2 logistic model replace six separately fitted condition-specific models on the same nominal d3 family?

## Frozen design

- Six CSS basis/profile conditions at gate/measurement p=.003 and bias ratio 10. Use the same nominal correlated/ordinary PyMatching flag, 40 detector bits plus two matcher logical outputs, L2 objective, and L-BFGS-B settings as the existing selector.
- Train one global model on the union of flagged cases from six independent 1M-shot/condition training streams. Fit only flagged detector/matcher features; simulator observables are offline labels. Keep the six previous independent-replication models unchanged as a same-validation reference, not for selecting/tuning the pooled model.
- Validate on six fresh 1M-shot/condition streams; preflight 10k/condition. Seeds: preflight 2026118501–8506, training 2026118511–8516, validation 2026118521–8526.
- Primary gate: >=10% equal-cell macro LER reduction vs correlated matching, no condition harmed >5%, and two-matcher-plus-classifier inference <2x. Report shared-vs-specialized paired outcomes, flag rates, aggregate training class counts, per-cell intervals, and runtime.

## Stop rules

Verify 26 qubits/40 detectors/one observable, noiselessness, scalar/batch agreement, feature dimension 42, both training label classes in pooled flagged data, and projected train+validation runtime <=300 seconds. No confirmatory/sealed data; no post-validation tuning.
