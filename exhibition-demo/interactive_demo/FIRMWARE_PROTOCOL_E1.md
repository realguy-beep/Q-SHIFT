# Q-SHIFT Exhibition E1 — Firmware Interface Specification

Status: software protocol, optional host-side pySerial worker, and in-memory mock implemented; **no ESP32 firmware has been flashed and no physical USB serial device has been tested**. Perform a wiring/power review before hardware deployment.

## Electrical and transport assumptions

- ESP32 USB CDC or USB-to-UART presents a laptop COM port.
- 115200 baud, 8 data bits, no parity, 1 stop bit (8N1).
- UTF-8 JSON Lines, one JSON object per LF-terminated line; maximum line size 4096 bytes.
- Device button inputs are active-low with internal pull-ups. Firmware debounces each press for at least 50 ms; the host applies the same minimum.
- LED order is fixed: 9 data-qubit indicators in row-major order, followed by the 8 check indicators in `check_sites` order.
- Reconnect sends a full state snapshot; it does not repeat the last action.

## Device-to-host messages

On serial open, begin a session with a per-boot `session_id` and sequence zero:

```json
{"v":1,"type":"hello","session_id":"esp32-boot-7c21","seq":0}
```

After that, send only debounced button-down events. Sequence values are unsigned 32-bit integers, increasing per device session:

```json
{"v":1,"type":"button","session_id":"esp32-boot-7c21","seq":1,"button":"inject_error"}
{"v":1,"type":"button","session_id":"esp32-boot-7c21","seq":2,"button":"decode"}
{"v":1,"type":"button","session_id":"esp32-boot-7c21","seq":3,"button":"reset"}
```

The physical Inject button uses the configured default scenario (row-major data index 4, Stim qubit 10, X fault). A laptop selection may override `data_index` (0–8) and `pauli` (`X`, `Y`, or `Z`) in the same version-1 message. Decode and Reset have no additional fields.

## Host-to-device acknowledgement and state

Every accepted, rejected, or malformed command receives an acknowledgement followed by a full state message. Host sequence values are independent of device sequence values.

```json
{"v":1,"type":"ack","session_id":"esp32-boot-7c21","seq":1,"accepted":true,"duplicate":false,"error":null,"phase":"syndrome_ready"}
```

The state envelope is `{"v":1,"type":"state","session_id":...,"seq":...,"state":{...}}`. In the current engine, `state` has these fields:

| Field | Type / shape | Meaning |
|---|---|---|
| `version`, `run_id`, `mode`, `phase`, `transitions` | integer, integer, string, string, string array | Protocol state and the audited UI transition trace. |
| `code` | object | Code ID and counts (9 data sites, 8 checks, 40 detectors, 1 observable). |
| `layout.data_sites` | 9 objects | LED index, Stim qubit ID, and Stim x/y coordinate. |
| `layout.check_sites` | 8 objects | Check LED index, Stim qubit ID, coordinate, and X/Z check path. |
| `fault_input` | object or `null` | Explicitly known simulated data-qubit/Pauli input; not inferred from the syndrome. |
| `qubit_states` | string array, length 9 | `idle` or `known_simulated_fault_input`; never an inferred physical correction. |
| `detector_events` | integer array, length 40, or `null` | Exact detector bits in Stim detector-ID order. |
| `detector_frames` | 6 objects or `null` | Each has `time_index` 0–5 and `valid`/`events` boolean arrays of length 8 in check-LED order. |
| `decoder` | object or `null` | After Decode, PyMatching name and its predicted logical-observable bit. |
| `simulation_reference` | object or `null` | After Decode only: simulator observable and prediction-match flag. Never passed to the decoder. |
| `physical_processor_data`, `correction_map` | boolean, `null` | Always `false` and `null`; this software has no quantum hardware or verified per-qubit correction map. |

An idle state example is:

```json
{
  "v": 1,
  "type": "state",
  "session_id": "esp32-boot-7c21",
  "seq": 12,
  "state": {
    "version": 1,
    "run_id": 0,
    "mode": "deterministic_simulation_only",
    "phase": "idle",
    "transitions": ["idle"],
    "code": {"id": "stim_rotated_memory_z_d3_r5_e1", "data_qubits": 9, "check_sites": 8, "detectors": 40, "observables": 1},
    "layout": {
      "data_sites": [
        {"data_index": 0, "stim_qubit": 1, "x": 1, "y": 1}, {"data_index": 1, "stim_qubit": 3, "x": 3, "y": 1}, {"data_index": 2, "stim_qubit": 5, "x": 5, "y": 1},
        {"data_index": 3, "stim_qubit": 8, "x": 1, "y": 3}, {"data_index": 4, "stim_qubit": 10, "x": 3, "y": 3}, {"data_index": 5, "stim_qubit": 12, "x": 5, "y": 3},
        {"data_index": 6, "stim_qubit": 15, "x": 1, "y": 5}, {"data_index": 7, "stim_qubit": 17, "x": 3, "y": 5}, {"data_index": 8, "stim_qubit": 19, "x": 5, "y": 5}
      ],
      "check_sites": [
        {"led_index": 0, "stim_qubit": 2, "x": 2, "y": 0, "basis": "X"}, {"led_index": 1, "stim_qubit": 9, "x": 2, "y": 2, "basis": "Z"},
        {"led_index": 2, "stim_qubit": 11, "x": 4, "y": 2, "basis": "X"}, {"led_index": 3, "stim_qubit": 13, "x": 6, "y": 2, "basis": "Z"},
        {"led_index": 4, "stim_qubit": 14, "x": 0, "y": 4, "basis": "Z"}, {"led_index": 5, "stim_qubit": 16, "x": 2, "y": 4, "basis": "X"},
        {"led_index": 6, "stim_qubit": 18, "x": 4, "y": 4, "basis": "Z"}, {"led_index": 7, "stim_qubit": 25, "x": 4, "y": 6, "basis": "X"}
      ]
    },
    "fault_input": null,
    "qubit_states": ["idle", "idle", "idle", "idle", "idle", "idle", "idle", "idle", "idle"],
    "detector_events": null,
    "detector_frames": null,
    "decoder": null,
    "simulation_reference": null,
    "physical_processor_data": false,
    "correction_map": null
  }
}
```

Active syndrome states carry 40 `detector_events` and six `detector_frames`. `valid[i] == false` means there is no detector at that check/time boundary; it does not mean a measured zero. `events[i]` is meaningful only when valid.

After Decode, `decoder.predicted_logical_observable` reports PyMatching's one-bit prediction. `simulation_reference.logical_observable` and `.correct` are simulator-only truth revealed after decoding. These fields are not sent to the decoder. There is deliberately no physical-qubit correction map: the existing decoder call returns an observable prediction, not a verified data-qubit correction projection.

## Error, duplicate, and reconnect behavior

- Invalid JSON, an unsupported version, unknown button, invalid sequence, oversized line, or missing handshake is rejected without applying an action.
- A repeated sequence with the identical message returns a duplicate acknowledgement and the current full state without repeating the action.
- Reusing a sequence with different content or sending a stale sequence is rejected.
- On disconnect, a physical display should show its local disconnected/idle cue and must not invent new syndrome values. The host keeps the current in-memory trial. On reconnect, send `hello`; the host returns the current full state for resynchronization.
- If the laptop server restarted, its in-memory state is idle; the device receives that state rather than a fabricated continuation.
- Host serial I/O is started only when `QSHIFT_ESP32_PORT` is explicitly set before server startup. The `SerialBridgeWorker` retries a missing/disconnected port and uses the same parser as the mock. Without that environment variable, no COM-port scan or open is attempted.

## LED semantics and check order

Data LED indices 0–8 map row-major to Stim data qubits:

`0:q1 (1,1), 1:q3 (3,1), 2:q5 (5,1), 3:q8 (1,3), 4:q10 (3,3), 5:q12 (5,3), 6:q15 (1,5), 7:q17 (3,5), 8:q19 (5,5)`.

Check LED indices 0–7 map to:

| LED | Stim check qubit | Coordinate | Check path | Detector IDs |
|---:|---:|---:|---|---|
| 0 | 2 | (2,0) | X | 4, 12, 20, 28 |
| 1 | 9 | (2,2) | Z | 1, 5, 13, 21, 29, 37 |
| 2 | 11 | (4,2) | X | 6, 14, 22, 30 |
| 3 | 13 | (6,2) | Z | 3, 7, 15, 23, 31, 39 |
| 4 | 14 | (0,4) | Z | 0, 8, 16, 24, 32, 36 |
| 5 | 16 | (2,4) | X | 9, 17, 25, 33 |
| 6 | 18 | (4,4) | Z | 2, 10, 18, 26, 34, 38 |
| 7 | 25 | (4,6) | X | 11, 19, 27, 35 |

The check basis assignments follow the Stim-generated circuit's initial Hadamard layer and measurement structure. A lit data marker in this mode means the known simulated input location. It must not be presented as a hidden stochastic fault discovered by decoding.

## Hardware review still required

Use a single 17-pixel WS2812B chain (9 RGB data markers and 8 check markers) if the chosen board layout and budget support it. Verify the selected ESP32 pin, 3.3 V-to-5 V data-level compatibility, LED current budget, 5 V supply, common ground, series data resistor, bulk capacitor, button pull-ups, enclosure spacing, and USB power isolation before connecting hardware. No prices or electrical safety properties were validated in this software-only phase.
