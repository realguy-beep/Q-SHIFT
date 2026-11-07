# Direction C — Error-correction operating limits

## Question

How do code distance, physical gate-fault probability, measurement-fault probability, and selected correlation structure change logical reliability in a controlled surface-code memory simulation?

## Established science

Distance scaling and threshold behavior are foundational surface-code questions. Dennis, Kitaev, Landahl and Preskill established the statistical-mechanical threshold framework for topological quantum memory ([*J. Math. Phys.* 43, 4452 (2002)](https://doi.org/10.1063/1.1499754)). Recent hardware work has measured logical-error suppression with increasing surface-code distance, while also identifying correlated events and model mismatch as practical limits; for example, Google’s below-threshold study reports distance-dependent suppression and a residual error floor in long repetition-code data ([*Nature* 638, 920 (2025)](https://doi.org/10.1038/s41586-024-08449-y)). Threshold and finite-distance scaling are therefore well-established topics, not open in themselves.

## Existing Q-SHIFT readiness

The headroom phase has already preflighted rotated X/Z memories at distances 3, 5, and 7 with rounds equal to distance, producing 24, 120, and 336 detectors. It separately builds native-depolarizing and biased Pauli banks and checks noiseless behavior. Its 900,000 paired evaluation shots were aimed at specialist headroom at a small set of fixed noise strengths, not at a systematic threshold curve. Rare errors at larger distance led to many zero-error cells, so those data do not establish threshold or precise scaling.

## Feasibility and presentation value

- **Reuse:** High for circuits, DEMs, both memory bases, distance-specific model construction, and batched sampler/decoder code.
- **Implementation:** Low-to-moderate for controlled sweeps; ensure measurements and data-gate probabilities are independently varied and use identical code definitions within each comparison.
- **Compute:** Moderate to high for d=7 and a broad probability sweep. A short d=3/5 feasibility grid is manageable; accurate low-LER estimates require many shots or importance sampling, which adds validation burden.
- **Measurability:** High. The output is an intuitive reliability-vs-noise/distance plot with uncertainty. This is the most robust direction if a null adaptive result still needs a strong science-model narrative.
- **Competition value:** Very high and accessible: “when does adding code distance help, and how do faulty measurements change the benefit?”
- **Novelty:** Low for a generic threshold sweep. A narrower contribution might be a transparent, reproducible sensitivity map for an explicitly specified circuit/noise family, not a new threshold discovery.
- **Risk:** Lower risk of an uninterpretable null, but risk of sparse failures, runtime, and appearing textbook-like unless comparisons answer a specific question.

## Assessment

Choose as the fallback. If the correlation-aware pilot yields no stable practical benefit, run a predeclared finite-distance operating map with no adaptive claims. Do not call it a new threshold estimate unless multiple distances, enough physical-error points, finite-size analysis, and uncertainty justify that term.

