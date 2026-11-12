# Q-SHIFT Phase E2 — firmware preparation report

## Status

Implemented the ESP32 firmware source, a board-specific candidate profile, an E2 hardware/protocol guide, a wiring diagram, and deterministic host-side contract tests. Work is confined to `exhibition-demo/` on `codex/exhibition-phase-e1`. E1 batch-simulation endpoints and research code were not changed. No real COM port was opened; no board was connected, energized, or flashed; no scientific sampling, performance benchmark, protected evaluation, or research evidence access occurred.

## Firmware behavior

`firmware/phase_e2/src/main.cpp` implements v1 JSON-Lines over USB serial, boot-unique session IDs, monotonic 32-bit sequences, 50 ms active-low button debounce, ACK/state parsing, exact-payload retransmission, bounded retry intervals, duplicate-safe button replay, periodic full-state sync, malformed/oversize line rejection, and nonblocking connection/error indicators. It freezes the last verified LED frame during disconnection and drops new disconnected button presses instead of replaying them later.

The 17-pixel chain follows E1 exactly: pixel 0–8 are Stim data qubits `1,3,5,8,10,12,15,17,19`; pixel 9–16 are check qubits `2,9,11,13,14,16,18,25`. Valid zero, event, and unavailable check states use different colors. Known input stays amber; decode acknowledgment uses a separate green status pulse and never implies a per-qubit correction.

The E1 browser time slider was local-only. E2 adds `display_slice_index` to demo state and `POST /api/interactive/slice`. The laptop is the slice selector; the board receives that selected index on its periodic full-state hello. This makes both displays refer to one state without independent timers drifting. All six detector frames retain separate `valid` and `events` fields.

## Test and validation record

Command run from `exhibition-demo/`:

```powershell
python -m unittest tests.test_interactive_e1 tests.test_firmware_e2 -v
```

Result: **17 tests passed** (12 E1 + 5 E2). Coverage includes Stim geometry order, deterministic single-fault signatures without a sampler, API/state transitions, PyMatching output, research-file isolation, JSON-Lines handshake and actions, retry duplicate idempotence, slice synchronization across all six frames, missing-versus-zero checks, pin/pixel profile, input validation, and allow-listed diagnostic logging.

Additional checks passed:

```powershell
python -m py_compile interactive_demo/api.py interactive_demo/engine.py interactive_demo/serial_protocol.py interactive_demo/serial_bridge.py firmware/phase_e2/tools/protocol_harness.py tests/test_firmware_e2.py
git diff --check
python -c "import xml.etree.ElementTree as E; E.parse('firmware/phase_e2/hardware_wiring_e2.svg'); print('SVG XML: OK')"
python -c "import re,sys; s=open('interactive_demo/index.html',encoding='utf-8').read(); blocks=re.findall(r'<script>(.*?)</script>',s,re.S); sys.stdout.write(blocks[-1])" | node --check
```

The broader command `python -m unittest discover -s tests -p 'test_*e*.py' -v` imported the historical `tests/test_demo.py` and failed because `pytest` is not installed; the 17 explicit E1/E2 unittest cases passed. No package was installed.

## Build and hardware status

No `pio`, `platformio`, `arduino-cli`, `g++`, `clang++`, or `cl` executable was available. Thus the Arduino C++ firmware was **not compiled**. `platformio.ini` pins PlatformIO's Espressif32 platform and library versions; the build command is documented in `firmware/phase_e2/HARDWARE_GUIDE_E2.md`. Building may fetch packages and must use the exact, verified classic ESP32-WROOM-32 DevKit V1 profile.

The physical board model is still unknown. The pinout and power plan are therefore a conditional candidate, not a passed hardware review. The proposed topology powers the ESP32 from USB and LED chain/translator B rail from a separate regulated 5 V/2 A supply; grounds are common and positive rails remain separate. A dual-rail SN74LVC1T45 translator is specified for 3.3-to-5 V data and partial-power-down isolation. Exact parts, board schematic, supply, strip current, connector polarity, layout, and electrical review must be checked before energizing. ESP32 GPIOs must never see 5 V; WS2812B must never receive 11.1/12 V.

## Files changed

- Updated `README.md`, `interactive_demo/api.py`, `interactive_demo/engine.py`, `interactive_demo/index.html`, `interactive_demo/serial_bridge.py`.
- Added `E2_FIRMWARE_PREPARATION_REPORT.md`, `tests/test_firmware_e2.py`.
- Added `firmware/phase_e2/` with `platformio.ini`, `.gitignore`, C++ firmware, protocol/hardware guides, SVG wiring diagram, and host contract harness.
- Added exhibition-only package marker files under `firmware/`.

The host-side harness validates protocol agreement with the real exhibition `SerialCommandProcessor`; it is not a test of the compiled C++ binary or electrical behavior. Physical integration remains pending.
