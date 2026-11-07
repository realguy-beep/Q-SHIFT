# Categorical factor graph

## Variables and factors

For each noisy circuit location `i`, define a categorical variable `F_i` with one state per mutually exclusive outcome. Its domain includes identity and has a unary prior `phi_i(F_i)=p_i(F_i)`. One-qubit locations have states `{I,X,Y,Z}`; two-qubit locations have `{II}` plus the 15 ordered nonidentity Pauli pairs; measurement-fault locations are binary.

Each outcome has a detector mask and logical-observable mask. For detector bit `j`, the parity constraint is

`D_j = XOR_i detector_mask(F_i)[j]`.

For observable bit `k`,

`L_k = XOR_i observable_mask(F_i)[k]`.

The joint distribution is the sum-product of all categorical priors and these parity indicators. Exact marginalization over fault states yields `P(D,L)`; conditioning on detector bits and selecting the maximum logical posterior gives the decoder decision.

## Effect-mask derivation

For toy circuits, the analytic repetition-code parity equations are checked against Stim one-hot channel outcomes for every complete toy configuration. For the surface-code fragments, effects are obtained by forcing exactly one nonidentity categorical Pauli outcome at its original gate location, removing other noise, and reading the deterministic detector/observable vector. Each result is checked to be identical across two forced sampler rows, and the noiseless circuit is checked to produce all-zero detector and observable vectors. This yields exact per-location Pauli effects without sampling a noisy evaluation batch.

The fragment extraction uses the frozen Phase 2B `noise_model.py`, with distance 3, Z-memory, X-biased probabilities (10:1:1 Pauli bias), gate total p=0.003 and measurement p=0.003. Reduced-round circuits are constructed by the same Stim generator and replacement rules; the five-round circuit calls the frozen builder directly. The 5-round source circuit hash and all outcome masks are saved in `FRAGMENT_R5.json`.

## Difference from a DEM graph

The categorical graph has one variable per channel location. Its outcomes at one location are mutually exclusive. Stim's `approximate_disjoint_errors=True` DEM may instead emit multiple independent `error(p)` mechanisms. DEM separators annotate suggested decomposition for matching; they are not a replacement for the categorical variable's full outcome table. The categorical factor graph therefore does not treat approximate-DEM edges as exact physical faults.

## Graph sizes

The saved fragment JSON files record fault-variable counts, domain sizes, output parity factor scopes, number of factor nodes/incidences, and the complete categorical configuration count. The direct parity graph is useful for symbolic min-fill/min-degree width estimates. For inference, the implementation instead exploits XOR structure and accumulates/combines the joint parity state.

