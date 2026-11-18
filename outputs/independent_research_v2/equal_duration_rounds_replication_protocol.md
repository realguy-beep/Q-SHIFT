# Independent-seed replication: equal-duration syndrome schedule

## Purpose

Challenge the initial positive development result using wholly fresh circuit sampler seeds while keeping the idle model, decoders, conditions, sample count, and metrics fixed.

## Frozen replication

- Reuse the exact circuit construction from `equal_duration_rounds.py`: aligned X memory/X bias and Z memory/Z bias, d3, p_gate=p_measure=.003, bias ratio 10; three active rounds plus two .003 regime-biased one-qubit data-idle cycles versus five active rounds.
- Rebuild each arm's correlation-enabled PyMatching decoder from its own approximate DEM at threshold .0018. No parameter changes.
- 500,000 fresh samples per arm/condition. Preflight: 100 per arm/condition, seeds 2026113801–2026113804. Main seeds: 2026113811–2026113814 in the original condition/arm order.
- The primary replication endpoint is the equal-weight mean of the two cell-specific independent-sample LER rate ratios. Directional replication requires both cell rate-ratio point estimates below 1 and the macro ratio below 1. No parameter search follows this replication.

## Stop and scope

Abort main if circuit/readout invariants, source builder equality, noiseless determinism, decoder scalar/batch agreement, or the five-minute runtime projection fails. This is independent development replication under one assumed idle channel, not a hardware or confirmatory result.
