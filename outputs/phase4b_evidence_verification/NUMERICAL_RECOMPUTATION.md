# Numerical recomputation

`verify_phase4b.py` independently loaded all 20 test NPZ files with `allow_pickle=False`. It computed residual = observable XOR prediction for every shot. It did not import runner/reporting code or trust the aggregate.

600,000 shots: fixed 1,165; calibrated 1,008; candidate-only 99; fixed-only 256; disagreements 355. Exact two-sided McNemar p=3.730722857432864e-17. Seed bootstrap 95% CI [-0.000331667,-0.000200000] rate; calibrated wins/losses/ties = 20/0/0. JSON, CSV per-seed rows, and manifest all reconcile. Calibration recovered 20/20.
