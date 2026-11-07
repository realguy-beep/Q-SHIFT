# Categorical fault model specification

## Scope

This prototype asks whether an exact posterior decoder can be constructed for small circuits whose noise is expressed as mutually exclusive categorical Pauli outcomes. It is a deterministic feasibility study. It does not replace any Phase 2B noise model or evaluate newly sampled Phase 2B shots.

## Model

Each noisy location `i` has a finite outcome set `O_i`, exactly one of which occurs. One outcome is explicitly identified as identity. Every outcome stores a label, probability, detector-flip bit mask, and logical-observable-flip bit mask. Validation requires one identity outcome with zero masks, unique labels, masks within the declared dimensions, probabilities in `[0,1]`, and per-location probabilities summing to one within `1e-12`.

Locations are independent in these toy models; outcomes within a location are mutually exclusive. A complete configuration selects exactly one outcome from every location. Its probability is the product of the selected location probabilities. Its syndrome and observable are the bitwise XORs of the selected masks. Therefore

`P(s,l) = sum_{configurations mapping to (s,l)} product_i p_i(outcome_i)`.

For each syndrome, the reference predicts the logical-observable bit with maximum joint mass (equivalently maximum posterior mass). Floating-point values within `1e-15` of the maximum are treated as tied; ties select the smallest observable bit pattern (bit 0 for the binary toys). The exact decoding risk is the sum, over syndromes, of the posterior mass not assigned to the chosen logical value.

## Toy circuits

Both toys use three qubits initialized in `|000>`, parity measurements `MZZ(0,1)` and `MZZ(1,2)` with detectors on their outcomes, then final Z-basis measurements. `L0` is the parity of the three final measurement bits. In this convention X and Y flip a computational-basis measurement bit; Z does not. Thus `D0=x0 XOR x1`, `D1=x1 XOR x2`, and `L0=x0 XOR x1 XOR x2`.

The one-qubit toy has one `PAULI_CHANNEL_1` categorical location on each qubit with `(I,X,Y,Z)=(0.94,0.02,0.01,0.03)`. This gives `4^3=64` complete configurations.

The two-qubit toy has two adjacent `PAULI_CHANNEL_2` locations, on qubit pairs `(0,1)` and `(1,2)`. It uses Stim's 15 non-identity pair ordering `IX,IY,IZ,XI,XX,XY,XZ,YI,YX,YY,YZ,ZI,ZX,ZY,ZZ`; their probabilities are `0.12 * rank / 120` for ranks 1 through 15, with identity `II=0.88`. This is a deliberately asymmetric categorical distribution for a small comparison, not a fitted device model. It gives `16^2=256` configurations.

