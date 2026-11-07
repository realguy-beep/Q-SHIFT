# Compute and memory benchmark

The complete development run used 2,181,216 simulator shots and completed in 70.97 seconds. Calibration and independent development evaluation each used 900,000 shots. Template generation used 360,000 shots.

Peak resident memory was **not measured**: psutil was unavailable in the restricted environment. The configured 2 GiB memory cap therefore cannot be certified from this run. Compressed on-disk evidence occupied: raw bundles 11,118,967 bytes, templates 2,111,223 bytes, saved circuit/DEM models 7,945,462 bytes. These disk sizes are not substitutes for peak RAM.

Model construction took 2.949 s; templates 1.665 s; calibration 17.962 s; evaluation 17.685 s; saved-prediction re-decoding 14.455 s.

| Bank | Detectors | 1k-shot simulator s/shot | Mean candidate decoder s/shot | All-candidate decode seconds |
|---|---:|---:|---:|---:|
| native_d3_z | 24 | 1.19e-07 | 4.12e-07 | 0.003712 |
| native_d3_x | 24 | 1.06e-07 | 4.13e-07 | 0.003713 |
| native_d5_z | 120 | 3.04e-07 | 2.31e-06 | 0.02083 |
| native_d5_x | 120 | 3.21e-07 | 2.49e-06 | 0.02238 |
| native_d7_z | 336 | 7.74e-07 | 8.24e-06 | 0.07419 |
| native_d7_x | 336 | 8.01e-07 | 8.1e-06 | 0.07287 |
| pauli_biased_d3_z | 24 | 3.61e-07 | 6.41e-07 | 0.001922 |
| pauli_biased_d3_x | 24 | 3.45e-07 | 6.25e-07 | 0.001874 |
| pauli_biased_d5_z | 120 | 9.79e-07 | 3.88e-06 | 0.01163 |
| pauli_biased_d5_x | 120 | 9.72e-07 | 4.01e-06 | 0.01202 |
| pauli_biased_d7_z | 336 | 2.22e-06 | 1.26e-05 | 0.03767 |
| pauli_biased_d7_x | 336 | 2.27e-06 | 1.24e-05 | 0.0371 |

Benchmark rows use 1,000 paired shots per bank and decode all candidates. The aggregate run time includes model construction, sampling, decoding, independent recomputation and reporting; it is software simulation latency, not hardware latency. The measured forecast passed the 30-minute cap; actual wall time was about 71 seconds.
