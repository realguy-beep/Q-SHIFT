# Experiment protocols and gates

## Completed deterministic feasibility check

The check and its exact outcome are recorded in `EXPERIMENT_RESULTS.md`. It was a conversion/API feasibility check only, with no stochastic samples.

## Candidate protocol: native categorical inference feasibility

**Status: proposed, not run.** The exact-DEM correlation mechanism protocol is blocked for the categorical two-qubit circuit. A replacement should not simulate a fictitious exact DEM. The existing `outputs/categorical_decoder_feasibility/` has an exhaustive exact reference for tiny categorical models and reports 209 categorical fault locations (2^609 complete assignments) for the Phase 2B distance-3 circuit.

A useful next prototype would build a factor graph directly from mutually exclusive local Pauli outcomes and parity effects on a reduced circuit fragment, then compare exact variable elimination or tensor contraction with exhaustive categorical enumeration on a toy and a bounded fragment. Before coding, define a fragment with explicit detector/observable boundary conditions and verify its native-channel distribution against deterministic forced-outcome Stim enumeration. Advance only if the inference exactly matches brute force on multiple small fragments, with a recorded maximum intermediate factor size and memory/time. No full-circuit performance inference follows from fragment agreement.

No sampling, final evaluation, or Phase 2B pilot-data reuse is part of this feasibility protocol. If exact variable elimination has prohibitive induced width on the fragment, stop and report the measured width and cost. Do not replace it with a posterior surrogate without a separate approximation validation plan.
