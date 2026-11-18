# Sequential profile calibration end-to-end development test

## Question

Does the independently replicated detector-only SPRT reduce logical failure rate and/or correct-output throughput cost versus static X/Z memory choices and fixed-budget detector classifiers, when each calibration decision is followed by a fixed block of logical-memory attempts?

## Frozen setup

Use the 2,500/profile validation windows already generated under seeds 2026115401/5402 and the exact frozen LDA/Gaussian score parameters. Recompute SPRT and fixed 25/100/500-shot decisions on these same detector streams; they are reused, not new samples. For each profile, run 250,000 fresh X-memory and 250,000 fresh Z-memory attempts (2,500 blocks of 100 per basis) under the same d3/five-round, ratio-10, p=.003 simulator. Use correlation-enabled PyMatching on each circuit's approximate DEM. Every policy is scored on identical logical failure blocks; the policy chooses X or Z once per 100-attempt block. Include static-X, static-Z, and profile-oracle choices as references. Calibration shots produce no logical output and are charged to total circuit-shot cost.

Preflight reuses the saved calibration seeds and draws 5,000 logical attempts per profile/basis at seeds 2026115601–5604. Check source builder identity, common resources across X/Z within each profile (qubits, detectors, observables, ticks, two-qubit interactions and two-qubit-noise targets), detector/observable shapes, noiseless determinism, finite failure vectors, and projected runtime under 300s. Main uses fresh logical seeds 2026115611–5614. Report all one-qubit-noise and terminal measurement operation differences explicitly; do not call the two basis circuits fully gate-resource matched. Report per-profile and equal-weight LERs, paired window bootstrap intervals, calibration shots consumed, and correct outputs per logical-plus-calibration circuit shot. This is a synthetic development policy test; profile transitions, hardware behavior, and arbitrary-state performance are outside scope.

## Deterministic resource audit amendment

The first preflight attempt stopped before sampling because the X and Z circuits use different terminal readout instructions and different X/Z one-qubit fault instructions, despite matching aggregate one-qubit-noise target counts, qubits, detectors, rounds, CX interactions and two-qubit channel pairs. The protocol now preserves these measured differences explicitly and gates only the shared resource fields listed above. This does not change the policy comparison: every selector is evaluated on the same per-basis logical circuits. It limits interpretation of cross-basis aggregate LER and throughput as a pure decoder comparison.
