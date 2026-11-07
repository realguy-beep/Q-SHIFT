# Implementation feasibility in the existing Q-SHIFT repository

## Existing components inspected

The local workspace contains the headroom utilities in [`headroom.py`](../headroom_feasibility/headroom.py), its [runner](../headroom_feasibility/run_pilot.py), [frozen configuration](../headroom_feasibility/config.json), and Phase 5 adaptive modules under [`phase4c_strong_baselines/adaptive/`](../phase4c_strong_baselines/adaptive/). Historical files were read only.

`headroom.py` already builds rotated Stim `surface_code:rotated_memory_x/z` circuits with distance/round configuration and native gate/readout noise; it extracts DEMs and constructs PyMatching models. The native family uses `decompose_errors=True`; the categorical Pauli-biased family uses `approximate_disjoint_errors=True` and correlated matching. This latter conversion is an approximation for channels Stim cannot express exactly as independent DEM mechanisms. Stim documents that `PAULI_CHANNEL_1`, `PAULI_CHANNEL_2` and `ELSE_CORRELATED_ERROR` may require that approximation. [Stim documentation](https://github.com/quantumlib/Stim/blob/main/doc/usage_command_line.md).

The current nine-candidate native grid is static. The code samples independent calibration/evaluation roots, calculates logical residuals, selects a pooled model, and estimates detector-marginal profiles. It does not estimate time-varying physical parameters, rebuild weights online, or run an equal-budget periodic baseline. Stim circuits in the current utilities are constructed per noise condition, so the directly supported first dynamic experiment is **noise changing between batches of complete memory shots**, not changing during one shot.

## API and safe update path

The local Python environment has Stim and PyMatching available; PyMatching is version **2.4.0**. Runtime introspection found `Matching.add_edge`, `edges`, `get_edge_data`, and `to_networkx`, but **no public `set_edge` or weight-mutation method**. The documented API permits weights when adding edges and supports construction from a Stim DEM or graph object. [Official PyMatching API](https://pymatching.readthedocs.io/en/stable/api.html).

Therefore, do not mutate internals or edit graph attributes in place. A safe prototype should:

1. Freeze detector-node ordering, boundary convention, fault IDs and the circuit/DEM-to-graph map.
2. Convert a causal parameter estimate into a complete, internally consistent DEM/weight specification.
3. Build a *new* PyMatching instance from the updated model (or a freshly validated graph with explicit weights, error probabilities, boundaries and fault IDs).
4. Check graph schema and expected observable count, compare graph topology and edge/correlation metadata against the approved model family, and run deterministic decoder checks.
5. Atomically activate that immutable decoder only at the next block boundary; keep the prior pooled decoder as fallback.

For a graph-only independent-error model, rebuilding with `add_edge` can assign a weight to each edge. For correlated matching, merely copying the exposed edge list may lose DEM-derived correlation information used by the two-pass decoder. The safer first prototype is to regenerate the full DEM and Matching from a parameterized circuit and verify that correlation hints survive. If estimated per-edge quantities cannot be mapped back into a consistent DEM without unsupported graph modifications, restrict the first study to a validated graphlike independent family or use a separately validated decoder that accepts updated model weights. Do not silently mix new weights with stale DEM probabilities/correlation metadata.

PyMatching edge weights conventionally encode log-likelihood ratios for independent graph mechanisms; correlated matching uses extra decomposition/correlation information. [PyMatching documentation](https://pymatching.readthedocs.io/en/stable/api.html). Stim notes that some categorical Pauli channels need approximate independent DEM conversion. Therefore native depolarizing and categorical Pauli studies must be reported separately, and any approximation setting must remain fixed across policies.

## Minimal technical prototype plan (not implementation authorization)

1. Add isolated modules for `parameter_estimator`, `weight_mapper`, `matching_factory`, `update_policy` and an evaluation runner; leave Phase 1–5 untouched.
2. Begin with one small code/memory and a single interpretable parameter family already represented by the current circuit generator (separate gate versus measurement error rates). Validate the estimator on a toy analytically identifiable detector model, then in static synthetic development data.
3. At each block boundary, reconstruct and validate the new decoder, recording parameter intervals, graph hashes, build/decode times and exact detector-history cutoff.
4. Run deterministic unit checks for causality, identical test arrays, fallback, graph/fault-ID invariants, and no logical-label access before any development simulation.
5. Only after this feasibility pilot passes should a preregistered multi-root study be considered.

The present assessment did not run a circuit simulation, alter any decoder, or measure online update latency. Software API availability is verified; real-time hardware feasibility is not.
