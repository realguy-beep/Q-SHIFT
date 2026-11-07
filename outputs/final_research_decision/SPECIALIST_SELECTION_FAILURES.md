# Specialist-selection outcomes and failure modes

## Recomputed selections

Each regime specialist was selected by minimum calibration LER; pooled fixed was selected by minimum equal-weight mean calibration LER over the three regimes. Evaluation labels were not used for selection. Each table row compares the selected specialist with that bank's pooled fixed decoder on the same 25,000 evaluation shots. The interval is a descriptive bootstrap over five independent evaluation roots.

| Bank | Regime | Specialist index / parameters | Pooled index / parameters | Calibration choice frequency | Eval errors specialist / pooled | Specialist-only / pooled-only errors | Root wins-losses-ties | Δ LER | Root-bootstrap 95% CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| native d3 Z | data-heavy | 3 (0.003, 0.001) | 1 (0.001, 0.003) | .738 | 189 / 203 | 23 / 37 | 4-0-1 | −0.000560 | [−0.000960, −0.000160] |
| native d3 Z | nominal | 2 (0.001, 0.006) | 1 (0.001, 0.003) | .859 | 65 / 67 | 11 / 13 | 2-2-1 | −0.000080 | [−0.000520, +0.000320] |
| native d3 Z | measurement-heavy | 2 (0.001, 0.006) | 1 (0.001, 0.003) | .966 | 33 / 38 | 1 / 6 | 4-1-0 | −0.000200 | [−0.000440, +0.000040] |
| native d3 X | data-heavy | 6 (0.006, 0.001) | 2 (0.001, 0.006) | .670 | 215 / 213 | 42 / 40 | 2-3-0 | +0.000080 | [−0.000520, +0.000680] |
| native d5 Z | measurement-heavy | 0 (0.001, 0.001) | 5 (0.003, 0.006) | .639 | 6 / 5 | 1 / 0 | 0-1-4 | +0.000040 | [+0.000000, +0.000120] |
| native d5 X | measurement-heavy | 2 (0.001, 0.006) | 0 (0.001, 0.001) | .676 | 7 / 8 | 0 / 1 | 1-0-4 | −0.000040 | [−0.000120, +0.000000] |
| native d7 Z | nominal | 3 (0.003, 0.001) | 0 (0.001, 0.001) | .674 | 11 / 10 | 3 / 2 | 0-1-4 | +0.000040 | [+0.000000, +0.000120] |
| native d7 X | nominal | 5 (0.003, 0.006) | 2 (0.001, 0.006) | .566 | 14 / 12 | 3 / 1 | 0-1-4 | +0.000080 | [+0.000000, +0.000240] |
| native d7 X | measurement-heavy | 3 (0.003, 0.001) | 2 (0.001, 0.006) | .671 | 1 / 1 | 0 / 0 | 0-0-5 | +0.000000 | [+0.000000, +0.000000] |
| Pauli d3 Z | X-biased | 0 (X-biased) | 2 (Z-biased) | .909 | 82 / 76 | 12 / 6 | 1-3-1 | +0.000240 | [−0.000040, +0.000480] |
| Pauli d5 Z | X-biased | 0 (X-biased) | 2 (Z-biased) | .914 | 46 / 60 | 6 / 20 | 4-1-0 | −0.000560 | [−0.001000, −0.000040] |
| Pauli d5 X | X-biased | 0 (X-biased) | 1 (balanced) | .722 | 3 / 6 | 0 / 3 | 3-0-2 | −0.000120 | [−0.000200, −0.000040] |
| Pauli d7 X | X-biased | 0 (X-biased) | 2 (Z-biased) | 1.000 | 2 / 1 | 1 / 0 | 0-1-4 | +0.000040 | [+0.000000, +0.000120] |
| Pauli d7 X | balanced | 0 (X-biased) | 2 (Z-biased) | .608 | 5 / 6 | 2 / 3 | 2-1-2 | −0.000040 | [−0.000160, +0.000080] |

Native parameter pairs are (gate probability, measurement probability). The full machine-readable version is `SPECIALIST_SELECTIONS_RECOMPUTED.csv`.

## Why only seven of fourteen improved

The recomputation gives seven lower evaluation LERs, six higher LERs and one tie among the 14 changed selections. Across those 14 paired comparisons, specialist-only failures total 105 and pooled-only failures total 132, over 350,000 shots. This is a descriptive net difference of 27 errors, not a predeclared pooled estimand or a significance claim.

The data support several explanations, but not a single causal explanation:

1. **Weak output headroom.** Across all 702 candidate pairs, 95 were prediction-identical on the finite evaluation samples; the overall maximum disagreement was 0.42%. Among the 14 changed selections, one produced no prediction disagreements at all. In many distance-5/7 cells only one to fourteen logical errors occurred per 25,000 shots.
2. **Calibration selection variability.** Calibration used five roots per regime. A leave-one-root-out recomputation retained the full calibration specialist in all five omissions for only 20/36 regime cells; the pooled choice remained in all five omissions for 6/12 banks. Bootstrap selection frequencies are conditional summaries of those five observed roots, not probabilities that a decoder is truly optimal.
3. **Sampling uncertainty in evaluation.** Several deltas are only one or two errors per 25,000 shots; most root-bootstrap intervals cross or touch zero. The one cell with a consistently negative interval does not repeat across another regime and distance.
4. **A stronger baseline.** Pooled fixed is selected using all three calibration regimes, so it already captures common weight improvements. A regime specialist must add reliable utility beyond that selected baseline, which these data rarely demonstrate.

Thus the six worse and one tied changed selections are consistent with a combination of finite calibration/evaluation noise and sparse decision differences. The study does not identify the fraction attributable to each mechanism. A high calibration bootstrap frequency did not guarantee evaluation improvement (for example, the Pauli d3 Z-memory X-biased specialist had .909 selection frequency but higher observed evaluation LER with an interval crossing zero).
