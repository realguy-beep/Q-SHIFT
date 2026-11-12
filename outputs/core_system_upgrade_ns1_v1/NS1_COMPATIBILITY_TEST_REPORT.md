# NS-1 Compatibility Test Report

## Scope

Deterministic construction and compatibility checks only. Tests build Stim circuits/DEMs and pass a supplied all-zero detector array to the existing dashboard PyMatching adapter. No Stim sampler, stochastic simulation, training, protected evaluation, or bulk decoder evaluation is called.

## Regression coverage

`dashboard/tests/test_circuit_identity_v1.py` covers:

- Reproducible circuit/DEM and identity digests; ordered detector IDs, coordinates, and time coordinates.
- Equal detector counts with changed circuit/DEM identity are rejected.
- A declared detector-column permutation and mismatched ordering fingerprint are rejected.
- Observable convention/dimension mismatch and an invalid decoder return type are rejected.
- Unknown required semantics remain explicit and prevent compatibility claims.
- A distance-5 model is not implicitly supported by a distance-3 candidate.
- A valid external spec decodes only detector bits and returns the expected prediction shape.
- The existing dashboard distance-3/five-round PyMatching preparation and supplied-syndrome decode still operate.

The existing `dashboard.tests.test_core_system_v1` suite separately preserves both explicit PyMatching correlation modes and the legacy Phase 2B adapter behavior.

## Commands

Run from repository root with the existing environment:

```powershell
python -m unittest dashboard.tests.test_circuit_identity_v1 -v
python -m unittest dashboard.tests.test_core_system_v1 -v
python -m unittest dashboard.tests.test_dashboard.SeedAndConfigTests dashboard.tests.test_dashboard.MetricAndStorageTests -v
python -m unittest dashboard.tests.test_dashboard.StructuredDecoderTests.test_qshift_stim_coordinates_make_expected_round_geometry dashboard.tests.test_dashboard.StructuredDecoderTests.test_residual_target_and_xor_correction_convention -v
python -m compileall -q qshift_core_v1 dashboard\tests\test_circuit_identity_v1.py outputs\core_system_upgrade_ns1_v1
```

No full test discovery is used because the repository contains tests that intentionally sample or train.

## Results

Final deterministic runs on Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, and NumPy 2.5.3:

- NS-1 compatibility tests: **11/11 passed**.
- Core v1.1 contract/regression tests: **35/35 passed**, including both explicit PyMatching correlation modes and legacy adapter shape/mode.
- Safe dashboard configuration/storage/telemetry tests: **11/11 passed**.
- Structured geometry and residual-XOR tests: **2/2 passed**.
- Python `compileall`: passed.
- Dashboard JavaScript `node --check`: passed.
- Dashboard HTML parser check: passed.

The dashboard compatibility test constructs the existing distance-3/five-round matching baseline and decodes one supplied all-zero `[1,40]` detector matrix; it does not sample. No test invokes the Stim sampler, trains a model, or reads protected outcomes. The safe dashboard tests emitted an existing Starlette/httpx deprecation warning; their assertions passed.

The historical v1.1 manifest verifier returned **FAIL** for four existing entries. For each, current worktree bytes equal the accepted base commit's Git blob, but differ from the old manifest's expected digest. The exact discrepancies are:

| File | Historical expected SHA-256 | Current bytes and base Git blob SHA-256 |
|---|---|---|
| `qshift_core_v1/controller.py` | `49e7987867324fe9b81c771ee78848c9be9863f3cedb4b98d2688faa31c94a08` | `b27bb76d59273fc1af06cb1c0db8bd545df21be6997c939ebfba9d540ef7bf90` |
| `qshift_core_v1/evaluation.py` | `a4de30fa858864fd7b66c693e921963b2d7011a633d186fc4ff76768bb7163e3` | `3012cd5822aa8b93f74b8b07f909aea60264278563fffc1a16b94d3df71c0c65` |
| `outputs/core_system_upgrade_v1_1/CORRECTIVE_REVIEW_REPORT.md` | `8e55b5c0339f8701528fcd6e3bef13d9f5d4c3027bd18287c48cfec4fcab373c` | `048f1decfac2ae50101ae10a4ca6bf4b2befbe52143d0acedfcf0fb85f46cf7b` |
| `outputs/core_system_upgrade_v1_1/V2_4_HOLD_AUDIT.json` | `22dccabcd80d98d0e1ba2d0c489803f4af194751fb4fc0f6ce226d3e19e16766` | `7b5ca864fd0f1c9921c3f1688d07ce67bb7a03aaabccb545b5f10110daaf87b1` |

The verifier separately reports the previously documented V2.4 state as HOLD with **13 expected-hash mismatches among 17** and confirms its recorded authorization flags remain false. No old manifest or audit was rewritten. NS-1 supplies a new manifest for the NS-1 source and documents this pre-existing integrity discrepancy; it does not make the historical v1.1 verifier pass.

Initial implementation checks found a test import-path issue, missing Stim coordinate tuples on a no-coordinate toy circuit, and the initial slice in the dashboard circuit's time coordinate. These were corrected according to the observed API semantics; the final commands above are green. No historical research evidence was involved.
