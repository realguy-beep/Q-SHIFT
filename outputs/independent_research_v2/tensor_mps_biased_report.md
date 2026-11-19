# Exact planar MPS gives a small d3 biased code-capacity gain

## Design

The qecsim planar distance-3 code was tested under IID biased-depolarizing code-capacity noise at p=.05, bias 10, for X- and Z-dominant axes. Exact MPS (`chi=None`, mode `c`) was paired against noise-aware planar MWPM on 20,000 shared error samples per axis. Every recovery reproduced the sampled syndrome. This is a known decoder family; the question was bounded efficacy under a Q-SHIFT-inspired bias, not novelty.

## Results

Equal-weight macro LER was .03920 for MWPM and .037025 for exact MPS, a 5.55% reduction. Axis gains were 5.15% (X bias) and 5.94% (Z bias); neither axis was harmed. MPS decode time totaled 37.0 seconds over 40,000 main decodes, below the 300-second cap. The fixed >=10% utility gate failed, so there was no replication. qecsim reported its optional `libpypm.so` unavailable and used its Python MWPM fallback; this may affect runtime but not the paired failure comparison.

## Interpretation

The screen provides limited evidence that degeneracy-aware MPS can improve on MWPM under this distance-3, ideal-syndrome, known biased code-capacity model. It is below the frozen practical-effect gate and does not generalize to multi-round Q-SHIFT circuits, higher distance, hardware, or a 10,000-fold relative reduction. No tuning or replication followed.

Only qecsim code-capacity samples were generated (40,200 including preflight); new Q-SHIFT circuit samples: zero.
