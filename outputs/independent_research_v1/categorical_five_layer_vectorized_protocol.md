# Vectorized exact signature convolution for five final layers

## Rationale

The fixed sparse-dictionary preflight stopped at 251.7M Python-level state transitions. A separate exact algorithm can use dense NumPy arrays over compact signatures, applying each 16-outcome XOR kernel as vectorized permutation-and-accumulate updates; this avoids Python dictionary work and remains bounded by the 524,288-state signature space. This is a new method/protocol with its own declared caps, not a change to the stopped sparse-DP run.

## Fixed caps and validation

- Reuse only the forced-outcome signature map for the final five channel layers (30 native categorical locations, 18 touched detectors); verify its stored signature hash and inspect its structural preflight.
- Proceed only if joint states <=1,000,000, vectorized DP work <=300,000,000 element updates, Walsh-Hadamard work <=400,000,000 operations, and peak memory estimate <=1 GiB.
- Compute the exact full state distribution independently with vectorized XOR-kernel DP and Walsh-Hadamard convolution. Require maximum absolute mass difference <=1e-12, normalization error <=1e-12, and no mass below -1e-12.
- Verify 512 forced combined-fault assignments against Stim using the stored outcome signatures and shared noiseless reference.
- Report work, memory, runtime, and isolated-fragment logical MAP risk. No dense VE and no stochastic samples. Stop if any cap/check fails.

## Scope

This remains an exact isolated-fragment posterior. It does not include other stochastic circuit locations and is not a full-circuit LER or decoder feasibility result.
