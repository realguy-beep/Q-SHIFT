# Research implications

The original toy's discrepancy is a useful diagnostic but not a surface-code performance result. Exact categorical MAP and exact enumeration under the independent DEM mechanism law agree on all four toy decisions. The standard and correlation-enabled PyMatching predictions differ only when the separator-bearing graph decomposition is used; removing the separators without changing mechanism probabilities or total detector/logical masks restores the logical edge and the exact decision at syndrome 11.

This suggests a concrete next technical question: when Stim decomposes mutually exclusive categorical channel outcomes into separator-bearing graph components, which logical-frame information is preserved by PyMatching's graph builder and correlation pass? The minimal audit should test the same event law under graphlike and decomposed representations on a systematic set of small circuits before claiming the issue generalizes.

The structured inference prototype proves that categorical fault exclusivity can be respected in exact sums on bounded instances, and that output parity structure avoids enumerating complete assignments. It also exposes a hard scaling boundary: a global detector/logical state grows exponentially and the full distance-3, five-round state table is far beyond 2 GiB. A more local tree decomposition would need measured treewidth, validated posterior results, and resource tests before it could support a scalable decoder claim.

No novel decoder, adaptive controller, stochastic performance advantage, hardware compatibility, or full-circuit exact decoder is claimed. No new Phase 2B evaluation shots or held-out labels were used.

