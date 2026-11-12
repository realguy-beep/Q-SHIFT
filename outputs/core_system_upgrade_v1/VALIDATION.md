# Validation Record — Core System Upgrade v1

## Environment observed

- Python: 3.12.10 (C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe)
- Stim: 1.16.0
- PyMatching: 2.4.0
- NumPy: 2.5.3
- PyTorch: 2.14.1+cu126 (import/version check only; no model training or CUDA operation)

## Commands

Run from repository root:

    python -m unittest dashboard.tests.test_core_system_v1 -v
    python -m unittest dashboard.tests.test_dashboard.SeedAndConfigTests dashboard.tests.test_dashboard.MetricAndStorageTests -v
    python -m compileall -q qshift_core_v1 dashboard\configuration.py dashboard\simulator.py dashboard\tests\test_core_system_v1.py
    node --check dashboard\static\app.js

The final focused suite passed 26 deterministic tests. It constructs small Stim DEMs and PyMatching graphs and decodes explicitly supplied all-zero/one detector rows, including a zero-syndrome fixture on the actual configured Q-SHIFT DEM; it does not call a Stim sampler. The existing safe config/seed and metrics/storage classes passed 11 tests, and two selected geometry/XOR tests passed. The full dashboard suite was intentionally not run because several methods invoke Stim sampling, training or run generation.


## Test coverage

- Strict default, malformed, coercive, nonfinite and out-of-range configuration handling.
- Seed derivation determinism and duplicate detection.
- PyMatching 2.4.0 DEM construction and decode in both explicit correlation modes.
- Legacy dashboard decoder path with the Phase 2B correlation-enabled model and preserved one-dimensional return shape.
- Detector/output shape, binary-value and one-observable validation.
- Sampler input rejection before any sampler call; fake sampler failure context/cause; malformed fake output shape.
- Decoder registry, experimental opt-in, low-confidence/missing/unsupported fallback, noncausal rejection, hysteresis/dwell and estimated/configured-noise logging.
- Paired sample identity, label-after-decode scoring, error and discordance counts, and protected-test scope rejection.

## Non-executed validation

- No actual Stim sampling, training, full dashboard API run, GPU execution, large performance benchmark, Stage 5 execution, or hardware integration.
- Browser layout was not exercised; the UI change is a static explanatory note.
- Resource performance and end-to-end dashboard throughput were not benchmarked because this upgrade does not require a research run and no simulation authorization was given.

The engineering manifest verifier compares the 17 V2.4 freeze entries against their expected hashes and newline-normalized base-commit contents. It reports 13 pre-existing expected-hash mismatches and four matches; it does not call the historical expected-hash audit a pass. V2.4 remains HOLD.
