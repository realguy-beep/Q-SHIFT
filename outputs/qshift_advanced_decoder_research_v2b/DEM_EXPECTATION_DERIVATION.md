# DEM and Exact Circuit Expectation Derivation

This report explains two distributions that must not be conflated:

1. the original Stim circuit's independent **categorical fault-location** distribution; and
2. the independent-error distribution represented by `detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)` and passed to matching.

## Circuit noise and location classes

The builder chain is `noise_model.build_circuit` → `build_spatial_burst_circuit` → `DetectorProfileEstimator` in `outputs/phase2b_pauli_bias/noise_model.py`, `outputs/phase3a_correlated_noise_preflight/simulator.py`, and `outputs/stage4_noise_adaptive_feasibility_v1/prototype.py`.

For the tested balanced model at gate p=.003, each `PAULI_CHANNEL_1` target has mutually exclusive X/Y/Z outcomes of probability .001 each and identity .997. Each `PAULI_CHANNEL_2` target pair has fifteen mutually exclusive non-II Pauli-pair outcomes of probability .0002 each and identity .997. There are 40 one-qubit channel targets, 120 two-qubit channel pairs, 49 independent measurement-flip targets, and five independent burst Bernoulli locations: **214 independent locations** and **1,974 nonidentity alternatives**. Each burst site is one Bernoulli location with identity probability `1−p_burst` and simultaneous XX probability `p_burst`.

The code forms a signature for each physical categorical alternative without sampling: preserve the ideal Clifford circuit, remove every stochastic location except one, set that one alternative to probability one, and convert that deterministic single-fault circuit to a detector error model with `decompose_errors=False`. For a selected `PAULI_CHANNEL_2` instruction, `approximate_disjoint_errors=True` is needed syntactically by Stim; only one alternative is nonzero and all other stochastic operations are removed, so there is no alternative competition in this single-fault conversion to approximate. Every signature is the resulting detector parity mask. The original Clifford circuit is linear in Pauli-frame effects, so combined independent faults XOR these masks. The signature process therefore recovers the circuit-level detector response to each individual categorical branch exactly for this model.

## Character identity

Let location l have identity probability `q_l0`, alternative outcomes a with probability `q_la`, and detector mask `v_la∈{0,1}^40`. For a subset A of detector indices, define the parity character

`χ_A = E[(-1)^(⊕_{i∈A} D_i)] = Π_l [q_l0 + Σ_a q_la (-1)^(|A∩v_la| mod 2)]`.

The product is exact because distinct locations are independent; alternatives within one location are summed as categorical, not multiplied as independent faults. Then

`E[D_i] = (1−χ_{i})/2`

and for an extracted pair `(i,j)`,

`E[D_i D_j] = (1−χ_i−χ_j+χ_{i⊕j})/4`.

These are expectations for the original circuit's categorical distribution, using its exact per-location probabilities and exact single-fault signatures. They do not rely on the DEM's disjoint-error approximation.

For covariance of arbitrary binary features `f_T=Π_{i∈T}D_i`, use

`E[f_T] = 2^(−|T|) Σ_{A⊆T} (−1)^|A| χ_A`.

Products of features reduce to the union of their detector-index sets because `D_i²=D_i`. This gives the exact 45×45 per-shot feature covariance used for the covariance-whitened Jacobian metric.

## Approximate DEM expectation

A detector error model represents a list of **independent** mechanisms, each with probability p_m and detector symptom mask w_m. For the emitted DEM itself, the same character identity is exact:

`χ_A^DEM = Π_m [1−p_m + p_m (−1)^(|A∩w_m| mod 2)]`.

When the circuit contains mutually exclusive Pauli-channel outcomes, Stim may approximate them as independent DEM errors if `approximate_disjoint_errors=True`. Applying the identity above therefore calculates exact expectations under that **approximated independent DEM**, not under the original categorical circuit. `decompose_errors=True` adds decompositions/separators for decoder use; for detector moments each error instruction's complete detector symptom set is counted as one event. No observable or logical label enters this calculation.

At `(p_burst=.008,p_measure=.003)`, the approximate DEM has 591 independent error instructions. Its 45 expected features differ from the exact categorical circuit means by maximum absolute `3.272×10⁻⁵` and RMS `2.136×10⁻⁵`. The five pair-cofire differences are each below `7.3×10⁻⁷` in magnitude. These small moment differences do not prove equality of the full syndrome distributions; the documented approximation is real and is retained in the report.

## Pair features and physical burst mapping

The extracted feature function is `40 raw detector bits + 5 conjunctions` in `prototype.py`; the pair order is `((8,10),(16,18),(24,26),(32,34),(36,38))`. The deterministic single-fault masks of the five `E` instructions are exactly those same pairs. Thus feature indices 40–44 are aligned with the five injected physical sites. The event does not merely toggle a pair-feature bit independently: other gate/measurement errors XOR into the same detector bits, so pair cofires are nonlinear moments of the full joint distribution.

## Approximation boundary

The full distribution over 40 detector bits is not enumerated (2^40 possible detector strings). This audit computes exact first and second moments required by the 45 features under the physical categorical model, and exact moments of the approximate independent DEM. It does not establish equality of all higher-order moments/distributions, logical-risk equivalence, or decoder optimality. Numerical agreement of feature means is not permission to label DEM outputs as exact circuit-level behavior.
