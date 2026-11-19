# 500k selector training budget under combined noise shift

## Question

Does the replicated 500k-shot d3 training budget retain the frozen selector's benefit under the previously replicated combined measurement/bias shift (measurement p .003→.006 and physical bias ratio 10→5)? This directly tests whether halving training data preserves the bounded robustness result.

## Frozen design

- Six d3 Phase 2B conditions. Generate one fresh nominal 1M-shot training stream/condition at gate/measurement p=.003 and ratio 10. Fit logistic models on nested 500k and 1M prefixes using the existing 42 features/objective. All six trainability checks must pass before validation.
- Validation: 500k fresh shots/condition at gate p=.003, measurement p=.006, physical bias ratio 5. Keep nominal ratio-10 matchers fixed. Apply both the 500k and 1M learned models to the same nominal matcher disagreement features. An actual-shift correlated matcher is diagnostic only.
- Preflight: 5,000 shifted shots/condition; geometry, noiselessness, nominal scalar/batch parity, feature dimension, and projected runtime <=300s.
- Seeds: preflight 2026122501–2506; nominal training 2026122511–2516; shifted validation 2026122521–2526.

## Advancement gate

The 500k model advances only if it retains >=80% of the 1M model's absolute macro gain on the shifted validation, each model reduces macro LER by >=10% vs nominal correlated matching, neither harms a cell by >5%, and total two-matcher-plus-classifier inference remains <2x. Report paired uncertainty and per-cell outcomes. No shift retraining, tuning, or post-validation threshold changes. Development only.
