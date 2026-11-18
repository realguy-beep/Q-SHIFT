# Frozen selector at bias ratio 2

## Question

Does the ratio-10 trained d3 selector survive a stronger reduction in Pauli anisotropy, to ratio 2, with gate and measurement p held at .003?

## Fixed design

- Freeze the six per-condition logistic models and nominal correlated/ordinary matchers trained at bias ratio 10, gate/measurement p=.003. Physical X/Z-biased channels use ratio 2; balanced profiles are unchanged controls.
- No retraining, calibration, threshold change, or decoder profile update. Use the same 500k main +10k preflight per condition and the same gate: >=10% macro reduction, no cell harmed >5%, total inference <2x.
- First seeds: preflight 2026120201–0206, main 2026120211–0216. If gate passes, fresh replication preflight 2026120291–0296 and main 2026120301–0306.
- Actual ratio-2 correlated matching is only a profile-matched diagnostic, not an optimality bound.

## Stop rules

Check geometry, noiselessness, scalar/batch, feature shape, and runtime projection <=300s. No confirmatory/sealed data and no post-validation tuning.
