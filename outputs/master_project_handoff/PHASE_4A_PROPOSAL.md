# Phase 4A Proposal — Model Adequacy Before Adaptation

**Status: proposal only. No experiment in this phase has been run. Explicit user authorization is required before running.**

## Question

Does an independently calibrated composition-specific DEM/PyMatching model change corrections and lower residual logical-observable errors relative to fixed nominal matching on a carefully specified rotated surface-code memory circuit?

## Rationale

Phase 3A showed a small unadjusted pilot difference that failed multiplicity adjustment, and Phase 3B did not replicate it. Before considering detector-based selection, establish whether the circuit/noise construction is physically interpretable and whether calibrated specialists can produce repeatable correction differences at all.

## Proposed bounded protocol

1. Freeze a distance-3, 3-round `rotated_memory_z` ideal circuit, detector and observable annotations, code/library versions, and channel definitions. Add explicit, separately named data-gate and measurement fault probabilities. Specify whether two-qubit faults are truly correlated or independent participant channels; never label one as the other.
2. Validate noiseless detector/observable behavior and DEM conversion. Record circuit/DEM hashes and inspect decomposition warnings. Confirm that each intended physical Pauli fault maps to expected detector and logical effects on controlled injections.
3. Use independent calibration, validation, and paired test seed families. Fix the nominal model before looking at test outcomes. Calibrate specialists only on calibration data; use validation only for the preregistered choice of specialist family/weight settings.
4. Compare fixed nominal PyMatching, composition-specific specialists (including correct-noise oracle as an explicitly informed reference), and the retained phase-3 implementation on identical test detector shots. Primary endpoint: paired residual logical-observable error difference for the one preregistered specialist/condition comparison. Secondary comparisons receive Holm or equivalent correction.
5. Use at least 20 fresh seeds if compute allows, report per-seed counts, seed-level bootstrap interval and sign/permutation analysis separately from shot-level exact paired McNemar. Predefine a bounded shot budget and stop if the calibration/model checks fail.
6. Apply a usefulness gate: proceed to any selector only if a specialist changes corrections and has a consistent, statistically supported benefit on untouched test seeds without a material regression in prespecified controls. Otherwise stop and document the negative result.

## Not in scope

No classifier, regime estimator, time-windowed adaptive policy, online switching, hardware integration, or claim of adaptive superiority. Do not use true noise labels or logical labels at inference. Do not tune using test results.

## Decision after authorization

If approved, implement the protocol in a new `phase4a_model_adequacy` directory without modifying earlier phase outputs. If declined or revised, record the decision and do not run. This document itself is not permission to execute.
