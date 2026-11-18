# Combined measurement and bias shift for the frozen selector

## Question

Do the two separately positive d3 stress results combine without degrading the frozen learned policy? The challenge changes measurement p from .003 to .006 and physical bias ratio from 10 to 5 simultaneously.

## Frozen design

- Freeze the per-condition logistic coefficients and nominal correlated/ordinary matching graphs from the independent nominal ratio-10, p=.003 replication. No training, recalibration, or threshold adjustment on shifted samples.
- Generate six d3 basis/profile circuits at gate p=.003, measurement p=.006, bias ratio 5. Decode and form disagreement features using the nominal p=.003, ratio-10 matchers.
- Use an actual shifted-profile correlated matcher only as a diagnostic, not an optimality bound.
- Main 500,000 samples/condition; preflight 10,000/condition. First stream seeds: preflight 2026116801–6806, main 2026116811–6816. If the unchanged gate passes, replicate with preflight 2026116891–6896 and main 2026116901–6906, keeping models and all settings fixed.
- Gate: >=10% equal-condition macro LER reduction vs nominal correlated matching, no condition harmed >5%, full two-matcher-plus-classifier inference <2x.

## Stop rules

Require correct d3 geometry, noiselessness, scalar/batch consistency, fixed feature/coefficient shapes, and projected runtime <=300s. No confirmatory/sealed data; no post-validation tuning. The balanced profile is unchanged in bias composition but receives the measurement shift.
