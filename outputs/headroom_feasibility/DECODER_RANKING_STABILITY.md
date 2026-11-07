# Decoder ranking stability

All nine native or three Pauli-biased candidates are listed in RANKING_STABILITY.csv. Calibration bootstrap frequencies resample the five calibration roots within a regime (20,000 replicates); they are selection-stability summaries, not posterior probabilities. Evaluation root-best counts are retrospective diagnostics only and did not select a model.

Across 36 family×distance×basis×regime cells, calibration selected a different regime specialist than the pooled fixed decoder in 14; the selected specialist had lower LER on independent evaluation data in 7. Only 1 cells met every per-regime stability and practical-effect threshold before the stricter two-regime/two-distance replication requirement.
Across 702 evaluated regime-stratified candidate pairs, 95 had identical predictions on every paired shot; the maximum observed disagreement rate was 0.420%.

| Bank | Regime | Pooled fixed | Cal-selected specialist | Detector-fit | Specialist bootstrap frequency | Eval specialist errors | Pooled errors | Delta LER | Root-bootstrap 95% CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| native_d3_z | data_heavy | 1 | 3 | 6 | 0.738 | 189 | 203 | -0.00056 | [-0.00096, -0.00016] |
| native_d3_z | nominal | 1 | 2 | 4 | 0.859 | 65 | 67 | -8e-05 | [-0.00052, +0.00032] |
| native_d3_z | measurement_heavy | 1 | 2 | 2 | 0.966 | 33 | 38 | -0.0002 | [-0.00044, +4e-05] |
| native_d3_x | data_heavy | 2 | 6 | 6 | 0.670 | 215 | 213 | +8e-05 | [-0.00052, +0.00068] |
| native_d3_x | nominal | 2 | 2 | 4 | 0.721 | 79 | 79 | +0 | [+0, +0] |
| native_d3_x | measurement_heavy | 2 | 2 | 2 | 0.979 | 32 | 32 | +0 | [+0, +0] |
| native_d5_z | data_heavy | 5 | 5 | 6 | 0.630 | 175 | 175 | +0 | [+0, +0] |
| native_d5_z | nominal | 5 | 5 | 4 | 0.401 | 35 | 35 | +0 | [+0, +0] |
| native_d5_z | measurement_heavy | 5 | 0 | 2 | 0.639 | 6 | 5 | +4e-05 | [+0, +0.00012] |
| native_d5_x | data_heavy | 0 | 0 | 6 | 0.546 | 193 | 193 | +0 | [+0, +0] |
| native_d5_x | nominal | 0 | 0 | 4 | 1.000 | 36 | 36 | +0 | [+0, +0] |
| native_d5_x | measurement_heavy | 0 | 2 | 2 | 0.676 | 7 | 8 | -4e-05 | [-0.00012, +0] |
| native_d7_z | data_heavy | 0 | 0 | 6 | 0.829 | 107 | 107 | +0 | [+0, +0] |
| native_d7_z | nominal | 0 | 3 | 4 | 0.674 | 11 | 10 | +4e-05 | [+0, +0.00012] |
| native_d7_z | measurement_heavy | 0 | 0 | 2 | 1.000 | 0 | 0 | +0 | [+0, +0] |
| native_d7_x | data_heavy | 2 | 2 | 6 | 0.781 | 150 | 150 | +0 | [+0, +0] |
| native_d7_x | nominal | 2 | 5 | 4 | 0.566 | 14 | 12 | +8e-05 | [+0, +0.00024] |
| native_d7_x | measurement_heavy | 2 | 3 | 2 | 0.671 | 1 | 1 | +0 | [+0, +0] |
| pauli_biased_d3_z | x_biased | 2 | 0 | 0 | 0.909 | 82 | 76 | +0.00024 | [-4e-05, +0.00048] |
| pauli_biased_d3_z | balanced | 2 | 2 | 1 | 0.981 | 62 | 62 | +0 | [+0, +0] |
| pauli_biased_d3_z | z_biased | 2 | 2 | 2 | 0.897 | 31 | 31 | +0 | [+0, +0] |
| pauli_biased_d3_x | x_biased | 0 | 0 | 0 | 1.000 | 27 | 27 | +0 | [+0, +0] |
| pauli_biased_d3_x | balanced | 0 | 0 | 1 | 1.000 | 94 | 94 | +0 | [+0, +0] |
| pauli_biased_d3_x | z_biased | 0 | 0 | 2 | 0.852 | 103 | 103 | +0 | [+0, +0] |
| pauli_biased_d5_z | x_biased | 2 | 0 | 0 | 0.914 | 46 | 60 | -0.00056 | [-0.001, -4e-05] |
| pauli_biased_d5_z | balanced | 2 | 2 | 1 | 0.844 | 18 | 18 | +0 | [+0, +0] |
| pauli_biased_d5_z | z_biased | 2 | 2 | 2 | 0.671 | 2 | 2 | +0 | [+0, +0] |
| pauli_biased_d5_x | x_biased | 1 | 0 | 0 | 0.722 | 3 | 6 | -0.00012 | [-0.0002, -4e-05] |
| pauli_biased_d5_x | balanced | 1 | 1 | 1 | 0.871 | 39 | 39 | +0 | [+0, +0] |
| pauli_biased_d5_x | z_biased | 1 | 1 | 2 | 0.363 | 54 | 54 | +0 | [+0, +0] |
| pauli_biased_d7_z | x_biased | 0 | 0 | 0 | 0.851 | 18 | 18 | +0 | [+0, +0] |
| pauli_biased_d7_z | balanced | 0 | 0 | 1 | 0.906 | 4 | 4 | +0 | [+0, +0] |
| pauli_biased_d7_z | z_biased | 0 | 0 | 2 | 1.000 | 0 | 0 | +0 | [+0, +0] |
| pauli_biased_d7_x | x_biased | 2 | 0 | 0 | 1.000 | 2 | 1 | +4e-05 | [+0, +0.00012] |
| pauli_biased_d7_x | balanced | 2 | 0 | 1 | 0.608 | 5 | 6 | -4e-05 | [-0.00016, +8e-05] |
| pauli_biased_d7_x | z_biased | 2 | 2 | 2 | 0.560 | 27 | 27 | +0 | [+0, +0] |

A regime-specific choice differed from the pooled fixed choice in 14/36 cells; those selected choices had lower independent-evaluation LER in 7/36 cells. Only 1 individual regime cell met all per-regime stability and practical-effect thresholds. No same two-regime pair replicated across two distances, so the overall gate remained closed.

The complete candidate-by-candidate calibration LER, calibration root wins, bootstrap selection frequencies, pooled selection frequencies and evaluation root-best counts are in RANKING_STABILITY.csv. Test/evaluation data did not affect any selected decoder. Sparse error counts, zero-error strata, and only five roots per regime make these rankings exploratory and potentially unstable.
