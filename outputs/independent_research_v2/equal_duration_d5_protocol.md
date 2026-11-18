# Distance-5 equal-duration schedule extension

## Question

Does the Z-aligned d3 result for fewer active syndrome rounds survive at d5, where the standard memory schedule has nine extraction rounds?

## Fixed design

- Condition: rotated d5 Z memory under the source Z-biased ratio-10 Pauli circuit; gate and measurement p=.003.
- Compare five active rounds plus four explicit data-idle cycles to nine active rounds. Each idle cycle applies the same source biased one-qubit Pauli channel at total p=.003 to all 25 data qubits before terminal readout. Do not alter the nine-round comparator.
- Use each arm's own approximate DEM (`decompose_errors=True`, threshold .0018) and correlation-enabled PyMatching.
- Fresh main streams: 1,000,000 shots/arm, seeds 2026114011–4012. Preflight: 10,000/arm, seeds 2026114001–4002. Report LER and Wilson intervals, independent-arm RR and log interval, detector/gate/idle resources, and runtime.
- Interpret as a finite d5 development extension under one assumed idle model. It is not a threshold or scaling fit. No tuning or second idle-rate condition is part of this protocol.

## Stop rule

Verify the nine-round circuit byte-matches the established d5 source builder; data readout targets match; exactly 25 data qubits receive four idle cycles; 120 detectors/one observable for five-round arm and 216 detectors/one observable for nine-round arm; noiseless determinism and scalar/batch decoding; and projected total main runtime <=300 seconds. Stop before main if any check fails.
