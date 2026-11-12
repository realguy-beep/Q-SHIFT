# Q-SHIFT Phase E1 — Test Results

Date: 2026-11-12
Branch: `codex/exhibition-phase-e1`
Base: `f537f7fafa164d38bffd854d3af2c0aabaecf935`

## Commands and outcome

| Command | Result |
|---|---|
| `python -m unittest discover -s tests -p test_interactive_e1.py -v` | **PASS — 12 tests** |
| `python -m compileall -q server.py interactive_demo tests/test_interactive_e1.py` | **PASS** |
| Node inline-JavaScript parse check for `index.html` and `interactive_demo/index.html` | **PASS — both scripts parsed** |
| `git diff --check` | **PASS** |

The deterministic test suite covers Stim-derived data/check geometry, all 40 detector IDs grouped into six time slices, all 27 single-qubit X/Y/Z input locations, a known `X` fault signature (`Stim q10` → detector IDs 5 and 10), state transitions, decoder input isolation, a single actual PyMatching decode, API validation, desktop mock state, button debounce, serial acknowledgement/deduplication/malformed messages, loopback serial-worker behavior, disconnect/reconnect synchronization, and research-file isolation.

The loopback serial test uses a fake port factory; it does not open a COM port. The deterministic fault tests use `stim.TableauSimulator` with a fixed seed and a circuit from which stochastic noise instructions were removed. They do not call `compile_detector_sampler`, `.sample()`, or run a shot batch.

## Test environment and limitations

- Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, FastAPI 0.162.0, NumPy 2.5.3.
- Optional pySerial is not installed. No physical ESP32 connection or firmware upload was attempted.
- The existing full `pytest` suite was not run because it includes real Stim sampling tests and pytest is not installed in this environment. An initial `python -m pytest` attempt stopped immediately with `No module named pytest`; no dependency was installed. The new deterministic suite was run with Python's built-in `unittest` instead.
- `TestClient` emits a Starlette deprecation warning about its installed HTTPX integration; the tested requests passed.
- No visible-browser E2E test or hardware/power test was performed.
