# Distance-5 validation of frozen bias-strength decoder pair

## Question

Does the fresh d3 development result for the fixed ratio10 matching model versus the fixed ratio5 model persist at d5? This is a second finite-distance check of the same mechanism, not a threshold or scaling study.

## Fixed design

- d=5 rotated-memory circuits, nine rounds, p_gate=p_measure=.003. Actual ratios are 2, 3.5, 5, and 10; both X/Z profiles and both memory bases give 16 cells.
- Compare only correlation-enabled PyMatching models built at assumed ratios5 and10 on identical detector streams. The ratio10 custom channel builder must be byte-identical to the existing scaled d5 source builder for all profile/basis combinations.
- Preflight uses 100 shots/cell, seeds 2026112501–2026112516. Require 216 detectors, one observable, matching resource counts within actual ratio, batch/scalar equality, and a projected runtime at or below five minutes. Stop before main if any check fails.
- Main uses 100,000 independent direct circuit shots/cell, seeds 2026112521–2026112536. Primary endpoint is the equal-weight macro paired LER difference ratio10 minus ratio5 over the 16 fixed cells, with conditional Monte Carlo standard error and 95% interval. Report per-cell results and actual-ratio stratum summaries to show heterogeneity.
- No decoder tuning, threshold fitting, or confirmatory evaluation. Results are limited to this simulator's stationary Pauli channel, d5, and two assumed decoder weights.
