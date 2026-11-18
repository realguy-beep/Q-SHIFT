# Native-categorical Phase 2B circuit-fragment mapping

## Question

Can exact detector/observable effects for real native categorical Pauli locations in the d=3 repeated-memory circuit be mapped into the validated variable-elimination representation, and what exact inference width does a small same-layer fragment require?

## Frozen bounded fragment

- Read the published source d=3, five-round Z-memory circuit for the X-biased ratio-10 profile. Do not edit its builder or historical files.
- Select the last `PAULI_CHANNEL_2` instruction in the final extraction round and its first three independent target pairs. An initial first-layer attempt used Stim's detector-sampler output, which is relative to each deterministic circuit's own reference and therefore erased forced-fault differences. That artifact is preserved as an invalid implementation pass; it is not evidence about first-layer effects. Each final-layer pair is one 16-state mutually exclusive location with the source channel probabilities (identity plus 15 Pauli pairs). All other stochastic instructions and other target pairs are set to identity for the fragment model.
- Obtain every location/outcome detector and observable effect by replacing all noise with identity and forcing one Pauli pair at a time at the original instruction position. Compare to the same noiseless circuit baseline. Compact to the detector bits touched by the three selected locations.
- Cross-check combined deterministic faults against XOR composition, enumerate all 16^3 categorical assignments for exact joint syndrome/logical masses, and compare variable-elimination results on every reachable syndrome/logical target. Preserve the categorical prior exactly.
- Limit each VE intermediate factor to 1,000,000 entries. No stochastic Q-SHIFT shots are generated; this is a deterministic circuit-structure screen.

## Scope and stop rule

This final-layer three-location fragment is a local exactness and width check, not a decoder benchmark or full-circuit model. Stop if no detector/observable effect is observed, forced Stim effects disagree with XOR composition, exact enumeration and VE joint masses differ by more than 1e-10, source resource/detector counts change, or the factor cap is exceeded. Do not expand the fragment based on apparent success without a separately saved width preflight.
