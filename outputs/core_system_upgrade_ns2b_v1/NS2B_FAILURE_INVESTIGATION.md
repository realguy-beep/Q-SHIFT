# NS-2B Broader-Suite Failure Investigation

## Finding

**Classification: BASELINE-PREEXISTING.** The single failure in the earlier 92-test combined run was reproduced by running the failing test directly on a clean detached worktree at accepted NS-1 base `e015a18e22de653b479cc206026d520e7dc71b5d`, using the same installed Windows Python environment. The exception and failing artifact were identical.

## Exact commands and outputs

NS-2B combined run:

```powershell
python -m unittest dashboard.tests.test_sampling_model_identity_v2 dashboard.tests.test_circuit_identity_v1 dashboard.tests.test_core_system_v1 dashboard.tests.test_dashboard
```

Result: 92 tests; 91 passed and one errored. The error was:

```text
RuntimeError: Prepared protocol integrity check failed: structured_diagnostic_config.json
fastapi.exceptions.HTTPException: 409: Prepared protocol integrity check failed: structured_diagnostic_config.json
```

The complete output is preserved in `NS2B_TEST_RESULTS.txt`.

Reproduction on a temporary clean detached worktree at the accepted base:

```powershell
python -m unittest dashboard.tests.test_dashboard.ControlAndApiTests.test_structured_api_uses_frozen_multiregime_allocation_and_keeps_test_reserved -v
```

Result: one test, one error, with the same `structured_diagnostic_config.json` integrity exception. The exact output is in `NS2B_BASE_COMPARISON_TEST_RESULTS.txt`. The temporary worktree was clean after the test and was removed without force.

## Integrity check detail

`dashboard/structured_training.py:335-345` loads the prepared configuration, inventory, and freeze. At lines 339-342 it compares the config hash first, then the inventory hash. The recorded/current SHA-256 values in the accepted-base checkout were:

| File | Freeze expected SHA-256 | Current SHA-256 | Result |
|---|---|---|---|
| `outputs/neural_decoder_diagnostic/structured_diagnostic_config.json` | `1ef0e84b7a2ede6968e6e09f3f8095dd1413b52d7a5142d410afff1d0e975799` | `35ea9d9b9c5031f624f4fee5c5796afa4ce1c2c322f7694854d59f3ad2d7d7b0` | mismatch |
| `outputs/neural_decoder_diagnostic/structured_seed_inventory.json` | `ce044c465f9dea959f4b5c34f92fc256433b224d2bfc3f76f9a2e040a7eaec7d` | `559cca69f74a847aa6c4096e2935b39a519575f53118cfe9080ce5d22025db58` | mismatch |

The config mismatch is encountered first; the inventory mismatch is independently visible in the same check order but is not the exception raised by this test. No file was changed, repaired, rehashed, or rebaselined.

## Why this is not an NS-2B regression

The failing route calls `load_prepared_freeze()` at `dashboard/app.py:413-414`, before seed screening, run-directory creation, worker launch, or any sampling. The same accepted-base code and the same tracked prepared files fail the identical check. NS-2B changed only core identity/contract code, its tests, and its new versioned documentation; it did not change `dashboard/app.py`, `dashboard/structured_training.py`, the prepared config/inventory, or the freeze.

## Integrity and safety

- Reproduction used a clean detached base worktree; status was clean afterward.
- The reproduction was deterministic and did not invoke a Stim sampler or worker.
- No training, scientific experiment, protected Stage 5 outcome access, or freeze modification occurred.
- The mismatch is retained as a historical integrity failure; this investigation does not make the structured-training endpoint pass.
- The environment used Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, FastAPI 0.162.0, and Starlette 1.10.0.

The failure is classified baseline-preexisting in this tested environment. This does not establish behavior under other Python environments or alter the historical scientific status of the prepared training freeze.
