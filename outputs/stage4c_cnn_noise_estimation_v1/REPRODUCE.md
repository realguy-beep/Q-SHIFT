# Stage 4C reproduction

Run from the Q-SHIFT repository root with the installed environment that provides Stim, PyMatching, NumPy, PyTorch, and psutil.

```powershell
python outputs/stage4c_cnn_noise_estimation_v1/prepare_inventory.py
python -m unittest outputs.stage4c_cnn_noise_estimation_v1.tests.test_models -v
python outputs/stage4c_cnn_noise_estimation_v1/build_freeze.py --write
python outputs/stage4c_cnn_noise_estimation_v1/build_freeze.py --verify
python -m outputs.stage4c_cnn_noise_estimation_v1.experiment --run
python -m outputs.stage4c_cnn_noise_estimation_v1.analysis
python -m outputs.stage4c_cnn_noise_estimation_v1.audit_results
python outputs/stage4c_cnn_noise_estimation_v1/build_manifest.py
```

`prepare_inventory.py` reads only the explicitly enumerated development seed metadata in its own source. It does not search for independent-test paths. The experiment runner verifies the frozen file hashes before data generation. `analysis.py` aggregates development results; `audit_results.py` independently re-estimates p, rebuilds all decoders, and verifies stored predictions from the raw calibration/evaluation arrays. The `run/` folder contains local ignored `.npz` arrays and model weights; preserve it for reproduction. The audit never imports the runner's result counters. Do not run the experiment command again after status is complete.
