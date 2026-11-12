# Q-SHIFT Phase E1 — Isolated Interactive Exhibition Implementation

## Status

Implemented and validated on isolated branch `codex/exhibition-phase-e1`, based on exhibition commit `f537f7fafa164d38bffd854d3af2c0aabaecf935`. The research checkout remains on `codex/research-strong-baselines-v1`; no research branch, V2.4 freeze, research evidence, approval record, or PR #1 was modified. No Stim sampling, batch experiment, performance benchmark, protected evaluation, firmware upload, or physical COM-port open occurred.

## What was added

- A separate `/interactive` page with a Stim-coordinate board view, selectable data-qubit/Pauli input, Inject Error / Decode / Reset controls, detector time-slice view, decoder output, and simulation-only reference outcome.
- Separate routes: `GET /api/interactive/state`, `POST /api/interactive/inject`, `POST /api/interactive/decode`, and `POST /api/interactive/reset`. Existing batch routes and their meaning are preserved.
- A deterministic state engine, Stim-derived geometry mapping, version-1 JSON-Lines protocol, in-memory serial mock, and opt-in pySerial worker. The worker only starts if `QSHIFT_ESP32_PORT` is explicitly set before the server starts; the normal desktop mode does not scan or open serial ports.
- The root exhibition page links to the separate mode. Documentation describes the protocol, wiring review boundary, and operation commands.

## Circuit and deterministic signature method

The implementation starts from the existing exhibition `make_circuit(0.0)` result, which is Stim's `surface_code:rotated_memory_z` circuit at distance 3 and five rounds. It retains the generated `QUBIT_COORDS`, `R`, `H`, `CX`, `TICK`, `MR`, `M`, `DETECTOR`, and `OBSERVABLE_INCLUDE` instructions, while stripping the existing `DEPOLARIZE1`, `DEPOLARIZE2`, and `X_ERROR` stochastic channels from the deterministic reference. Any unreviewed stochastic instruction fails closed.

For a chosen data qubit, the engine inserts exactly one explicit `X`, `Y`, or `Z` gate immediately after the first `MR` stabilizer-measurement instruction (after the first measured round). It runs one fixed-seed `stim.TableauSimulator` trajectory, obtains its measurement record, and converts that record using a measurement-to-detector converter compiled from the **unfaulted ideal reference circuit**. The converter therefore compares the injected circuit's measurement record against the actual code circuit's detector definitions; no syndrome pattern is hardcoded. It also returns the simulator's logical-observable reference, but the API withholds that reference until after Decode.

For a tested `X` fault on Stim data qubit 10, the derived event IDs are 5 and 10, both on detector time slice 1. These map to check LEDs 1 and 6. PyMatching receives only the detector vector and returns its predicted logical observable. The implementation deliberately reports no per-qubit correction map.

## Geometry and physical indicators

The 9 data LEDs map row-major to Stim qubits `1, 3, 5 / 8, 10, 12 / 15, 17, 19`. The 8 check LEDs map in documented stable order to Stim check IDs `2, 9, 11, 13, 14, 16, 18, 25`, preserving their coordinates, check path, detector IDs, and six-slice event history. At boundary slices some checks have no detector; the API marks these with `valid=false` rather than presenting an absent measurement as zero. Stim's `num_qubits == 26` reflects sparse qubit indices through index 25; the circuit has 17 coordinate-assigned code sites, not 26 physical markers.

The ESP32 protocol supports 9 RGB data pixels plus 8 check pixels as one addressable WS2812B chain. The proposed board scales Stim coordinates onto a 25 × 18 cm layout. Wiring, power capacity, LED level shifting, and local component cost still need a separate physical review.

## Important interpretation boundary

The highlighted data site is a known simulated input supplied by the user. It is not an error location inferred from detectors. The current PyMatching call predicts a logical observable and does not expose a verified mapping to data-qubit LEDs. Simulation truth is separate and appears only after decoding. This is a deterministic educational circuit exercise, not a quantum-processor connection or a decoder-performance experiment. The existing stochastic batch demo remains separate and unchanged in behavior.

## API and operation

Start from `exhibition-demo/` using the existing Windows launcher or the README's manual commands, then open `http://127.0.0.1:8765/interactive`. The page defaults to **DESKTOP MOCK · NO ESP32**. Its buttons call the isolated interactive routes; the batch simulation remains available through the original page and `/api/run` API.

For a later hardware session, after wiring/power review and firmware validation, install optional `requirements-hardware.txt`, set `QSHIFT_ESP32_PORT` (for example `COM5`), then start the same server. This phase did not enable that environment variable, install pySerial, open a port, or flash firmware.

## Validation

See [`E1_TEST_RESULTS.md`](E1_TEST_RESULTS.md) for exact commands and outcomes. The isolated suite passed all 11 tests, Python compilation passed, both inline JavaScript blocks parsed with Node, and `git diff --check` passed. The existing pytest suite was not run because it samples Stim circuits and pytest was unavailable; no sampling tests were invoked.

## Remaining risks

- No physical board, ESP32 firmware, COM-port reconnect, or actual LED timing has been validated.
- Full browser-visible E2E/keyboard/accessibility testing remains outstanding.
- A single fixed-seed stabilizer trajectory is not a noise or logical-error-rate study.
- The educational mode uses the existing nominal PyMatching DEM approximation; it does not claim an optimal or correlation-aware decoder.
- The in-memory demo state is lost if the server restarts, consistent with the existing local demonstration.
- The ₹2,000–₹3,000 parts budget was not price-checked.
