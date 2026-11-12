# Reproduce Core System Upgrade v1 Checks

Run from the repository root in the existing Q-SHIFT Python environment. No dependency installation is needed for these commands.

    python -m unittest dashboard.tests.test_core_system_v1 -v
    python -m unittest dashboard.tests.test_dashboard.SeedAndConfigTests dashboard.tests.test_dashboard.MetricAndStorageTests -v
    python -m unittest dashboard.tests.test_dashboard.StructuredDecoderTests.test_qshift_stim_coordinates_make_expected_round_geometry dashboard.tests.test_dashboard.StructuredDecoderTests.test_residual_target_and_xor_correction_convention -v
    python -m compileall -q qshift_core_v1 dashboard\configuration.py dashboard\simulator.py dashboard\tests\test_core_system_v1.py
    node --check dashboard\static\app.js
    python outputs\core_system_upgrade_v1\verify_manifest.py


The focused 26-test suite constructs deterministic DEM fixtures and explicitly supplied detector arrays. It also constructs the actual configured circuit/DEM and decodes a manually supplied zero syndrome; this is not a Stim sampling command. Do not run python -m unittest discover -s dashboard\tests -v as part of this engineering check unless separately prepared to run all local dashboard tests; that suite includes sampler/training tests.

To verify the PyMatching version independently without any sampling:

    python -c "import pymatching, stim; print('Stim', stim.__version__, 'PyMatching', pymatching.__version__)"

The integration wrapper in dashboard/simulator.py is exercised by test_legacy_dashboard_decode_preserves_one_observable_shape_and_mode; that test creates a tiny DEM and supplies zero detector rows directly to decode_batch. It never invokes compile_detector_sampler.

The verifier reports the historical V2.4 expected-hash discrepancy separately from this engineering manifest result. A passing engineering check is not V2.4 freeze validation: 13 of 17 expected hashes were already inconsistent with the base-commit files. It also checks newline-normalized content against base and confirms all V2.4 authorization flags remain false.
