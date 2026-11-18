# d9 challenge of the XZZX/CSS basis-workload tradeoff

## Purpose

At d3/d5/d7, the equal-weight rate over separate X/Z memory tasks shifted from CSS at d3 to XZZX at d5/d7, while CSS-X remained much stronger for known X memory. Test whether the balanced-task advantage persists at d9, where a CSS basis-alignment stream already exists. This is a bounded finite-size development challenge, not a threshold fit.

## Fixed design

Distance 9, rounds 17, X-biased ratio 10:1, gate and measurement probabilities .003. Four conditions: CSS-X, CSS-Z, native-XCX XZZX-X, native-XCX XZZX-Z. Equal-weight separate-memory average is the primary endpoint. Basis-specific XZZX/CSS ratios are secondary. Use 10,000 preflight shots per condition (seeds 2026114501–2026114504), then 500,000 development shots per condition (seeds 2026114511–2026114514). Streams are independent.

Require equal counts of qubits, detectors, observables, two-qubit interactions, one-qubit noise targets, ticks, and measurement targets; equal `PAULI_CHANNEL_2` probability vectors; successful DEM construction; noiseless detector/observable checks; and scalar/batch decoder agreement. Stop if projected main runtime exceeds 300 seconds. Report failure counts, Wilson intervals, conditional independent-rate-ratio intervals including zero-count boundaries, latency, max RSS, and resources.

The native CX/XCX/CZ equality of duration and noise remains an unverified hardware assumption. Separate X/Z memory-task rates do not measure an arbitrary-state logical channel. No sealed or confirmatory evaluation data are accessed.
