# Q-SHIFT Phase 2A protocol

This is a new exploratory decoder-bank and oracle-headroom study. It does not modify previous experiments and does not treat the previously inspected 307,200-shot development evaluation as confirmatory evidence.

## Selection and test separation

The existing development calibration NPZ is the only decoder-selection data. Its three generating regimes have 20,000 shots each. The global fixed decoder minimizes equal-regime mean calibration LER. The per-regime decoder minimizes that regime's calibration LER. Exact ties are resolved by the lowest frozen grid index. This selection uses calibration observables and is an offline development step; it does not represent a deployable regime selector.

The Phase 2A evaluation is fresh: 20 independent RNG roots per regime and 10,000 shots per root, for 600,000 total. Every one of the nine matching models receives the exact same detector shot matrix within each root. Fresh evaluation labels are used only for scoring and explicitly retrospective oracles.

## Comparators and estimands

1. Calibration-selected best global fixed decoder.
2. Calibration-selected decoder for each known generating regime (regime labels are given only to this non-deployable comparison).
3. Stage 1 pooled fixed decoder 1.
4. Nominal decoder 4.
5. Two retrospective evaluation-label diagnostics: hindsight best model per regime and a per-shot best-of-nine logical prediction. These are unattainable lower bounds on residual error, not decoders available at inference.

The primary headroom is equal-regime mean residual LER for the calibration-selected per-regime policy minus the calibration-selected global fixed model. For per-regime bank comparisons, each non-global candidate is paired against the global fixed model across 20 independent roots. Seed-cluster bootstrap intervals and root-level paired sign-flip tests are used; Holm adjustment covers the 24 prespecified non-global decoder-by-regime comparisons. Shotwise Wilson intervals and exact paired McNemar summaries are descriptive secondary measures, not substitutes for root replication.

## Model and circuit

Use the existing ordered 3-by-3 grid over assumed gate and measurement probabilities 0.001, 0.003, 0.006 with Stim `surface_code:rotated_memory_z`, distance 3, five rounds, native circuit-level depolarizing gate noise, and basis-appropriate measurement flip noise. The generating conditions remain (0.006, 0.001), (0.003, 0.003), and (0.001, 0.006). Detector and logical-observable definitions remain fixed.

## Interpretation boundaries

The stored evidence contains detector bits, logical-observable labels, and predicted logical-observable flips; it does not store physical correction chains. Graph topology and edge fault-ID mappings can be inspected, but do not claim to recover physical corrections from logical-output arrays. The oracle is retrospective. All findings are simulation-only and exploratory. Noise is stationary within each five-round circuit; this study does not validate within-circuit adaptation.
