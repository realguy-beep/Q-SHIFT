# Q-SHIFT ESP32 exhibition firmware — protocol E2.0.0

The firmware implements the existing E1 UTF-8 JSON-Lines v1 envelope at 115200 baud, 8N1. It is designed for the separate exhibition demo host; it is not research firmware and does not communicate with quantum hardware.

## Session and message flow

Each boot creates a session ID from the ESP32 eFuse MAC and a boot nonce. The device sends `hello` with sequence 0. The host replies with an `ack` line and then a full `state` line. The device sends debounced button-down events only:

```json
{"v":1,"type":"button","session_id":"e2-123456789abc-abcdef01","seq":1,"button":"inject_error"}
{"v":1,"type":"button","session_id":"e2-123456789abc-abcdef01","seq":2,"button":"decode"}
{"v":1,"type":"button","session_id":"e2-123456789abc-abcdef01","seq":3,"button":"reset"}
```

The first `inject_error` uses the existing host default: data index 4, Stim qubit 10, X. No hardware-side fault is measured or inferred. Sequence numbers increase for every new hello or button message and never wrap; the device refuses further messages near `uint32` exhaustion rather than reusing IDs.

Hello messages carry optional bounded diagnostics that the E1 host ignores as extra fields and logs after allow-list filtering:

```json
{"v":1,"type":"hello","session_id":"e2-123456789abc-abcdef01","seq":0,"diag":{"fw":"2.0.0","retry":0,"bad_rx":0,"reconnects":0,"button_drops":0,"tx_blocked":0}}
```

Every host response remains two lines: ACK first, then full state. The firmware applies state only if the protocol version, session, phase, six-frame count, eight check values per frame, and selected slice are valid. A malformed or oversized line is discarded; the previous verified display remains in place and the error counter/status LED are updated.

## Retry, duplicates, and reconnect

- The device retains one pending serialized message and retransmits the exact same bytes with the exact same sequence after 800 ms. After four attempts it marks the link disconnected and retries every 2.5 seconds.
- The host caches accepted button messages by session and sequence. A retransmission therefore returns a duplicate ACK and current full state without applying the button twice.
- A 2-second hello heartbeat requests the current state, including the laptop-selected `display_slice_index`. The website writes slider selections through `POST /api/interactive/slice`; the firmware and laptop then render the same time slice. The device never runs a separate timer that could drift from the web view.
- The connected green status LED is steady after a valid full state. The red status LED blinks while disconnected. During a disconnect, the last verified pixel state is frozen; button presses are dropped and counted, never queued for a surprise action after reconnect.
- If the host process restarted and rejects a pending button with `hello_required`, firmware drops that uncertain action, sends a fresh hello, and waits for a new user press. This is fail-safe; the board does not replay an action into a reset host state.
- The green status LED double-flashes when the host reports the `decoded` phase. This means only that the demo's Decode step completed; it does not represent a physical correction.
- Diagnostic counters are included in the hello JSON and are logged by the host. Do not print free-form text to USB `Serial`: it would corrupt JSON Lines.

## LED frame semantics

One 17-pixel WS2812B chain is ordered exactly as follows:

- Pixels 0–8: nine data sites in row-major E1 order, Stim qubits `1,3,5,8,10,12,15,17,19`.
- Pixels 9–16: eight check sites in E1 order, Stim qubits `2,9,11,13,14,16,18,25`.

The selected detector frame is a single one of six histories. The laptop slider is authoritative; an HTTP update changes the engine snapshot and the next firmware hello refreshes the board. The browser state poll runs every second; firmware requests a full snapshot every two seconds. Boundary `valid=false` is displayed as dim amber. It is never treated as a valid no-event result. `valid=true,event=false` is dim cyan; a true event is magenta. The known input data site stays amber before and after Decode and is never recolored as an inferred correction.

## Compatibility and limits

The wire envelope and button vocabulary remain E1 v1 compatible. E2 relies on the E1 host's documented tolerance of extra JSON fields and adds a host-side shared slice index. An old host build that predates this slice endpoint still accepts hello/buttons, but cannot synchronize the board's selected frame; use the E2 branch build for synchronized six-slice viewing. No COM port, board, or LED chain has been tested physically.
