# Correlated decoder feasibility v1

This isolated development package tests one synthetic per-round three-qubit X common-cause factor on the existing distance-3, five-round rotated Z-memory Stim circuit. It is not hardware-calibrated and does not access sealed or Stage 5 evidence.

## Reproduction

Use the already installed Python 3.12.10 environment with Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3 and psutil 7.2.2. No dependencies are installed by this package.

Sampler-free checks:

```powershell
python outputs/qshift_correlated_decoder_feasibility_v1/prepare_seed_inventory.py
python outputs/qshift_correlated_decoder_feasibility_v1/freeze_pretest.py
python -m unittest discover -s outputs/qshift_correlated_decoder_feasibility_v1/tests -v
python outputs/qshift_correlated_decoder_feasibility_v1/run_pilot.py --dry-run
python outputs/qshift_correlated_decoder_feasibility_v1/run_watchdog.py
```

The only sampling entry point is the frozen, explicit Windows command:

```powershell
python outputs/qshift_correlated_decoder_feasibility_v1/run_watchdog.py --execute --expected-head <FROZEN_COMMIT_SHA>
```

It refuses a dirty checkout, wrong branch, missing/mismatched pretest freeze, wrong runtime, or an existing attempt directory. It creates `pilot_runs/attempt_001` once and never automatically resumes or repeats it. The watchdog kills the Python process tree at 600 seconds using Windows `taskkill /T /F`; if termination cannot be confirmed, it exits as a failure. The runner also checks elapsed time at safe boundaries.

Raw arrays and run artifacts are local and ignored. The committed result package contains aggregate paired results and archive hashes, not the raw detector/observable arrays.

## Interpretation limits

A is one globally fixed q-calibrated PyMatching decoder. A2 and B use the same per-root calibration estimate; B enumerates 32 explicit burst-factor subsets and uses background PyMatching residual costs. This hybrid is not exact full-circuit maximum likelihood. C receives the true generating q and is privileged. Ten roots per condition and a percentile root bootstrap are only exploratory. The common-cause model is synthetic, and no hardware or generalization claim follows.
