# Leave-one-memory-basis-out transfer

## Question

Can the shared relative-choice classifier trained on one logical memory basis transfer to the other basis across all three Pauli profiles?

## Frozen design

- Two folds: train on all three regimes for one memory basis and validate on all three regimes for the other basis, then reverse. Use 1M training shots/condition and 1M validation shots/condition. Every held-out condition is evaluated once. Each condition's matching graphs remain profile-matched.
- Train the pooled logistic model on flagged 40-detector-bit syndromes with target `correlated_wrong`; no memory-basis ID or profile ID is input. Apply the same selector policy, optimizer, and matcher disagreement flag.
- Preflight 10k/condition seeds 2026120101–0106. Z-basis held out: training on X conditions seeds 2026120111–0113. X-basis held out: training on Z conditions seeds 2026120121–0123. Validation seeds in condition order are 2026120131–0136.
- Compare against correlated matching and the previously trained all-profile relative/absolute and specialized models on identical held-out streams.
- Gate: >=10% macro reduction vs correlated matching, no condition harmed >5%, total inference <2x, and positive macro direction for each held-out memory basis.

## Stop rules

Verify d3 geometry/noiselessness, scalar/batch consistency, one observable, 40-bit features, both training labels per fold, and projected time <=300s. No confirmatory/sealed data or post-validation tuning.
