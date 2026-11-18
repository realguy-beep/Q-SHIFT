# Frozen selector under halved gate noise

Keep the ratio-10 selector and matcher graphs trained at gate/measurement p=.003 fixed. Evaluate physical gate p=.0015, measurement p=.003, bias ratio 10. No retraining, calibration, threshold change, or nominal graph update. Actual-profile matching is diagnostic only.

Six d3 conditions; 500k main and 10k preflight shots/cell. First stream preflight seeds 2026120801–0806 and main 2026120811–0816. If the unchanged gate passes (>=10% macro reduction, no cell harmed >5%, full inference <2x), replicate with preflight 2026120891–0896 and main 2026120901–0906.

Verify geometry, noiselessness, scalar/batch consistency, features, and projected runtime <=300s. No confirmatory/sealed evaluation or post-validation tuning.
