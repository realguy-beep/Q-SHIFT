# Feasibility decision: PARTIAL

## What passed

- The saved toy baseline and its hashes were reproduced without modifying prior artifacts.
- Exact categorical MAP and `P(s,L)` were independently validated for the 64- and 256-configuration toy models.
- Exact inference was also run through two different variable-elimination heuristics and through the XOR/Walsh structured method; both recover all toy syndromes, posteriors, ties and risks.
- Actual Phase 2B channel faults were propagated deterministically for reduced-round distance-3 Z-memory circuits. Exact structured posteriors completed for rounds 1, 2 and 3, with the three-round job within the 2 GiB cap.

## What remains unresolved

- Rounds 4 and 5 were not inferred: the tested global parity-state method would require 64 GiB and 16 TiB just for a dense float64 joint table, so both were skipped before allocation.
- Direct parity-factor-graph min-fill/min-degree values for circuit fragments are only symbolic width estimates; large factors were not materialized.
- The three-round circuit posterior was checked for normalization and tiny floating-point residues, not independently compared to a second full-circuit solver.
- No optimized spacetime-local exact elimination or approximation-error study was performed.

## Answers

1. **Why does exact categorical MAP beat PyMatching on syndrome 11?** The exact categorical posterior has `P(L0=1|11)=0.968085`; the exact independent-DEM posterior also chooses 1. The separator-bearing PyMatching graph has only two boundary edges with no logical fault IDs and predicts 0. Removing only the separator decomposition hints, while preserving the same six error-event probabilities and masks, gives a direct logical `D0-D1` edge and changes both PyMatching modes to predict 1.
2. **How much is DEM approximation versus decoder inference?** The approximate DEM changes the joint distribution (TV distance 0.0048681), but changes none of the four exact MAP decisions. On this toy, the full observed 0.0528 risk gap is associated with the matching graph/decomposition decision: it disappears under the same independent-DEM event law when represented graphlike without separators. This is not a general PyMatching claim.
3. **Can structured inference avoid exhaustive fault enumeration?** Yes for the toys and tested circuit fragments. Walsh XOR convolution returns the exact sum-product distribution without enumerating `2^129`, `2^249`, or `2^369` complete assignments. Arithmetic is float64 and the larger fragments have normalization checks rather than an independent exhaustive oracle.
4. **Largest successfully decoded fragment?** Distance 3, Z-memory, three rounds: 24 detectors, 1 observable, 129 categorical locations, `2^25` output states; inference took 89.09 seconds and peak working set was 764 MB.
5. **Credible path to full distance-3, five-round inference?** Not established. The measured global-parity method cannot fit its `2^41` state table. A circuit-local tree decomposition might be viable but would require a separate width-driven prototype and independent validation.
6. **Does this justify a new categorical-aware decoder?** Not yet. First investigate why the matching graph conversion with separators loses the logical edge in this toy and whether the same behavior occurs in larger cases. No decoder-performance or surface-code benefit is established.

`PARTIAL` is the appropriate outcome: exact toy inference is validated and nontrivial circuit fragments work, but five-round feasibility remains unresolved under the stated budgets.

