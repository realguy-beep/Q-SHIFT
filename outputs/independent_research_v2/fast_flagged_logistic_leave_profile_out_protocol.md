# Leave-one-regime-out transfer for the relative-choice selector

## Question

Can one shared relative-choice model trained on two of the three Pauli profiles select between correlated and ordinary matching on a third profile whose training labels were excluded?

## Frozen design

- Three folds, holding out one entire regime (X-biased, balanced, or Z-biased) at a time. Train on the other two regimes across both memory bases: four 1M-shot training streams/fold. Validate on the held-out regime's X- and Z-memory cells: 1M shots/cell. Each of the six held-out cells is evaluated once; fold training streams use distinct seeds.
- Fit one pooled L2 logistic model per fold on flagged 40-bit detector vectors. Label `correlated_wrong`; at inference choose ordinary output only when predicted true. The flagged set and correlated/ordinary matchers use the held-out profile's own nominal graph, so the experiment isolates selector transfer, not decoder graph mismatch.
- Preflight 10k/condition, seeds 2026118941–8946. Fold training seeds: X-biased holdout 2026118901–8904; balanced holdout 2026118911–8914; Z-biased holdout 2026118921–8924. Held-out validation seeds by condition order (Z-memory X-biased, Z-memory balanced, Z-memory Z-biased, then X-memory X-biased, balanced, Z-biased): 2026118931–8936.
- Fixed gate: >=10% equal-cell macro LER improvement vs correlated matching, no cell harmed >5%, total inference <2x; additionally require positive macro improvement in each held-out regime fold. Compare with prior all-profile shared relative-choice and per-condition models on the same held-out streams as context only.

## Stop rules

Check d3 geometry/noiselessness, scalar/batch consistency, one observable, 40 features, both pooled training labels per fold, and projected total runtime <=300s. No confirmatory/sealed data; do not tune after held-out outcomes.
