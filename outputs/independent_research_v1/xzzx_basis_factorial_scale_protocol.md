# Distance robustness of the CSS/XZZX basis-workload tradeoff

## Question

The d5 development factorial, independently replicated, found a lower XZZX rate for an equal-weight mix of separate X/Z memory tasks, while CSS-X was substantially better for known X memory. Determine whether this tradeoff persists at smaller and larger distances without fitting the basis weights to outcomes.

## Frozen design

Fresh d3 and d7 circuits, with rounds=2d-1, X-biased Pauli ratio 10:1, gate and measurement p=.003. Four cells at each distance: CSS-X, CSS-Z, native-XCX XZZX-X, native-XCX XZZX-Z. Equal-weight average of separate X- and Z-memory task rates is the primary endpoint at each distance. Basis-specific XZZX/CSS rate ratios are secondary. Use 10,000 preflight shots/cell at seeds 2026114301–2026114308 and 500,000 development shots/cell at seeds 2026114311–2026114318. Streams are independent.

Before samples, require identical qubits, detectors, observables, two-qubit interactions, one-qubit noise targets, ticks, and measurement-error target counts within each distance, plus the same `PAULI_CHANNEL_2` probability vectors. Require DEM construction, noiseless detector/observable checks, and scalar/batch decoder agreement. Stop if projected main time exceeds 300 seconds or a check fails.

Report counts, Wilson intervals, exact conditional independent-rate-ratio intervals, resources, and runtime. This is a finite-size simulator development extension, not a threshold, arbitrary-state, hardware, or confirmatory evaluation. Native CX/XCX/CZ duration and noise equality remains an explicit unverified assumption.
