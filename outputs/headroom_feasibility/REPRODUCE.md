# Reproduce the headroom feasibility pilot

Run from the repository workspace:

    python -m unittest discover -s outputs/headroom_feasibility -p test_headroom_unittest.py -v
    python outputs/headroom_feasibility/run_pilot.py

The legacy pytest-form test file is retained, but pytest could not be installed in the restricted network environment used for this run; the standard-library unittest suite exercises the same core checks.

The runner refuses to overwrite FREEZE.json. It writes the prospective freeze and machine-readable seed inventory before diagnostics, templates, calibration or evaluation. Calibration and evaluation arrays are saved as atomic compressed NPZ bundles under raw/; templates are under templates/. Evaluation predictions are independently re-decoded from packed saved detectors before aggregate metrics are accepted.

Environment observed for this run: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3. Optional psutil is used for process RSS; if unavailable, memory is reported as unavailable rather than fabricated.

All evidence is development-only. The code does not sample final confirmatory data or test adaptive switching.
