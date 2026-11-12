# Reproduce NS-1 Circuit Identity Checks

Use the existing Q-SHIFT Python environment from the repository root. Do not install dependencies for this engineering check.

```powershell
python -m unittest dashboard.tests.test_circuit_identity_v1 -v
python -m unittest dashboard.tests.test_core_system_v1 -v
python -m unittest dashboard.tests.test_dashboard.SeedAndConfigTests dashboard.tests.test_dashboard.MetricAndStorageTests -v
python -m unittest dashboard.tests.test_dashboard.StructuredDecoderTests.test_qshift_stim_coordinates_make_expected_round_geometry dashboard.tests.test_dashboard.StructuredDecoderTests.test_residual_target_and_xor_correction_convention -v
python -m compileall -q qshift_core_v1 dashboard\tests\test_circuit_identity_v1.py outputs\core_system_upgrade_ns1_v1
python outputs\core_system_upgrade_ns1_v1\verify_manifest.py
```

The tests construct deterministic Stim circuit and DEM objects, then decode only an explicitly supplied all-zero syndrome for the dashboard regression. They do not call `compile_detector_sampler`, `sample`, training code, Stage 5 code, or protected evaluation paths. The dashboard regression may build its existing matching model; this is a deterministic graph construction, not a sampling benchmark.

The pre-incident `NS1_ENGINEERING_MANIFEST.json` is retained unchanged as a historical preparation snapshot. The post-incident allowlisted manifest is `NS1_ENGINEERING_MANIFEST_V2.json`; it records the scope deviation and does not assert complete protected-data non-access. After changing any listed NS-1 deliverable, regenerate and verify V2:

```powershell
python outputs\core_system_upgrade_ns1_v1\create_manifest.py
python outputs\core_system_upgrade_ns1_v1\verify_manifest.py
```

The manifest identifies this branch's source/docs and the immutable accepted v1.1 parent. It is not a scientific freeze and authorizes no experiment.
