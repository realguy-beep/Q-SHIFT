# Exact planar MPS under two biased code-capacity channels

## Question

The prior MPS study established runtime feasibility only. This bounded efficacy screen asks whether exact planar MPS decoding improves on noise-aware planar MWPM under known X- and Z-biased IID code-capacity noise.

## Frozen design

- qecsim `PlanarCode(d,d)` at d=3.
- `BiasedDepolarizingErrorModel(bias=10, axis=X/Z)`, total data-qubit error probability p=.05. Both decoders receive the same exact model and p.
- Candidate: `PlanarMPSDecoder(chi=None, mode='c')`; comparator: `PlanarMWPMDecoder()`.
- Paired noise samples: 20,000 per bias direction; 100 per direction in preflight. Every recovery must reproduce the sampled syndrome.
- Report per-direction and equal-weight macro LER, paired intervals, failures, and decode time. Advancement requires >=10% equal-weight macro reduction, no direction >5% harmed, and total decoding under 300 seconds.
- Seeds: preflight 2026122701–2702; main 2026122711–2712.

This is a d3 ideal-syndrome code-capacity surrogate, not the multi-round categorical Q-SHIFT circuit or a hardware claim. Exact MPS is a known decoder family; no novelty claim is made. No Q-SHIFT circuit shots are counted or generated.
