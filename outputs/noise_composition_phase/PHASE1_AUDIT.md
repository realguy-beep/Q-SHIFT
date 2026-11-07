# Phase 1 — implementation audit

## Existing project and preserved finding

The original starter project remains at `C:\Users\LENOVO\Downloads\Q-SHIFT_v0.1_starter`. Its original CSV contains 150,000 rows, generated at three `after_clifford_depolarization` settings (0.001, 0.003, 0.006). The original circuit is Stim `repetition_code:memory`, distance 3, rounds 3, with 5 qubits, 8 detectors, and 1 observable. The observable is the final data-qubit parity flip (`L0`) relative to the ideal reference. The eight original `syndrome_0..7` fields are detector bits for that circuit.

The original circuit supports one noise mechanism: depolarization after Clifford gates (`DEPOLARIZE1`/`DEPOLARIZE2` according to Stim's generated-circuit convention). It does not model a selectable X/Z composition, explicit measurement flips, time-varying noise, or hardware telemetry. Later exploratory code in the prior output directory substituted X or Z faults and separately tried measurement flips, but those are not the original dataset's noise model.

## Decoder target and score audit

The proper decoder input is the detector vector. The decoder output is an estimate of the observable flip/correction. Simulation residual is `actual_observable XOR predicted_correction`; the actual observable label is an evaluation target only. The older classifier's use of `logical_error` as a label was acceptable for supervised simulation, but the label cannot be available to a live decoder. The prior research report's corrected ten-seed result did not demonstrate adaptive superiority; it remains preserved and is not replaced by this phase.

The new phase holds the ideal circuit skeleton and detector/observable annotations fixed. It inserts explicit local noise operations after the same CX locations and, when selected, before the same Z-basis measurement locations. Every compared decoder receives exactly the same detector shots for a test block. Noise-condition names and logical labels are withheld from all inference code.

## Probability convention

For X-, Z-, depolarizing-, and mixed-X/Z data conditions, `p_data` is the total probability of a non-identity single-qubit Pauli fault on each participant immediately after each CX location. Conditional composition is specified by probabilities `(pX,pY,pZ)` summing to `p_data`:

- X-dominant: `(0.8, 0.1, 0.1)`
- Z-dominant: `(0.1, 0.1, 0.8)`
- depolarizing: `(1/3, 1/3, 1/3)`
- mixed X/Z: `(0.5, 0, 0.5)`

For measurement noise, `p_meas` is the independent probability of an X measurement flip immediately before each Z-basis measurement. The study uses the same numeric nominal probability (0.01) per local channel invocation, not an equal total circuit fault count: data and measurement locations occur different numbers of times. The data-plus-measurement condition uses 0.01 for each source, so its total opportunity for faults is intentionally larger and is reported separately.

The X/Z/depolarizing comparison therefore holds the total single-qubit non-identity probability fixed at each inserted data location while changing composition. This is not the same channel as Stim's original two-qubit depolarizing model; it is a controlled composition experiment on the same ideal circuit skeleton.

## Known constraints before implementation

- This is a distance-3, three-round, eight-detector simulation; conclusions do not scale automatically to larger codes.
- The single logical observable is appropriate for the generated repetition-memory circuit, not a general logical-failure metric for arbitrary codes.
- Detector-only regime classification may be weak because the detector vector has only eight bits and adjacent detector patterns can be shared by different channels.
- An adaptive selector consumes prior windows and therefore has a nonzero detection delay. It cannot use the current block's hidden noise label or logical target.
- The phase uses a finite computational budget: 10 seeds, 30k training shots and 10k validation shots per trained composition, 20k static test shots per condition per seed, and 4k shots per time-varying block. This is sufficient for exploratory paired comparisons, not a final rare-event logical-error estimate.
- No hardware integration, telemetry, or device-level latency is available.
