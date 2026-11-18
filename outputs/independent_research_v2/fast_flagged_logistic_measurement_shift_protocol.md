# Frozen selector under measurement-noise composition shift

## Question

Does the nominally trained disagreement-subset logistic selector remain useful when measurement-flip probability doubles from .003 to .006 while gate noise and X/Z Pauli composition remain fixed?

## Fixed design

- Use the already trained per-condition logistic coefficients from the independent nominal replication. No retraining, calibration, threshold change, or coefficient update on shifted samples.
- Draw fresh d3 samples for all six basis/profile conditions at gate p=.003, measurement p=.006, bias ratio10. Decode using the nominal p_measure=.003 correlated and ordinary matching graphs; the flag and logistic features use those same nominal graph outputs. This tests frozen-policy robustness to model mismatch.
- For diagnostic context only, also decode the same shifted detector streams with correlation-enabled PyMatching built from the actual p_measure=.006 circuit. Treat this as a profile-matched diagnostic, not an optimality bound or eligible adaptive policy.
- Main: 500,000 samples/condition; preflight 10,000/condition. Seeds: preflight 2026114601–4606 and main 2026114611–4616.
- Primary gate: frozen logistic policy improves equal-weight macro LER >=10% over nominal correlated matching, no condition harmed by >5%, and full nominal two-matcher-plus-classifier inference <2x correlated matching. Report paired intervals, flag rates, per-condition error, oracle comparison, and runtime.

## Stop rules

Require 26 qubits/40 detectors/one observable, deterministic noiseless circuits, nominal matcher scalar/batch consistency, fixed feature/coefficient shape, and projected runtime <=300 seconds. This is a simulator composition-shift stress test; no confirmatory/sealed data or retuning is permitted.
