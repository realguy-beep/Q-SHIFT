# Focused alternative-decoder assessment

## Candidate screen

| Method | Fit to this model | Main caveat | Assessment |
|---|---|---|---|
| PyMatching sparse blossom | Fast, established, already installed; graphlike decomposed DEM is its native input | Decomposition/approximation and optional correlations must be controlled | Strong primary baseline. The authors describe sparse blossom's surface-code decoding and high throughput ([paper](https://arxiv.org/abs/2303.15933)). |
| Belief matching / belief-find | Designed for circuit noise and hyperedge information; combines BP-derived information with matching | Reference implementation depends on LDPC and rebuilds a matching instance per shot; its README warns it can be over 100x slower than PyMatching alone | Strongest next candidate for Q-SHIFT's undecomposed detector mechanisms, after pinning implementation and checking representation parity. The paper reports circuit-level surface-code use ([PRX paper](https://journals.aps.org/prx/abstract/10.1103/PhysRevX.13.031007)); claims do not guarantee benefit on Q-SHIFT. |
| This prototype's loopy BP logical marginal | Minimal dependencies; exact on tested small tree and deterministic on tested fixtures | Approximate on loops; current Python runtime is far slower than matching; convergence depends on iteration cap and model | Keep as a correctness/diagnostic prototype, not a proposed production contender. |
| BP+OSD | Widely studied for sparse parity-check decoding, especially quantum LDPC | Q-SHIFT has surface-code circuit DEM mechanisms with hyperedges and categorical origins; adaptation and dependency absent | Could be revisited if the project expands to qLDPC or a well-defined binary parity model, but less direct than belief matching here. |
| Correlated PyMatching | Same fast solver with correlation option | Requires correct decomposed DEM and correlation flags; on this five-row set it matched ordinary mode | Essential PyMatching ablation, not an independent algorithm. |
| Tensor-network / MPS | Can approximate logical-class likelihoods and exploit code geometry | More specialized setup, contraction truncation choices and likely cost; exact circuit correlation mapping is nontrivial | Plausible offline accuracy reference if a vetted implementation supports this exact repeated-measurement circuit; not the next implementation under current constraints. See primary circuit-noise TN work ([PRE](https://journals.aps.org/pre/abstract/10.1103/PhysRevE.97.051302), [PRX Quantum](https://doi.org/10.1103/PRXQuantum.5.040303)). |
| Hypergraph matching / search (e.g. HyperBlossom, Tesseract) | Can target non-graphlike mechanisms more directly | Must verify current support for Q-SHIFT's DEM semantics, logical output contract and runtime; no installation or benchmark here | Worth a later feasibility screen, not superficial parallel implementations. |
| Learned/GNN decoder | Could adapt to local structures | Requires training and strict train/dev separation; training is outside current authorization | Defer. |

## Recommendation

The next candidate should be **belief matching**, preferably the pinned, maintained implementation after a deterministic input/output and model-information audit. It uses BP to exploit hyperedge structure and then matching for a valid logical correction, aligning better with this circuit-level DEM than a bare BP logical marginal. Keep PyMatching sparse blossom as the strong baseline. Preserve this BP prototype as the exact-small-case comparison and test harness seed. No performance advantage is established.

The official repository states its use of PyMatching and LDPC subroutines and documents a greater-than-100x slowdown in its unoptimized implementation: [BeliefMatching repository](https://github.com/oscarhiggott/BeliefMatching). This is a feasibility warning, not a Q-SHIFT runtime estimate.
