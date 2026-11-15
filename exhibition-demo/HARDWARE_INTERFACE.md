# Exhibition hardware interface draft

The laptop demo works without the ordered hardware. This document defines a
small future serial boundary for an ESP32 and WS2812B strip. It does not select
ESP32 pins, LED power wiring, grounds, a board, or a final baud rate; those must
be confirmed from the delivered parts and reviewed wiring before connection.

## Host-to-board messages

UTF-8 JSON Lines: one JSON object followed by `\n`; no binary framing. Initial
proposal is 115200 baud, 8 data bits, no parity, 1 stop bit, subject to board
verification. The host should keep `seq` increasing for the current session.

```json
{"v":1,"seq":12,"mode":"explain","state":"syndrome","leds":[0,0,0,1,0,0,0,0,0],"logical":{"fixed":0,"adaptive":1,"privileged":null}}
```

Fields:

- `v`: protocol version, currently `1`.
- `seq`: nonnegative message sequence number.
- `mode`: `explain`, `stage5`, or `changing_noise`.
- `state`: `idle`, `error`, `syndrome`, `decode`, `success`, or `failure`.
- `leds`: nine integer brightness values from 0 to 255 in logical display order.
- `logical`: predicted observable correction bits; `privileged` is `null` unless
  the active simulation explicitly exposes its true-parameter reference.

Board acknowledgement is one JSON line:

```json
{"v":1,"seq":12,"ok":true}
```

The board can report a debounced button event as `{"v":1,"button":"next"}`,
where `button` is `next`, `mode`, or `reset`. Unknown versions, fields outside
the documented ranges, malformed JSON, or stale sequence values should be
rejected without changing the displayed state.

## Logical LED index map

These are **logical demo slots**, not a physical strip direction or a mapping
to Stim qubit IDs. If a strip is installed, its physical index order must be
confirmed on the actual chain before wiring labels are applied.

| Logical LED | Display role |
|---:|---|
| 0 | Current mode/status |
| 1–5 | First five active detector indicators (display subset only) |
| 6 | Fixed arm status/result indicator |
| 7 | Detector-profile adaptive arm status/result indicator |
| 8 | Privileged true-parameter reference status/result indicator |

The browser preview highlights these as activity/error indicators, not as a
physical correction chain or a direct mapping from detector ID to strip LED.

## Three-button interaction

| Button label | Action |
|---|---|
| Next | Advance the Mode A teaching sequence; no effect while a live run is busy |
| Mode | Cycle Explain → Stage 5 → Changing noise |
| Reset | Return the visualizer to its idle state; it must not silently erase saved research data |

Use software debounce and send only press events. The exact electrical pull-up,
button polarity, GPIO assignment, and debounce interval remain to be set after
the specific ESP32 board and wiring are inspected.

## Laptop preview and port setting

The browser page includes a hardware-independent nine-LED preview and a saved
COM-port preference. At this stage the preference is configuration only: no
serial device is opened and no bytes are sent. The preview exercises the same
logical state that a future adapter would serialize. Hardware enablement should
follow delivery confirmation, wiring review, and a separate serial loopback test.
