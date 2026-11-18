# Deterministic matching-graph audit for bias-strength sensitivity

## Question

The frozen assumed-ratio10/ratio5 comparison favored ratio10 at d3 but was near-neutral at d5. Test a narrow structural explanation: do the two assumed-noise models preserve the same matching graph topology while changing edge weights, and does the size of that reweighting vary with distance?

## Fixed audit

- Rebuild d3/5, five-round circuits and d5/9-round circuits for both X/Z profile directions and memory bases, using only assumed ratios5 and10; p_gate=p_measure=.003 and DEM approximation threshold .0018.
- Convert each DEM with correlation-enabled PyMatching. For each paired model report nodes, edges, boundary edges, edge-topology and logical-fault-label equality, graph signatures, median/mean/max absolute edge-weight changes, sign of weight changes, and median absolute change in error probability.
- Verify d3 circuits with the Phase 2B source builder. Verify d5 ratio10 circuits against the existing scaled builder. Stop if any circuit/DEM construction fails.
- No samples are generated and no performance outcome is used as an input. This is a descriptive mechanism audit only; it cannot establish that graph differences caused the observed LER pattern.
