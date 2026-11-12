from __future__ import annotations

import re
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import server
from firmware.phase_e2.tools.protocol_harness import FirmwareContractHarness
from interactive_demo.serial_protocol import SerialCommandProcessor


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "firmware" / "phase_e2" / "src" / "main.cpp"


class FirmwareE2ContractTests(unittest.TestCase):
    def setUp(self):
        self.engine = server.app.state.interactive_engine
        self.engine.reset()
        self.processor = SerialCommandProcessor(self.engine, clock=time.monotonic)
        self.device = FirmwareContractHarness(self.processor)

    def tearDown(self):
        self.engine.reset()

    def test_pin_profile_and_pixel_order_match_e1(self):
        source = FIRMWARE.read_text(encoding="utf-8")

        def integer(name: str) -> int:
            match = re.search(rf"constexpr int {name} = (\d+);", source)
            self.assertIsNotNone(match, f"missing {name}")
            return int(match.group(1))

        self.assertEqual(integer("kPixelsPin"), 18)
        self.assertEqual(integer("kInjectButtonPin"), 25)
        self.assertEqual(integer("kDecodeButtonPin"), 26)
        self.assertEqual(integer("kResetButtonPin"), 27)
        self.assertEqual(integer("kConnectedLedPin"), 22)
        self.assertEqual(integer("kDisconnectedLedPin"), 23)
        data = re.search(r"kDataStimQubits\[kDataCount\] = \{([^}]+)\}", source)
        checks = re.search(r"kCheckStimQubits\[kCheckCount\] = \{([^}]+)\}", source)
        self.assertEqual([int(x.strip()) for x in data.group(1).split(",")], [1, 3, 5, 8, 10, 12, 15, 17, 19])
        self.assertEqual([int(x.strip()) for x in checks.group(1).split(",")], [2, 9, 11, 13, 14, 16, 18, 25])
        self.assertIn("constexpr uint8_t kPixelBrightness = 48", source)
        self.assertIn("kDebounceMs = 50", source)
        self.assertIn("age < 100 || (age >= 200 && age < 300)", source)
        self.assertNotIn("delay(", source)

    def test_handshake_buttons_retry_dedup_decode_and_reset(self):
        ack, state = self.device.hello()
        self.assertTrue(ack["accepted"])
        self.assertEqual(state["state"]["phase"], "idle")

        ack, state = self.device.button("inject_error")
        self.assertTrue(ack["accepted"])
        self.assertEqual(state["state"]["fault_input"]["stim_qubit"], 10)
        run_id = state["state"]["run_id"]

        duplicate, duplicate_state = self.device.retry_last()
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate_state["state"]["run_id"], run_id)

        decoded, decoded_state = self.device.button("decode")
        self.assertTrue(decoded["accepted"])
        self.assertEqual(decoded_state["state"]["phase"], "decoded")
        self.assertIsNone(decoded_state["state"]["correction_map"])

        reset, reset_state = self.device.button("reset")
        self.assertTrue(reset["accepted"])
        self.assertEqual(reset_state["state"]["phase"], "idle")
        self.assertIsNone(reset_state["state"]["fault_input"])

    def test_six_slice_selection_stays_synchronized_to_laptop_state(self):
        self.device.hello()
        self.device.button("inject_error")
        statuses = []
        with TestClient(server.app) as client:
            for slice_index in range(6):
                response = client.post("/api/interactive/slice", json={"slice_index": slice_index})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["display_slice_index"], slice_index)
                # ESP32's periodic hello receives the same host-selected index
                # and all eight valid/event values in its full-state snapshot.
                _, state = self.device.hello()
                self.assertEqual(state["state"]["display_slice_index"], slice_index)
                self.assertEqual(len(state["state"]["detector_frames"]), 6)
                self.assertEqual(len(self.device.check_leds_for_selected_slice()), 8)
                statuses.append(self.device.check_leds_for_selected_slice())

        # At least one frame contains boundary-unavailable checks; the harness
        # and firmware treat them separately from measured zero events.
        self.assertTrue(any(status == "unavailable" for row in statuses for status in row))
        self.assertTrue(any("valid_zero" in row for row in statuses))

    def test_slice_api_validation_and_disconnected_actions_are_not_queued(self):
        with TestClient(server.app) as client:
            self.assertEqual(client.post("/api/interactive/slice", json={"slice_index": 6}).status_code, 422)
            self.assertEqual(client.post("/api/interactive/slice", json={"slice_index": True}).status_code, 422)
        source = FIRMWARE.read_text(encoding="utf-8")
        self.assertIn("if (!connected)", source)
        self.assertIn("Never replay a disconnected physical press later", source)
        self.assertIn("pendingLine", source)
        self.assertIn("Byte-identical payload and identical sequence", source)

    def test_host_logs_bounded_firmware_diagnostics_without_changing_actions(self):
        from interactive_demo.serial_bridge import _log_device_diagnostics

        with self.assertLogs("qshift.exhibition.serial", level="INFO") as captured:
            _log_device_diagnostics(
                b'{"v":1,"type":"hello","session_id":"unit","seq":0,'
                b'"diag":{"fw":"2.0.0","retry":2,"bad_rx":1,"secret":"ignored"}}'
            )
        self.assertIn('"retry": 2', captured.output[0])
        self.assertNotIn("secret", captured.output[0])


if __name__ == "__main__":
    unittest.main()
