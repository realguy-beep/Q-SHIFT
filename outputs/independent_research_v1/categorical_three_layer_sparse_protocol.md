# Exact sparse and Walsh-XOR inference for three categorical circuit layers

## Question

Two-layer sparse XOR convolution exactly solved a 12-location fragment that exceeded the dense-VE cap. Test the next adjacent temporal slice to see whether exact aggregation by detector/logical signatures extends further.

## Fixed fragment and method

- Source: d3, five-round Z-memory, X-biased ratio10 Phase 2B circuit. Select exactly the final three `PAULI_CHANNEL_2` instructions (six pairs each), with every other stochastic location set to identity.
- Preflight maps each mutually exclusive Pauli outcome through forced Stim circuits relative to one shared noiseless baseline. It records touched detector IDs, probabilities, and compact `(detector,logical)` signatures; no stochastic shots or posterior arrays are created in preflight.
- Proceed only if all three layers have six pairs, joint signature states `2^(touched_detectors+1)` are <=1,000,000, and conservative sparse-DP transitions are <=100,000,000.
- Main performs exact sparse DP across all 18 categorical locations and an independent XOR convolution using Walsh-Hadamard transforms over the finite binary signature group. Compare every state mass, check normalization/nonnegative mass within floating-point tolerance, and verify 512 forced combined-fault assignments against Stim.
- Report state/operation counts and runtime. Do not allocate dense VE factors. Stop on any cap or exact-check failure.

## Scope

This is an exact posterior for an 18-location final-three-layer slice only; all other circuit faults remain identity. It does not demonstrate full-circuit decoder feasibility or practical LER.
