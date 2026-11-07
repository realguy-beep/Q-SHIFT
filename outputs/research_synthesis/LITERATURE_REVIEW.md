# Literature review: position and overlap

This review verifies references against publisher records or official project documentation. It focuses on the requested decoder/adaptation topics, not an exhaustive systematic review.

## Adaptive and noise-aware decoding

Noise-aware adaptation is established. Darmawan, *Optimal adaptation of surface-code decoders to local noise* (Physical Review A, 2025), uses a tensor-network decoder and process-matrix noise descriptions to quantify which physical-noise parameters materially affect near-optimal decoding. Its reported finding—that a small subset of parameters may be sufficient to adapt—directly overlaps the premise of selecting decoders as noise changes. Q-SHIFT cannot claim novelty for “estimate regime, switch decoder.” A possible distinction is a benchmark of whether a practical calibration-selected PyMatching bank has enough utility headroom to justify causal switching. Current Q-SHIFT evidence is too small and mostly null to establish that contribution. [APS article](https://journals.aps.org/pra/abstract/10.1103/r2dc-qcrx).

The Local Clustering Decoder (LCD) paper presents an FPGA decoder with an adaptation engine that updates graph properties in response to prelearned runtime control signals such as heralded leakage. This differs from Q-SHIFT's software classifier of detector windows, but establishes that runtime adaptation and hardware engineering are active areas. A publication should distinguish simulated hidden regime labels from observable hardware triggers and compare the contribution with leakage-triggered adaptation. [Nature Communications article](https://www.nature.com/articles/s41467-025-66773-x).

Chen et al.'s *Calibrated Decoders for Experimental Quantum Error Correction* reports a perfect-matching decoder calibrated from measured correlated events. This is a precedent for improving a matching decoder from calibration evidence. Q-SHIFT's static measurement-heavy result is related but is not itself a new adaptive method. [Physical Review Letters article](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.128.110504).

## Biased-noise decoding

Tuckett et al.'s *Tailoring Surface Codes for Highly Biased Noise* demonstrates gains by tailoring surface-code structure and boundaries to dephasing-biased noise. This is not just swapping weights among standard DEM/PyMatching candidates; it changes code structure and studies bias directly. However, it shows that code/decoder behavior under Pauli bias is well studied. Phase 2B's basis-specific fixed-model selection is expected given memory orientation and Pauli component, not a standalone novelty claim. Q-SHIFT would need distance scaling, bias sweeps and stronger physical controls. [Physical Review X article](https://journals.aps.org/prx/abstract/10.1103/PhysRevX.9.041031).

## PyMatching, DEMs, and correlated matching

PyMatching is an established and efficient minimum-weight perfect-matching implementation. It should not be called maximum-likelihood decoding in general: it optimizes a correction under supplied graph weights, while logical-class posterior decoding is a distinct objective. Correlated mode can use decomposition hints but remains constrained by the supplied DEM. [Peer-reviewed ACM paper](https://doi.org/10.1145/3505637).

Stim's official documentation defines a DEM as independent error mechanisms with detector symptoms and logical frame changes. It explains that approximate disjoint-error conversion can approximate certain categorical Pauli channels as independent mechanisms; PAULI_CHANNEL_1, PAULI_CHANNEL_2 and ELSE_CORRELATED_ERROR can require the approximation. This matters to Phase 2B's categorical Pauli channel. It should not automatically be attributed to later Phase 4 native DEPOLARIZE1/2 experiments. Phase 2C was motivated by this model gap, but did not isolate its effect. [Stim error-analysis guide](https://github.com/quantumlib/Stim/blob/main/doc/usage_command_line.md); [DEM format specification](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md).

## Learned and maximum-likelihood decoders

Bravyi, Suchara and Vargo describe exact maximum-likelihood decoding for a restricted surface-code noise case and approximate tensor-network decoding for broader local noise. Exactness depends on assumptions; a generic classifier is not thereby exact. Phase 2C's forest estimates an observable label from finite samples and supplies no full-circuit posterior error bound. [Physical Review A article](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.90.032326).

AlphaQubit sets a high evidence bar: it combines simulated and experimental training, tests on experimental surface-code data at distances 3 and 5, and reports simulated performance up to distance 11 under richer device-like noise. This does not mean every learned model must be that large, but shows the evidence scale required before claiming a strong learned-decoding improvement. [Nature article](https://www.nature.com/articles/s41586-024-08148-8).

## Benchmarking and scaling

The 2025 *Benchmarking quantum computers* review emphasizes using metrics that match the claimed capability. Q-SHIFT should separate paired shot-level disagreement, independent seed-level uncertainty, runtime overhead and generalization to unseen schedules. Many correlated shots do not replace independent noise realizations. [Nature Reviews Physics review](https://www.nature.com/articles/s42254-024-00796-z).

A nonsignificant superiority test is not evidence that two decoders are equivalent. Lakens' peer-reviewed primer on equivalence tests explains why a smallest effect size of interest and sufficiently narrow confidence interval are needed to support a practically null claim. Thus Phase 4C's p=.66658 is “no detected improvement” and not proof that a meaningful adaptive benefit is absent; its interval must be compared with a margin fixed before the experiment. [Social Psychological and Personality Science article](https://doi.org/10.1177/1948550617697177).

Surface-code experimental work measures performance across code distance and rounds. Google's *Suppressing quantum errors by scaling a surface code logical qubit* reports multiple distances, rounds and measured noise characterization. Q-SHIFT's main adaptation studies are distance-3 simulations, so they do not establish threshold behavior, asymptotic scaling or hardware utility. [Nature 2023 article](https://www.nature.com/articles/s41586-022-05434-1); [Nature 2025 below-threshold study](https://doi.org/10.1038/s41586-024-08449-y).

Stim is a standard fast stabilizer circuit simulator. Its peer-reviewed paper supports simulation claims, not transfer of simplified synthetic channels to hardware. [Quantum article](https://quantum-journal.org/papers/q-2021-07-06-497/).

## Synthesis and verified references

The literature supports noise-aware decoding but weakens broad novelty claims for regime detection, decoder switching, bias tailoring or calibrated matching. The credible opening is a rigorous multi-distance benchmark of when a practical calibration-selected decoder bank has paired LER headroom over the strongest fixed model and whether causal detector data can exploit it.

1. Craig Gidney, “Stim: a fast stabilizer circuit simulator,” *Quantum* 5, 497 (2021). [DOI](https://doi.org/10.22331/q-2021-07-06-497).
2. Oscar Higgott, “PyMatching: A Python Package for Decoding Quantum Codes with Minimum-Weight Perfect Matching,” *ACM Transactions on Quantum Computing* 3(3), Article 16 (2022). [DOI](https://doi.org/10.1145/3505637).
3. David K. Tuckett et al., “Tailoring Surface Codes for Highly Biased Noise,” *Physical Review X* 9, 041031 (2019). [DOI](https://doi.org/10.1103/PhysRevX.9.041031).
4. Edward H. Chen et al., “Calibrated Decoders for Experimental Quantum Error Correction,” *Physical Review Letters* 128, 110504 (2022). [DOI](https://doi.org/10.1103/PhysRevLett.128.110504).
5. Sergey Bravyi, Martin Suchara and Alexander Vargo, “Efficient algorithms for maximum likelihood decoding in the surface code,” *Physical Review A* 90, 032326 (2014). [DOI](https://doi.org/10.1103/PhysRevA.90.032326).
6. Andrew S. Darmawan, “Optimal adaptation of surface-code decoders to local noise,” *Physical Review A* 112, 042431 (2025). [DOI](https://doi.org/10.1103/r2dc-qcrx).
7. Abbas B. Ziad et al., “Local clustering decoder as a fast and adaptive hardware decoder for the surface code,” *Nature Communications* 16, 11048 (2025). [DOI](https://doi.org/10.1038/s41467-025-66773-x).
8. Google Quantum AI, “Suppressing quantum errors by scaling a surface code logical qubit,” *Nature* 614, 676–681 (2023). [DOI](https://doi.org/10.1038/s41586-022-05434-1).
9. J. Bausch et al., “Learning high-accuracy error decoding for quantum processors,” *Nature* 635, 834–840 (2024). [DOI](https://doi.org/10.1038/s41586-024-08148-8).
10. Timothy Proctor et al., “Benchmarking quantum computers,” *Nature Reviews Physics* 7, 105–118 (2025). [DOI](https://doi.org/10.1038/s42254-024-00796-z).
11. Daniël Lakens, “Equivalence Tests: A Practical Primer for t Tests, Correlations, and Meta-Analyses,” *Social Psychological and Personality Science* 8(4), 355–362 (2017). [DOI](https://doi.org/10.1177/1948550617697177).
