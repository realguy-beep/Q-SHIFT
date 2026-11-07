# Cross-distance stability of decoder utility

## Calibration-selected index patterns

The lists show specialist indices in generating-regime order. Native indices follow the frozen 3×3 (gate, measurement) grid; Pauli indices are X-biased=0, balanced=1, Z-biased=2. “Numeric-pass regimes” have each passed the calibration-frequency, practical LER, root-win and interval conditions, but still need a second distinct regime and a repeated distance.

| Family / memory | Distance | Pooled fixed | Regime specialist indices | Numeric-pass regimes |
|---|---:|---:|---|---|
| Native Z | 3 | 1 | data 3, nominal 2, measurement 2 | — |
| Native Z | 5 | 5 | data 5, nominal 5, measurement 0 | — |
| Native Z | 7 | 0 | data 0, nominal 3, measurement 0 | — |
| Native X | 3 | 2 | data 6, nominal 2, measurement 2 | — |
| Native X | 5 | 0 | data 0, nominal 0, measurement 2 | — |
| Native X | 7 | 2 | data 2, nominal 5, measurement 3 | — |
| Pauli-biased Z | 3 | 2 | X 0, balanced 2, Z 2 | — |
| Pauli-biased Z | 5 | 2 | X 0, balanced 2, Z 2 | X-biased only |
| Pauli-biased Z | 7 | 0 | X 0, balanced 0, Z 0 | — |
| Pauli-biased X | 3 | 0 | X 0, balanced 0, Z 0 | — |
| Pauli-biased X | 5 | 1 | X 0, balanced 1, Z 1 | — |
| Pauli-biased X | 7 | 2 | X 0, balanced 0, Z 2 | — |

## Gate result

No family/memory basis passes. All native bank strata have zero regimes meeting every numeric condition. The single qualifying regime cell is Pauli-biased Z-memory at distance 5 under X-biased generating noise: candidate 0 is selected versus pooled candidate 2, with 46 versus 60 errors, 6 specialist-only versus 20 pooled-only failures, 4/5 roots favoring the specialist, calibration selection frequency 0.914, and root-bootstrap 95% interval [−0.00100, −0.00004].

That isolated result does not meet the gate: the balanced and Z-biased regimes select the pooled candidate, so a second distinct specialist is absent. At distance 3, the X-biased selection is worse (82 versus 76 errors; interval crosses zero). At distance 7, the pooled choice is candidate 0, the same as the X-biased specialist. Thus the one favorable distance does not extend to a replicated two-regime pair at a second distance.

Across the native banks, selected index patterns change substantially with distance and memory basis; that is not evidence of stable specialization because evaluation effects are mostly zero, weak, or uncertain. Several distance-7 regimes have zero to a few failures among 25,000 shots, limiting resolution. The five-root calibration and five-root evaluation design is adequate for a bounded feasibility screen, not a strong claim about small utility differences or scaling with code distance.

The prespecified result is **NO-GO** for the tested bank. The criterion was a development gate, not a multiplicity-adjusted hypothesis test; no confirmatory samples or power analysis followed it. Machine-readable cell details are in `CROSS_DISTANCE_ELIGIBILITY.csv` and `INDEPENDENT_RECOMPUTATION.json`.
