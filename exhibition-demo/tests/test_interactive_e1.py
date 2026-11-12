from __future__ import annotations

import ast
import json
import queue
import threading
import time
import unittest
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

import server
from interactive_demo.engine import InteractiveDemoEngine, InvalidTransition
from interactive_demo.geometry import CHECK_SITES
from interactive_demo.serial_bridge import SerialBridgeWorker
from interactive_demo.serial_protocol import MockSerialTransport, SerialCommandProcessor


class InteractiveE1Tests(unittest.TestCase):
    def setUp(self):
        self.engine = server.app.state.interactive_engine
        self.engine.reset()

    def tearDown(self):
        self.engine.reset()

    def test_geometry_is_the_expected_stim_distance_three_layout(self):
        geometry = self.engine.geometry
        self.assertEqual(geometry.data_qubits, (1, 3, 5, 8, 10, 12, 15, 17, 19))
        self.assertEqual(tuple(site.stim_qubit for site in geometry.checks), (2, 9, 11, 13, 14, 16, 18, 25))
        self.assertEqual(tuple((site.x, site.y) for site in geometry.checks), (
            (2, 0), (2, 2), (4, 2), (6, 2), (0, 4), (2, 4), (4, 4), (4, 6)
        ))
        self.assertEqual(tuple(site.basis for site in CHECK_SITES), ("X", "Z", "X", "Z", "Z", "X", "Z", "X"))
        self.assertEqual((geometry.detector_count, geometry.observable_count, geometry.measurement_count), (40, 1, 49))
        self.assertEqual([sum(loc.check_index == i for loc in geometry.detector_locations) for i in range(8)], [4, 6, 4, 6, 6, 4, 6, 4])

    def test_fault_signature_is_derived_from_stim_and_maps_to_check_time_slice(self):
        state = self.engine.inject_and_prepare_syndrome(data_index=4, pauli="X")
        self.assertEqual(state["transitions"], ["idle", "injected", "syndrome_ready"])
        self.assertEqual(state["fault_input"], {
            "data_index": 4,
            "stim_qubit": 10,
            "pauli": "X",
            "known_simulated_input": True,
            "injection_after_measurement_round": 1,
        })
        self.assertEqual([i for i, bit in enumerate(state["detector_events"]) if bit], [5, 10])
        self.assertIsNone(state["simulation_reference"])
        frame = state["detector_frames"][1]
        self.assertEqual(frame["valid"], [True] * 8)
        self.assertEqual([i for i, bit in enumerate(frame["events"]) if bit], [1, 6])
        self.assertEqual(state["detector_frames"][0]["valid"], [False, True, False, True, True, False, True, False])

    def test_second_fault_signature_and_fixed_seed_reproducibility(self):
        first = self.engine.inject_and_prepare_syndrome(data_index=0, pauli="X")
        self.assertEqual([i for i, bit in enumerate(first["detector_events"]) if bit], [5])
        self.engine.reset()
        second = self.engine.inject_and_prepare_syndrome(data_index=0, pauli="X")
        self.assertEqual(second["detector_events"], first["detector_events"])
        self.assertIsNone(second["simulation_reference"])

    def test_all_single_pauli_inputs_produce_valid_stim_derived_signatures(self):
        for data_index in range(9):
            for pauli in ("X", "Y", "Z"):
                with self.subTest(data_index=data_index, pauli=pauli):
                    if self.engine.phase != "idle":
                        self.engine.reset()
                    state = self.engine.inject_and_prepare_syndrome(data_index, pauli)
                    self.assertEqual(len(state["detector_events"]), 40)
                    self.assertTrue(set(state["detector_events"]) <= {0, 1})
                    self.assertEqual(len(state["detector_frames"]), 6)
                    for frame in state["detector_frames"]:
                        self.assertEqual(len(frame["valid"]), 8)
                        self.assertEqual(len(frame["events"]), 8)

    def test_state_machine_and_decoder_gets_detectors_only(self):
        class SpyDecoder:
            def __init__(self):
                self.seen = None

            def decode(self, detectors):
                self.seen = np.array(detectors, copy=True)
                return np.array([0], dtype=np.uint8)

        spy = SpyDecoder()
        demo = InteractiveDemoEngine(server.make_circuit, lambda _p: spy)
        self.assertEqual(demo.snapshot()["phase"], "idle")
        syndrome = demo.inject_and_prepare_syndrome(4, "X")
        self.assertEqual(syndrome["phase"], "syndrome_ready")
        self.assertIsNone(syndrome["simulation_reference"])
        with self.assertRaises(InvalidTransition):
            demo.inject_and_prepare_syndrome(0, "Z")
        decoded = demo.decode()
        self.assertEqual(decoded["transitions"], ["idle", "injected", "syndrome_ready", "decoded"])
        self.assertEqual(spy.seen.tolist(), syndrome["detector_events"])
        self.assertEqual(decoded["decoder"]["predicted_logical_observable"], 0)
        self.assertEqual(decoded["simulation_reference"]["logical_observable"], 0)
        self.assertTrue(decoded["simulation_reference"]["correct"])
        self.assertIsNone(decoded["correction_map"])
        reset = demo.reset()
        self.assertEqual(reset["phase"], "idle")
        self.assertEqual(reset["transitions"][-2:], ["reset", "idle"])
        self.assertIsNone(reset["fault_input"])

    def test_real_pymatching_decodes_one_controlled_signature_without_sampling(self):
        state = self.engine.inject_and_prepare_syndrome(4, "X")
        # This exercises one deterministic decode, not a performance or LER test.
        decoded = self.engine.decode()
        self.assertEqual(decoded["decoder"]["name"], "PyMatching nominal educational decoder")
        self.assertIn(decoded["simulation_reference"]["logical_observable"], (0, 1))
        self.assertIn(decoded["decoder"]["predicted_logical_observable"], (0, 1))
        self.assertEqual(decoded["detector_events"], state["detector_events"])

    def test_api_validation_transitions_and_batch_endpoints_remain_separate(self):
        with TestClient(server.app) as client:
            self.assertEqual(client.get("/interactive").status_code, 200)
            initial = client.get("/api/interactive/state").json()
            self.assertEqual(initial["phase"], "idle")
            self.assertEqual(initial["transport"], "desktop_mock_no_esp32_connected")
            self.assertEqual(client.post("/api/interactive/decode", json={}).status_code, 409)
            self.assertEqual(client.post("/api/interactive/inject", json={"data_index": 9, "pauli": "X"}).status_code, 422)
            self.assertEqual(client.post("/api/interactive/inject", json={"data_index": "4", "pauli": "X"}).status_code, 422)
            injected = client.post("/api/interactive/inject", json={"data_index": 4, "pauli": "X"})
            self.assertEqual(injected.status_code, 200, injected.text)
            self.assertEqual(injected.json()["phase"], "syndrome_ready")
            decoded = client.post("/api/interactive/decode", json={})
            self.assertEqual(decoded.status_code, 200)
            self.assertEqual(decoded.json()["phase"], "decoded")
            reset = client.post("/api/interactive/reset", json={})
            self.assertEqual(reset.status_code, 200)
            self.assertEqual(reset.json()["phase"], "idle")
            paths = set(server.app.openapi()["paths"])
            self.assertTrue({"/api/run", "/api/run/{job_id}", "/api/health", "/interactive"} <= paths)

    def test_serial_handshake_ack_duplicate_malformed_and_reconnection(self):
        now = [0.0]
        processor = SerialCommandProcessor(self.engine, clock=lambda: now[0])
        device = MockSerialTransport(processor)
        connected = device.connect("test-device-a")
        self.assertEqual(connected[0]["type"], "ack")
        self.assertTrue(connected[0]["accepted"])
        self.assertEqual(connected[1]["type"], "state")
        self.assertEqual(connected[1]["state"]["phase"], "idle")

        now[0] = 1.0
        raw = json.dumps({
            "v": 1, "type": "button", "session_id": "test-device-a", "seq": 1,
            "button": "inject_error", "data_index": 4, "pauli": "X",
        })
        first = processor.handle_line(raw)
        run_id = first[1]["state"]["run_id"]
        duplicate = processor.handle_line(raw)
        self.assertTrue(first[0]["accepted"])
        self.assertTrue(duplicate[0]["duplicate"])
        self.assertEqual(duplicate[1]["state"]["run_id"], run_id)
        self.assertEqual(self.engine.phase, "syndrome_ready")

        malformed = processor.handle_line("{not-json}\n")
        self.assertFalse(malformed[0]["accepted"])
        self.assertEqual(malformed[0]["error"], "malformed_json")
        changed = processor.handle_line(raw.replace('"X"', '"Z"'))
        self.assertFalse(changed[0]["accepted"])
        self.assertEqual(changed[0]["error"], "sequence_reused_with_different_payload")

        device.session_id = "test-device-a"
        device.connected = True
        device.next_seq = 2
        device.disconnect()
        with self.assertRaises(ConnectionError):
            device.press("decode")
        restored = device.reconnect()
        self.assertEqual(restored[1]["state"]["phase"], "syndrome_ready")
        self.assertEqual(restored[1]["state"]["run_id"], run_id)
        decoded = device.press("decode")
        self.assertTrue(decoded[0]["accepted"])
        self.assertEqual(decoded[1]["state"]["phase"], "decoded")
        reset = device.press("reset")
        self.assertEqual(reset[1]["state"]["phase"], "idle")

    def test_serial_button_debounce_and_unknown_button_are_fail_closed(self):
        now = [10.0]
        processor = SerialCommandProcessor(self.engine, clock=lambda: now[0])
        processor.handle_line(json.dumps({"v": 1, "type": "hello", "session_id": "debounce", "seq": 0}))
        first = processor.handle_line(json.dumps({
            "v": 1, "type": "button", "session_id": "debounce", "seq": 1, "button": "reset"
        }))
        now[0] += 0.02
        second = processor.handle_line(json.dumps({
            "v": 1, "type": "button", "session_id": "debounce", "seq": 2, "button": "reset"
        }))
        self.assertTrue(first[0]["accepted"])
        self.assertFalse(second[0]["accepted"])
        self.assertEqual(second[0]["error"], "debounced")
        unknown = processor.handle_line(json.dumps({
            "v": 1, "type": "button", "session_id": "debounce", "seq": 3, "button": []
        }))
        self.assertFalse(unknown[0]["accepted"])
        self.assertEqual(unknown[0]["error"], "unknown_button")

    def test_serial_bridge_runs_against_a_loopback_port_mock(self):
        class FakeSerialPort:
            def __init__(self):
                self.incoming = queue.Queue()
                self.writes = []
                self.closed = False

            def read(self, _size):
                try:
                    return self.incoming.get(timeout=0.03)
                except queue.Empty:
                    return b""

            def write(self, data):
                self.writes.append(bytes(data))
                return len(data)

            def close(self):
                self.closed = True

        fake = FakeSerialPort()
        processor = SerialCommandProcessor(self.engine, clock=time.monotonic)
        worker = SerialBridgeWorker(
            "MOCK-COM", processor,
            serial_factory=lambda _port, **_kwargs: fake,
            reconnect_seconds=0.02,
        ).start()
        try:
            deadline = time.monotonic() + 2
            while not worker.connected and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(worker.connected)
            fake.incoming.put(b'{"v":1,"type":"hello","session_id":"loopback","seq":0}\n')
            deadline = time.monotonic() + 2
            while len(fake.writes) < 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertGreaterEqual(len(fake.writes), 2)
            hello_reply = [json.loads(line) for line in fake.writes[:2]]
            self.assertTrue(hello_reply[0]["accepted"])
            self.assertEqual(hello_reply[1]["type"], "state")

            fake.incoming.put(b'{"v":1,"type":"button","session_id":"loopback","seq":1,"button":"inject_error"}\n')
            deadline = time.monotonic() + 2
            while len(fake.writes) < 4 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertGreaterEqual(len(fake.writes), 4)
            action_reply = [json.loads(line) for line in fake.writes[2:4]]
            self.assertTrue(action_reply[0]["accepted"])
            self.assertEqual(action_reply[1]["state"]["phase"], "syndrome_ready")
            self.assertEqual(self.engine.phase, "syndrome_ready")
        finally:
            worker.stop()
        self.assertFalse(worker.connected)
        self.assertTrue(fake.closed)

    def test_interactive_package_is_exhibition_scoped_and_has_no_research_file_io(self):
        package_root = Path(server.__file__).resolve().parent / "interactive_demo"
        self.assertTrue(package_root.is_relative_to(Path(server.__file__).resolve().parent))
        forbidden_import_roots = {"outputs", "dashboard", "research", "stage5"}
        for source_path in package_root.glob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = {alias.name.split(".", 1)[0].lower() for alias in node.names}
                    self.assertFalse(names & forbidden_import_roots)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".", 1)[0].lower(), forbidden_import_roots)
            text = source_path.read_text(encoding="utf-8").lower()
            self.assertNotIn("sys.path", text)
            self.assertNotIn("read_bytes(", text)
            self.assertNotIn("np.load(", text)
        self.assertEqual(server.ROOT.resolve(), Path(server.__file__).resolve().parent)

    def test_source_uses_tableau_measurements_not_stim_sampler(self):
        engine_source = (
            Path(server.__file__).resolve().parent / "interactive_demo" / "engine.py"
        ).read_text(encoding="utf-8")
        self.assertIn("TableauSimulator", engine_source)
        self.assertNotIn("compile_detector_sampler", engine_source)
        self.assertNotIn(".sample(", engine_source)


if __name__ == "__main__":
    unittest.main()
