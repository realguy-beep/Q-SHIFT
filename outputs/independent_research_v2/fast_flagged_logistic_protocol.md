# Fast supervised selector on flagged disagreement syndromes

## Hypothesis

Disagreement between correlation-enabled and ordinary PyMatching marks a small, higher-ambiguity subset. BP+LSD improved LER on this subset but was 8x too slow. A small detector-only classifier trained on development labels may choose the correct logical bit within the flagged subset at substantially lower inference cost.

## Fixed method

- Six d3 Phase 2B conditions, p=.003, ratio10; same two PyMatching models and flag iff their predicted logical observables differ.
- Fit a separate binary logistic regression per condition on training-flag rows only. Features are the 40 detector bits plus the correlated and ordinary predicted logical bits. Target is the sampled logical observable, used only for training. Use mean binary cross-entropy plus L2 penalty `0.5 * ||beta||^2` (lambda=1), unpenalized intercept, L-BFGS-B, max 300 iterations, fixed zero initialization. Predict logical 1 iff logit >=0. No hyperparameter tuning or held-out selection.
- Training: 1,000,000 fresh shots/condition, seeds 2026114401–4406. Independent validation: 1,000,000 shots/condition, seeds 2026114411–4416. Preflight: 10,000/condition, seeds 2026114391–4396.
- On unflagged validation syndromes use correlated matching; on flagged ones use the logistic classifier. Baselines are correlated and ordinary PyMatching. Report flagged counts/class balance, training fit status, paired validation LER deltas, uncertainty, per-cell results, classifier fit time, total inference time (both matching passes plus classifier), and stored coefficient counts.
- Advancement requires >=10% equal-weight macro LER reduction vs correlated matching, no cell harmed by >5%, and total inference time <2x correlated matching. This is a development-only trained hybrid, not a novel method claim.

## Integrity and stopping

Preflight verifies all circuits, noiseless determinism, matching shape, and runtime projection <=300 seconds. Stop if a training subset has fewer than two target classes or the optimizer fails its fixed convergence criteria. Test sets are independent of fit. No confirmatory/sealed data or installation of additional libraries is used.
