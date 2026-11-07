# Q-SHIFT Phase 2C Protocol — Decoder Fidelity Feasibility Pilot

## Question and status

This exploratory feasibility pilot asks whether replacing the Phase 2B Stim detector-error-model (DEM) approximation with a decoder trained to estimate the logical-observable posterior from samples of the actual categorical Pauli circuit changes predictions or logical error rates. It is not a confirmatory study and does not reuse Phase 2B held-out labels for model selection. Phase 2A and 2B are immutable historical evidence.

## Fixed circuit and noise

Use the exact Phase 2B model: Stim rotated surface-code Z- and X-memory circuits, distance 3, five rounds, 40 detectors, one observable, total per-location 1Q and 2Q fault probability 0.003, measurement flip probability 0.003, and the X-biased, balanced, and Z-biased categorical channels at a 10:1:1 ratio. Gate locations, generated detector/observable definitions, channel probabilities/order, and measurement-noise instructions are unchanged. The Phase 2B implementation is imported read-only and its source hashes are recorded.

## Reference decoder and partitions

For each of the six memory-basis × generating-regime cells, draw 60,000 independent development shots and fit a 128-tree RandomForestClassifier to the 40 detector bits and single observable bit. Model probabilities are interpreted as an approximation to `P(observable=1 | detectors)`; inference receives detector bits only. A fixed threshold of 0.5 returns the MAP observable correction, with ties assigned 0. Training class weights are disabled so the forest is not intentionally given an altered class prior. This is a sample-trained posterior surrogate, not an exact likelihood decoder.

Use separate 10,000-shot calibration samples per cell. Among the three reference forests for a basis, select a global fixed forest minimizing the equally weighted mean calibration LER across the three generating regimes. Independently select a regime-specific forest per calibration cell. Exact ties select the lower candidate index in frozen order X-biased, balanced, Z-biased. This regime-informed diagnostic uses the known simulated condition only to choose among candidates; it is not deployable adaptation. No pilot test label is used for fit, calibration, model selection, or threshold selection.

For each of six cells, evaluate four independent pilot roots of 5,000 paired shots (120,000 total). Each root's same detector and observable arrays are decoded by all three Phase 2B matching models and all three reference forests. The Phase 2B comparators include regime-matched DEM decoding and balanced fixed DEM decoding; the reference comparators include all candidates, calibration-selected fixed reference, and calibration-selected regime-informed reference.

## Endpoints and analysis

Report residual LER, Wilson 95% interval, paired disagreements, exact two-sided McNemar test for shot-level discordances, Brier score, log loss and expected calibration error for reference posterior probabilities, training/inference time, model file size, and process working-set measurements. The primary feasibility contrast is regime-informed reference minus fixed reference on paired pilot shots, equally weighted over six cells; also report reference-versus-regime-matched Phase 2B comparisons. Bootstrap roots within each cell for 20,000 draws and use a paired root-cluster sign-flip test with 50,000 Monte Carlo assignments. Pilot findings are descriptive; multiplicity and low root count preclude confirmatory claims.

Posterior-estimation quality is summarized by proper scores and calibration error on held-out pilot outcomes, not by claiming the unknown full-circuit posterior itself is known. Exact enumeration is restricted to finite toy cases where all categorical outcomes can be enumerated.

## Seeds and freeze

Diagnostic seeds: 89000001–89000006; development: 89010001–89010006; calibration: 89020001–89020006; pilot seed `89200001 + 100*cell_index + root_index` for six cells in listed order and four roots per cell; bootstrap 89300001; sign-flip 89300002. A collision audit scans recoverable prior manifests, text records and NPZ seed fields before any Phase 2C sampling. Protocol, source, config, imported Phase 2B code, circuits/DEMs, development/calibration arrays, fitted models, and selection record are frozen before pilot sampling.

## Stop and interpretation rules

Stop if source/config/circuit validation, detector shape, noiseless behavior, seed screening, exact-toy tests, calibration separation, DEM reconstruction, or the pre-pilot hash check fails. Do not tune model parameters, candidate selection, or thresholds from pilot results. This phase ends after feasibility reporting; no adaptive selector or larger held-out study is run.
