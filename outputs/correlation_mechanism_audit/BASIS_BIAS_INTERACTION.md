# Basis–bias interaction audit

## Reconstructed six-condition comparison

All entries below were recomputed from the saved 72 NPZs. Each cell has 120,000 paired shots and 12 roots. δ is pooled correlation-enabled minus pooled correlation-disabled LER; positive means the correlation-enabled decoder made more residual errors.

| Memory | Pauli bias | Off errors | On errors | δ LER (root-bootstrap 95% interval) | Root direction help / harm / tie |
|---|---|---:|---:|---:|---:|
| X | X-biased | 100 | 122 | +0.000183 [+0.000033, +0.000317] | 1 / 9 / 2 |
| X | Balanced | 727 | 629 | −0.000817 [−0.001225, −0.000450] | 11 / 1 / 0 |
| X | Z-biased | 1,070 | 984 | −0.000717 [−0.000892, −0.000533] | 12 / 0 / 0 |
| Z | X-biased | 938 | 884 | −0.000450 [−0.000650, −0.000250] | 9 / 1 / 2 |
| Z | Balanced | 575 | 550 | −0.000208 [−0.000425, 0.000000] | 8 / 3 / 1 |
| Z | Z-biased | 122 | 180 | +0.000483 [+0.000317, +0.000642] | 1 / 11 / 0 |

The two same-name pairs (X memory/X-biased and Z memory/Z-biased) are the adverse conditions. Their mean δ is +0.0003333. The other four cells have mean δ −0.0005479. Their post-hoc difference is +0.0008813. This is an exploratory contrast, not a confirmatory interaction test: the grouping was highlighted after looking at the results, and the first group contains only two fixed cells.

## Decoder and label mapping check

The stored fixed model indices are X-memory index 0 and Z-memory index 2. In the ordered bank these are X-biased and Z-biased models, respectively. For X-memory/X-biased, the fixed index and generating-regime index are both 0. For Z-memory/Z-biased, both are 2. The pooled and regime-informed uncorrelated predictions, and likewise their correlated predictions, are identical in these two conditions. Metadata and these prediction identities were checked directly from all checkpoints.

Consequently, the worsening in the two same-name conditions is not a mismatch between a pooled-model label and the regime-informed model, nor a condition-to-index reporting error. It is observed when correlation mode changes on the same decoder model and same paired samples. The prior independent pilot audit re-decoded all stored predictions; this audit separately reproduces residual counts from those saved predictions.

## Privileged regime-informed arm

The regime-informed arms use the generating noise regime and are a diagnostic, not a runtime policy. In the two same-name conditions they are exactly the pooled arms. In the other four conditions, regime-informed correlated minus pooled correlated errors were +84 (X-memory balanced), +2 (X-memory Z-biased), +28 (Z-memory X-biased), and +257 (Z-memory balanced). Thus regime matching did not reliably improve the correlated arm. The corresponding uncorrelated regime-informed differences were 0, −71, −73, and −16 errors.

The original pilot’s Holm-adjusted secondary comparisons found four of the 12 privileged contrasts below adjusted p=0.05: two helped the uncorrelated regime-informed arm (X-memory/Z-biased and Z-memory/X-biased), while two harmed the correlated regime-informed arm (both balanced cells). These remain secondary, privileged, and exploratory; they do not establish a deployable strategy.

## Interpretation limits

The same-name pattern is compatible with basis-dependent sensitivity to Pauli composition, but it is also compatible with distance-3 degeneracy, the DEM disjoint-event approximation, or sampling variation amplified by post-hoc subgrouping. Because the pilot records syndrome and observable outcomes rather than latent Pauli events or matching paths, it does not show which physical error component or correction chain produced the interaction. Six per-cell estimates also do not support a general law about X or Z memory.
