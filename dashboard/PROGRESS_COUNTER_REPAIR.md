# Progress counter repair

`completed_shots`, `generated_shots`, and `processed_shots` are now read only
from their own persisted fields. Missing values remain unknown in the UI; a
generated count or training-only counter cannot stand in for completed work.
The dashboard computes percentage only when both completed and total counts
are available, and ETA only when those counts and positive measured throughput
are available. Initial zero is shown as zero only when the worker explicitly
reports it. The generated and processed cards show an em dash when their own
counter is absent.

## Verification

- `node --test dashboard/tests/monitoring_ui.test.cjs`: 8 passed.
- `python -m unittest dashboard.tests.test_dashboard.ControlAndApiTests.test_progress_endpoint_survives_refresh_and_reports_terminal_state -v`: passed.
- `python -m unittest dashboard.tests.test_monitoring_integration -v`: passed as part of the combined backend run; the real bounded Stim/PyMatching worker emitted and persisted progress through completion.
- `python -m py_compile dashboard/app.py dashboard/storage.py dashboard/manager.py dashboard/worker.py dashboard/structured_training.py`: passed.
- The combined `test_dashboard` and `test_monitoring_integration` run reported 33 passes and one existing error: the structured-run test rejects the historical `structured_diagnostic_config.json` freeze hash. That integrity failure is unrelated to progress counters and was not changed.
- Visible-browser E2E remains incomplete. The prior browser-tool attempt could not determine the current Windows browser URL and explicitly ended computer use; no browser retry was made for this narrowly scoped repair.

No research freeze, Stage 5 allocation, or experimental data was modified or sampled.
