# Paired utility analysis

Across 36 family×distance×basis×regime cells, calibration selected a specialist different from pooled fixed in 14; these choices improved independent evaluation LER in 7 cells. Only 1 individual regime cell met every per-regime gate threshold, and no repeated two-regime/two-distance pattern passed.

Each evaluation root stores one packed detector matrix, one observable vector and all bank predictions. Residual indicators are recomputed as logical observable XOR prediction. Candidate and pooled outcomes are paired shot by shot. Root bootstrap resamples the five independent evaluation-root differences; these intervals are descriptive feasibility estimates, not confirmatory inference.

| Bank | Regime | Specialist | Pooled | Specialist errors | Pooled errors | Candidate-only | Pooled-only | Delta LER | Relative reduction | Root 95% CI | Candidate disagreement |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| native_d3_z | data_heavy | 3 | 1 | 189 | 203 | 23 | 37 | -0.00056 | +6.90% | [-0.00096, -0.00016] | 0.2400% |
| native_d3_z | nominal | 2 | 1 | 65 | 67 | 11 | 13 | -8e-05 | +2.99% | [-0.00052, +0.00032] | 0.0960% |
| native_d3_z | measurement_heavy | 2 | 1 | 33 | 38 | 1 | 6 | -0.0002 | +13.16% | [-0.00044, +4e-05] | 0.0280% |
| native_d3_x | data_heavy | 6 | 2 | 215 | 213 | 42 | 40 | +8e-05 | -0.94% | [-0.00052, +0.00068] | 0.3280% |
| native_d3_x | nominal | 2 | 2 | 79 | 79 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| native_d3_x | measurement_heavy | 2 | 2 | 32 | 32 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| native_d5_z | data_heavy | 5 | 5 | 175 | 175 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| native_d5_z | nominal | 5 | 5 | 35 | 35 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| native_d5_z | measurement_heavy | 0 | 5 | 6 | 5 | 1 | 0 | +4e-05 | -20.00% | [+0, +0.00012] | 0.0040% |
| native_d5_x | data_heavy | 0 | 0 | 193 | 193 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| native_d5_x | nominal | 0 | 0 | 36 | 36 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| native_d5_x | measurement_heavy | 2 | 0 | 7 | 8 | 0 | 1 | -4e-05 | +12.50% | [-0.00012, +0] | 0.0040% |
| native_d7_z | data_heavy | 0 | 0 | 107 | 107 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| native_d7_z | nominal | 3 | 0 | 11 | 10 | 3 | 2 | +4e-05 | -10.00% | [+0, +0.00012] | 0.0200% |
| native_d7_z | measurement_heavy | 0 | 0 | 0 | 0 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| native_d7_x | data_heavy | 2 | 2 | 150 | 150 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| native_d7_x | nominal | 5 | 2 | 14 | 12 | 3 | 1 | +8e-05 | -16.67% | [+0, +0.00024] | 0.0160% |
| native_d7_x | measurement_heavy | 3 | 2 | 1 | 1 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d3_z | x_biased | 0 | 2 | 82 | 76 | 12 | 6 | +0.00024 | -7.89% | [-4e-05, +0.00048] | 0.0720% |
| pauli_biased_d3_z | balanced | 2 | 2 | 62 | 62 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d3_z | z_biased | 2 | 2 | 31 | 31 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d3_x | x_biased | 0 | 0 | 27 | 27 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d3_x | balanced | 0 | 0 | 94 | 94 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d3_x | z_biased | 0 | 0 | 103 | 103 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d5_z | x_biased | 0 | 2 | 46 | 60 | 6 | 20 | -0.00056 | +23.33% | [-0.001, -4e-05] | 0.1040% |
| pauli_biased_d5_z | balanced | 2 | 2 | 18 | 18 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d5_z | z_biased | 2 | 2 | 2 | 2 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d5_x | x_biased | 0 | 1 | 3 | 6 | 0 | 3 | -0.00012 | +50.00% | [-0.0002, -4e-05] | 0.0120% |
| pauli_biased_d5_x | balanced | 1 | 1 | 39 | 39 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d5_x | z_biased | 1 | 1 | 54 | 54 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d7_z | x_biased | 0 | 0 | 18 | 18 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d7_z | balanced | 0 | 0 | 4 | 4 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d7_z | z_biased | 0 | 0 | 0 | 0 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |
| pauli_biased_d7_x | x_biased | 0 | 2 | 2 | 1 | 1 | 0 | +4e-05 | -100.00% | [+0, +0.00012] | 0.0040% |
| pauli_biased_d7_x | balanced | 0 | 2 | 5 | 6 | 2 | 3 | -4e-05 | +16.67% | [-0.00016, +8e-05] | 0.0200% |
| pauli_biased_d7_x | z_biased | 2 | 2 | 27 | 27 | 0 | 0 | +0 | +0.00% | [+0, +0] | 0.0000% |

Positive delta means the regime specialist is worse. Candidate-only is specialist wrong / pooled correct; pooled-only is the reverse. Decoder disagreement is not error improvement. Per-root paired observations are in PER_ROOT_UTILITY.csv; all candidate-pair disagreement counts are in DECODER_DISAGREEMENT.csv.

## Prespecified gate result

Gate passed: **False**. No useful regime-dependent utility headroom was established under the prespecified development gate.

No evaluation-label winner or retrospective oracle contributes to this decision.


In the full paired disagreement matrix, 95/702 candidate pairs were exactly prediction-equivalent on evaluated shots; the largest observed pairwise disagreement rate was 0.420%. Prediction differences were sparse and did not by themselves imply lower logical error.