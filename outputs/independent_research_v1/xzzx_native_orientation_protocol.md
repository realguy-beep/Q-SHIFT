# Complementary native-XCX XZZX orientation

## Hypothesis

The fixed native-XCX checkerboard orientation improved X-biased LER but hurt Z-biased LER. A single complementary checkerboard mark class may reverse the preference by swapping which data sublattice is locally conjugated. This tests whether the observed interaction is specifically an orientation/noise alignment effect.

## Fixed design

Under the same explicit assumption as `xzzx_native_xcx_protocol.md` (native CX/XCX/CZ equal duration and identical source PAULI_CHANNEL_2 error distribution), compare three variants: CSS; the already tested checkerboard with data-coordinate `(x+y) mod 4 = 2` marked; and exactly its complement `(x+y) mod 4 = 0` marked. Do not try any other pattern.

Use only Z-biased ratio-10 noise at p=.003, Z-memory, distances 3 and 5, rounds 5 and 9. Run 500,000 shots per variant/distance. The primary contrast is complementary XZZX versus CSS at each distance; the fixed original orientation is a secondary within-study reference. Report LER/Wilson intervals, exact conditional rate ratios, qubits/detectors/rounds, H and one-qubit noise targets, native CX/XCX/CZ counts, two-qubit interactions, decoder runtime, and source probability maps.

Condition order: d3 CSS/original/complement, then d5 CSS/original/complement. Preflight seeds 2026112801–2806; main seeds 2026112811–2816. The 100-shot/cell preflight must validate the local Clifford tableaux, noiseless detectors and observable, same physical pair probabilities/targets, matched qubits/detectors/rounds/two-qubit interaction count, no added H targets, deterministic DEM generation and scalar/batch decoder agreement. Stop before main if any check fails or if the projected 500k/cell runtime exceeds 300 seconds.

## Interpretation

This is a finite-size, simulator-specific orientation test, not a threshold or hardware claim. The XZZX-vs-CSS ratio uses independent circuit streams. The original-vs-complement contrast is descriptive. Native-gate noise equality remains an assumption; hardware use requires measured native gate costs and noise channels. No decoder tuning or pattern search is allowed.
