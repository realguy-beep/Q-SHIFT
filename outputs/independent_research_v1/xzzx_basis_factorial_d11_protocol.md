# d11 challenge of the XZZX/CSS memory-basis tradeoff

## Purpose

Challenge the d3/d5/d7/d9 development trend for an equal-weight mixture of separate X/Z memory tasks at the next distance. The trend is finite-size and model-specific; this test does not assume that the d9 result extrapolates.

## Fixed design

Distance 11, rounds 21, X-biased Pauli ratio 10:1, gate and measurement probabilities .003. Four conditions: CSS-X, CSS-Z, native-XCX XZZX-X, native-XCX XZZX-Z. The primary endpoint is the equal-weight average of the separate X/Z memory failure rates; basis-specific rate ratios are secondary. Use 10,000 preflight shots/condition (seeds 2026114601–2026114604) and 500,000 development shots/condition (seeds 2026114611–2026114614). Streams are independent.

Before the main run, require equal qubits, detectors, observables, two-qubit interactions, one-qubit noise targets, ticks, measurement targets, and `PAULI_CHANNEL_2` probability vectors across all four cells. Require successful DEM construction, noiseless detector/observable checks, and scalar/batch agreement. Stop if projected main runtime exceeds 300 seconds. Report counts, Wilson intervals, conditional independent-rate-ratio intervals, runtime, max RSS, and resources, including zero-failure boundaries.

Native CX/XCX/CZ equal duration and noise is unverified. Separate basis-memory rates do not constitute arbitrary-state performance. Development-only; no confirmatory or sealed data.
