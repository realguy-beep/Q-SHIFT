# Final decision: PARTIAL

## Answers to the research questions

1. **Does the toy failure generalize?** Representation sensitivity recurs in eight categorical toy channels, a fixed 64-cell graphlike family, and exact-DEM surface fragments. It has not been shown to generalize into a safe full-circuit fix.
2. **Can separator removal worsen decisions?** In the 64 preregistered *valid graphlike* grid cells it improved 59 and tied 5, worsening none. That narrow result does not establish universal safety. For complete events with >2 detector symptoms or logical-only faults, erasure is invalid; this implementation rejects those cases. No valid full-surface separator-free comparison was possible.
3. **Can a principled representation avoid the toy failure?** Yes, in the limited case where the full event has ≤2 detector symptoms and is not logical-only: preserve its entire probability and parity mask as one graphlike mechanism. This exactly fixes the toy, but the Phase 2B five-round DEM contains many hyperedges, so the rule does not cover it.
4. **Can bounded local inference improve matching?** It agrees with exact MAP in tiny categorical toys, but in one-round surface fragments it has low syndrome coverage, falls back 89.5%, and is slightly worse than valid separator-free matching. No two-round/full-circuit result exists for the local method.
5. **What is the cost?** The complete bounded investigation took 4.53 s and peaked near 98 MiB. Local full-syndrome one-round sweeps took 4.4–6.7 ms with at most 4,096 local assignments. Exponential global exact inference is not feasible at 40 detectors in the previous state-vector implementation.
6. **Does either candidate justify a full decoder?** No. Candidate A is a conservative preprocessing guard but rejected all six target full-round DEMs. Candidate B is an instructive toy reference, but its restricted boundary assumption and low coverage prevent a credible full decoder claim.
7. **Best evidence-supported next direction?** Treat this as an implementation/representation audit, then evaluate established hypergraph/factor-graph or belief-based methods against carefully verified exact small cases before proposing a distinct decoder. Do not claim novelty or improvement based on this pilot.

## Decision rationale

**PARTIAL** is the correct gate: both candidate ideas are correct in clearly limited domains, with reproducible exact results and manageable toy-case cost, but neither demonstrates the required multi-instance full-circuit improvement, scaling, and semantic coverage for GO. It is not NO-GO because the diagnosis and graphlike rewrite are valid, useful engineering results; it is not GO because the central full-circuit mechanism remains unresolved.

No confirmatory experiment is authorized or was run. The work used no stochastic Phase 2B evaluation shots, did not access Phase 2B full-test labels, and preserves all prior negative results.
