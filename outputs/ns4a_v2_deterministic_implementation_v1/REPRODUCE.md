# Reproduce the deterministic NS-4A V2 checks

This package is deterministic-only. It contains no production runner, no numeric production seed inventory, and no callable sampling path. `activate_sampling()` intentionally raises `SamplingNotAuthorized`.

## Environment

Use the already-created isolated environment matching `../ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt`. The tested environment reported Python 3.12.10, NumPy 2.2.6, SciPy 1.18.1, pytest 9.2.0, Stim 1.16.0, and PyMatching 2.4.0. Tests use NumPy/SciPy and the deterministic Q-SHIFT core contract; no Stim sampler, circuit generation, PyMatching decoder construction, or scientific outcomes are used.

## Windows PowerShell

From the repository root:

```powershell
$py = '<path-to-lock-matched-venv>\Scripts\python.exe'
$env:PYTHONPATH = (Get-Location).Path
& $py -m pytest -q outputs/ns4a_v2_deterministic_implementation_v1/tests
& $py -m compileall -q outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic outputs/ns4a_v2_deterministic_implementation_v1/tests
& $py outputs/ns4a_v2_deterministic_implementation_v1/verify_source_manifest.py
```

Replace only the environment path with the location of the existing approved virtual environment. Do not install or update dependencies for this package.

## Scope and seed note

Bootstrap/sign-flip unit tests use fixed test-only NumPy generator seeds. The fixture inventory in tests is generated from small literal integers solely to test collision detection; it is not written as a production seed inventory or provided to a sampler. `seed_inventory_template.json` contains no numeric values and reports historical collision screening as incomplete. No scientific experiment was run.

## Expected result

The deterministic test suite should report 24 passing tests. The verifier should report all manifest-listed hashes match. Neither command creates experiment arrays, Stim detector events, evaluation labels, nor a freeze/authorization record.
