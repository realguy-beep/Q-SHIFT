# Stage 5 v3 candidate protocol — 666 roots/condition

**For review only; no sampling authorization.** This is a separate candidate and does not modify Stage 5 v2 or its 2.5M-shot cap. It preserves the d=3, five-round rotated Z-memory circuit, five probabilities, frozen Stage 4C detector-profile estimator, and three paired decoder arms.

The candidate allocation is 666 roots per condition, 2,000 calibration detector shots/root, and 2,500 paired evaluation shots/root: 14,985,000 total unique shots. It exceeds the v2 cap and would require explicit approval of a new budget. Seed inventory uses 6,660 new, screened streams and remains unused.

## Primary method

The candidate endpoint is the equal-weight mean over the four nonzero conditions of one root-level paired adaptive-minus-fixed LER difference. The decision boundary is −0.0002. The studentized mean is compared with the precomputed conservative envelope critical value 1.8346; the one-sided upper bound is the estimate plus that critical value times the stratified root-level standard error. p=0 has a separate upper bound using critical value 1.7267306837 and harm limit +0.0002. These constants come from `outputs/stage5_design_validation_v2/DESIGN_SIMULATION_RESULTS.json` and are valid only for the finite prespecified distribution envelope documented there.

Four condition-level Welch p-values and Holm adjustments are retained as descriptive secondary outputs only; their own operating characteristics were not part of the primary-method validation, so they cannot support confirmatory condition-specific claims without an additional frozen validation.

## Candidate status

The primary method passed null size and coverage checks in the simulated envelope. The proposed allocation failed the predeclared 80% lower-Wilson power requirement at Δ=−0.0003 under the 1.5× skewed and tied root-effect scenarios. Therefore this runner is packaged solely to permit code review and deterministic no-shot preflight. It is **not recommended for Stage 5 sampling**. No sample command has been run; the independent-test allocation remains sealed.
