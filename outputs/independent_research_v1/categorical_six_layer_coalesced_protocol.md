# Exact coalesced-kernel inference for six final layers

## Rationale

The six-layer raw-outcome vector preflight narrowly exceeded its 300M update cap. At a location, different Pauli outcomes can induce the same compact `(detector_mask, logical_mask)` signature. Their mutually exclusive probabilities can be summed exactly before convolution. This preserves the target distribution while reducing the number of state updates.

## Fixed procedure and caps

- Reuse the forced-signature map for the final six channel layers (36 locations, 18 detectors) in the d3 five-round Z-memory/X-biased-ratio10 source.
- Coalesce outcomes only when both detector and logical signatures are identical; sum their original categorical probabilities. No other approximation or pruning is allowed.
- Proceed only if joint states <=1,000,000, coalesced vector updates <=300,000,000, Walsh work <=400,000,000, and memory estimate <=1 GiB.
- Compare vectorized XOR-kernel DP against Walsh-Hadamard convolution over every state, require mass error and normalization error <=1e-12, nonnegative mass within tolerance, and 512 forced combined-fault checks against Stim.
- No dense VE and no stochastic samples. If any cap/check fails, stop.
