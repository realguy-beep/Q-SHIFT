# Feasibility and direction ranking

Scores are qualitative planning judgments from 1 (low) to 5 (high). “Null risk” means risk of failing to obtain a clearly interpretable result, not risk of finding no benefit.

| Criterion | A. DEM information loss | B. Correlation-aware decoding | C. Operating limits |
|---|---:|---:|---:|
| Scientific value | 5 | 4 | 3 |
| Measurable with current infrastructure | 3 | 5 | 5 |
| Implementation difficulty (easy=5) | 2 | 4 | 4 |
| Existing-code/data reuse | 4 | 5 | 5 |
| Compute economy (cheap=5) | 3 | 4 | 2 |
| Competition presentation value | 3 | 4 | 5 |
| Risk of an uninterpretable/null feasibility outcome (low risk=5) | 2 | 3 | 4 |
| Algorithmic novelty potential | 3 | 1 | 1 |

## Interpretation

- **Primary: B.** It has the cleanest controlled contrast that is missing from the historical study: same approximate DEM, same graph weights, same sampled syndrome and logical label; only the supported correlation-aware decoding option changes. The direct paired effect and compute overhead can be measured without creating a new decoder or selecting on test labels.
- **Fallback: C.** It has a clear, visually intuitive outcome and established code support for d=3,5,7. It should be framed as a finite-distance operating map under a named simulation model, not as an original threshold discovery.
- **Defer: A.** It is scientifically interesting but lacks a validated reference method that attributes decoder outcomes to the DEM approximation. Use B’s same-model controls first; revisit A only if a reliable distributional or likelihood analysis can be designed.

## Practical competition framing

The strongest honest story is not “Q-SHIFT invented an adaptive decoder.” It is: “We tested whether making PyMatching use the correlations already present in a circuit model changes error-correction outcomes, under paired simulation controls; if it does not, we map reliability versus distance and noise.” The prior Q-SHIFT adaptation results remain negative/inconclusive and are not erased by choosing this new question.

