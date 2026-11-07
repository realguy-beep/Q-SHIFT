# Feasibility decision: PARTIAL

An exact categorical reference decoder is implemented and independently checked on two small Pauli-channel toys. It computes joint syndrome/logical masses, deterministic maximum-posterior logical decisions, and exact risk. Independent Stim forced-outcome enumeration matches all 320 toy configurations. The toy comparison also demonstrates a case where standard and correlation-enabled PyMatching on an approximate DEM both differ from the categorical MAP decision.

The full distance-3, five-round Phase 2B circuit has 209 independent categorical fault locations and `2^609` complete assignments. Direct exact enumeration is not feasible, and exact structured inference has not been implemented or costed on that circuit. Therefore the result is **PARTIAL**, not FEASIBLE: toy exactness is validated; scaling to the research circuit remains unresolved. This prototype makes no algorithmic novelty or performance claim.

No previous Phase 2B pilot, audit, or frozen file was modified. No Phase 2B evaluation shots were generated. The only Stim samples were 320 one-shot deterministic forced-outcome checks for the explicitly defined toy circuits; stochastic shot count is zero.

