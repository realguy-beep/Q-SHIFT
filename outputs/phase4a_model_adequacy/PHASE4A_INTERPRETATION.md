# Phase 4A interpretation

The prespecified primary usefulness gate passed. Primary rate difference: -0.00029666667; bootstrap 95% interval: [-0.0003666666666666667, -0.00022166666666666667]; exact McNemar p: 5.600789e-23.

This tests calibrated static models under stationary calibration/test conditions. It does not test online switching, unfamiliar mixtures, calibration drift, hardware integration, or adaptive superiority. Native two-qubit depolarizing channels and five rounds differ from Phase 3B; results cannot be attributed solely to measurement noise by comparing across phases.

Templates are shared and finite; the fitting objective approximates detector correlations. All generating rates occur on the candidate grid. The informed reference knows true rates and remains an approximate matching decoder, not a proven lower bound on error. Fixed and specialist use the same ordinary matching algorithm. A uniform nominal model is a useful baseline, but superiority to every possible pooled fixed model is not established.

## Scope of the observed gain

Measurement-heavy residuals fell from 1,118 to 940 on 600,000 paired final shots: 178 fewer errors, 15.92% relative reduction, or 0.02967 percentage points absolute. Nominal tied exactly. Data-heavy had 22 more errors (8,599 versus 8,577), with no statistically supported difference. The successful gate is specific to the primary measurement-heavy condition. Calibration selected the true grid pair in all 60 batches, so calibrated and model-informed predictions coincide. This does not establish performance when calibration is inaccurate.

The calibration/validation gate was inspected before final test sampling. Validation selected whether to run the frozen study, not new model parameters or a new primary endpoint. Finite shared templates and on-grid generating conditions make this an optimistic, controlled model-adequacy pilot. An independently replicated benefit against a pooled fixed competitor is needed before any broad claim.
