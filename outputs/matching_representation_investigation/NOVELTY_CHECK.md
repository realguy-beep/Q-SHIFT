# Novelty and prior-method check

This investigation does not support a publication-level novelty claim for either candidate.

Stim's documented DEM syntax defines `^` as a suggested decomposition marker, not a physical event. PyMatching already provides standard and two-pass correlation-aware matching for decomposable hyperedge information. Belief-matching and belief-find use belief-propagation information to improve graph-decoder weights/decisions; BP+OSD and related inference methods address broader non-pairwise decoding. Thus the present work is best described as a small implementation audit and feasibility study around representation sensitivity and a deliberately restricted local exact subproblem.

Potential engineering contribution: an explicit validation rule that only rewrites a DEM mechanism to a direct matching edge when its *complete* parity support is graphlike and preserves its probability and observable mask, while rejecting hyperedges and logical-only events. Candidate B demonstrates a small exact conditional calculation with a transparent boundary approximation and fallback. Neither is a demonstrated new decoder architecture.

References checked:

1. [Stim DEM file format](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md) — separator and event semantics.
2. Higgott, [PyMatching: A Python package for decoding quantum codes with minimum-weight perfect matching](https://arxiv.org/abs/2105.13082), ACM TQC 3 (2022) — matching graph decoder.
3. Higgott et al., [Improved decoding of circuit noise and fragile boundaries of tailored surface codes](https://doi.org/10.1103/PhysRevX.13.031007), PRX 13, 031007 (2023) — belief-matching/belief-find.
4. Roffe et al., [Decoding across the quantum low-density parity-check code landscape](https://doi.org/10.1103/PhysRevResearch.2.043423), PR Research 2, 043423 (2020) — belief propagation plus ordered-statistics postprocessing.
5. Higgott and Gidney, [Sparse Blossom: correcting a million errors per core second with minimum-weight matching](https://arxiv.org/abs/2303.15933) — PyMatching v2 matching implementation context.

These references establish related techniques, not exhaustive priority or novelty. A broader literature review would be needed before any novelty claim.
