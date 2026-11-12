# Q-SHIFT Science Exhibition Demo

A local, single-laptop demonstration of quantum error correction using **real Stim circuit sampling** and **real PyMatching decoding**. The dark cyan/violet page is designed for a school science exhibition and does not need a cloud service or login.

## Start on Windows

1. Install Python 3.10 or newer and enable **Add Python to PATH**.
2. Double-click `START_WINDOWS.bat`.
3. On the first launch, the script creates an isolated `.venv` and installs the pinned packages in `requirements.txt`. This first installation needs internet access.
4. The script starts the local server and opens `http://127.0.0.1:8765` after its health endpoint responds. Keep the command window open while using the site; press **Ctrl+C** there to stop it.
5. Later launches use the already-installed virtual environment and work offline. No CDN, remote font, cloud database, or remote simulation service is used. The optional GitHub links need internet.

Manual commands from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

To run the automated checks, install test-only packages once and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## What a live run does

- Supports 1,000, 5,000, or 10,000 **evaluation** shots and five listed burst probabilities (0, 0.4%, 0.8%, 1.2%, 1.6%).
- Builds a distance-3, five-round rotated Z-memory Stim circuit with 40 detectors and one logical observable.
- Uses 2,000 separate detector-only calibration shots. It also generates 17 independent detector-profile reference batches of 1,200 shots each (20,400 reference shots). The page reports these streams separately from evaluation.
- Estimates burst probability from calibration detector frequencies only. It does not pass logical-observable labels or the generating probability into the estimator.
- Builds a burst-blind fixed PyMatching decoder and a decoder using the estimated burst probability. Both decode the **same evaluation detector rows**; errors are scored against those rows’ simulated observable labels.
- Updates progress only after sampling and decoding each batch. `generated_shots` and `completed_shots` are separate backend fields. The two error counts, paired decoder disagreements, selected estimate, and measured elapsed time come from the run.
- Stores the active run ID in the browser tab’s session storage so refresh or a short connection interruption can reconnect while the same server process remains alive. The server keeps run status in memory; restarting the server loses that status and the page will say so rather than reconstructing results.

## Interactive single-fault model (E1)

Open `http://127.0.0.1:8765/interactive` after starting the same local server. This is a separate, deterministic learning mode with **Inject Error**, **Decode**, and **Reset** steps. It starts in desktop mock mode and works without an ESP32.

The mode derives its layout and detector mapping from the existing distance-3, five-round `surface_code:rotated_memory_z` circuit. It strips only stochastic noise instructions from that circuit, inserts one explicit X/Y/Z Pauli after the first stabilizer-measurement round, simulates one fixed-seed noiseless tableau trajectory, and converts that measurement record with Stim's measurement-to-detector converter compiled from the unmodified ideal reference circuit. It does not call a Stim sampler or create evaluation shots. PyMatching receives only the 40 detector bits; the simulated reference observable is displayed only after decoding. The decoder output is the predicted logical observable, not a per-qubit physical correction map.

The 9 data indicators use Stim qubits `1,3,5 / 8,10,12 / 15,17,19`; the 8 check indicators use `2,9,11,13,14,16,18,25`. Detector events remain grouped by their actual Stim spatial coordinate and detector-time slice, including unavailable boundary checks. The highlighted data site is a **known simulated input**, not a fault inferred by the decoder.

The ESP32 interface is specified in [`interactive_demo/FIRMWARE_PROTOCOL_E1.md`](interactive_demo/FIRMWARE_PROTOCOL_E1.md). The JSON-Lines protocol, optional host-side pySerial worker, and in-memory serial mock are implemented; a loopback test exercises the worker. No physical COM port was opened and no firmware was flashed. Complete the separate wiring and power review before connecting or programming hardware. To enable a future host bridge, install the optional `requirements-hardware.txt` and set `QSHIFT_ESP32_PORT` before starting the server. This mode is an educational simulation and not a quantum-processor connection.

### ESP32 firmware preparation (E2)

The source-only ESP32 implementation is in [`firmware/phase_e2/`](firmware/phase_e2/). It preserves the E1 JSON-Lines v1 hello/button/ACK/state exchange, retries the same sequence after lost acknowledgements, keeps the 17-pixel mapping, and shows the selected one of six detector frames. The laptop time-slice slider now writes a shared `display_slice_index`; firmware's periodic full-state hello follows that selection so the two displays stay aligned. `GET /api/interactive/state` and `POST /api/interactive/slice` are demo-only endpoints. The protocol details and wiring guide are [`FIRMWARE_PROTOCOL_E2.md`](firmware/phase_e2/FIRMWARE_PROTOCOL_E2.md) and [`HARDWARE_GUIDE_E2.md`](firmware/phase_e2/HARDWARE_GUIDE_E2.md); the wiring diagram is [`hardware_wiring_e2.svg`](firmware/phase_e2/hardware_wiring_e2.svg).

The provided PlatformIO profile is explicitly for a classic ESP32-WROOM-32 DevKit V1. Verify the physical board marking before build. PlatformIO was not installed in the implementation environment, so firmware compilation is not verified. Do not flash or power a board until the separate wiring and power review is complete. The recommended topology keeps laptop USB positive power on the ESP32 and an independent regulated 5 V LED supply on the pixels/translator, sharing ground only and leaving the positive rails separate.

Run the deterministic E1 + E2 host contract tests from this directory with:

```powershell
python -m unittest tests.test_interactive_e1 tests.test_firmware_e2 -v
```

These tests exercise the production host protocol processor and a desktop contract harness; they do not replace compiling/flashing the firmware or validating physical wiring.

## Scientific scope and limits

This is an **educational live simulation**, not the frozen Stage 5 research runner and not a hardware demonstration. It adds the synthetic paired-X event after each of five `MR` instructions in Stim’s generated circuit and uses `decompose_errors=True, approximate_disjoint_errors=True` when constructing the matching graph. The demo’s 17-point detector-profile estimator is a simplified nearest-profile procedure; it is not the exact frozen Stage 5 implementation. Do not pool or present live demo results as additional Stage 5 shots.

The lattice in the hero is decorative. The interactive 40-cell view is an **ordinal detector-index map**, not a surface-code layout or detector-coordinate map. Its highlights show detector indices triggered in the most recently completed evaluation batch. Before a real run, its animation is labeled illustrative and is not progress data.

The published **21.9% relative reduction** is a separate Stage 5 aggregate comparing detector-profile adaptation with a nominal burst-blind fixed decoder under the frozen synthetic conditions. It is not a live-run result, a claim over every strong static decoder, or a hardware result. The live demo uses a simpler circuit insertion and estimator and may produce different outcomes.

## Implementation and compatibility

The tested Windows environment uses Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, FastAPI 0.162.0, and Uvicorn 0.54.0. PyMatching graphs are constructed with correlation decoding disabled, and the code calls `decode_batch(detectors)` without `enable_correlations=True`. This directly avoids the prior configuration error instead of suppressing it.

The server binds to `127.0.0.1` only. A single-worker pool and a lock reject overlapping runs. Backend exceptions are returned as a useful run error and the full traceback is written to the local server console. No experimental output is written into the Q-SHIFT research evidence directories.

## Files

- `server.py` — local FastAPI backend and Stim/PyMatching experiment.
- `index.html` — responsive exhibition interface.
- `tests/` — regression and real-run API tests.
- `requirements.txt` — pinned runtime packages.
- `requirements-test.txt` — test-only packages.
- `START_WINDOWS.bat` — isolated one-click launcher.
