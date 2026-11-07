# Exact categorical versus PyMatching toy comparisons

PyMatching receives a Stim DEM constructed with `decompose_errors=True` and `approximate_disjoint_errors=True`. The standard and correlation-enabled modes use the same DEM in each toy. This is an approximate graph representation of the categorical channel; it is not the exact categorical posterior reference.

## Decisions and exact risk

| Toy | Exact categorical MAP risk | Standard PyMatching risk | Correlation-enabled risk | Syndrome decisions differing from exact (standard / correlated) |
|---|---:|---:|---:|---:|
| One-qubit locations | 0.002646 | 0.002646 | 0.002646 | 0 / 0 |
| Two-qubit categorical pairs | 0.060000 | 0.112800 | 0.112800 | 1 / 1 |

The risks are calculated exactly against the enumerated toy channel, not estimated from sampled shots. For the one-qubit toy, both PyMatching modes and the exact reference choose `L0=0` for syndrome `00`, and `L0=1` for `01`, `10`, and `11`.

## Two-qubit posterior by syndrome

| Syndrome integer (`D0` is bit 0) | P(s,L0=0) | P(s,L0=1) | P(L0=1 | s) | Exact MAP | Standard PM | Correlation PM |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.8290 | 0.0018 | 0.002167 | 0 | 0 | 0 |
| 1 | 0.0282 | 0.0282 | 0.500000 | 0 (tie) | 0 | 0 |
| 2 | 0.0282 | 0.0282 | 0.500000 | 0 (tie) | 0 | 0 |
| 3 | 0.0018 | 0.0546 | 0.968085 | 1 | 0 | 0 |

At syndrome `11`, the exact categorical MAP chooses the less likely matching correction represented by logical bit 1, while both graph decoders choose 0. The resulting exact-channel logical error risk is higher for this toy. Standard and correlation-enabled PyMatching give identical decisions here; enabling correlation did not fix the mismatch. This is a bounded counterexample to equivalence between this approximate DEM matching result and categorical MAP, not evidence about surface-code performance or general PyMatching quality.

The one-qubit toy's `P(s,L)` values and all decisions are retained in `TOY_RESULTS.json`. The toy's small detector count allows full syndrome enumeration (four syndromes); no Monte Carlo uncertainty applies.

