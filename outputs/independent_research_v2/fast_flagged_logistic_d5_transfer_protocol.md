# Distance-5 transfer of the flagged logistic decoding method

## Question

Does the same fixed method (correlated/ordinary PyMatching disagreement flag plus an L2 logistic selector on detector bits and both matching outputs) retain useful held-out LER gains when independently fitted at d5? This tests transfer of the method, not transfer of d3 coefficients: the d5 detector vector and model are distance-specific.

## Frozen design

- Six d5 CSS conditions: X/Z memory crossed with X-biased, balanced, and Z-biased channel profiles, source probability model, gate p=.003, measurement p=.003, bias ratio 10, nine rounds.
- Build circuits through the source-equivalent `build_scaled_circuit`; verify dimensions (64 qubits, 216 detectors, one observable) and deterministic noiseless circuit before sampling.
- Fit one L2 logistic model per condition using a fresh 1,000,000-shot training stream. Only matching-disagreement samples enter fitting; simulator observables are offline labels. Validate on an independent fresh 1,000,000-shot stream per condition. Preflight 10,000/condition.
- Use the existing approximation threshold .0018 and correlated/ordinary PyMatching policy. Keep the feature rule and optimizer from the d3 study; do not tune after seeing validation results.
- Seeds: preflight 2026115201–5206, training 2026115211–5216, validation 2026115221–5226. These streams are separate from prior d3/d5 runs.
- Advancement gate unchanged: >=10% equal-cell macro LER improvement, no cell harmed >5%, and two-matcher-plus-classifier inference <2x correlated matching. Record paired intervals, flag prevalence, train/test class counts, and runtime.

## Stop rules

Before main sampling, require correct geometry, noiselessness, scalar/batch agreement, nonempty flagged subset with both logical classes in preflight only as a warning (the training stream must have both), finite features, and projected training plus validation sampling/matching time <=300 seconds. Do not inspect any confirmatory/sealed data. No d3 coefficient is applied to d5.
