# Reproduce NS-2B Deterministic Validation

Run from the NS-2B worktree root with the repository's existing Python environment. No package installation is required or authorized by this report.

```powershell
python -m unittest dashboard.tests.test_sampling_model_identity_v2 dashboard.tests.test_circuit_identity_v1 dashboard.tests.test_core_system_v1
python -m unittest dashboard.tests.test_dashboard.ControlAndApiTests.test_loopback_ipv4_dashboard_health_and_control_routes dashboard.tests.test_dashboard.ControlAndApiTests.test_loopback_ipv6_websocket_and_health
python -m compileall -q qshift_core_v1 dashboard/tests/test_sampling_model_identity_v2.py
python outputs/core_system_upgrade_ns2b_v1/verify_manifest.py
```

The first focused command passed 62 tests; the dashboard smoke command passed 2. A broader combined command was also attempted:

```powershell
python -m unittest dashboard.tests.test_sampling_model_identity_v2 dashboard.tests.test_circuit_identity_v1 dashboard.tests.test_core_system_v1 dashboard.tests.test_dashboard
```

It ran 92 tests but errored in the existing `test_structured_api_uses_frozen_multiregime_allocation_and_keeps_test_reserved` because `dashboard.structured_training.load_prepared_freeze()` rejected `structured_diagnostic_config.json`. That test was not repaired or rebaselined. The same failure was subsequently reproduced on a clean detached worktree at accepted NS-1 base `e015a18e22de653b479cc206026d520e7dc71b5d` with:

```powershell
python -m unittest dashboard.tests.test_dashboard.ControlAndApiTests.test_structured_api_uses_frozen_multiregime_allocation_and_keeps_test_reserved -v
```

The failure is classified baseline-preexisting. See `NS2B_FAILURE_INVESTIGATION.md` and `NS2B_BASE_COMPARISON_TEST_RESULTS.txt` for details. It was not repaired or rebaselined.

The tests create deterministic Stim circuits and DEMs and decode fixed all-zero/all-pattern detector matrices. They do not invoke `compile_detector_sampler`, sample random shots, train, access protected outcome files, or benchmark decoding performance. The zero-syndrome PyMatching calls are deterministic interface checks, not an experiment.

Record environment with `python -c "import sys,stim,pymatching,numpy; print(sys.version); print('stim',stim.__version__); print('pymatching',pymatching.__version__); print('numpy',numpy.__version__)"`.

The engineering manifest is allowlisted and intentionally excludes itself. Recreate it only after the listed implementation, test, report, and test-output files are final by running `python outputs/core_system_upgrade_ns2b_v1/create_manifest.py`; verify with the command above. Do not change historical NS-1 manifests or records.

Build the explicit review ZIP, refusing to overwrite an existing destination:

```powershell
python outputs/core_system_upgrade_ns2b_v1/create_review_package.py --output "C:\Users\LENOVO\Documents\Codex\2026-11-12\QSHIFT_NS2B_Supervisor_Review.zip"
```
