# Decoder disagreement patterns

## Counting definitions

For each paired test shot, `standard-only` means pooled correlation-disabled prediction is wrong while pooled correlation-enabled prediction is correct. `correlation-only` means the reverse. A prediction disagreement occurs when the two predicted observable-flip bits differ. With binary labels, each disagreement belongs to exactly one of the two failure directions.

| Condition | Paired prediction disagreements | Standard-only failures | Correlation-only failures | Net change in residual errors |
|---|---:|---:|---:|---:|
| X-memory / X-biased | 86 | 32 | 54 | +22 |
| X-memory / balanced | 386 | 242 | 144 | −98 |
| X-memory / Z-biased | 210 | 148 | 62 | −86 |
| Z-memory / X-biased | 204 | 129 | 75 | −54 |
| Z-memory / balanced | 319 | 172 | 147 | −25 |
| Z-memory / Z-biased | 138 | 40 | 98 | +58 |
| **Total** | **1,343** | **763** | **580** | **−183** |

The primary direction is determined by the imbalance between the two discordant failure counts, not by the number of changed predictions alone. The correlation-enabled arm changes only 0.1865% of pooled-fixed predictions overall; those changes are sparse but materially determine the net result.

## Root-level consistency

| Condition | Roots where correlation helps | Roots where it harms | Ties | Paired LER difference | Root-bootstrap 95% interval |
|---|---:|---:|---:|---:|---:|
| X-memory / X-biased | 1 | 9 | 2 | +0.000183 | [+0.000033, +0.000317] |
| X-memory / balanced | 11 | 1 | 0 | −0.000817 | [−0.001225, −0.000450] |
| X-memory / Z-biased | 12 | 0 | 0 | −0.000717 | [−0.000892, −0.000533] |
| Z-memory / X-biased | 9 | 1 | 2 | −0.000450 | [−0.000650, −0.000250] |
| Z-memory / balanced | 8 | 3 | 1 | −0.000208 | [−0.000425, 0.000000] |
| Z-memory / Z-biased | 1 | 11 | 0 | +0.000483 | [+0.000317, +0.000642] |

Direction is consistent across most roots in all six cells, but there are only 12 roots per cell. These post-hoc cell intervals are unadjusted for six-way interpretation and should not be treated as independent confirmatory tests.

## Detector-only summaries

The 1,343 changed-prediction shots had mean syndrome weight **5.13** of 40 detector bits, compared with **0.96** across all 720,000 shots. The mean round-coordinate trigger counts among disagreement shots were 0.19, 0.97, 1.15, 1.22, 1.29, and 0.31 at detector coordinate times 0 through 5, respectively. A five-round Stim memory circuit has detector coordinates at times 0–5: the two boundary slices each have four detectors and interior slices each have eight.

Standard-only failures had mean syndrome weight 5.25, while correlation-only failures averaged 4.98. Their detector-time profiles are close and vary by condition. Both failure directions tend to have boundary triggers compared with all shots. This descriptive summary does not establish a syndrome feature that predicts when the correlation-enabled correction helps; the feature was computed after seeing the same test outcomes and no multiplicity-adjusted classifier analysis was predeclared.

Across the six conditions, 1,137 distinct packed detector signatures occurred among disagreement shots. Only 33 signatures were observed with both failure directions across repeated occurrences. The result is consistent with a small set of syndrome-specific correction changes, but the same detector signature can still accompany different hidden fault histories and logical outcomes.

## What is not in the evidence

The checkpoints preserve detector bits, observable labels, and predicted logical flips, not the latent gate-level Pauli event, matching path, chosen edge set, or correlation-group attribution. Therefore we cannot say that a specific two-qubit Pauli event or a named DEM separator caused any particular standard-only or correlation-only failure. Such attribution requires new instrumentation or a decoder/reference model that outputs auditable path information; it cannot be recovered from these arrays alone.

Derived machine-readable details are in `DISAGREEMENT_FEATURES.csv`, `STRATUM_METRICS.csv`, and `ROOT_METRICS.csv`.
