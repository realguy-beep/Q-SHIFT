# Frozen selector under doubled gate noise

Freeze the per-condition d3 selectors and matcher graphs trained at gate/measurement p=.003 and bias ratio 10. Evaluate physical gate p=.006, measurement p=.003, bias ratio 10. No retraining, recalibration, or graph update. The actual gate-p=.006 matcher is diagnostic only.

Use six d3 conditions, 500k main and 10k preflight/condition. First seeds: preflight 2026120601–0606, main 2026120611–0616. If the unchanged gate passes (>=10% macro gain, no cell harmed >5%, full inference <2x), replicate with preflight 2026120691–0696 and main 2026120701–0706, keeping coefficients fixed.

Check geometry, noiselessness, scalar/batch consistency, features, and projected runtime <=300s. No confirmatory/sealed evaluation or post-validation tuning.
