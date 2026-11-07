# Phase 2B Noise Model Specification

## Circuit-level location

For each memory basis, start from Stim's generated `surface_code:rotated_memory_z` or `_x` circuit at distance 3 and five rounds. This fixes the same stabilizer circuit and detector/observable definitions within a basis. Replace every generated post-Clifford `DEPOLARIZE1` operation with one `PAULI_CHANNEL_1` at the same qubit targets, and every post-two-qubit-Clifford `DEPOLARIZE2` with one `PAULI_CHANNEL_2` at the same ordered qubit pairs. Do not insert noise at reset, idle, or measurement locations other than the generated basis-appropriate measurement flips. The latter remain at probability 0.003 in every model.

Each one-qubit instruction has total non-identity probability 0.003. X-biased assigns `(pX,pY,pZ)=(0.0025,0.00025,0.00025)`; balanced assigns `(0.001,0.001,0.001)`; Z-biased assigns `(0.00025,0.00025,0.0025)`. Thus the compared regimes have equal total one-qubit fault probability, while Pauli composition changes.

Each two-qubit instruction also has total non-II probability 0.003. Stim's fifteen `PAULI_CHANNEL_2` arguments follow the order IX, IY, IZ, XI, XX, XY, XZ, YI, YX, YY, YZ, ZI, ZX, ZY, ZZ. For pair `AB`, assign probability `0.003 * w(A) * w(B) / Z`, where `w(I)=1`, and the axis weights are `(10,1,1)` for X/Y/Z in X-biased noise, `(1,1,1)` in balanced noise, and `(1,1,10)` in Z-biased noise. `Z` is the sum of these fifteen weights, so the channel probabilities sum to 0.003 exactly up to floating-point rounding. The two positions in a sampled Pauli pair are correlated as one categorical gate-fault event; no correlations between separate gate locations are introduced. `DECODER_BANK_AUDIT.json` records every probability and each qubit's marginal Pauli mass.

Measurement noise uses Stim's generated pre-measurement flip instructions at `p=0.003`. The generated circuit applies the appropriate physical Pauli before each measurement basis; the final audit inspects actual instructions in both memory circuits. Data-plus-measurement noise is held fixed while only the gate Pauli composition changes.

## Decoder approximation

The simulator samples the requested mutually exclusive Pauli channels. Stim's detector error model requires independent error mechanisms and therefore requires `approximate_disjoint_errors=True` for custom Pauli channels. We use Stim's `decompose_errors=True` and its explicit disjoint-channel approximation, then load the resulting graphlike DEM into PyMatching with correlated matching enabled. This preserves available decomposition correlations (including suggested decomposition of multi-detector faults), but it does not make the DEM an exact representation of the categorical circuit channels. The decoder is therefore a documented approximate model of the simulated channel. All three decoder assumptions use the same conversion flags.

This is a stochastic circuit-level Pauli study, not a phenomenological-only model and not hardware-calibrated. The ratio 10:1:1 is a sensitivity setting, not a measured noise bias. The model excludes coherent error, leakage, crosstalk across separate gates, drift within the circuit, and non-Markovian behavior.

## References

- Stim gate/channel definitions: [Stim gates.md](https://github.com/quantumlib/Stim/blob/main/doc/gates.md).
- Stim detector-error-model approximation and decomposition: [Stim command-line reference](https://github.com/quantumlib/Stim/blob/main/doc/usage_command_line.md).
- PyMatching DEM import and correlated matching: [PyMatching matching.py API](https://github.com/oscarhiggott/PyMatching/blob/master/src/pymatching/matching.py).
