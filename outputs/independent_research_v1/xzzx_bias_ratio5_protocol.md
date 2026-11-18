# d7 XZZX/CSS workload robustness at 5:1 X bias

## Question

The d7 equal-weight separate X/Z memory screen favored XZZX at 10:1 bias. Does that balanced-workload advantage persist at the already studied, less extreme 5:1 X-bias ratio?

## Fixed design

Distance 7, rounds 13, gate and measurement probabilities .003, X-bias ratio 5:1. Four cells: CSS-X, CSS-Z, native-XCX XZZX-X, native-XCX XZZX-Z. Equal-weight average of separate memory task rates is primary; basis-specific ratios are secondary. Use 10,000 preflight shots/cell at seeds 2026114801–2026114804, then 500,000 independent development shots/cell at seeds 2026114811–2026114814.

Require equal qubits, detectors, observables, two-qubit interactions, one-qubit noise targets, ticks, measurement-error targets, and `PAULI_CHANNEL_2` probability vectors across the four cells. Require DEM/noiseless/scalar-batch checks and projected runtime <=300 seconds. Report counts, Wilson intervals, exact conditional independent-rate-ratio intervals, runtime, and peak RSS. The streams are independent.

This is a bounded robustness development screen, not hardware-calibrated or confirmatory. Native CX/XCX/CZ error and duration equality is assumed but unverified; separate memory tests are not arbitrary-state performance.
