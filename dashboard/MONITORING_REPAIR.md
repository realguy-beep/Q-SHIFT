# Dashboard monitoring repair

## Diagnosis

The dashboard had three related progress failures. First, the WebSocket handler read a run snapshot before subscribing to worker events, leaving a window where an event could be persisted but missed by the initial snapshot and live stream. Second, the frontend depended on the WebSocket after page load and had no persisted-progress polling fallback, so a broken or stalled socket left stale values until refresh. Third, the workers did not report a consistent completed-shot count: the legacy worker counted generated rows as completed, while structured-training callbacks emitted sparse fields without an ETA. GPU telemetry also described the host GPU even for CPU or completed runs.

No pre-existing server log files, active worker processes, or saved browser logs were present in this worktree at inspection time. Worker stdout/stderr is now retained at `dashboard/run_data/runs/<run-id>/worker.log`, including non-JSON tracebacks; UI/API errors include the persisted failure detail.

## Changes

- Subscribe to the WebSocket event queue before fetching the initial snapshot.
- Add a read-only persisted progress endpoint at `GET /api/runs/{run_id}/progress` and poll it every 2.5 seconds while a run is active. Poll updates also feed the learning/throughput charts, so the display can recover after refreshes or socket interruptions.
- Define completed shots as rows that have completed the relevant worker processing. Report generated shots separately. Derive progress, throughput, and ETA from measured counters and elapsed time; unavailable values remain blank.
- Report simulation, decoding, and analysis counters where workers have them. Calibration is explicitly shown as “Not reported” because these dashboard workers do not expose a separate calibration stage.
- Show host CPU/RAM telemetry continuously, but show GPU utilization/VRAM/temperature/power only for a currently running job whose worker reports actual CUDA training. CPU and completed runs cannot inherit current host GPU readings.
- Persist worker output and show failed, cancelled/stopped, paused, and interrupted states with available errors.

## Verification

Commands run from the repository root:

```powershell
python -m py_compile dashboard/app.py dashboard/storage.py dashboard/manager.py dashboard/worker.py dashboard/structured_training.py
node --test dashboard/tests/monitoring_ui.test.cjs
python -m unittest dashboard.tests.test_dashboard -v
python -m unittest dashboard.tests.test_monitoring_integration -v
```

The real bounded integration run used a fresh CPU Stim/PyMatching worker through the dashboard's `/api/runs` job API: 4,096 training + 1,024 validation + 1,024 test shots. A WebSocket attached during execution received live measured progress frames. Worker events were persisted in SQLite and `worker.log`; the final snapshot reported 6,144/6,144 completed shots, 100%, positive measured throughput, and an ETA field. The test verified simulation/validation, decoding/validation, training, simulation/test, decoding/test, analysis, terminal `completed` status, and the persisted `GET /progress` snapshot. Its temporary database and run files were removed with the test's temporary directory.

The 5 Node frontend tests passed. The focused API/WebSocket persistence tests and traceback-log regression passed. The real Stim/PyMatching integration test passed. Python compilation passed. The full `test_dashboard.py` suite ran 33 tests: 32 passed and one unrelated existing structured-protocol test errored because `load_prepared_freeze()` rejects the historical `structured_diagnostic_config.json` hash. The same integrity failure was present in the pre-repair suite. No frozen protocol or evidence was changed to work around that mismatch.

The tests exercise the production UI progress-normalization module and its API wiring, but do not automate a visible browser session. No browser/server logs existed before this repair.
