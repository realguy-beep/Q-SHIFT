# Distance-3 syndrome-round resource frontier

## Hypothesis

At fixed distance 3 and the source p=.003 Pauli-biased circuit model, changing the number of syndrome-extraction rounds can trade measurement robustness against added gate-fault opportunities. The usual d=3 choice is five rounds. Fewer rounds may leave measurement faults less constrained; more rounds add circuit depth and noise. The useful point may depend on whether the memory basis is aligned with the X/Z bias.

## Fixed screen

- Use the source rotated-memory circuit builder at distance 3, rounds 3/5/7/9, p_gate=p_measure=.003, and X/Z bias ratio 10.
- Cross all four rounds with X/Z memory bases and X/Z biased profiles (16 cells). For each circuit, build correlation-enabled PyMatching from that same circuit's approximate DEM using `approximate_disjoint_errors=.0018`.
- Draw 100 preflight samples/cell, check detector/observable dimensions, resource counts, batch/scalar decoder agreement, and projected time. Abort before main if any check fails or projected sampling+decoding exceeds five minutes.
- If preflight passes, draw 200,000 fresh direct source-circuit shots/cell (3.2M main shots). Main seeds: 2026112221–2026112236 in round/profile/basis order; preflight seeds: 2026112201–2026112216.
- Primary measure: logical failure rate per memory attempt with Wilson 95% interval. Also report detector count, two-qubit channel-pair opportunities, one-qubit channel targets, decode time/sample, and descriptive rate ratios against rounds=5. The round count is an explicit resource cost; do not call cross-round differences decoder gains or fit a threshold.

## Scope

This is one fixed-distance synthetic resource screen under known stable profiles. It asks whether five rounds is locally efficient for this task/noise family. It is not a code-distance scaling law, unknown-noise adaptation result, hardware claim, or confirmatory evaluation. No post-hoc round expansion or noise retuning is allowed.
