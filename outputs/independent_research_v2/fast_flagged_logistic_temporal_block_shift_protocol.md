# Frozen selector under a blockwise gate-rate pattern

Test generalization beyond the previously evaluated alternating rate sequence. Freeze the stationary z-memory/X-biased ratio-10 selector and nominal matchers at p=.003. Use per-round two-qubit rate factors `[.25,.25,1.75,1.75,1]` and its reversal `[1,1.75,1.75,.25,.25]`; their mean is one. Keep one-qubit/measurement p=.003 and two-qubit Pauli composition fixed. An exact profile-specific matcher is diagnostic only.

Use Z-memory/X-bias d3, 500k main and 10k preflight/profile. First seeds preflight 2026121401–1402 and main 2026121411–1412. If the unchanged gate passes (>=10% macro reduction, no profile harmed >5%, full inference <2x), replicate with preflight 2026121491–1492 and main 2026121501–1502.

Verify five round groups, reversed factors, mean one, unchanged geometry/composition, noiselessness, scalar/batch agreement, 42 features, and runtime projection <=300s. No retraining, confirmatory/sealed data, or post-validation tuning.
