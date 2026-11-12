"""Versioned JSON-Lines button protocol and deterministic desktop mock.

This module does not open a COM port. The mock exercises the exact message
parser, sequence handling, debouncing, acknowledgements, and state resync used
by the future ESP32 bridge.
"""
from __future__ import annotations

import json
import threading
from collections import OrderedDict
from typing import Any, Callable


PROTOCOL_VERSION = 1
MAX_LINE_BYTES = 4096
BUTTONS = frozenset({"inject_error", "decode", "reset"})


class ButtonDebouncer:
    def __init__(self, interval_seconds: float = 0.05) -> None:
        if interval_seconds < 0:
            raise ValueError("Debounce interval cannot be negative")
        self.interval_seconds = float(interval_seconds)
        self._last_press: dict[str, float] = {}

    def clear(self) -> None:
        self._last_press.clear()

    def accept(self, button: str, now: float) -> bool:
        previous = self._last_press.get(button)
        if previous is not None and now - previous < self.interval_seconds:
            return False
        self._last_press[button] = now
        return True


class SerialCommandProcessor:
    """Converts device lines into safe demo actions and full-state replies."""

    def __init__(
        self,
        engine: Any,
        *,
        default_data_index: int = 4,
        default_pauli: str = "X",
        clock: Callable[[], float],
    ) -> None:
        self.engine = engine
        self.default_data_index = default_data_index
        self.default_pauli = default_pauli
        self._clock = clock
        self._lock = threading.RLock()
        self._session: str | None = None
        self._last_seq = -1
        self._cache: OrderedDict[int, tuple[str, dict[str, Any]]] = OrderedDict()
        self._host_seq = 0
        self._debouncer = ButtonDebouncer()

    def handle_line(self, line: str | bytes) -> list[dict[str, Any]]:
        """Return `[ack, full_state]`; malformed lines never mutate the engine."""
        with self._lock:
            try:
                raw = line.decode("utf-8", errors="strict") if isinstance(line, bytes) else line
                if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_LINE_BYTES:
                    return self._reply(None, False, "line_too_large_or_invalid")
                message = json.loads(raw.strip())
            except (UnicodeError, json.JSONDecodeError, AttributeError):
                return self._reply(None, False, "malformed_json")
            if not isinstance(message, dict):
                return self._reply(None, False, "message_must_be_object")
            if message.get("v") != PROTOCOL_VERSION:
                return self._reply(message.get("seq"), False, "unsupported_version")
            seq = message.get("seq")
            if isinstance(seq, bool) or not isinstance(seq, int) or not 0 <= seq <= 0xFFFFFFFF:
                return self._reply(None, False, "invalid_sequence")
            kind = message.get("type")
            session = message.get("session_id")
            if not isinstance(session, str) or not session or len(session) > 64:
                return self._reply(seq, False, "invalid_session_id")

            if kind == "hello":
                if self._session != session:
                    self._session = session
                    self._last_seq = -1
                    self._cache.clear()
                    self._debouncer.clear()
                if seq < self._last_seq:
                    return self._reply(seq, False, "stale_sequence")
                self._last_seq = max(self._last_seq, seq)
                return self._reply(seq, True, None, details={"synchronized": True})

            if kind != "button":
                return self._reply(seq, False, "unsupported_message_type")
            if session != self._session:
                return self._reply(seq, False, "hello_required")
            button = message.get("button")
            if not isinstance(button, str) or button not in BUTTONS:
                return self._reply(seq, False, "unknown_button")

            fingerprint = json.dumps(message, sort_keys=True, separators=(",", ":"))
            if seq in self._cache:
                old_fingerprint, old_ack = self._cache[seq]
                if fingerprint != old_fingerprint:
                    return self._reply(seq, False, "sequence_reused_with_different_payload")
                duplicate_ack = dict(old_ack)
                duplicate_ack["duplicate"] = True
                return [duplicate_ack, self._state_message()]
            if seq <= self._last_seq:
                return self._reply(seq, False, "stale_sequence")

            self._last_seq = seq
            now = self._clock()
            if not self._debouncer.accept(button, now):
                ack = self._ack(seq, False, "debounced", duplicate=False)
                self._remember(seq, fingerprint, ack)
                return [ack, self._state_message()]

            try:
                if button == "inject_error":
                    data_index = message.get("data_index", self.default_data_index)
                    pauli = message.get("pauli", self.default_pauli)
                    self.engine.inject_and_prepare_syndrome(data_index, pauli)
                elif button == "decode":
                    self.engine.decode()
                else:
                    self.engine.reset()
            except (ValueError, RuntimeError) as exc:
                ack = self._ack(seq, False, f"action_rejected:{type(exc).__name__}", duplicate=False)
                self._remember(seq, fingerprint, ack)
                return [ack, self._state_message()]

            ack = self._ack(seq, True, None, duplicate=False)
            self._remember(seq, fingerprint, ack)
            return [ack, self._state_message()]

    def _remember(self, seq: int, fingerprint: str, ack: dict[str, Any]) -> None:
        self._cache[seq] = (fingerprint, dict(ack))
        while len(self._cache) > 128:
            self._cache.popitem(last=False)

    def _ack(
        self, seq: int | None, accepted: bool, error: str | None, *, duplicate: bool
    ) -> dict[str, Any]:
        return {
            "v": PROTOCOL_VERSION,
            "type": "ack",
            "session_id": self._session,
            "seq": seq,
            "accepted": accepted,
            "duplicate": duplicate,
            "error": error,
            "phase": self.engine.snapshot().get("phase"),
        }

    def _state_message(self) -> dict[str, Any]:
        self._host_seq += 1
        state = self.engine.snapshot()
        return {
            "v": PROTOCOL_VERSION,
            "type": "state",
            "session_id": self._session,
            "seq": self._host_seq,
            "state": state,
        }

    def _reply(
        self,
        seq: int | None,
        accepted: bool,
        error: str | None,
        *,
        details: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        ack = self._ack(seq, accepted, error, duplicate=False)
        if details:
            ack.update(details)
        return [ack, self._state_message()]


class MockSerialTransport:
    """In-memory ESP32 link used by the desktop mock and regression tests."""

    def __init__(self, processor: SerialCommandProcessor) -> None:
        self.processor = processor
        self.connected = False
        self.session_id: str | None = None
        self.next_seq = 1
        self.last_reply: list[dict[str, Any]] | None = None

    def connect(self, session_id: str = "desktop-mock-1") -> list[dict[str, Any]]:
        self.connected = True
        self.session_id = session_id
        self.next_seq = 1
        self.last_reply = self.processor.handle_line(
            json.dumps({"v": 1, "type": "hello", "session_id": session_id, "seq": 0})
        )
        return self.last_reply

    def disconnect(self) -> None:
        self.connected = False

    def reconnect(self) -> list[dict[str, Any]]:
        if self.session_id is None:
            return self.connect()
        self.connected = True
        # Reusing the same hello/session is a state resynchronization, not a new action.
        self.last_reply = self.processor.handle_line(
            json.dumps(
                {"v": 1, "type": "hello", "session_id": self.session_id, "seq": self.next_seq}
            )
        )
        self.next_seq += 1
        return self.last_reply

    def press(
        self,
        button: str,
        *,
        data_index: int | None = None,
        pauli: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.connected or self.session_id is None:
            raise ConnectionError("Mock serial device is disconnected")
        message: dict[str, Any] = {
            "v": 1,
            "type": "button",
            "session_id": self.session_id,
            "seq": self.next_seq,
            "button": button,
        }
        if data_index is not None:
            message["data_index"] = data_index
        if pauli is not None:
            message["pauli"] = pauli
        self.last_reply = self.processor.handle_line(json.dumps(message))
        self.next_seq += 1
        return self.last_reply
