# Frozen selector under isotropic Pauli noise (ratio 1)

Freeze the per-condition d3 selectors and correlated/ordinary matching graphs at bias ratio 10, gate/measurement p=.003. Evaluate physical ratio 1, where the formerly X- and Z-biased channels become isotropic. Balanced profiles are unchanged controls. No retraining, recalibration, or graph update.

Use 500k main and 10k preflight samples/condition. First stream seeds: preflight 2026120401–0406, main 2026120411–0416. If the fixed gate passes (>=10% macro gain, no cell harmed >5%, inference <2x), replicate on preflight 2026120491–0496 and main 2026120501–0506 with the same models and settings. Treat the ratio-1 profile matcher as a diagnostic only.

Check d3 geometry, noiselessness, scalar/batch consistency, feature shapes, and projected runtime <=300s. No confirmatory/sealed data or post-validation tuning.
