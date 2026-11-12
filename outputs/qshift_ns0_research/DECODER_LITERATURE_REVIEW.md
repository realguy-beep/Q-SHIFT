# Decoder literature review (NS-0)

Search emphasis: primary research papers and upstream project documentation/code, including material available through 2026-11. Published results below are context, not expected Q-SHIFT gains.

## Highest-relevance lines of work

### Hypergraph approximate maximum-likelihood decoding (HAMLD)

HAMLD uses syndrome-guided hyperedge selection and probability-based truncation to approximate maximum-likelihood decoding while reducing redundant contraction work. Its 2026 *Physical Review Research* paper evaluates circuit-level noise on surface, color and bivariate-bicycle codes; for surface-code distance 3 with three repetition rounds it reports optimal accuracy and speedups against MLD/TN-MLD, and improvements against MWPM, Chromobius and BP+OSD in its two smallest settings. The public implementation is [kechen666/hamld](https://github.com/kechen666/hamld) and exposes Stim DEM input. Crucial qualification: its own README says accuracy gain on surface codes with data-qubit measurement syndromes is limited, and real-time superconducting requirements are not met. The Q-SHIFT distance-3/five-round Z-memory and synthetic spatial burst are not the paper's benchmark, and conversion of Q-SHIFT categorical channels remains a model-fidelity issue. This is the highest-value near-term candidate because it changes the inference objective, fits the small code, and is reproducible from public code; it is not presumed superior.

### AlphaQubit and streaming neural syndrome decoders

AlphaQubit combines a recurrent per-stabilizer state with convolutions and attention over stabilizer embeddings. It uses syndrome histories and, where available, analog readout. The 2024 Nature study used simulated pretraining and limited experimental fine-tuning; it reports gains over correlated matching/tensor-network baselines on Sycamore distance-3/5 data and correlated matching (including analog input) on simulated distances through 11. That evidence depends on hardware-specific training data and is not evidence for Q-SHIFT's synthetic discrete-detector model. The 2025/26 AlphaQubit 2 preprint adds a streaming recurrent/spatial-transformer architecture, reports long-duration and noise-strength generalization and real-time distance-11 decoding on accelerators. Neither result transfers to d=3 without reproduction, and no open AlphaQubit training/inference implementation was identified in the inspected public sources. This is an architectural reference, not the first candidate to implement locally.

### Neural pre-decoding and local-plus-global hybrids

NVIDIA's 2026 Ising-Decoding release provides public Stim/PyTorch inference/training recipes for CNN pre-decoders composed with global decoders. The public surface models have receptive fields R=9/13, and available pretrained weights are access-controlled on Hugging Face under separate licensing. The project lists correlated PyMatching as its strongest classical comparison. The repo recommends training at the receptive-field distance and 67 million shots per epoch on eight GPUs; published headline performance should not be read as a low-cost Q-SHIFT result. The local-predecode/global-fallback pattern is a better transfer hypothesis than another global CNN that predicts Q-SHIFT's rare residual label, but exact d=3 / 5-round / 40-detector mapping, checkpoint license/access, noise-channel compatibility and hardware cost must be checked first.

### Tensor-network / near-ML reference

Approximate tensor-network decoding has strong surface-code accuracy; *Tensor-Network Decoding Beyond 2D* extends contraction methods to repeated syndrome/circuit-level settings and reports improvement over matching on rotated surface-code circuit noise. The public [tndecoder3d](https://github.com/ChriPiv/tndecoder3d) source is suitable to investigate as a small-instance reference. Contraction cost and approximation sensitivity make it a benchmark/oracle candidate, not the preferred online decoder. Exact maximum-likelihood methods provide a way to quantify headroom at small instances, but their compute scaling can prevent broader use.

## Other families and why they rank lower here

- **BP-OSD / BP-LSD:** important general-purpose QLDPC references, with public implementations in [quantumgizmos/ldpc](https://github.com/quantumgizmos/ldpc) and its [BP+OSD predecessor](https://github.com/quantumgizmos/bp_osd). OSD post-processing is expensive; LSD localizes reliability-guided statistics decoding to disconnected error clusters to enable parallelism. The [LSD paper](https://arxiv.org/abs/2406.18655) includes later circuit-level surface-code comparisons, but its core motivation and strongest practical case are QLDPC. Q-SHIFT's current rotated surface code already has a mature matching incumbent, so these are not the first fair comparator absent a clearly specified parity-check/hypergraph mapping and evidence of a relevant advantage.
- **Astra/GNN message passing:** the 2025 Astra work learns message passing on a Tanner graph, improves upon BP+OSD in its QLDPC regimes, and tests distance extrapolation. Its paper explicitly treats X/Z components separately in the correlated-decoding discussion and the primary surface-code results concern code-capacity noise. That is not the same as Q-SHIFT's circuit-level correlated-burst problem. Treat as an alternative for a code-family expansion, not as direct evidence here.
- **Neural BP:** trainable message updates can improve BP under short-cycle/degenerate quantum Tanner graphs, but need syndrome constraints, noise priors and cross-root generalization. Most strongest evaluations target QLDPC codes, not this small rotated surface circuit.
- **Transformers / state-space models:** AlphaQubit 2 shows that persistent causal state can handle long streams with fixed compute per cycle. The novelty for Q-SHIFT would need a streaming comparator and delayed-change analysis; simply fitting a temporal neural net to IID synthetic labels would not reproduce the contribution.
- **Decoder ensembles:** combining diverse decoders may reduce error only when their failures are complementary and a selector is calibrated. Current Q-SHIFT CNN records show sparse changes to PyMatching were net harmful or zero; no local failure-diversity analysis justifies an ensemble yet. Add one only after per-shot disagreements and root-level conditional risk support it.
- **Correlation-aware matching:** `enable_correlations=True` adds a two-pass correction using decomposable hyperedge metadata. It can improve a correctly represented decomposable correlation, but is not exact treatment of arbitrary higher-order or cross-round common-cause events. Q-SHIFT's own preflight/pilot has not demonstrated benefit over ordinary matching.

## Evidence interpretation

The published comparisons vary in code, noise, measurement visibility, analog access, train/test split and compute target. A meaningful Q-SHIFT result must compare the candidate and incumbents on the same fresh circuit-generated detector/observable rows, with policy selection confined to separate development roots. It must report unconditional LER and paired root-cluster effects, runtime/latency and memory, and explicitly distinguish exact categorical circuit noise from the approximate DEM supplied to some decoders.

## Primary sources

- [AlphaQubit, Nature (2024)](https://www.nature.com/articles/s41586-024-08148-8); [AlphaQubit 2, arXiv:2512.07737](https://arxiv.org/abs/2512.07737).
- [HAMLD, Physical Review Research (2026)](https://doi.org/10.1103/ydb8-vd3x); [HAMLD source and build instructions](https://github.com/kechen666/hamld).
- [Fast and accurate AI-based pre-decoders for surface codes, arXiv:2604.12841](https://arxiv.org/abs/2604.12841); [NVIDIA Ising-Decoding source](https://github.com/NVIDIA/ising-decoding).
- [Tensor-Network Decoding Beyond 2D, PRX Quantum (2024)](https://doi.org/10.1103/PRXQuantum.5.040303); [implementation](https://github.com/ChriPiv/tndecoder3d).
- [Machine learning message-passing for scalable QLDPC decoding, npj Quantum Information (2025)](https://www.nature.com/articles/s41534-025-01033-w); [Astra source](https://github.com/arshpreetmaan/astra).
- [BP+OSD, Quantum (2021)](https://doi.org/10.22331/q-2021-11-22-585); [LSD, arXiv:2406.18655](https://arxiv.org/abs/2406.18655); [upstream BP+OSD repository](https://github.com/quantumgizmos/bp_osd); [LDPC library](https://github.com/quantumgizmos/ldpc).
- [PyMatching paper](https://doi.org/10.1145/3505637); [PyMatching upstream API](https://github.com/oscarhiggott/PyMatching).
- [Stim paper](https://arxiv.org/abs/2103.02202); [Stim DEM format semantics](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md).
