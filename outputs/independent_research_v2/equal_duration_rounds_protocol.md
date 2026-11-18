# Equal-duration syndrome-round versus storage-idle comparison

## Question

The d3 resource frontier found lower per-attempt LER with three active rounds than with five, but that comparison also shortened memory exposure. Does the advantage persist if a three-round attempt occupies the same five-cycle duration by adding two data-idle cycles with the same biased one-qubit Pauli channel?

## Frozen design

- Use only aligned d3 workload pairs: X memory under X bias and Z memory under Z bias, ratio 10, gate and measurement p=.003.
- Arm A is the source three-round circuit followed by two idle cycles on its nine data qubits. Each idle cycle applies the source regime's `PAULI_CHANNEL_1` probabilities (total .003) to the data qubits before final readout. Arm B is the source five-round circuit with its native noise. Both occupy five cycle units; they intentionally differ in active syndrome-extraction opportunities and associated gates.
- Build correlation-enabled PyMatching independently from each circuit's own DEM using `decompose_errors=True`, `approximate_disjoint_errors=.0018`.
- Use fresh direct streams, 500,000 shots/arm/condition. Conditions: (X, X-biased), (Z, Z-biased). Preflight: 100 shots/arm/condition. Report failures, Wilson intervals, independent-arm LER difference and rate ratio with 95% intervals, elapsed runtime, data-qubit idle counts, and gate resources.
- The equal-weight macro rate ratio is the primary endpoint. Advance fewer-active-round design only if the macro ratio is <=.90 and neither workload's rate ratio exceeds 1.05. This is a development-only code/circuit decision.

## Integrity and stopping rules

Before main sampling verify exactly nine data qubits are idled twice, identical logical basis/profile and gate/measurement probabilities, unchanged data-readout targets, detector/observable shapes expected for each arm, deterministic noiseless circuits, successful DEM construction, decoder scalar/batch equality, and projected end-to-end runtime <=300 seconds. Stop before main if any check fails. The idle channel is an explicit simulator assumption, not a hardware-calibrated coherence model. No sealed or confirmatory data are in scope.
