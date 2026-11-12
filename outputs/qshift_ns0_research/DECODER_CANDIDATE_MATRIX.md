# Decoder candidate matrix

Ranking is for the current Q-SHIFT rotated surface-code circuit (distance 3, five rounds, 40 detectors, one observable) and research goal. Scores are qualitative evidence/applicability, not predicted performance.

| Rank | Candidate | Why it may add headroom | Q-SHIFT fit / cost | Falsification / reason to defer |
|---:|---|---|---|---|
| **1** | **HAMLD approximate maximum likelihood** | Different inference objective from MWPM; uses the multi-detector event hypergraph and degeneracy-aware likelihood approximations. Public implementation and small d=3 surface-code paper case exist. | Direct DEM-oriented interface and tiny code size make a controlled static test plausible. C++/Bazel build, DEM conversion semantics and per-syndrome latency need audit; real-time implementation is not established. | No material paired improvement over strong detector-profile-tuned static PM on fresh roots, or model conversion loses the burst/categorical dependence, or runtime/memory is unacceptable. If no static utility, do not add adaptation to it. |
| **2** | **NVIDIA Ising local predecoder + global matching** | Published local correction with matching fallback offers a distinct hybrid inductive bias; it can make local decisions while preserving a global decoder. | Public inference/training source; trained model weights are access-controlled and separately licensed. R=9/13 surface receptive fields and training guidance (67M examples/epoch, 8 GPUs) are mismatched to Q-SHIFT d=3/r=5. Requires geometry/data-format adaptation and accelerator cost. | Checkpoint cannot legally/technically target Q-SHIFT geometry, fair advantage vanishes versus correlated matching, or false/harmful pre-corrections outweigh useful corrections. Not first until the interface and model access are resolved. |
| **3** | **Tensor-network decoder as small-instance reference** | Approximate posterior contraction can approach ML and can exploit circuit-level noise structures that graph matching simplifies. Provides an independent estimate of attainable headroom. | Public surface-code/circuit-level work and code; d=3/r=5 may be practical offline. Bond/truncation choices, memory and tail latency could dominate. Not a real-time candidate by default. | If reference agrees with strong PM on nearly all sampled syndromes or cannot complete the small instance under a prespecified resource cap, the oracle role has little value. Do not present a small-instance oracle as deployable. |

## Considered but not ranked in the top three

- AlphaQubit/AQ2: strongest evidence for temporal, recurrent syndrome decoding and analog/hardware data, but not an inspected public implementation; training/data and accelerator setup are substantial. Its value is architectural comparison, not an immediate reproduction.
- Astra/GNN, neural BP, BP-OSD/BP-LSD: strong in QLDPC/Tanner-graph regimes. Q-SHIFT currently uses a small surface-code detector circuit; translating circuit hyperedges, measurements and correlated X/Z into a comparable Tanner-graph objective requires work not justified by current evidence.
- Correlated PyMatching: must remain a mandatory comparator/ablation, but is not a new candidate by itself. Prior Q-SHIFT preflight shows mode availability, not reliable utility.
- More Q-SHIFT CNN residual gates / ensembles: deprioritized after repeated paired underperformance and identity-output failures. Revisit only if independent failure-disagreement evidence changes the case.

## Ranking caveat

HAMLD's own upstream README reports limited surface-code improvement for data-qubit measurement syndromes, which is close to Q-SHIFT's memory experiment. This contradictory caveat is why the recommendation is a modest falsifiable reproduction, not a scale-up decision. Published gains on QLDPC, d>3, analog readout, or other circuit/noise models are not transferable effect-size estimates.
