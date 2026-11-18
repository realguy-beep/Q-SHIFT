# Frozen selector under halved measurement noise

Freeze the per-condition d3 selectors and matcher graphs trained at gate/measurement p=.003 and bias ratio 10. Evaluate gate p=.003, measurement p=.0015, bias ratio 10. No retraining, calibration, or nominal graph update. Actual-profile matching is a diagnostic only.

Use six d3 conditions, 500k main and 10k preflight samples/condition. First seeds: preflight 2026121001–1006; main 2026121011–1016. If the unchanged gate passes (>=10% macro reduction, no cell harmed >5%, full inference <2x), replicate with preflight 2026121091–1096 and main 2026121101–1106.

Verify geometry, noiselessness, scalar/batch, feature shapes, and projected runtime <=300s. No confirmatory/sealed evaluation or post-validation tuning.
