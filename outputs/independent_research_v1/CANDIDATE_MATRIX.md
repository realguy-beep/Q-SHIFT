# Candidate comparison — preliminary screening

Scores are 1 (low) to 5 (high). Improvement and novelty are speculative upside, not evidence. Cost and integration scores are higher when cheaper/easier. Robustness scores higher when the method can handle model uncertainty. This is a screening matrix only. Literature verification and candidate-specific source audits remain pending.

| Candidate | Family | Upside | Q-SHIFT fit | Theory | Prior evidence | Stim fit | Feasible here | Cost | Robustness | Fair baseline | Novelty | Claude integration | Leakage risk | Initial view |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Syndrome-conditioned logical-class posterior summation on bounded subgraphs | Degeneracy-aware inference | 4 | 4 | 4 | 3 | 4 | 2 | 2 | 2 | 4 | 2 | 2 | 3 | High-upside feasibility study. First prove exactness on tiny circuits and cap separator width. |
| Tensor-network logical-class contraction | Degeneracy-aware inference | 5 | 3 | 5 | 4 | 3 | 1 | 1 | 2 | 4 | 1 | 1 | 3 | Strong theoretical comparator, likely impractical in this CPU-only instance for full d=5 circuit. Validate only tiny instances if implemented. |
| BP+OSD / generalized BP with calibrated factor graph | Probabilistic decoder | 3 | 3 | 4 | 4 | 2 | 3 | 3 | 2 | 4 | 1 | 3 | 3 | Conservative candidate. Stage S reportedly found min-sum 0.9 worse and OSD_CS-40+BP-200 near neutral, so only proceed with a defined structural change. |
| Learned hyperedge selection followed by matching | Hypergraph / matching | 3 | 4 | 3 | 3 | 4 | 3 | 3 | 2 | 4 | 2 | 3 | 3 | Plausible fit for correlated events, but distinguish real higher-order modeling from a convenient DEM approximation. |
| Belief matching or cluster-based local inference | Probabilistic / matching | 3 | 3 | 3 | 3 | 3 | 2 | 2 | 3 | 4 | 2 | 2 | 3 | Candidate for local degeneracy and correlation effects. Build on an auditable small factor graph. |
| Confidence-based selective escalation, matching then local search | Decoder ensemble | 2 | 4 | 3 | 3 | 5 | 4 | 4 | 4 | 5 | 2 | 4 | 3 | Conservative deployment idea. Needs confidence calibration and paired runtime/error tradeoff. |
| Neural-assisted correction proposals with exact syndrome validation | Neural hybrid | 3 | 3 | 3 | 3 | 4 | 2 | 2 | 2 | 4 | 2 | 3 | 4 | Could reduce search; validation enforces syndrome validity but does not guarantee logical class correctness. High leakage and overfit risk. |
| Spatiotemporal graph neural / transformer decoder | Neural | 4 | 3 | 2 | 3 | 4 | 1 | 1 | 2 | 4 | 2 | 1 | 5 | High compute and training-data demand; current neural results and sample size argue against scaling before a concrete representational hypothesis. |
| Bayesian noise-profile inference plus uncertainty-aware decoder selection | Noise inference / adaptation | 3 | 5 | 4 | 3 | 5 | 3 | 3 | 4 | 5 | 3 | 4 | 4 | Directly targets mismatch. Must infer from detector-only permitted data and beat a frozen pooled decoder out of root. |
| Change-point detection with bounded adaptive compute | Online adaptation | 2 | 4 | 3 | 2 | 4 | 3 | 3 | 4 | 5 | 2 | 4 | 4 | Fundamentally different from current static regime selection, but likely gains in latency or robustness rather than enormous LER ratios. |
| Importance sampling for rare logical faults | Rare-event statistics | 4 | 4 | 4 | 4 | 5 | 3 | 3 | 3 | 4 | 2 | 2 | 4 | High value for mapping logical error mechanisms and estimating tail rates, but unbiasedness/weight variance and support coverage must be demonstrated. |
| XZZX / code-distance / syndrome-extraction co-design | Code and circuit | 5 | 3 | 4 | 4 | 3 | 1 | 1 | 3 | 3 | 1 | 1 | 3 | High resource-direction upside; report separately from decoder-only gains and compare at declared qubit/time overhead. |

## Proposed feasibility shortlist

1. **Conservative:** selective escalation from fixed PyMatching to a bounded local search, using only syndrome-derived confidence. Check calibration, exact syndrome validity, paired errors, and added latency. Do not treat it as likely to yield orders-of-magnitude gain.
2. **High upside:** degeneracy-aware logical-class probability on tiny exactly solvable instances, then bounded subgraphs. Advancement requires agreement with exhaustive enumeration and a measured width/runtime scaling curve before any d=5 evaluation.
3. **Different mechanism:** Bayesian detector-profile inference under withheld regimes with uncertainty-aware selection. Compare against the frozen pooled fixed decoder and detector-profile calibrated alternatives, with root-held-out splits and explicit no-oracle inputs.

An importance-sampling prototype is a parallel measurement-method candidate, not a decoder. Literature and source review must determine whether it adds information beyond existing saved development arrays. No candidate is authorized for confirmatory evaluation by this matrix.
