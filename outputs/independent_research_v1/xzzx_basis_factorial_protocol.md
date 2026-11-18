# XZZX versus CSS with both memory bases under X-biased noise

## Question

Does the native-XCX checkerboard XZZX result change when both CSS and XZZX are allowed to store either logical basis? The prior XZZX screen used only Z-memory; a fair configuration comparison should include X-aligned CSS and X-aligned XZZX.

## Fixed design

At d=5, rounds=9, gate and measurement p=.003, Pauli bias ratio 10:1, use four conditions: CSS-X, CSS-Z, native-XCX XZZX-X, and native-XCX XZZX-Z memory. Build XZZX by applying the same fixed checkerboard transform to the corresponding X or Z CSS source circuit. Each circuit has a separately constructed correlation-enabled PyMatching decoder from its own DEM using `decompose_errors=True` and `approximate_disjoint_errors=.0018`.

Use 10,000 shots/condition for preflight with seeds 2026114101–2026114104. Use 500,000 fresh development shots/condition with seeds 2026114111–2026114114. The primary comparison is XZZX-X versus CSS-X; same-basis Z comparison and each code's X-vs-Z memory contrast are secondary. Streams are independent, not paired.

## Gates and reporting

Before sampling require equal physical-qubit, detector, observable, two-qubit-interaction, one-qubit-noise-target, tick, and measurement-error-target counts across all conditions. Verify noiseless detector/observable determinism, source `PAULI_CHANNEL_2` probability vectors under the transform, successful DEM construction, and scalar/batch decoder agreement on 100 preflight samples per condition. Stop if projected main time exceeds 300 seconds or any gate fails.

Report failure counts, Wilson intervals, exact conditional independent-rate-ratio intervals, runtime, RSS if available, resource counts, and decoder disagreement only where sample-level paired outputs exist (none in this design). This is a bounded development code/memory configuration screen. It is not a threshold, arbitrary-state, hardware, or confirmatory result. The equal duration/noise assumption for native CX/XCX/CZ remains unverified.


## Execution record

All four preflight cells passed with 128 noiseless checks and 100 scalar/batch prediction comparisons each. Resource and two-qubit probability-vector checks passed; projected main runtime was 13.99s (<300s). The fixed 500,000-shot-per-cell screen completed in 17.89s. Results: `xzzx_basis_factorial_results.json`.
