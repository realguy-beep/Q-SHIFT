from __future__ import annotations

import json
import io
import logging
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as dashboard_app  # noqa: E402
import configuration  # noqa: E402
import manager as manager_module  # noqa: E402
import qshift_stats  # noqa: E402
import seed_protocol  # noqa: E402
import storage  # noqa: E402
import telemetry  # noqa: E402
from analyze_saved_run import calibration_summary, confusion  # noqa: E402
from manager import WorkerManager  # noqa: E402
from structured_decoder import (DetectorGridEncoder, StructuredConv3DDecoder,
                               apply_residual_correction, residual_training_target)  # noqa: E402
from structured_protocol import build_inventory  # noqa: E402


class SeedAndConfigTests(unittest.TestCase):
    def test_smoke_seed_streams_are_disjoint_and_reproducible(self):
        cfg = configuration.validate_config({})
        a = seed_protocol.seed_plan(cfg["seed"], cfg["training_shots"], cfg["validation_shots"],
                                    cfg["test_shots"], cfg["batch_size"])
        b = seed_protocol.seed_plan(cfg["seed"], cfg["training_shots"], cfg["validation_shots"],
                                    cfg["test_shots"], cfg["batch_size"])
        self.assertEqual(a, b)
        self.assertTrue(a["no_overlap_within_run"])
        self.assertEqual(a["shots"], {"train": 8000, "validation": 1000, "test": 1000})
        self.assertNotEqual(seed_protocol.batch_seed(a, "train", 0),
                            seed_protocol.batch_seed(a, "validation", 0))
        self.assertNotEqual(seed_protocol.batch_seed(a, "validation", 0),
                            seed_protocol.batch_seed(a, "test", 0))
        self.assertTrue(seed_protocol.screen_plan(a)["passed"])

    def test_invalid_configuration_and_large_run_confirmation(self):
        with self.assertRaises(ValueError):
            configuration.validate_config({"distance": 5})
        with self.assertRaises(ValueError):
            configuration.validate_config({"gate_p": 0.2})
        with self.assertRaises(ValueError):
            configuration.validate_config({"device": "shell"})
        self.assertEqual(configuration.needs_confirmation(10_000), None)
        self.assertEqual(configuration.needs_confirmation(10_001), "large")
        self.assertEqual(configuration.needs_confirmation(100_000_000), "extreme")

    def test_api_preset_applies_default_budgets_when_omitted(self):
        cfg = dashboard_app.resolve_config({"preset": "pipeline"})
        self.assertEqual((cfg["training_shots"], cfg["validation_shots"], cfg["test_shots"]),
                         (100_000, 5_000, 5_000))


class MetricAndStorageTests(unittest.TestCase):
    def test_paired_metric_counts_and_intervals(self):
        y = np.array([0, 1, 0, 1], dtype=np.uint8)
        pred = {
            "pymatching": np.array([0, 0, 1, 1], dtype=np.uint8),
            "direct_neural": np.array([1, 1, 0, 1], dtype=np.uint8),
        }
        result = qshift_stats.compare_predictions(y, pred)
        self.assertEqual(result["pymatching"]["errors"], 2)
        pair = result["direct_neural"]["paired_vs_pymatching"]
        self.assertEqual(pair["candidate_only_failures"], 1)
        self.assertEqual(pair["pymatching_only_failures"], 2)
        self.assertEqual(pair["prediction_disagreements"], 3)
        self.assertEqual(pair["exact_mcnemar_two_sided_p_descriptive"], 1.0)
        lo, hi = result["direct_neural"]["wilson95"]
        self.assertLessEqual(lo, result["direct_neural"]["ler"])
        self.assertGreaterEqual(hi, result["direct_neural"]["ler"])

    def test_metric_rejects_nonbinary_predictions(self):
        with self.assertRaises(ValueError):
            qshift_stats.compare_predictions(np.array([0, 1]), {"pymatching": np.array([0, 2])})

    def test_sqlite_run_and_metric_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "runs.sqlite3"
            storage.init_db(db)
            plan = {"stream_ranges_inclusive": {}, "shots": {"train": 1}}
            storage.create_run("abc", {"training_shots": 1}, plan, db)
            event = {"type": "progress", "status": "running", "training_samples_processed": 1}
            storage.append_event("abc", event, db)
            row = storage.get_run("abc", db)
            self.assertEqual(row["status"], "running")
            self.assertEqual(row["state"]["status"], "running")
            self.assertEqual(row["state"]["progress"]["training_samples_processed"], 1)
            self.assertEqual(storage.get_metrics("abc", db_path=db)[0]["payload"], event)

    def test_missing_cuda_telemetry_is_explicit(self):
        with patch.object(telemetry.importlib.util, "find_spec", return_value=None), \
             patch.object(telemetry, "gpu_snapshot", return_value={"available": False, "unavailable_reason": "test"}):
            info = telemetry.device_snapshot()
        self.assertFalse(info["cuda_available"])
        self.assertIn("not installed", info["cuda_unavailable_reason"])
        self.assertFalse(info["gpu"]["available"])

    def test_cuda_ready_uses_torch_availability_and_reports_python(self):
        info = telemetry.device_snapshot()
        import torch
        self.assertEqual(info["python_executable"], sys.executable)
        self.assertEqual(info["cuda_available"], bool(torch.cuda.is_available()))

    def test_partial_nvml_failure_falls_back_per_metric_to_nvidia_smi(self):
        class FakeNVML:
            NVML_TEMPERATURE_GPU = 0
            @staticmethod
            def nvmlDeviceGetHandleByIndex(_index): return object()
            @staticmethod
            def nvmlDeviceGetName(_handle): return b"NVIDIA test GPU"
            @staticmethod
            def nvmlDeviceGetUtilizationRates(_handle): raise RuntimeError("simulated NVML utilization failure")
            @staticmethod
            def nvmlDeviceGetMemoryInfo(_handle): return SimpleNamespace(used=100, total=1000)
            @staticmethod
            def nvmlDeviceGetTemperature(_handle, _sensor): raise RuntimeError("simulated unsupported temperature")
            @staticmethod
            def nvmlDeviceGetPowerUsage(_handle): raise RuntimeError("simulated unsupported power")

        fallback = {"available": True, "name": "NVIDIA test GPU", "utilization_percent": 37,
                    "memory_used_bytes": 200, "memory_total_bytes": 2000, "memory_percent": 10.0,
                    "temperature_c": 49.0, "power_watts": 12.0, "source": "nvidia-smi", "provider_errors": []}
        test_logger = logging.Logger("qshift.test.telemetry.fallback")
        test_logger.addHandler(logging.StreamHandler(io.StringIO()))
        with patch.object(telemetry, "_logger", test_logger), \
             patch.object(telemetry, "_nvml", FakeNVML), patch.object(telemetry, "_nvml_error", None), \
             patch.object(telemetry, "_nvidia_smi_snapshot", return_value=(fallback, [])):
            result = telemetry.gpu_snapshot()
        self.assertTrue(result["available"])
        self.assertEqual(result["source"], "NVML + nvidia-smi")
        self.assertEqual(result["utilization_percent"], 37)
        self.assertEqual(result["temperature_c"], 49.0)
        self.assertEqual(result["power_watts"], 12.0)
        self.assertTrue(any("simulated NVML utilization failure" in error for error in result["provider_errors"]))

    def test_total_nvml_failure_uses_nvidia_smi_fallback(self):
        class BrokenNVML:
            @staticmethod
            def nvmlDeviceGetHandleByIndex(_index): raise RuntimeError("Unknown Error")

        fallback = {"available": True, "name": "NVIDIA fallback GPU", "utilization_percent": 14,
                    "memory_used_bytes": 1024, "memory_total_bytes": 4096, "memory_percent": 25.0,
                    "temperature_c": 42.0, "power_watts": 10.0, "source": "nvidia-smi", "provider_errors": []}
        test_logger = logging.Logger("qshift.test.telemetry.total_failure")
        test_logger.addHandler(logging.StreamHandler(io.StringIO()))
        with patch.object(telemetry, "_logger", test_logger), \
             patch.object(telemetry, "_nvml", BrokenNVML), patch.object(telemetry, "_nvml_error", None), \
             patch.object(telemetry, "_nvidia_smi_snapshot", return_value=(fallback, [])):
            result = telemetry.gpu_snapshot()
        self.assertTrue(result["available"])
        self.assertEqual(result["source"], "nvidia-smi fallback")
        self.assertEqual(result["utilization_percent"], 14)
        self.assertTrue(any("Unknown Error" in error for error in result["provider_errors"]))

    def test_telemetry_exception_log_retains_traceback(self):
        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        logger = logging.Logger("qshift.test.telemetry.traceback")
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        try:
            with patch.object(telemetry, "_logger", logger):
                try:
                    raise RuntimeError("sentinel telemetry failure")
                except RuntimeError as exc:
                    telemetry._log_provider_error("test-provider", "test-operation", exc)
        finally:
            logger.removeHandler(handler)
        self.assertIn("Traceback (most recent call last)", captured.getvalue())
        self.assertIn("sentinel telemetry failure", captured.getvalue())


class StructuredDecoderTests(unittest.TestCase):
    def test_diagnostic_confusion_and_calibration_metrics(self):
        table = confusion(np.array([0, 0, 1, 1]), np.array([0, 1, 0, 0]))
        self.assertEqual(table["matrix_true_rows_predicted_columns"], [[1, 1], [2, 0]])
        metrics = calibration_summary(np.array([0, 1]), np.array([.2, .8]))
        self.assertAlmostEqual(metrics["brier_score"], .04)
        self.assertAlmostEqual(metrics["log_loss"], -np.log(.8))
        self.assertEqual(sum(metrics["probability_histogram_10_bins"]), 2)

    def test_detector_coordinates_preserve_space_and_round_channels(self):
        coordinates = {0: [0, 0, 0], 1: [2, 0, 0], 2: [0, 2, 1]}
        encoder = DetectorGridEncoder(coordinates)
        encoded = encoder(torch.tensor([[1, 0, 1]], dtype=torch.float32))
        self.assertEqual(tuple(encoded.shape), (1, 2, 2, 2, 2))
        self.assertEqual(float(encoded[0, 0, 0, 0, 0]), 1.0)
        self.assertEqual(float(encoded[0, 0, 0, 0, 1]), 0.0)
        self.assertEqual(float(encoded[0, 0, 1, 1, 0]), 1.0)
        self.assertEqual(float(encoded[0, 1].sum()), 3.0)

    def test_qshift_stim_coordinates_make_expected_round_geometry(self):
        from simulator import prepare
        circuit, _, _, _, _, _ = prepare(configuration.DEFAULT_CONFIG)
        encoder = DetectorGridEncoder(circuit.get_detector_coordinates())
        encoded = encoder(torch.zeros((2, circuit.num_detectors), dtype=torch.float32))
        self.assertEqual(tuple(encoded.shape), (2, 2, 6, 4, 4))
        self.assertEqual([int(v) for v in encoder.occupancy[0, 0].sum(dim=(1, 2))], [4, 8, 8, 8, 8, 4])

    def test_structured_decoder_emits_one_logit_per_sample(self):
        coordinates = {0: [0, 0, 0], 1: [2, 0, 0], 2: [0, 2, 1], 3: [2, 2, 1]}
        model = StructuredConv3DDecoder(coordinates, channels=4, dropout=0.0).eval()
        output = model(torch.tensor([[0, 1, 0, 1], [1, 1, 0, 0]], dtype=torch.float32))
        self.assertEqual(tuple(output.shape), (2,))
        self.assertTrue(torch.isfinite(output).all())
        probabilities = torch.sigmoid(output)
        predictions = (probabilities >= .5).to(torch.uint8)
        self.assertTrue(torch.all((probabilities >= 0) & (probabilities <= 1)))
        self.assertTrue(torch.all((predictions == 0) | (predictions == 1)))
        output.sum().backward()
        self.assertIsNotNone(model.net[0].weight.grad)

    def test_residual_target_and_xor_correction_convention(self):
        matching = torch.tensor([0, 1, 1, 0], dtype=torch.uint8)
        observable = torch.tensor([1, 1, 0, 0], dtype=torch.uint8)
        target = residual_training_target(matching, observable)
        self.assertEqual(target.tolist(), [1.0, 0.0, 1.0, 0.0])
        corrected = apply_residual_correction(matching, target)
        self.assertEqual(corrected.tolist(), observable.tolist())
        with self.assertRaises(ValueError):
            residual_training_target(torch.tensor([0, 2]), torch.tensor([0, 1]))

    def test_prospective_100k_streams_are_unique_and_separate(self):
        inventory = build_inventory(prior_allocations=[])
        self.assertTrue(inventory["passed"], inventory["collisions"])
        self.assertEqual(inventory["derived_seed_count_including_model"], inventory["unique_seed_count"])
        by_split = {split: set(seed for stream in inventory["streams"] if stream["split"] == split
                               for seed in stream["seeds"]) for split in ("train", "validation", "test")}
        self.assertFalse(by_split["train"] & by_split["validation"])
        self.assertFalse(by_split["train"] & by_split["test"])
        self.assertFalse(by_split["validation"] & by_split["test"])


class ControlAndApiTests(unittest.TestCase):
    def test_progress_endpoint_survives_refresh_and_reports_terminal_state(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "runs.sqlite3"
            with patch.object(storage, "DB_PATH", db):
                storage.init_db()
                with TestClient(dashboard_app.app, client=("127.0.0.1", 54327)) as client:
                    # Create after lifespan recovery so this fixture represents a live job,
                    # rather than a queued job recovered as interrupted on backend start.
                    storage.create_run("progress-snapshot", {"training_shots": 1000}, {})
                    progress = {"type": "progress", "status": "running", "phase": "decoding",
                                "completed_shots": 350, "total_shots": 2000,
                                "throughput_shots_s": 21.5, "eta_seconds": 76.7,
                                "stage_counts": {"simulation": 500, "decoding": 350}}
                    storage.append_event("progress-snapshot", progress)
                    live = client.get("/api/runs/progress-snapshot/progress").json()
                    self.assertEqual(live["progress"], progress)
                    self.assertEqual(live["status"], "running")
                    self.assertGreater(live["updated_at"], 0)
                    for status in ("completed", "failed", "cancelled", "interrupted", "paused"):
                        storage.append_event("progress-snapshot", {"type": status, "status": status,
                            "summary": {"terminal_status": status}, "error": "fixture failure" if status == "failed" else None})
                        terminal = client.get("/api/runs/progress-snapshot/progress").json()
                        self.assertEqual(terminal["status"], status)
                        self.assertEqual(terminal["summary"]["terminal_status"], status)

    def test_worker_failure_log_preserves_traceback_and_marks_interrupted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db, runs = root / "runs.sqlite3", root / "runs"
            run_id = "worker-log-error"
            with patch.object(storage, "DB_PATH", db), patch.object(manager_module, "RUNS_DIR", runs):
                storage.init_db()
                storage.create_run(run_id, {}, {})
                class FailedProcess:
                    stdout = io.StringIO("Traceback (most recent call last):\n  File 'worker.py', line 1\nValueError: bad sample\n")
                    def wait(self): return 1
                WorkerManager()._drain(run_id, FailedProcess())
                log = (runs / run_id / "worker.log").read_text(encoding="utf-8")
                self.assertIn("Traceback (most recent call last):", log)
                self.assertIn("ValueError: bad sample", log)
                self.assertEqual(storage.get_run(run_id)["status"], "interrupted")
                self.assertIn("ValueError: bad sample", storage.get_run(run_id)["error"])

    def test_websocket_snapshot_closes_subscribe_race(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "runs.sqlite3"
            with patch.object(storage, "DB_PATH", db):
                storage.init_db()
                storage.create_run("ws-progress-race", {}, {})
                original = dashboard_app.manager.subscribe
                event = {"type": "progress", "status": "running", "phase": "simulation",
                         "completed_shots": 17, "total_shots": 100}
                def subscribe_then_write(run_id):
                    queue = original(run_id)
                    storage.append_event(run_id, event)
                    return queue
                with patch.object(dashboard_app.manager, "subscribe", side_effect=subscribe_then_write):
                    with TestClient(dashboard_app.app, client=("127.0.0.1", 54328)) as client:
                        with client.websocket_connect("/ws/ws-progress-race") as websocket:
                            snapshot = websocket.receive_json()
                            self.assertEqual(snapshot["type"], "snapshot")
                            self.assertEqual(snapshot["run"]["state"]["progress"], event)

    def test_loopback_ipv4_dashboard_health_and_control_routes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db, run_root = root / "runs.sqlite3", root / "runs"
            run_id = "control-local-test"
            run_dir = run_root / run_id
            run_dir.mkdir(parents=True)
            (run_dir / "checkpoint.pt").write_bytes(b"safe checkpoint fixture")
            with patch.object(storage, "DB_PATH", db), patch.object(dashboard_app, "RUNS_DIR", run_root), \
                 patch.object(manager_module, "RUNS_DIR", run_root):
                storage.init_db()
                storage.create_run(run_id, {}, {})
                storage.update_run(run_id, status="paused")
                with TestClient(dashboard_app.app, client=("127.0.0.1", 54321)) as client:
                    page = client.get("/")
                    self.assertEqual(page.status_code, 200)
                    self.assertIn("Q-SHIFT", page.text)
                    self.assertIn('id="autonomous-view"', page.text)
                    self.assertIn('id="autonomous-test-status"', page.text)
                    health = client.get("/api/health")
                    self.assertEqual(health.status_code, 200)
                    self.assertIn("telemetry", health.json())
                    runs = client.get("/api/runs")
                    self.assertEqual(runs.status_code, 200)
                    control = client.post(f"/api/runs/{run_id}/control", json={"action": "checkpoint"})
                    self.assertEqual(control.status_code, 200)
                    self.assertEqual(control.json()["result"], {"checkpoint": "already available"})

    def test_loopback_ipv6_websocket_and_health(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "runs.sqlite3"
            with patch.object(storage, "DB_PATH", db):
                storage.init_db()
                storage.create_run("ws-local-test", {}, {})
                with TestClient(dashboard_app.app, client=("::1", 54322)) as client:
                    self.assertEqual(client.get("/api/health").status_code, 200)
                    with client.websocket_connect("/ws/ws-local-test") as websocket:
                        self.assertEqual(websocket.receive_json()["type"], "snapshot")

    def test_remote_client_and_forwarded_loopback_spoof_get_normal_403(self):
        remote_client = TestClient(dashboard_app.app, client=("203.0.113.9", 54323))
        with self.assertLogs("qshift.security", level="WARNING") as captured:
            response = remote_client.get("/api/health", headers={"x-forwarded-for": "127.0.0.1"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Q-SHIFT controls accept localhost connections only.")
        self.assertIn("peer='203.0.113.9'", captured.output[0])
        self.assertIn("x_forwarded_for='127.0.0.1'", captured.output[0])

    def test_forwarded_remote_value_cannot_reject_or_rewrite_loopback_peer(self):
        with TestClient(dashboard_app.app, client=("127.0.0.1", 54324)) as client:
            response = client.get("/api/health", headers={"x-forwarded-for": "203.0.113.9"})
        self.assertEqual(response.status_code, 200)

    def test_remote_websocket_spoof_is_closed_before_accept(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "runs.sqlite3"
            with patch.object(storage, "DB_PATH", db):
                storage.init_db()
                storage.create_run("ws-remote-test", {}, {})
                client = TestClient(dashboard_app.app, client=("203.0.113.10", 54325))
                with self.assertLogs("qshift.security", level="WARNING"):
                    with self.assertRaises(WebSocketDisconnect) as raised:
                        with client.websocket_connect("/ws/ws-remote-test",
                                                      headers={"x-forwarded-for": "::1"}):
                            self.fail("remote websocket should not be accepted")
                self.assertEqual(raised.exception.code, 1008)

    def test_ipv4_mapped_ipv6_and_dual_loopback_bindings(self):
        self.assertTrue(dashboard_app.is_loopback("::1"))
        self.assertTrue(dashboard_app.is_loopback("127.0.0.1"))
        self.assertTrue(dashboard_app.is_loopback("::ffff:127.0.0.1"))
        self.assertFalse(dashboard_app.is_loopback("localhost"))
        self.assertFalse(dashboard_app.is_loopback("203.0.113.1"))
        listeners = dashboard_app._bind_loopback_sockets(0)
        try:
            self.assertEqual({sock.family for sock in listeners}, {dashboard_app.socket.AF_INET,
                                                                  dashboard_app.socket.AF_INET6})
            self.assertEqual({sock.getsockname()[1] for sock in listeners}.__len__(), 1)
            self.assertEqual({sock.getsockname()[0] for sock in listeners}, {"127.0.0.1", "::1"})
        finally:
            for sock in listeners:
                sock.close()
        server_config = dashboard_app._uvicorn_config(8765)
        self.assertFalse(server_config.proxy_headers)
        self.assertEqual(server_config.forwarded_allow_ips, "")


    @staticmethod
    def _write_json(path: Path, payload: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_snapshot_uses_only_hash_verified_persisted_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            prediction_bytes = b"prediction fixture; not an experiment sample"
            prediction_hash = __import__("hashlib").sha256(prediction_bytes).hexdigest()
            (run / "predictions").mkdir()
            (run / "job_results").mkdir()
            (run / "predictions" / "root00_position_flat_cnn_3000.npz").write_bytes(prediction_bytes)
            self._write_json(run / "progress.json", {
                "status": "running", "completed_jobs": ["root00_position_flat_cnn_3000"],
                "current_root": 0, "current_job": "root00_position_flat_cnn_3000",
                "active_wall_seconds": 123, "gpu_training_seconds": 45,
                "independent_test_access": 0,
            })
            self._write_json(run / "job_results" / "root00_position_flat_cnn_3000.json", {
                "status": "completed", "job_id": "root00_position_flat_cnn_3000",
                "model": "position_flat_cnn", "root_id": 0, "shots": 3,
                "train_size_per_regime": 3000, "predictions_sha256": prediction_hash,
                "per_regime": {"balanced": {"shots": 3, "ler": 0.1, "pymatching_ler": 0.2}},
                "history": [{"epoch": 1, "monitor_nll": 0.5}],
            })
            data_npz = b"root data fixture"
            (run / "data").mkdir()
            (run / "data" / "root_00.npz").write_bytes(data_npz)
            self._write_json(run / "data" / "root_00.json", {
                "root_id": 0, "sha256": __import__("hashlib").sha256(data_npz).hexdigest(),
                "splits": {"train__balanced": {"shots": 30}, "monitor__balanced": {"shots": 4}},
            })

            snapshot = dashboard_app.autonomous_run_snapshot(run)
            self.assertEqual(snapshot["status"], "running")
            self.assertEqual(snapshot["completed_jobs"], 1)
            self.assertEqual(snapshot["verified_jobs"], 1)
            self.assertEqual(snapshot["shot_counts"]["train"], 30)
            self.assertEqual(snapshot["shot_counts"]["monitor"], 4)
            self.assertEqual(snapshot["results"][0]["model_label"], "Position-preserving CNN")
            self.assertEqual(snapshot["results"][0]["history"], [{"epoch": 1, "monitor_nll": 0.5}])
            self.assertIn("SEALED", snapshot["independent_test_status"])

            # A changed prediction archive invalidates that result; no metrics leak through.
            (run / "predictions" / "root00_position_flat_cnn_3000.npz").write_bytes(b"changed")
            rejected = dashboard_app.autonomous_run_snapshot(run)
            self.assertEqual(rejected["verified_jobs"], 0)
            self.assertEqual(rejected["results"], [])
            self.assertTrue(rejected["warnings"])

    def test_partial_progress_is_graceful_and_route_is_get_only(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "progress.json").write_text('{"status":', encoding="utf-8")
            snapshot = dashboard_app.autonomous_run_snapshot(run)
            self.assertFalse(snapshot["available"])
            self.assertEqual(snapshot["status"], "unknown")
            with patch.object(dashboard_app, "AUTONOMOUS_RUN_DIR", run), \
                 patch.object(storage, "DB_PATH", run / "dashboard.sqlite3"):
                with TestClient(dashboard_app.app, client=("127.0.0.1", 54326)) as client:
                    response = client.get("/api/autonomous-research")
                    self.assertEqual(response.status_code, 200)
                    self.assertFalse(response.json()["available"])
                    self.assertEqual(client.post("/api/autonomous-research").status_code, 405)

    def test_pause_checkpoint_and_resume_controls(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db, runs = root / "db.sqlite3", root / "runs"
            with patch.object(storage, "DB_PATH", db), patch.object(manager_module, "RUNS_DIR", runs):
                storage.init_db()
                run_id = "control-run"
                run_dir = runs / run_id
                run_dir.mkdir(parents=True)
                (run_dir / "config.json").write_text("{}", encoding="utf-8")
                storage.create_run(run_id, {}, {})
                service = WorkerManager()

                class Process:
                    def poll(self):
                        return None

                service.processes[run_id] = Process()
                service.control(run_id, "pause")
                self.assertEqual((run_dir / "control.request").read_text(), "pause")
                self.assertEqual(storage.get_run(run_id)["status"], "pausing")
                service.control(run_id, "checkpoint")
                self.assertTrue((run_dir / "checkpoint.request").exists())
                (run_dir / "checkpoint.pt").write_bytes(b"checkpoint fixture")
                storage.update_run(run_id, status="paused")
                with patch.object(service, "start", return_value=321) as start:
                    self.assertEqual(service.control(run_id, "resume"), 321)
                    start.assert_called_once()
                with self.assertRaises(ValueError):
                    service.control(run_id, "exec")

    def test_api_start_requires_confirmation_and_prevents_duplicate_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db, runs = root / "db.sqlite3", root / "runs"
            with patch.object(storage, "DB_PATH", db), patch.object(dashboard_app, "RUNS_DIR", runs), \
                 patch.object(manager_module, "RUNS_DIR", runs), \
                 patch.object(dashboard_app.manager, "start", side_effect=lambda rid, path: (
                     storage.update_run(rid, status="running"), 12345)[1]) as start:
                storage.init_db()
                from fastapi import HTTPException
                from app import StartRequest

                def run_sync(coroutine):
                    try:
                        coroutine.send(None)
                    except StopIteration as finished:
                        return finished.value
                    raise AssertionError("route unexpectedly awaited an asynchronous operation")

                def exercise_routes():
                    over_budget = StartRequest(config={"preset": "pipeline", "training_shots": 20_000,
                                                       "validation_shots": 1000, "test_shots": 1000})
                    with self.assertRaises(HTTPException) as raised:
                        run_sync(dashboard_app.start_run(over_budget))
                    self.assertEqual(raised.exception.status_code, 428)
                    self.assertEqual(start.call_count, 0)
                    valid = StartRequest(config={"preset": "smoke", "seed": 1_800_200_001})
                    created = run_sync(dashboard_app.start_run(valid))
                    self.assertEqual(created["status"], "running")
                    run_id = created["run_id"]
                    duplicate = StartRequest(config={"seed": 1_800_300_001})
                    with self.assertRaises(HTTPException) as raised:
                        run_sync(dashboard_app.start_run(duplicate))
                    self.assertEqual(raised.exception.status_code, 409)
                    self.assertEqual(start.call_count, 1)
                    saved = run_sync(dashboard_app.get_run(run_id))
                    self.assertEqual(saved["run"]["id"], run_id)

                exercise_routes()

    def test_structured_api_uses_frozen_multiregime_allocation_and_keeps_test_reserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db, runs = root / "db.sqlite3", root / "runs"
            with patch.object(storage, "DB_PATH", db), patch.object(dashboard_app, "RUNS_DIR", runs), \
                 patch.object(manager_module, "RUNS_DIR", runs), \
                 patch.object(dashboard_app.manager, "start", side_effect=lambda rid, path: 12345):
                storage.init_db()
                from app import HTTPException, StartRequest

                def run_sync(coroutine):
                    try:
                        coroutine.send(None)
                    except StopIteration as finished:
                        return finished.value
                    raise AssertionError("route unexpectedly awaited an asynchronous operation")

                request = StartRequest(config={"worker_kind": "structured_3d_cnn",
                                               "model_selection": "direct_plus_residual",
                                               "preset": "smoke", "device": "cuda"},
                                       confirmed_large=True)
                created = run_sync(dashboard_app.start_run(request))
                self.assertEqual(created["status"], "running")
                self.assertEqual(created["test_samples_generated"], 0)
                saved_config = json.loads((Path(created["run_directory"]) / "config.json").read_text())
                self.assertEqual(saved_config["worker_kind"], "structured_3d_cnn")
                self.assertEqual(saved_config["training_shots"], 70_000)
                self.assertEqual(saved_config["validation_shots"], 15_000)
                self.assertEqual(saved_config["test_shots"], 15_000)
                plan = json.loads((Path(created["run_directory"]) / "seed_inventory.json").read_text())["plan"]
                self.assertIn("test_x_biased", plan["stream_ranges_inclusive"])
                self.assertIn("candidate_model_rng", plan["stream_ranges_inclusive"])


class ContractTests(unittest.TestCase):
    def test_worker_keeps_validation_training_and_test_order_separate(self):
        source = (ROOT / "worker.py").read_text(encoding="utf-8")
        val = source.index('split_samples(circuit, matching, plan, "validation"')
        train = source.index("for step_idx in range(start_step, steps_total):")
        test = source.index('split_samples(circuit, matching, plan, "test"')
        self.assertLess(val, train)
        self.assertLess(train, test)
        self.assertIn("Test is generated and read only after all gradient updates are complete.", source)
        self.assertIn('seed_plan(cfg["seed"]', source)

    def test_websocket_reconnect_is_bounded_and_resets_after_connect(self):
        source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("ws.onclose", source)
        self.assertIn("Math.min(30000, 500 * (2 ** Math.min(state.retry, 6)))", source)
        self.assertIn("ws.onopen", source)
        self.assertIn("state.retry = 0", source)


if __name__ == "__main__":
    unittest.main()
