# Novelty and publication assessment

## Literature context

The targeted review found substantial prior work on noise-aware decoding, syndrome-based calibration, bias-tailored codes, learned decoders, and runtime adaptation. This search is evidence-informed but not an exhaustive systematic review; it cannot certify novelty.

- **Adaptation is established.** The Local Clustering Decoder includes an FPGA adaptivity engine that updates graph properties at runtime from control signals such as heralded leakage, and evaluates leakage-aware performance. This differs from Q-SHIFT’s proposed detector-only noise-regime classification, but rules out a broad “first adaptive decoder” claim. [Ziad et al., *Nature Communications* 16, 11048 (2025)](https://doi.org/10.1038/s41467-025-66773-x).
- **Decoder sensitivity and adaptation limits are studied.** Darmawan analyzes how decoder performance changes when local-noise parameters are mischaracterized, quantifying which noise features matter for a near-optimal surface-code decoder. [Darmawan, *Physical Review A* 112 (2025)](https://doi.org/10.1103/r2dc-qcrx).
- **Syndrome-based noise estimation is established.** Bayesian inference from surface-code syndrome statistics includes sequential Monte Carlo for time-varying noise parameters, directly overlapping the general premise of estimating changing noise from syndrome observations. [Kobori and Todo, *Physical Review A* (2025)](https://doi.org/10.1103/wg5h-spy6).
- **Experimentally informed matching calibration is established.** Syndrome correlations have been used to infer physical error mechanisms and optimize matching weights without relying only on a theoretical noise model. [Remm et al., *Physical Review Research* 8, 013044 (2026)](https://doi.org/10.1103/z1ng-wg3k).
- **Bias-aware decoder design is established.** Tailored surface codes and matching decoders have demonstrated strong performance under biased Pauli noise; basis dependence alone is not a novel contribution. [Tuckett et al., *Physical Review Letters* 124, 130501 (2020)](https://doi.org/10.1103/PhysRevLett.124.130501).
- **Learned decoding is established.** AlphaQubit combines sequence modeling and attention and reports results on experimental Sycamore data, making a small random-forest surrogate under simulated noise a weak novelty position. [Davies et al., *Nature* 635, 834–840 (2024)](https://doi.org/10.1038/s41586-024-08148-8).
- **The fixed matching baseline is mature and optimized.** PyMatching v2’s sparse blossom implementation is designed for fast MWPM decoding, so a bank of nearby weights should be evaluated against a strong calibrated global model, not a deliberately weak nominal-only comparator. [Higgott and Gidney, “Sparse Blossom” (2023)](https://arxiv.org/abs/2303.15933).

## What Q-SHIFT can currently claim

The project demonstrates a reproducible simulation pipeline, multiple PyMatching configurations, several noise models, paired decoder evaluation, detector-only regime estimation prototypes, fallback logic, and substantial integrity/debugging work. It establishes conditional static calibration gains against nominal weights in Phase 4A/4B, followed by a null calibrated-versus-pooled comparison in Phase 4C. The new multi-distance feasibility audit finds no stable, repeated specialist utility in the tested bank.

These results are scientifically useful as feasibility evidence. They do not establish adaptive superiority, a general limit on adaptation, or a new decoding algorithm. A cautious internal technical report or software-demonstration note may be appropriate; the combined results are not yet a strong novel negative-results benchmark because:

- the adaptive controller has no fresh frozen confirmatory evaluation;
- Phase 4C Stage 2 calibration arrays are missing and its RNG protocol was amended prospectively after the original plan;
- Phase 4B has a fresh-template deviation;
- early prototype and Phase 5 metrics required correction, and exploratory phases use different codes, regimes, and estimands;
- the headroom pilot has only five calibration and five evaluation roots per cell and very sparse logical failures at larger distances;
- the gate is a screening rule, not a powered equivalence or noninferiority design;
- current simple noise regimes and nine nearby decoder models yield sparse prediction changes.

## Publication decision implication

The most defensible future paper direction is a **narrow decoder-utility headroom benchmark**: when does a calibration-selected decoder bank create enough distinct, stable logical utility for a causal selector to beat its strongest pooled fixed baseline? The current data motivate this question but do not answer it across conditions strongly enough for a publishable negative conclusion. Any claim must be explicitly restricted to the tested Stim circuits and model families.
