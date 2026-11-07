# Decoder comparisons

| Decoder | Interpretation | What was compared |
|---|---|---|
| Exact categorical MAP | Best logical-observable posterior decision under the stated categorical channel | Exhaustive all-syndrome risk for toy chains |
| Exact independent-DEM MAP | Best posterior under mutually independent DEM mechanisms | Exhaustive toy and reduced-surface reference; on categorical cases, scored under the actual categorical channel |
| PyMatching standard | Matching prediction from the separated DEM | Same syndromes/models as the correlation-enabled arm |
| PyMatching correlated | PyMatching two-pass correlation-aware matching | Same DEM as standard PM; not exact Bayesian inference |
| Separator-free PyMatching | Graphlike full-event rewrite, only after support validation | Valid in toy and graphlike family; rejected for hyperedges |
| Local restricted posterior | Exact under exterior-zero conditioning | Compared syndrome-by-syndrome; fallback and cap behavior recorded |

## Main findings

On the historical categorical toy, exact MAP risk is 0.0600; standard and correlation-enabled matching are both 0.1128; valid separator-free matching is 0.0600. Across the eight categorical chain toys, standard and correlated matching predictions are identical in every case. Separator-free matching improves upon separated matching, but only matches exact MAP in two of eight cases; the bounded local method matches MAP in these tiny fixtures. This illustrates that matching decisions differ materially from posterior MAP in some bounded models, while the small rewrite is not a proven full-scale remedy.

As a positive control, the earlier manifest-verified one-qubit categorical toy has exact, standard PyMatching, and correlation-enabled risk all equal to 0.002646 with identical decisions on all four syndromes. The new preregistered extension therefore includes both a case where standard matching is already exact and cases where it is not.

For reduced exact-DEM surface fragments, standard and correlation-enabled predictions coincide on the one-round fragments. On two-round fragments, they disagree on 12,048 of 65,536 syndromes (Z) and 18,122 of 65,536 (X); logical risks are 0.001957 vs 0.001922 (Z), and 0.002213 vs 0.002808 (X). The latter is a regression for correlation-enabled matching in this exact-DEM finite fragment. These are deterministic DEM-model risks, not sampled categorical-circuit performance estimates.

All comparisons share the same probability models and enumerate feasible syndromes. There are no Monte Carlo error bars. The primary caveat is model: independent DEM mechanisms are not identical to native categorical Pauli channels in general, though the toy runs directly quantify categorical-vs-DEM differences.
