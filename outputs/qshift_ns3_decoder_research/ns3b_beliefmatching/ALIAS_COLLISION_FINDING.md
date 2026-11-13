# Upstream DEM aliasing limitation and fail-closed guard

## Deterministic counterexample

In pinned BeliefMatching 0.2.0, `detector_error_model_to_check_matrices` keys hyperedges and edges by detector support alone and stores one observable support per key. A later mechanism with identical detector support overwrites the earlier observable support. This is not safe when two DEM events share detector targets but differ in L targets.

Counterexample DEM:

```text
error(0.002) D0
error(0.0005) D0 L0
```

For syndrome rows `[0]` and `[1]`, independent exact MAP gives `[[0], [0]]`; PyMatching on the same DEM gives `[[0], [0]]`; direct upstream BeliefMatching gives `[[0], [1]]`. On syndrome D0, the more probable event is the nonlogical p=.002 mechanism, but the pinned converter's observable map is overwritten by the p=.0005 logical event. This deterministic example is independently checked by the NS-3A exact oracle and a separate PyMatching decode. No stochastic data is involved.

The same-support/different-observable possibility also applies to separator components, so the adapter checks both full hyperedge detector support and each graphlike component support. It rejects repeated detector/observable targets within a decomposed component and any component with more than two detector targets. A rejected DEM never reaches upstream construction.

## Q-SHIFT result

The actual Q-SHIFT d3/five-round balanced Z-memory DEM at the declared development configuration (gate p=.003, measurement p=.003, bias ratio 10, burst p=.01 on pair (8,10)) passes the adapter guard. The static scan found no full-mechanism or component detector-support alias with conflicting observable parity in this concrete decomposed DEM. The adapter built and decoded all five saved deterministic NS-3A fixtures.

## Preserved negative probe

`benchmark_results_ns3b_alias_collision_probe.json` preserves an earlier synthetic-cycle probe that generated duplicate D0 support with and without L0. It showed one BM/PyMatching disagreement for each tested cycle size (10, 40, 80 detectors). That output is retained as a negative representation-adequacy result and is not used for runtime scaling. The adapter now rejects that unsafe representation. The final scaling benchmark uses a chain DEM with unique logical support and reports zero disagreements on its selected rows.
