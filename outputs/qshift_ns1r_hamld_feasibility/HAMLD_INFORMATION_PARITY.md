# Information parity and fair future comparison

## Three different model objects

1. **Original categorical Stim circuit.** Each `PAULI_CHANNEL_2` location selects one mutually exclusive two-qubit Pauli outcome; the five added burst events are separate per-round correlated X-pair mechanisms. This is the circuit distribution to which future synthetic shots would belong, but no such shots were generated here.
2. **HAMLD input candidate.** The tested `decompose_errors=False, approximate_disjoint_errors=True` Stim DEM retains high-order detector hyperedges and the error probabilities. The exact pinned HAMLD parser preserves each tested event/weight. The DEM conversion still approximates the disjoint categorical gate alternatives, so it is not the exact circuit law.
3. **PyMatching input.** Existing Q-SHIFT builds with `decompose_errors=True, approximate_disjoint_errors=True`; graph construction and decode correlation flags are separately configurable. Decomposition introduces `^` components and presents correlated/decomposed graphlike structure to PyMatching. Its representation is not the same event list supplied to HAMLD.

Thus a future LER difference between HAMLD and PyMatching could reflect (a) inference objective, (b) Stim DEM decomposition/approximation, or (c) both. The parser round-trip does not establish equivalence between the two DEMs or equality to the original circuit distribution.

## Fair comparison proposal after the build gate

- Generate all candidate models from the same frozen original Stim circuit builder, gate/measurement/burst settings and parameter profile. If profile choice is detector-calibrated, use the same detector-only selection data and tuning budget. Do not supply true hidden burst probability to one deployable arm only.
- Primary native-input comparison: HAMLD on the validated undecomposed DEM versus PyMatching on the established decomposed DEM, with both transformations, flags, mechanism counts and approximation details reported. Label this **algorithm-plus-representation comparison**.
- PyMatching ablation: hold the decomposed DEM and weights fixed; compare ordinary mode with correlation mode, setting `enable_correlations=True` at both graph construction and decode for the correlation arm. This isolates the PyMatching correlation option subject to its supported decomposition semantics.
- Add a model-representation control before interpreting a HAMLD advantage: compare detector/event/logical behavior of the two DEM forms on exhaustive small toy models and deterministic targeted mechanisms; separately verify the categorical-to-DEM approximation. Do not count a parser-preserving event map as proof the probability distributions are equivalent.
- Pair all eventual evaluation detectors and observable labels across decoder arms; keep selection roots disjoint from evaluation roots; use independent roots as the inference clusters. Keep any true-parameter arm privileged and separate.

No study authorization or performance claim follows from this proposed design.
