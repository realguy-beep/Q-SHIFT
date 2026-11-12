# HAMLD deterministic compatibility preflight

## Scope and method

No stochastic circuit shots, decoder calls, logical scoring or performance comparison were run. The preflight used the actual Q-SHIFT builders at `outputs/phase2b_pauli_bias/noise_model.py::build_circuit` and `outputs/phase3a_correlated_noise_preflight/simulator.py::build_spatial_burst_circuit`, with Z-memory, d=3, five rounds, balanced categorical gate noise `.003`, measurement flips `.003`, burst pair `(8,10)` and burst probabilities 0 and `.01`. Stim 1.16.0 deterministically built the circuits and DEMs. We exercised DEM conversion flags and counted instructions/targets; this is structural inspection only.

## Circuit conventions observed

- Circuit and DEM both report **40 detectors, one observable**.
- Detector IDs follow the order of `DETECTOR` annotations emitted by the generated circuit. The first coordinates are D0 `(0,4,0)`, D1 `(2,2,0)`, D2 `(4,4,0)`, D3 `(6,2,0)`; the last three are D37 `(2,2,5)`, D38 `(4,4,5)`, D39 `(6,2,5)`. Do not remap by sorting coordinates.
- The sole logical mask is `OBSERVABLE_INCLUDE(0) rec[-7] rec[-8] rec[-9]` at the final circuit location; it defines L0 parity as the XOR of those measurement records under Stim's detector/observable convention.
- The burst is inserted after each of five `MR` boundaries and does not change detector/observable counts. It is a correlated Pauli event in the original circuit, independent across rounds by construction.

## Deterministic DEM results

| Burst p | `decompose_errors` | `approximate_disjoint_errors` | DEM instructions | `error` instructions | separator-bearing errors | max detector targets in one error | observable-bearing errors |
|---:|---|---|---:|---:|---:|---:|---:|
| 0 | false | true | 483 | 443 | 0 | 4 | 71 |
| 0 | true | true | 626 | 586 | 444 | 4 | 130 |
| .01 | false | true | 488 | 448 | 0 | 4 | 71 |
| .01 | true | true | 631 | 591 | 444 | 4 | 130 |

With `approximate_disjoint_errors=False`, Stim raises a deterministic `ValueError`: `PAULI_CHANNEL_2` requires `approximate_disjoint_errors=True` for DEM error analysis. Thus a non-approximated categorical-channel DEM is not available through this conversion route. The code explicitly shares this approximation across the ordinary and correlated PyMatching arms, but it means the graph DEM is not the exact original categorical circuit distribution.

The Q-SHIFT matching pipeline constructs the DEM with `decompose_errors=True, approximate_disjoint_errors=True`; PyMatching graph construction uses `Matching.from_detector_error_model(..., enable_correlations=...)`. For a fair PyMatching correlation arm, the same mode must also be passed at decode (`decode_batch(..., enable_correlations=True)`); graph construction and decode flags are separate. HAMLD’s generic tutorial instead supplies `decompose_errors=False, flatten_loops=True` and no equivalent correlation flag exists in its API.

## Deterministic cases and stop condition

The expected syndrome input shape is `(n,40)` and the nominal HAMLD declared output shape is `(n,1)`; these dimensions agree. The deterministic script constructed and asserted a 40-bit all-zero row, a length-40 one-hot row at D0, and a hand-constructed Stim DEM mechanism `error(0.1) D0 L0`, whose parsed target IDs were exactly detector 0 and observable 0. These are representation checks, not HAMLD decode predictions; the one-hot vector is not asserted to be physically reachable. We did not call `decode` or `decode_batch` because the package cannot be imported/built here.

The source-level parser review finds that it traverses all DEM targets in an `error` instruction and ignores separator targets. Therefore each separated component sequence is flattened into one larger hyperedge, instead of retaining Stim's documented decomposition semantics. The Q-SHIFT nominal decomposed DEM has 444 such instructions, so passing it as-is is invalid for a semantics-preserving comparison. The undecomposed DEM has no separators and is a plausible direct HAMLD input; its error hyperedges are at most degree four and target signatures are unique in the tested p=0 and p=.01 cases. It remains an approximation of the categorical circuit because Stim requires `approximate_disjoint_errors=True` for `PAULI_CHANNEL_2`. We did not execute HAMLD's parser/contraction to verify it preserves this representation.

**Preflight result: FIX required before a decoder comparison.** The decomposed PyMatching DEM is incompatible with the parser's separator handling. The undecomposed DEM is a plausible HAMLD path, but no HAMLD output was verified. We did not attempt zero/single-fault decode because importing/using the pinned package was blocked: the source `__init__` imports an absent C++ extension, required Bazel 8.2.1 is unavailable, and the declared Python environment excludes installed Python 3.12. No detector sample or logical outcome was generated.
