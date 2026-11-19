# Small nonlinear model on flagged d3 disagreement cases

## Hypothesis

The current 42-feature L2 logistic selector may miss nonlinear interactions among detector bits on the rare matching-disagreement subset. One compact, fixed 8-unit tanh MLP may improve that subset without increasing end-to-end inference cost beyond the existing 2x limit.

## Frozen comparison

- Six nominal d3 Phase 2B conditions; correlation-enabled and ordinary PyMatching outputs define the same disagreement flag and 42 features used by the logistic selector.
- Train a per-condition logistic model and an 8-hidden-unit tanh MLP on the same 500,000 labeled training shots/condition, using only flagged rows. Use 500,000 fresh validation shots/condition, shared across both candidates and the correlated baseline.
- Standardize features using training flagged rows only. MLP objective is summed binary cross-entropy plus 0.5 L2 penalties on weight matrices; biases unpenalized. Xavier-style seeded Gaussian initialization, SciPy L-BFGS-B, max 500 iterations, fixed tolerance; no hyperparameter selection.
- Preflight: 5,000 shots/condition; verify circuit geometry, noiselessness, 42 features, both matchers, and projected runtime <=300s. Require >=100 flagged training rows and both labels in all six conditions before opening validation.
- Seeds: preflight 2026122401–2406; training 2026122411–2416; validation 2026122421–2426.

## Advancement gate

To justify the nonlinear model, require >=2% relative macro LER reduction versus the logistic model, paired macro 95% interval for MLP-minus-logistic below zero, and the established baseline gates versus correlated matching (>=10% macro improvement, no cell >5% harmed, <2x full inference cost). No parameter sweep or post-validation tuning. Development only.
