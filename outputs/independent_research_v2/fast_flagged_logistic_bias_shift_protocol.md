# Frozen selector under reduced Pauli-bias ratio

## Question

Does the d3 per-condition logistic selector trained at bias ratio 10 remain useful when an X- or Z-biased channel becomes less anisotropic (ratio 5), with the model and matchers kept at their ratio-10 profile?

## Frozen design

- Use the six existing d3 CSS basis/profile conditions at gate and measurement p=.003. Shift the physical biased profiles from ratio 10 to ratio 5; balanced profiles are unchanged by the ratio parameter and serve as fixed controls.
- Freeze the six trained coefficients from `fast_flagged_logistic_replication_results.json`; no retraining, recalibration, or threshold change. Build correlated and ordinary matching graphs at ratio 10; use both for flagging and prediction on ratio-5 syndromes.
- Also decode with a correlated matcher built from the ratio-5 profile as a profile-matched diagnostic, not an optimality bound.
- Use 500,000 main and 10,000 preflight samples per cell. First stream seeds: preflight 2026116601–6606, main 2026116611–6616. If and only if the frozen gate passes, independent replication seeds are preflight 2026116691–6696, main 2026116701–6706, with no model changes.
- Advancement gate: >=10% equal-cell macro LER reduction, no cell harmed >5%, and full two-matcher-plus-classifier inference <2x correlated matching.

## Stop rules

Check 26 qubits/40 detectors/one observable, deterministic noiseless circuits, scalar/batch equivalence, fixed model/feature shapes, and projected runtime <=300s. Do not access confirmatory or sealed data. No post-validation tuning.
