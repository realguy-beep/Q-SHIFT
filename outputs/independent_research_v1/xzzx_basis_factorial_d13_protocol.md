# d13 feasibility and bounded challenge of the balanced-memory trend

## Purpose

The equal-weight separate-memory XZZX/CSS point ratio decreased from .279 at d7 to .107 at d9 and .0448 at d11, but the d11 run took 282 seconds. This protocol tests whether the same fixed 2x2 circuit screen can fit the 300-second runtime cap at d13; it is also a challenge of the workload trend if the preflight passes.

## Fixed design

Distance 13, rounds 25, X-biased ratio 10:1, gate and measurement probabilities .003; CSS-X, CSS-Z, native-XCX XZZX-X, native-XCX XZZX-Z. Primary endpoint: equal-weight average over separate X/Z memory task LER. Secondary endpoints: basis-specific XZZX/CSS ratios. Preflight: 10,000 shots/cell, seeds 2026114701–2026114704. If the projected 500,000-shot-per-cell main run is <=300 seconds and all resource/noiseless/decoder checks pass, use seeds 2026114711–2026114714 for 500,000 shots/cell. Otherwise stop without main sampling.

Require equal qubits, detectors, observables, two-qubit interactions, one-qubit noise targets, ticks, and measurement targets across all four cells, and identical `PAULI_CHANNEL_2` probability vectors. Record max RSS. This remains development-only, finite-size simulation; native CX/XCX/CZ duration/noise equivalence is unverified, and separate basis-memory rates are not arbitrary-state performance.


## Execution record

The first preflight completed all cells but hit a JSON output variable typo after sampling; the failed record is preserved in `xzzx_basis_factorial_d13_preflight_failed_attempt.json`. The typo was fixed and the identical seeds were replayed. All gates passed, but the projected 500k/cell run was 454.7s, above the 300s cap. The declared stop rule applied: no d13 main samples were generated. Count the 40k unique preflight samples once.
