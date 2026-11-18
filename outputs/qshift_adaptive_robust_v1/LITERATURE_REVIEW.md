# Literature review: adaptive, noise-aware and correlated-error decoding

**Verification status.**
- **[V]:** metadata checked by web search on 2026-11-18 (title, authors, venue, identifier).
- **[K]:** cited from prior knowledge and **not re-verified this session**. Check before any external use.
- **Scope:** only claims stated in abstracts or listings are attributed to the papers. Nothing here is a full-text review.

## 1. Decoders for circuit-level and correlated noise

| Ref | Status | Relevance |
|---|---|---|
| J. Roffe, D. R. White, S. Burton, E. Campbell, "Decoding across the quantum low-density parity-check code landscape," *Phys. Rev. Research* 2, 043423 (2020); arXiv:2005.07016 | [V] | BP+OSD as a general QLDPC decoder; the basis of the `ldpc` package Q-SHIFT uses |
| P. Panteleev, G. Kalachev, "Degenerate quantum LDPC codes with good finite length performance," *Quantum* 5, 585 (2021); arXiv:1904.02703 | [K] | Origin of OSD post-processing for degenerate quantum codes |
| O. Higgott, T. C. Bohdanowicz, A. Kubica, S. T. Flammia, E. T. Campbell, "Improved decoding of circuit noise and fragile boundaries of tailored surface codes," *Phys. Rev. X* 13, 031007 (2023); arXiv:2203.04948 | [V] | Belief-matching and belief-find: BP-reweighted matching, threshold 0.94% vs 0.82% for MWPM. Q-SHIFT's parallel belief-matching failed the d=7 screen; serial is untested |
| O. Higgott, C. Gidney, "Sparse Blossom: correcting a million errors per core second with minimum-weight matching," *Quantum* 9, 1600 (2025); arXiv:2303.15933 | [V] | PyMatching v2, the comparator implementation |
| C. Gidney, "Stim: a fast stabilizer circuit simulator," *Quantum* 5, 497 (2021) | [K] | Simulator |
| A. G. Fowler, "Optimal complexity correction of correlated errors in the surface code," arXiv:1310.0863 (2013) | [K] | The correlated-matching reweighting idea behind `enable_correlations` |
| N. Raveendran, B. Vasić, "Trapping sets of quantum LDPC codes," *Quantum* 5, 562 (2021); arXiv:2012.15297 | [V] | Defines quantum trapping sets; relevant to BP non-convergence on floor failures |
| T. Hillmann, L. Berent, A. O. Quintavalle, J. Eisert, R. Wille, J. Roffe, "Localized statistics decoding for quantum low-density parity-check codes," *Nat. Commun.* 16 (2025), doi:10.1038/s41467-025-63214-7; arXiv:2406.18655 | [V] | BP+LSD: parallel, local OSD-like post-processing that performs on par with BP+OSD at lower runtime. A latency route, not an accuracy route |
| S. Wolanski, B. Barber, "Ambiguity Clustering: an accurate and efficient decoder for qLDPC codes," arXiv:2406.14527 (2024) | [V] | BP-guided clustering that searches clusters independently; claims large speedups over BP-OSD with no fidelity loss |
| N. Shutty, M. Newman, B. Villalonga, "Efficient near-optimal decoding of the surface code through ensembling," arXiv:2401.12434; *Phys. Rev. Lett.* 136, 070603 (2026), doi:10.1103/77j6-32xx | [V] | "Harmonization" ensembles of matching decoders approach maximum-likelihood accuracy. Directly relevant to the degeneracy-dominated floor (§BACKGROUND_ERROR_ANALYSIS) |
| S. Bravyi, M. Suchara, A. Vargo, "Efficient algorithms for maximum likelihood decoding in the surface code," *Phys. Rev. A* 90, 032326 (2014) | [K] | Tensor-network maximum-likelihood decoding: the degenerate optimum that MLE-consistent failures need |
| P. Iyer, D. Poulin, "Hardness of decoding quantum stabilizer codes," *IEEE Trans. Inf. Theory* 61, 5209 (2015) | [K] | Degenerate maximum-likelihood decoding is #P-hard in general, which bounds expectations |
| J. Bausch et al., "Learning high-accuracy error decoding for quantum processors," *Nature* 635, 834–840 (2024), doi:10.1038/s41586-024-08148-8 | [V] | AlphaQubit, a transformer neural decoder. Shows neural decoders can beat matching and tensor-network baselines given very large training sets. Speed and scalability remain open |

## 2. Noise estimation from syndromes and calibrated priors

| Ref | Status | Relevance |
|---|---|---|
| T. Wagner, H. Kampermann, D. Bruß, M. Kliesch, "Pauli channels can be estimated from syndrome measurements in quantum error correction," *Quantum* 6, 809 (2022); arXiv:2107.14252 | [V] | Identifiability: Pauli noise with correlations over up to ⌊(d_p−1)/2⌋ qubits is estimable from syndrome statistics. A theoretical anchor for "detector-only" estimation and its limits (cf. the V1.6 FAIL) |
| E. H. Chen, T. J. Yoder, et al., "Calibrated decoders for experimental quantum error correction," *Phys. Rev. Lett.* 128, 110504 (2022); arXiv:2110.04285 | [V] | Matching weights calibrated from experimental syndrome correlations |
| V. Sivak, M. Newman, P. Klimov, "Optimization of decoder priors for accurate quantum error correction," *Phys. Rev. Lett.* 133, 150603 (2024); arXiv:2406.02700 | [V] | RL-style optimisation of DEM priors, using small codes as local sensors. Priors are tied to the decoder used in training |
| E. Takou, K. R. Brown, "Estimating decoding graphs and hypergraphs of memory QEC experiments," *Phys. Rev. A* 112, 052414 (2025); arXiv:2504.20212 | [V] | DEM reconstruction from two-point and multipoint detector correlators. The closest established method to Q-SHIFT's parity-moment learner |
| Arms et al., "Estimating Detector Error Models on Google's Willow," arXiv:2512.10814 | [V], author list only partly checked | Long-range detector correlations; checking DEM fit without a circuit model |
| E. Takou, et al. (incl. K. R. Brown), "Logical error estimation from syndrome data of surface-code experiments," arXiv:2606.11496 (2026) | [V] | Syndrome-estimated DEMs comparable to RL-optimised DEMs on Willow data |
| H. Cao, D. Feng, C. Ye, F. Pan, "Differentiable Maximum Likelihood Noise Estimation for Quantum Error Correction," arXiv:2602.19722 (2026) | [V] | Exact, differentiable syndrome-likelihood maximisation for DEM priors (tensor networks for surface codes). A principled joint estimator of background and correlated parameters |

## 3. Time-varying noise, bursts and change detection

| Ref | Status | Relevance |
|---|---|---|
| S. T. Spitz, B. Tarasinski, C. W. J. Beenakker, T. E. O'Brien, "Adaptive weight estimator for quantum error correction in a time-dependent environment," *Adv. Quantum Technol.* 1, 1800012 (2018); arXiv:1712.02360 | [V] | Weights estimated online from measured data without an error model; works when drift is slow relative to (cycle time ÷ error rate) |
| D. Bhardwaj, E. Takou, Y. Lin, K. R. Brown, "Adaptive Estimation of Drifting Noise in Quantum Error Correction," arXiv:2511.09491 (2025) | [V] | Closest prior work to Q-SHIFT's mission: online drift estimation for decoding. **Any Q-SHIFT adaptive claim must be positioned against it** |
| M. McEwen et al., "Resolving catastrophic error bursts from cosmic rays in large arrays of superconducting qubits," *Nat. Phys.* 18, 107–111 (2022); arXiv:2104.05219 | [V] | Physical motivation for chip-wide correlated bursts |
| Y. Suzuki et al., "Q3DE: A fault-tolerant quantum computer architecture for multi-bit burst errors by cosmic rays," MICRO 2022 | [K] | Burst detection followed by code or decoder response |
| E. S. Page, "Continuous inspection schemes," *Biometrika* 41, 100–115 (1954) | [K] | CUSUM |
| G. Lorden, "Procedures for reacting to a change in distribution," *Ann. Math. Statist.* 42, 1897–1908 (1971) | [K] | Optimality of CUSUM (worst-case detection delay) |

## 4. Biased noise and code tailoring (benchmark axis)

| Ref | Status | Relevance |
|---|---|---|
| D. K. Tuckett, S. D. Bartlett, S. T. Flammia, B. J. Brown, "Fault-tolerant thresholds for the surface code in excess of 5% under biased noise," *Phys. Rev. Lett.* 124, 130501 (2020) | [K] | Bias-tailored decoding |
| J. P. Bonilla Ataides, D. K. Tuckett, S. D. Bartlett, S. T. Flammia, B. J. Brown, "The XZZX surface code," *Nat. Commun.* 12, 2172 (2021) | [K] | Bias-tailored code |

## 5. What is established and what could be a defensible contribution

**Established (not novel):**
- BP+OSD, belief-matching, correlated matching, ensembles of matchers;
- DEM estimation from detector correlators, RL or likelihood-optimised priors;
- CUSUM change detection;
- online weight estimation under drift (Spitz 2018; Bhardwaj 2025).

**Candidate contributions.** These are combinations or evaluations, not new algorithms. Each is defensible only if the evidence holds:
1. **A pre-registered, strong-comparator benchmark of adaptive decoding** across the noise axes in `BROAD_NOISE_BENCHMARK.md`. The comparators include pooled-calibrated and periodically recalibrated static decoders, the arm most published adaptive results omit. Its value is the methodology and the negative/positive evidence, not a new decoder.
2. **Mismatch-robust burst-support inference.** Joint estimation of a background scale (per detector class) and a localized burst, with an explicit UNKNOWN outcome. This is a small extension of correlator-based DEM estimation (Takou & Brown 2025). Its novelty is uncertain and needs a literature check against 2511.09491 and 2602.19722 before any claim.
3. **A decomposition of where relative gains come from:** background inference vs burst handling vs adaptation vs information access, using ablations. This addresses a gap: published relative reductions often mix these.

**No algorithmic novelty is claimed.**
