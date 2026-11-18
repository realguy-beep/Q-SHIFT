# Exact sparse inference for two adjacent categorical circuit layers

## Question

Dense VE stopped on a 12-location, 16-state final-two-layer fragment because its largest projected table exceeded 17 billion entries. Test a distinct exact representation that aggregates probability by compact XOR syndrome/logical signatures rather than materializing VE factors.

## Fixed fragment and method

- Source: d3, five-round Z-memory, X-biased ratio10 Phase 2B circuit. Keep exactly the final two `PAULI_CHANNEL_2` instructions (six pairs each); set every other stochastic location to identity.
- Map all 12 pair locations and 16 mutually exclusive outcomes/location by forcing each Pauli outcome through Stim, always measured relative to one shared noiseless detector/observable reference.
- Run exact sparse dynamic programming over `(detector_mask, logical_mask)` states. Independently aggregate the first and second six-location halves, then convolve the two half-distributions. Compare every reachable joint mass. Verify 512 deterministic combined-fault assignments against Stim XOR composition.
- Preflight cap: at most 100,000 aggregate states and 10,000,000 state-transition/convolution operations; stop before exact mass expansion if exceeded. No dense VE table is allocated. Report source fault configuration count, reachable states/syndromes, operation count, max absolute error, normalization, isolated-fragment MAP risk, and runtime.

## Scope

This tests exact decoding of the isolated final two layers, not the full circuit. The result does not imply that sparse syndrome-state convolution will scale to all circuit locations; the full syndrome/logical state space may be exponentially larger. No stochastic samples are generated.
