"""Desktop protocol-contract harness; this is not a physical firmware test.

It sends the same JSON-Lines messages as the ESP32 and consumes replies from
the production E1 SerialCommandProcessor. The C++ firmware still requires a
PlatformIO build and a separately authorized hardware test.
"""
from __future__ import annotations

import json
from typing import Any


class FirmwareContractHarness:
    def __init__(self, processor: Any, session_id: str = "e2-test-session") -> None:
        self.processor = processor
        self.session_id = session_id
        self.next_sequence = 0
        self.connected = False
        self.snapshot: dict[str, Any] | None = None
        self.last_wire_line: str | None = None

    def _exchange(self, message: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        line = json.dumps(message, separators=(",", ":"))
        self.last_wire_line = line
        replies = self.processor.handle_line(line)
        if len(replies) != 2 or replies[0].get("type") != "ack" or replies[1].get("type") != "state":
            raise ValueError("Host reply must contain ACK then full state")
        ack, state = replies
        if state.get("session_id") == self.session_id:
            self.apply_state(state)
        return ack, state

    def apply_state(self, message: dict[str, Any]) -> None:
        if message.get("v") != 1 or message.get("type") != "state":
            raise ValueError("Not a protocol v1 state message")
        if message.get("session_id") != self.session_id:
            raise ValueError("State belongs to a different session")
        state = message.get("state")
        if not isinstance(state, dict):
            raise ValueError("State payload is missing")
        frames = state.get("detector_frames")
        if frames is not None:
            if not isinstance(frames, list) or len(frames) != 6:
                raise ValueError("Expected six detector frames")
            for frame in frames:
                if not isinstance(frame, dict) or len(frame.get("valid", [])) != 8 or len(frame.get("events", [])) != 8:
                    raise ValueError("Each detector frame must have eight valid/event values")
        index = state.get("display_slice_index", 0)
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
            raise ValueError("display_slice_index must be in range 0..5")
        self.snapshot = state
        self.connected = True

    def hello(self) -> tuple[dict[str, Any], dict[str, Any]]:
        seq = self.next_sequence
        self.next_sequence += 1
        return self._exchange({"v": 1, "type": "hello", "session_id": self.session_id, "seq": seq,
                              "diag": {"fw": "2.0.0", "retry": 0, "bad_rx": 0}})

    def button(self, name: str) -> tuple[dict[str, Any], dict[str, Any]]:
        seq = self.next_sequence
        self.next_sequence += 1
        return self._exchange({"v": 1, "type": "button", "session_id": self.session_id,
                              "seq": seq, "button": name})

    def retry_last(self) -> tuple[dict[str, Any], dict[str, Any]]:
        if self.last_wire_line is None:
            raise ValueError("No command is available to retry")
        replies = self.processor.handle_line(self.last_wire_line)
        ack, state = replies
        if state.get("session_id") == self.session_id:
            self.apply_state(state)
        return ack, state

    def check_leds_for_selected_slice(self) -> list[str]:
        if self.snapshot is None or self.snapshot.get("detector_frames") is None:
            return ["idle"] * 8
        frame = self.snapshot["detector_frames"][self.snapshot["display_slice_index"]]
        # These names match the three distinct firmware render states. A
        # missing/invalid boundary is never collapsed into a zero-event state.
        return [
            "unavailable" if not frame["valid"][i] else "event" if frame["events"][i] else "valid_zero"
            for i in range(8)
        ]
