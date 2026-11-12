"""Optional USB JSON-Lines worker; dormant unless explicitly started.

The desktop mock remains the default. This adapter is deliberately not started
at import time and requires an explicit COM port plus optional pySerial.
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Any, Callable

from .serial_protocol import MAX_LINE_BYTES, SerialCommandProcessor

logger = logging.getLogger("qshift.exhibition.serial")


def _log_device_diagnostics(raw_line: bytes) -> None:
    """Log only the bounded, documented counters in an E2 hello message."""
    try:
        message = json.loads(raw_line.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError):
        return
    if not isinstance(message, dict) or message.get("type") != "hello":
        return
    diag = message.get("diag")
    if not isinstance(diag, dict):
        return
    safe = {}
    for key in ("fw", "retry", "bad_rx", "reconnects", "button_drops", "tx_blocked"):
        value = diag.get(key)
        if key == "fw" and isinstance(value, str):
            safe[key] = value[:24]
        elif key != "fw" and isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            safe[key] = value
    logger.info("ESP32 firmware diagnostics: %s", json.dumps(safe, sort_keys=True))


class SerialBridgeWorker:
    def __init__(
        self,
        port: str,
        processor: SerialCommandProcessor,
        *,
        serial_factory: Callable[..., Any] | None = None,
        reconnect_seconds: float = 0.5,
    ) -> None:
        if not port or len(port) > 128:
            raise ValueError("An explicit serial port name is required")
        if reconnect_seconds <= 0:
            raise ValueError("Reconnect delay must be positive")
        self.port = port
        self.processor = processor
        self._serial_factory = serial_factory
        self._reconnect_seconds = reconnect_seconds
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_error: str | None = None

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    def start(self) -> "SerialBridgeWorker":
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="qshift-esp32-serial", daemon=True)
        self._thread.start()
        return self

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
            if thread.is_alive():
                raise RuntimeError("Serial worker did not stop within the requested timeout")
        self._connected.clear()

    def _factory(self) -> Callable[..., Any]:
        if self._serial_factory is not None:
            return self._serial_factory
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError(
                "ESP32 port requested but pySerial is not installed; see requirements-hardware.txt"
            ) from exc
        return serial.Serial

    def _write_reply(self, connection: Any, reply: dict[str, Any]) -> None:
        wire = json.dumps(reply, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
        connection.write(wire)

    def _run(self) -> None:
        while not self._stop.is_set():
            connection = None
            try:
                connection = self._factory()(self.port, baudrate=115200, timeout=0.1)
                self._connected.set()
                self.last_error = None
                buffer = bytearray()
                dropping_oversized_line = False
                while not self._stop.is_set():
                    chunk = connection.read(256)
                    if not chunk:
                        continue
                    for byte in chunk:
                        if byte == 10:
                            if dropping_oversized_line:
                                replies = self.processor.handle_line(b"x" * (MAX_LINE_BYTES + 1))
                            else:
                                _log_device_diagnostics(bytes(buffer))
                                replies = self.processor.handle_line(bytes(buffer))
                            buffer.clear()
                            dropping_oversized_line = False
                            for reply in replies:
                                self._write_reply(connection, reply)
                        elif not dropping_oversized_line:
                            buffer.append(byte)
                            if len(buffer) > MAX_LINE_BYTES:
                                buffer.clear()
                                dropping_oversized_line = True
            except Exception as exc:  # disconnect/reconnect is a normal demo condition
                self.last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("serial bridge unavailable on %s: %s", self.port, self.last_error)
            finally:
                self._connected.clear()
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:
                        logger.debug("serial close failed", exc_info=True)
            self._stop.wait(self._reconnect_seconds)
