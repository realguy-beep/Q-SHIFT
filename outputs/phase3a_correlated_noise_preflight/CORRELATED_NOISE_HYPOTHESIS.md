# Phase 3A Correlated-Noise Hypothesis

## Selected mechanism: spatial common-cause X bursts

The primary candidate is a stochastic event that applies simultaneous X errors to two neighboring data qubits at a syndrome-round boundary in a rotated Z-memory surface-code circuit. In the prototype these are data qubits 8 and 10 (Stim coordinates `(1, 3)` and `(3, 3)`), a nearest-neighbor pair on the data-qubit lattice. The same pair is used at five round boundaries. Each boundary event is Bernoulli with probability `p_burst`; events in different rounds are independent.

The motivating physical picture is a shared control or crosstalk event that perturbs more than one nearby qubit during one cycle. That is a plausible class of hardware imperfection, but the current model is a **synthetic stochastic proxy**: it has no device-specific coupling map, pulse model, coherent dynamics, leakage, or calibrated event rate. The 1% per-round rate in the preflight is a stress-test setting, not a physical estimate. No claim is made that this exact two-qubit burst occurs on the user's hardware.

The implementation starts from the frozen Phase 2B categorical-Pauli circuit and inserts Stim's `CORRELATED_ERROR` instruction (Stim canonicalizes this to `E`) immediately after each `MR` ancilla-measurement/reset instruction. Thus the event is explicitly a joint outcome at two distinct data locations, rather than two independently sampled single-qubit errors. The event is introduced after a syndrome round and can affect subsequent checks and the final observable. It does not alter the circuit's detector definitions: distance 3, five rounds, 40 detectors, one logical observable.

## Why this is the first mechanism to test

| Candidate | Motivation | Feasibility in this simulator | Interpretability | Decision |
|---|---|---|---|---|
| Spatial common-cause burst | Shared control/crosstalk can affect a nearby pair | Stim directly represents a joint Pauli event; pair compatibility can be checked before sampling | One cause, two specified data locations, known per-cycle probability | **Selected** |
| Temporally persistent Pauli error | Slow drift or quasi-static fields can persist across cycles | Requires a latent state or persistent fault process, not the independent per-location model already used | Must separate persistence from ordinary time-varying rates | Defer; add only after a defined hardware-motivated process and detector model are specified |
| Correlated measurement faults | Shared readout electronics can couple outcomes across checks/rounds | Can be represented with joint measurement-error mechanisms, but changes detector-history semantics and can create larger hyperedges | Strongly dependent on which checks share hardware/readout | Defer; needs a readout topology and explicit event definition |

The existing Phase 2B channel is categorical within each two-qubit gate, but its draws at distinct gate locations are independent. The proposed burst adds a cross-location cause and therefore tests a different assumption. It is spatially correlated; it does **not** model temporal persistence. Independent burst draws at successive rounds are a deliberate simplifying approximation.

## Empirical preflight observation

In a 2,048-shot isolated Stim fixture at `p=0.1`, both readouts flipped together in 201 shots (joint and both marginals 0.09814), with zero discordant pairs and sample correlation approximately 1. In the surface-code burst-only smoke check (`p_burst=0.02`, 256 shots), 25 shots had nonzero detectors and none flipped the logical observable. This confirms the intended joint event enters the circuit and can produce syndrome information; it is not evidence of decoding improvement.

## Limits of the hypothesis

This preflight makes no claim that a neural decoder should outperform matching. For the selected pair the burst's detector signature is graphlike and Stim/PyMatching can represent it as a matching edge. A burst-inclusive matching model may therefore be a strong informed reference. Other data-qubit pairs generated higher-order detector signatures; 9 of 36 pairs failed Stim's graphlike decomposition. Those mechanisms must not be silently approximated or included in a PyMatching comparison without a valid, matched representation. Phase 3B should use only a predeclared graph-compatible physical pair and report the DEM approximation inherited from the categorical two-qubit channels.

The initial question is narrow: does adding a known cross-location burst mechanism change the errors that the frozen matching model sees, and does a correctly parameterized burst-inclusive matching DEM improve the correction of paired detector samples? The neural arm tests whether a detector-only residual CNN can learn useful corrections under the same samples. Even a positive small pilot would support only a follow-up study under this synthetic noise model, not a hardware claim or an adaptive-decoding claim.
