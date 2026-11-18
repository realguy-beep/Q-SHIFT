# Width-only preflight for two adjacent Phase 2B channel layers

## Frozen scope

Inspect the last two `PAULI_CHANNEL_2` instructions of the source d=3, five-round Z-memory/X-biased-10:1 circuit (the adjacent channel instructions in the final extraction round). Include all six independent target pairs in each instruction, for 12 mutually exclusive 16-state categorical variables total. All other noise remains identity in the model.

Use the corrected shared-noiseless-reference/raw-measurement mapping from the six-location screen. Derive local detector/logical signatures by deterministic Pauli forcing. Build only factor scopes and run weighted min-fill size estimation; do not allocate inference tables or compute posterior masses in this preflight. Because weighted min-fill exceeded the cap, also compare seven fixed alternative scope-only orderings (weighted min-product, unweighted min-fill, min-degree, natural, reverse, and two location/carry interleavings). This is an exploratory ordering audit, not a decoder-outcome search. Report all orderings' induced width and largest predicted factor entries. Cap at 1,000,000 entries.

This checks whether adding one adjacent noisy gate layer causes a sharp temporal-width increase or whether a simple ordering choice explains the growth. It is not an exact inference result or decoder benchmark. No stochastic Q-SHIFT circuit shots are generated. If every tested ordering fails the cap, stop dense exact inference on this two-layer factorization.
