# Fast selector for matching-disagreement syndromes: held-out result

## Result

A fixed L2 logistic model was trained per d3 condition using only 1,000,000 fresh training samples/condition. It saw training labels only for syndromes where correlation-enabled and ordinary PyMatching disagreed. Inputs were the 40 detector bits and both matchers' predicted logical bits. On a separate 1,000,000-shot/condition validation stream, the selector reduced equal-weight macro LER from .005156 to .004271, a 17.17% relative reduction. All six paired 95% intervals excluded zero; per-condition reductions ranged 4.2%–35.7%. The smallest gain was X memory under Z bias; its point reduction still exceeded the 5% harm allowance.

The flag rate ranged from about .10% to .53% across cells. Full inference time includes both matching passes and classifier evaluation and averaged 1.35x the correlated matcher, below the 2x gate. The models had 42 coefficients including intercept, with training fits converging in 49–60 iterations. Training across all conditions took 7.76 seconds; validation and full run took 15.74 seconds. The predeclared advancement gate passed.

## Interpretation and limits

This is promising, held-out development evidence for a low-cost learned selector on the high-ambiguity subset. It uses known simulator conditions and supervised training labels from an independent synthetic stream. It is not evidence for unknown-noise robustness, real-time hardware calibration, arbitrary logical tasks, or a novel decoding algorithm. Each condition has one training and one validation seed stream; an independent train/validation replication is still required. A same-stream comparator reanalysis against the slower BP+LSD hybrid is recorded below.

## Same-validation-stream comparator reanalysis

Replaying the exact held-out validation seeds with the fixed BP+LSD disagreement hybrid gave macro LER .004456, versus .004271 for the trained logistic selector and .005156 for fixed correlated matching. The learned selector had lower LER than BP+LSD in five of six cells; BP+LSD was better only for Z memory under Z bias. The logistic selector also retained its 1.35x timing profile; the BP+LSD reanalysis took 33.8 seconds for the same six million shots. This is a deterministic reanalysis of the existing held-out stream, not new evidence, and it does not replace independent model replication.
