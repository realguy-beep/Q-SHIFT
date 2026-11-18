# Native-XCX checkerboard XZZX code/circuit screen

## Hypothesis

The prior checkerboard local-H XZZX transform lost under the explicit H-CX-H compilation because it added 150–167% one-qubit noise targets. Stim exposes the exact Clifford conjugate `XCX = H_control CX H_control` directly. Replacing marked-control CX interactions with native `XCX` and marked-target interactions with `CZ` may retain the code transform without added one-qubit H targets.

## Hardware/noise assumption and fairness

This is a conditional development screen, not a hardware claim. Assume the platform natively supports CX, XCX, and CZ, each with equal two-qubit duration and the same source PAULI_CHANNEL_2 distribution immediately after the gate. All three consume one two-qubit interaction slot. Existing one-qubit, measurement, reset, and idle noise probabilities remain the source lab-frame probabilities; the transform adds no physical one-qubit gate. If that native gate/noise assumption is unavailable, no performance conclusion transfers to hardware.

Use the same fixed checkerboard marked-data pattern as `xzzx_codesign.py`, and its exact local-Clifford conjugation of resets, measurements, single-qubit Clifford gates, and explicit Pauli/measurement errors. For each source CX: marked control only -> XCX; marked target only -> CZ; neither -> CX; both marked -> reversed CX. Keep the source PAULI_CHANNEL_2 instructions at the same circuit positions and on the same pairs. No pattern, distance, decoder-threshold, or schedule search.

## Fixed experiment

Compare CSS and native-gate XZZX on the same abstract Z-memory task at d=3/5, rounds 5/9, physical p=.003, X- and Z-biased ratio10 noise. Build correlation-enabled PyMatching independently from each circuit's DEM using `approximate_disjoint_errors=.0018`; no graph is shared across codes. Run 500,000 Stim circuit shots per cell (8 cells). Report LER and Wilson 95% intervals, exact conditional rate ratios, sample/decode runtime, qubits/detectors/rounds, two-qubit pair count and gate counts by type. These are finite-distance engineering comparisons, not thresholds or arbitrary-state memory performance.

Use preflight seeds 2026112701–2708 and main seeds 2026112711–2718, in condition order d3 X-bias CSS/XZZX, d3 Z-bias CSS/XZZX, d5 X-bias CSS/XZZX, d5 Z-bias CSS/XZZX. The 100-shot-per-cell preflight must verify deterministic noiseless detectors/observables, exact Clifford equivalence for each CX conjugation, successful DEM construction, source circuit reproduction, equal qubits/detectors/observables/rounds/two-qubit pairs/TICKs, unchanged PAULI_CHANNEL_2 targets and probabilities, no added H gates, and decode-batch/scalar agreement. Stop without main sampling if any check fails or the main runtime projection exceeds 300 seconds. Preflight outcomes are excluded from the main comparison.

## Interpretation gate

The native gate/noise assumption is part of the result. Report every cell and retain the CSS baseline as primary. Do not tune the decoder threshold or pattern from these samples. A favorable result advances only a hardware-specific follow-up with measured native XCX/CZ error rates and durations; it is not a general XZZX advantage claim.
