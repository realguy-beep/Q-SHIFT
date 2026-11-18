# Six-layer sparse-signature resource preflight

## Question

The vectorized/Walsh exact method passed five final layers. Measure compact detector support for the final six channel layers and test against the already fixed vectorized limits before expanding any probabilities.

## Fixed caps

- Use the same d3 five-round Z-memory/X-biased-ratio10 source and shared-reference forced Pauli signatures for the final six `PAULI_CHANNEL_2` layers (36 locations).
- Proceed only if joint signature states <=1,000,000, vectorized state updates <=300,000,000, Walsh operations <=400,000,000, and estimated memory <=1 GiB. If any cap fails, stop before mass expansion.
- No stochastic samples and no dense VE table. This is a structural preflight only.
