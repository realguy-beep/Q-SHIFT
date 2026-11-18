# Sparse exact categorical inference preflight for five final layers

## Question

Extend the final temporal slice from four to five adjacent `PAULI_CHANNEL_2` instructions, giving 30 native 16-state fault locations. Determine whether its compact detector/logical signature state remains tractable under fixed sparse caps.

## Fixed procedure

- Use the same d3 five-round Z-memory/X-biased-ratio10 source and shared-reference forced Pauli mapping. Map the final five six-pair channel layers only.
- Preflight limits remain 1,000,000 joint detector/logical states and 100,000,000 sparse-DP transitions. If either fails, save the structural stop without expanding probabilities.
- If preflight passes, run sparse DP and Walsh-Hadamard XOR convolution, compare all state masses to 1e-12, check normalization, and verify 512 forced combined faults against Stim. No dense VE and no stochastic samples.
- This fragment remains a method-feasibility result, not a full-circuit decoder benchmark.
