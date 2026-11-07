# Circuit and decoder preflight

All cells use Stim rotated surface-code memory circuits with rounds equal to distance. Noiseless samples use the identical circuit with noise instructions removed. Native DEMs use decomposed graph errors without approximate-disjoint conversion; Pauli categorical channels use approximate-disjoint conversion and correlated PyMatching.

| Bank | Detectors | Observables | Noiseless | Noise sensitivity |
|---|---:|---:|---|---|
| native_d3_z | 24 | 1 | 256 all-zero | 512 nonzero |
| native_d3_x | 24 | 1 | 256 all-zero | 512 nonzero |
| native_d5_z | 120 | 1 | 256 all-zero | 512 nonzero |
| native_d5_x | 120 | 1 | 256 all-zero | 512 nonzero |
| native_d7_z | 336 | 1 | 256 all-zero | 512 nonzero |
| native_d7_x | 336 | 1 | 256 all-zero | 512 nonzero |
| pauli_biased_d3_z | 24 | 1 | 256 all-zero | 512 nonzero |
| pauli_biased_d3_x | 24 | 1 | 256 all-zero | 512 nonzero |
| pauli_biased_d5_z | 120 | 1 | 256 all-zero | 512 nonzero |
| pauli_biased_d5_x | 120 | 1 | 256 all-zero | 512 nonzero |
| pauli_biased_d7_z | 336 | 1 | 256 all-zero | 512 nonzero |
| pauli_biased_d7_x | 336 | 1 | 256 all-zero | 512 nonzero |

Detector dimension formula: (d²−1)r, giving 24, 120 and 336 detectors for d=r=3,5,7. Every model has one logical fault ID and the same generated detector/observable definition within each bank. Candidate DEM, circuit and edge-weight hashes are in MODEL_INVENTORY.json. Noiseless behavior was checked with 256 shots per bank; noisy sensitivity with 512 per bank.

Noiseless and sensitivity preflights are diagnostics, not calibration or evaluation data. The circuit generator sets basis-appropriate measurement noise. The native and Pauli families are analyzed separately.
