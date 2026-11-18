# Frozen ratio-10 versus ratio-5 decoder validation

## Question and frozen contrast

The preceding development grid suggested that correlation-enabled PyMatching built under assumed bias ratio10 outperformed ratio5 across actual ratios 2/5/10. This fresh development run freezes only the ratio10-minus-ratio5 paired contrast and the equal-weight 16-condition objective. It adds actual ratio3.5 as an interpolation check. No decoder ranking or threshold will be adjusted after observing these outcomes.

## Fixed design

- Source circuits: rotated-memory d=3, five rounds, gate and measurement p=.003; actual ratios 2, 3.5, 5, and 10, both X/Z profile directions and both memory bases (16 conditions).
- Compare only correlation-enabled matching models built at assumed ratios 5 and 10. Both decoders receive the same detector samples and are scored against the same observable stream.
- Preflight: 100 samples/cell with seeds 2026112401–2026112416; check 40 detectors/one observable, geometry resource equality within each actual ratio, scalar/batch decoder agreement, and projected total runtime <=5 minutes. Abort before main if any fails.
- Main: 100,000 fresh source-circuit samples/cell with seeds 2026112421–2026112436, in actual-ratio/profile/basis order.
- Primary endpoint: equal-weight macro paired LER difference ratio10 minus ratio5 across all 16 fixed cells, with its conditional Monte Carlo standard error and 95% normal interval. Also report all per-cell paired differences and LERs. Secondary descriptive endpoint: the four actual-ratio-specific macro contrasts; these are not additional primary hypothesis tests.
- Resource and runtime are reported. This is independent development validation, not confirmatory evaluation or hardware evidence. It tests only the two frozen decoders and these stationary Pauli models.
