# Sparse exact categorical inference preflight for four final layers

## Question

Test the resource boundary after the exact three-layer pass. Map the final four `PAULI_CHANNEL_2` instructions (24 native categorical locations) in the same d3 Phase 2B circuit and estimate sparse signature-state work before any mass calculation.

## Fixed procedure

- Use the same source, shared noiseless reference, and forced Pauli outcome mapping as the three-layer screen. Record all touched detector IDs and 16 outcomes/location.
- Preflight allows at most 1,000,000 joint detector/logical states and 100,000,000 sparse-DP transitions. If either conservative bound fails, record the stop and do not expand probabilities.
- If it passes, independently compute exact sparse DP and Walsh-Hadamard convolution; require all joint masses to agree within 1e-12, total mass within 1e-12 of one, and 512 combined-fault checks to match Stim XOR composition. No dense VE table and no stochastic shots.
- The result remains an isolated final-layer fragment, not a full-circuit posterior.
