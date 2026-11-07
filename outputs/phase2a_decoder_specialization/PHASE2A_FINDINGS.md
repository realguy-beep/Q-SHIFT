# Q-SHIFT Phase 2A findings

## Executive finding

The nine candidate DEMs share the same detector graph topology and have nine different edge-weight fingerprints. On the fresh paired evaluation set, they form six observed logical-prediction equivalence groups: {0,4,8}, {1}, {2}, {3,7}, {5}, {6}. These are finite-sample groups, not mathematical equivalence proofs.

Calibration selected zero-based decoder-grid index 1 as the best global fixed model and index 1 in all three regimes. The fresh 600,000-shot evaluation therefore gives the same result for the calibrated per-regime policy and best global fixed decoder: 4,192 errors (LER 0.69867%) each. Headroom is exactly zero conditional on these selected indices; the paired bootstrap CI is [0, 0] and root sign-flip p=1. This is not an adaptive advantage.

## Prior evidence integrity

The prior prototype manifest passed SHA-256 verification. All 50 prior evaluation bundles were independently decoded again. The 307,200-shot totals reproduced: identity/no decode 19,726 errors, pooled index 1 1,989, nominal index 4 1,976. Those already-inspected samples were not reused as the Phase 2A fresh evaluation.

## Decoder graph and logical output behavior

All nine circuits produce 40 detectors and one logical observable; each matching graph has 142 edges and the same topology hash. The weighted edge graph differs in all nine configurations. Twelve matching edges carry logical fault ID 0 for each model. The stored arrays contain detector bits, observable labels, and predicted logical flips, not physical correction chains; this analysis does not infer physical corrections.

Across 600,000 new shots, most tested pairs return the same predicted logical flip. The most distinct pair has under 1% disagreement in data-heavy noise; disagreement is lower in nominal and measurement-heavy noise. Full regime-stratified counts, candidate-only errors, baseline-only errors, error-indicator correlations, and syndrome signatures are in `DECODER_DISAGREEMENT.csv` and `SYNDROME_DISAGREEMENT_PATTERNS.json`.

## Regime specialization and uncertainty

| Regime | Calibration-selected model | Fresh-evaluation lowest point-rate model (retrospective rank only) | Fresh LER for calibrated model | Interpretation |
|---|---:|---:|---:|---|
| data-heavy | 1 | 3 | 1.4125% | Candidate 3 point estimate is lower, but its root-level comparison does not survive Holm correction. |
| nominal | 1 | 1 | 0.488% | Same model wins calibration and evaluation. |
| measurement-heavy | 1 | 2 | 0.1955% | Candidate 2 point estimate is lower, but does not survive Holm correction. |

Calibration margins are small: zero-based decoder-grid index 1 ties index 2 in measurement-heavy noise and differs by only 0.005 percentage points from the closest point-rate competitors in data-heavy and nominal conditions. Paired calibration intervals and all model ranks are recorded in `CALIBRATION_SELECTION_UNCERTAINTY.json`. Fresh-test root-level comparisons used 20 roots per regime and a 24-test Holm family; no candidate showed a multiplicity-adjusted, credible improvement over the global fixed baseline. Some alternatives were significantly worse.

## Oracle headroom

The calibration-selected global model and calibration-selected per-regime policy both made 4,192 errors. A hindsight per-regime oracle selected separately using test labels makes 4,079 errors, a descriptive 113-error or 0.0188% LER headroom. The per-shot best-of-nine logical-prediction oracle makes 2,975 errors, a 1217-error or 0.2028% headroom. These are unattainable diagnostics: they use the same evaluation labels to select and score the model and have no confirmatory interpretation.

## Answers and next experiment

1. **Are the decoders genuinely distinct?** Using zero-based grid indices 0–8, they have distinct weights and DEM hashes but one shared graph topology. Six different logical-output behaviors were observed on these samples; three groups contain exact duplicates in the tested data.
2. **Which performs best by regime?** Calibration chooses zero-based decoder-grid index 1 in every regime. Test-label point rankings favor index 3 in data-heavy, index 1 in nominal, and index 2 in measurement-heavy; the non-baseline rankings are exploratory and fail the predeclared multiplicity gate.
3. **Does regime-informed selection beat the global model?** No. It selects the same index in every regime and ties exactly.
4. **How much oracle headroom?** Zero for the deployable calibration-selected regime policy; positive only for test-label hindsight diagnostics.
5. **Is this bank ready for adaptive QEC?** Not for demonstrating gains under these three scalar depolarizing/noisy-measurement settings. Weight tuning changes few logical decisions, and calibrated utilities do not select a regime-specific model.
6. **Next experiment:** only after a separate protocol decision, use independently motivated hardware-calibrated Pauli bias or different syndrome-readout versus final-data-readout error rates. Freeze noise locations, candidate DEM construction, calibration roots, and held-out seeds before evaluation. Do not tune a controller on this Phase 2A test set.

All results are simulation-only. Noise is stationary within each generated five-round circuit; this study does not test within-circuit changes or physical correction chains.
