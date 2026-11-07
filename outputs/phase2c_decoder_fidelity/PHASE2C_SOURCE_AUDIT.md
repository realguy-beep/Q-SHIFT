# Phase 2C Source Audit

Audited read-only from Phase 2B `noise_model.py`, `decoder_bank.py`, `PHASE2B_PROTOCOL.md`, `NOISE_MODEL_SPECIFICATION.md`, and `test_phase2b.py`. Their hashes are included in the Phase 2C pre-pilot freeze and final manifest.

## Pauli channel definitions and ordering

`one_qubit_probabilities` returns `(pX,pY,pZ)` in that order. At total gate probability 0.003 and 10:1:1 bias, X-biased gives `(0.0025, 0.00025, 0.00025)`, balanced gives `(0.001,0.001,0.001)`, and Z-biased gives `(0.00025,0.00025,0.0025)`.

`PAULI_PAIRS` is exactly `IX,IY,IZ,XI,XX,XY,XZ,YI,YX,YY,YZ,ZI,ZX,ZY,ZZ`, the Stim two-qubit custom-channel order. For a pair `AB`, the probability is proportional to the product of symbol weights, with `I=1`, dominant axis=10, other non-identity axes=1; normalization makes the 15 non-II probabilities sum to 0.003. A PAULI_CHANNEL_2 outcome is one categorical paired event; it is not two independent one-qubit draws. There is no cross-gate correlation in this model.

## Insertion locations and memory circuits

`build_circuit` obtains Stim's generated `surface_code:rotated_memory_z` or `_x`, distance 3 and five rounds, with a nonzero depolarizing placeholder so the generator emits its post-Clifford noise sites. It regex-replaces each `DEPOLARIZE1` and `DEPOLARIZE2` instruction in place with one custom categorical Pauli-channel instruction at the same targets. It does not inject gate noise at resets, idle periods, or measurements. The generated `before_measure_flip_probability=0.003` remains in place; Stim materializes basis-appropriate physical flips in the actual generated circuit (an anticommuting Pauli before each measurement). Phase 2B tests assert both bases retain 40 detectors and one observable, contain both custom channel instruction types, have no remaining depolarizing instructions, are noiselessly deterministic at zero noise, and respond to nonzero noise. `CIRCUIT_VALIDATION.json` records actual instruction and target counts for each basis/regime.

The circuit's generated `DETECTOR` and `OBSERVABLE_INCLUDE(0,...)` definitions are retained. The target is Stim's one-bit observable flip for observable id 0. Decoder outputs are the predicted observable correction bit; residual failure is `raw_observable XOR prediction`. The Phase 2B bank checks 40 input detectors, one output bit, and logical fault id `[0]` for all three candidates.

## DEM conversion and matching

`decoder_bank.build_bank` converts each noisy categorical circuit using `decompose_errors=True` and `approximate_disjoint_errors=True`, then constructs PyMatching with `enable_correlations=True`. This is an approximation. Stim DEMs describe independent error mechanisms, while `PAULI_CHANNEL_1`/`PAULI_CHANNEL_2` specify mutually exclusive categorical outcomes. Stim documents that conversion of these channels may require approximation as independent mechanisms; the flag does not preserve the original categorical distribution exactly. Decomposition supplies graphlike components for faults with multiple detection events; PyMatching can retain available decomposition correlations, but cannot reverse information already lost in the DEM conversion. In Phase 2B all three candidates use the same flags, so the bank is internally consistent but only approximate to the generating channel.

## Phase 2C reference target and caveat

The new reference trains on detector/observable pairs sampled by the original Stim circuit, so its training distribution includes the actual categorical channel probabilities rather than DEM-independent component approximations. It estimates the posterior from finite samples and a random forest. It does not enumerate full-circuit Pauli histories and therefore is not exact. See `REFERENCE_DECODER_DESIGN.md` and `REFERENCE_DECODER_VALIDATION.md`.

## Primary sources

- Stim documents the parameter order and behavior of `PAULI_CHANNEL_1`, `PAULI_CHANNEL_2`, and measurement-error channels in [Stim gate documentation](https://github.com/quantumlib/Stim/blob/main/doc/gates.md).
- Stim explains that DEM mechanisms are independent and that disjoint Pauli-channel outcomes require approximation in [Stim's `approximate_disjoint_errors` documentation](https://github.com/quantumlib/Stim/blob/main/doc/usage_command_line.md).
- PyMatching's DEM import and correlation option are documented in its [Matching API source](https://github.com/oscarhiggott/PyMatching/blob/master/src/pymatching/matching.py).
