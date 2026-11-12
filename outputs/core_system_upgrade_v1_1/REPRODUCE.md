# Reproduce Corrective Review v1.1

Run from `C:\Users\LENOVO\Documents\QSHIFT-Core-Upgrade` using the existing Python environment. These commands are deterministic and do not sample shots or access protected outcomes.

```powershell
python -m unittest dashboard.tests.test_core_system_v1 -v
python -m unittest dashboard.tests.test_dashboard.SeedAndConfigTests dashboard.tests.test_dashboard.MetricAndStorageTests -v
python -m unittest dashboard.tests.test_dashboard.StructuredDecoderTests.test_qshift_stim_coordinates_make_expected_round_geometry dashboard.tests.test_dashboard.StructuredDecoderTests.test_residual_target_and_xor_correction_convention -v
python -m compileall -q qshift_core_v1 dashboard\configuration.py dashboard\seed_protocol.py dashboard\simulator.py dashboard\tests\test_core_system_v1.py outputs\core_system_upgrade_v1_1
node --check dashboard\static\app.js
python -c "from html.parser import HTMLParser; from pathlib import Path; HTMLParser().feed(Path('dashboard/static/index.html').read_text(encoding='utf-8')); print('HTML parse: PASS')"
python outputs\core_system_upgrade_v1_1\audit_v2_4_hold.py
python outputs\core_system_upgrade_v1_1\create_manifest.py
python outputs\core_system_upgrade_v1_1\verify_manifest.py
```

The focused test suite builds small deterministic Stim DEM/circuit objects and decodes explicitly supplied detector arrays. It never calls `compile_detector_sampler` or samples data. Existing full dashboard test discovery is intentionally excluded because it includes sampling and training paths.

The V2.4 audit creates only `outputs/core_system_upgrade_v1_1/V2_4_HOLD_AUDIT.json`; it reads the V2.4 freeze and its listed file hashes plus Git base blobs. It does not access run outputs or outcome data. The v1 manifest is historical and is not rewritten; v1.1 has its own manifest and verifier.
