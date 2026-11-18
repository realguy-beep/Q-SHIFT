# Equal-duration rounds: initial development result

## Result

On the aligned X-memory/X-bias and Z-memory/Z-bias workloads, three active syndrome rounds followed by two explicit data-idle cycles produced lower LER than five active rounds at equal five-cycle storage duration. At X alignment, failures were 557/500,000 (.001114) versus 657/500,000 (.001314), rate ratio .848 (95% interval .757–.949). At Z alignment, failures were 469/500,000 (.000938) versus 694/500,000 (.001388), rate ratio .676 (.601–.760). The equal-weight mean of cell-specific rate ratios was .762, a 23.8% relative reduction, passing the predeclared .90 gate in both conditions.

The shorter-active circuit retains 26 qubits and the same terminal data-readout targets. It has 24 detectors, 72 two-qubit pair locations, and 24 source one-qubit noise targets; the two idle cycles add 18 data-qubit Pauli targets, bringing its total to 42. The five-active-round comparator has 40 detectors, 120 pair locations, and 40 one-qubit targets. Thus elapsed storage duration is matched, while active syndrome and entangling-gate resources intentionally differ. The five-round circuit was byte-identical to the Phase 2B source builder. Both arms use their own correlation-enabled PyMatching model from the corresponding approximate DEM.

## Scope and next step

This initial positive result is an unpaired finite-sample simulator comparison under a specific assumed idle channel: two cycles of the same biased one-qubit Pauli channel at total p=.003 on nine data qubits immediately before readout. It is not a hardware coherence model. Fresh independent-seed replication is required before retaining the finding. No confirmatory or sealed data were used.

Artifacts: `equal_duration_rounds_protocol.md`, `equal_duration_rounds.py`, `equal_duration_rounds_results.json`.
