# Exact variable-elimination feasibility for native categorical noise

## Question

Can exact variable elimination recover the native categorical model's syndrome/logical posterior on nontrivial toy graphs, and what intermediate factor size does the explicit ordering require? This targets the loopy Bethe prototype's posterior error without flattening mutually exclusive Pauli outcomes into binary mechanisms.

## Model and algorithm

- A categorical variable represents one fault location, with a unary prior over its mutually exclusive outcomes.
- Each detector contributes an exact XOR constraint over locations whose outcomes toggle that detector.
- A chain of binary prefix-parity variables represents the logical observable without making one global factor over every fault location.
- The constrained partition is computed in the log domain by dense table multiplication and sum elimination. A greedy weighted min-fill ordering is frozen; report induced width and maximum intermediate table entries.
- Enumerate every syndrome/logical target on the existing distance-1 one- and two-qubit repetition models and compare every joint mass, normalized posterior, MAP decision, and aggregate MAP risk against the independent exhaustive reference. Independently verify fault-to-syndrome mapping by forcing each toy Pauli outcome through Stim. Include the existing single-location tree control.
- Measure exact elimination width on 2x2 through 11x11 synthetic grid-incidence models at one consistent syndrome, exhaustively crosschecking the 2x2 case. Enforce a one-million-entry cap on every intermediate factor. This is a topology stress test only, not a mapped Q-SHIFT circuit.
- Stop before any circuit-level application. These models are feasibility controls, not a representative Phase 2B circuit fragment.

## Gate

Advance this implementation only if all joint masses agree within 1e-10, every posterior is normalized, MAP decisions match, and no intermediate table exceeds 1,000,000 entries on these controls. Report timings only as toy-level diagnostics. No stochastic Q-SHIFT circuit shots or confirmatory data are involved.
