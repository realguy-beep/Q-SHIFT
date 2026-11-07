# Final research and publication decision

## Outcome: REDESIGN

The independent audit confirms the headroom phase’s NO-GO. The tested decoder bank did not show a replicated, calibration-stable pair of regime specialists with practically meaningful evaluation gains across distances. The result is specific to the tested circuits, model families, noise ranges, and small root counts; it does not prove that adaptive decoding is generally ineffective.

The cumulative Phase 2–5 history is not sufficient for a novel publishable negative-results benchmark as currently assembled. It is valuable prototype and feasibility work, but it combines exploratory studies and different circuit/noise/selection protocols, includes known protocol deviations and corrected analyses, lacks Phase 4C Stage 2 calibration samples, and has no independent confirmatory adaptive evaluation. Established work already covers adaptive decoding for leakage signals, syndrome-based noise estimation, matching-weight calibration, and bias-aware decoding. A paper must make a narrower, clearly differentiated contribution.

## What the evidence supports

- The headroom NO-GO is reproduced from saved calibration/evaluation arrays: 36 cells, 702 candidate-pair contrasts, 95 finite-sample prediction-identical pairs, 14 specialist choices different from pooled fixed, and a split of 7 lower / 6 higher / 1 equal evaluation LER.
- None of the 95 sample-identical pairs has the same saved DEM or canonical matching-graph signature. They are finite-sample coincidences; full decoding-function equivalence remains unproved.
- Only one regime cell meets every numeric per-regime criterion, and it does not form a second-regime pair at that distance or repeat across another distance.
- The current bank is not shown to offer enough consistent utility headroom to justify building a confirmatory switching benchmark around it.

## Minimum additional analysis without new simulations

The requested raw-array recomputation, graph-identity audit, specialist breakdown, leave-one-calibration-root-out stability check, and cross-distance gate audit are complete. Before drafting any publication from the existing files, the minimum remaining no-simulation work is:

1. Produce a unified evidence ledger mapping every numerical manuscript claim to its frozen protocol, raw arrays, audit, and deviations; keep Phase 4A/4B nominal-baseline effects separate from Phase 4C pooled-baseline effects.
2. Reconstruct a candidate-by-candidate paired evaluation table with root-cluster intervals and explicitly marked multiplicity; avoid treating retrospectively inspected outcomes as a selector.
3. Map edge-weight/DEM changes to the detector patterns where selected specialist and pooled predictions diverge, so “weak headroom” is separated from “candidate graphs differ but are rarely decision-relevant.”
4. Reconcile the corrected Phase 5 causal timelines and controller outcomes against raw development records; exclude superseded v1 and do not present the small development run as a confirmatory test.
5. Complete a broader literature search and novelty check before claiming a benchmark contribution.

These analyses can improve explanation and reproducibility, but cannot restore missing Phase 4C calibration arrays or turn the present feasibility data into independent confirmatory evidence.

## Redesign direction

If the project continues, revise the research hypothesis around **measurable decoder-utility headroom and its causal identifiability**, rather than assuming that regime classification should improve logical performance. Define a new experimental architecture with (i) a stronger candidate bank whose corrections differ on meaningful syndromes, (ii) calibration selected against a robust pooled fixed baseline, (iii) frozen practical-effect and equivalence margins, (iv) enough independent calibration and evaluation roots, and (v) fresh dynamic schedules testing a causal selector with delay and switching costs. A new protocol should address missing calibration evidence and multiplicity prospectively. No such experiment was run for this audit.

## Integrity boundary

No simulation shots were generated. Existing Phase 4/5 records were not edited. The output files in this directory are a separate read-only audit, literature assessment, and publication decision.
