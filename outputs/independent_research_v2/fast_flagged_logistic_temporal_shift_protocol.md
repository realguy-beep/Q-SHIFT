# Frozen selector under alternating per-round gate rates

## Question

Does the d3 ratio-10 selector, trained on stationary p=.003 circuits, retain utility under a temporal gate-rate pattern whose five-round average remains .003?

## Fixed design

- Use the existing temporal-rate hotspot builder for Z-memory/X-biased ratio-10 circuits. Profile A per-round factors are [0.25, 1.75, 1.0, 0.25, 1.75]; profile B reverses this order. One-qubit and measurement probabilities remain .003, and the two-qubit Pauli composition is unchanged.
- Freeze the nominal z-memory/x-biased selector coefficients and both nominal matchers from the independent d3 replication. No retraining, calibration, or model-graph update.
- Compare frozen selector to nominal correlated matching on the same temporal syndrome stream. Decode with a matcher built from the actual temporal profile only as a diagnostic, not an optimality bound.
- Use 500,000 main and 10,000 preflight samples/profile. First seeds: preflight 2026121201–1202, main 2026121211–1212. If the gate passes, replicate with preflight 2026121291–1292 and main 2026121301–1302.
- Gate: >=10% equal-profile macro LER reduction, no profile harmed >5%, full two-nominal-matcher-plus-classifier inference <2x.

## Stop rules

Verify geometry, unchanged Pauli composition and targets, five round groups, reversed factors and mean one, deterministic noiseless circuits, scalar/batch consistency, fixed 42-feature shape, and projected runtime <=300s. No confirmatory/sealed data or post-validation tuning.
