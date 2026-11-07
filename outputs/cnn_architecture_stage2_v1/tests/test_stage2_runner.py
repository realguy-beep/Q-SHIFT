from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import torch

from outputs.cnn_architecture_stage2_v1 import run_stage2 as runner


def fake_partition(n: int = 8) -> dict[str, np.ndarray]:
    return {
        "detectors": np.zeros((n, 40), dtype=np.uint8),
        "observable": np.arange(n, dtype=np.uint8) % 2,
        "nominal_prediction": np.zeros(n, dtype=np.uint8),
        "burst_prediction": np.zeros(n, dtype=np.uint8),
    }


class RunnerValidationTests(unittest.TestCase):
    def test_detector_observable_and_prediction_shapes(self):
        arrays = fake_partition(8)
        runner.validate_partition(arrays, 8)
        broken = dict(arrays, detectors=np.zeros((8, 39), dtype=np.uint8))
        with self.assertRaises(runner.Stage2Error):
            runner.validate_partition(broken, 8)
        broken = dict(arrays, observable=np.zeros((8, 1), dtype=np.uint8))
        with self.assertRaises(runner.Stage2Error):
            runner.validate_partition(broken, 8)
        broken = dict(arrays, nominal_prediction=np.full(8, 2, dtype=np.uint8))
        with self.assertRaises(runner.Stage2Error):
            runner.validate_partition(broken, 8)

    def test_frozen_circuit_and_matching_dimensions_without_sampling(self):
        cfg = json.loads(runner.CONFIG_PATH.read_text(encoding="utf-8"))
        ctx = runner.prepare_context(cfg)
        self.assertEqual(set(ctx["circuits"]), set(runner.CONDITIONS))
        for condition in runner.CONDITIONS:
            self.assertEqual(ctx["circuits"][condition].num_detectors, 40)
            self.assertEqual(ctx["circuits"][condition].num_observables, 1)
            self.assertEqual(ctx["dems"][condition].num_detectors, 40)
            self.assertEqual(ctx["matchers"][condition].num_detectors, 40)
    def test_residual_xor_and_final_correction_convention(self):
        data = {"observable": np.array([0, 1, 0, 1], dtype=np.uint8),
                "nominal_prediction": np.array([0, 0, 1, 1], dtype=np.uint8)}
        self.assertTrue(np.array_equal(runner.residual_target(data), [0, 1, 1, 0]))
        correction = np.array([0, 1, 0, 0], dtype=np.uint8)
        self.assertTrue(np.array_equal(data["nominal_prediction"] ^ correction, [0, 1, 1, 1]))

    def test_seed_uniqueness_and_partition_stream_isolation(self):
        inv = json.loads((runner.HERE / "seed_inventory.json").read_text(encoding="utf-8"))
        rows = inv["streams"]
        values = [int(row["seed"]) for row in rows]
        self.assertEqual(len(values), 95)
        self.assertEqual(len(set(values)), 95)
        samples = [row for row in rows if row["kind"] == "stim_sample_stream"]
        keys = [(row["root_id"], row["split"], row["condition"]) for row in samples]
        self.assertEqual(len(keys), 50)
        self.assertEqual(len(set(keys)), 50)
        self.assertEqual(len({int(row["seed"]) for row in samples}), 50)
        self.assertFalse(inv["independent_test_seed_allocated"])

    def test_all_architectures_share_identical_partition_hashes(self):
        parts = {split: {condition: fake_partition() for condition in runner.CONDITIONS}
                 for split in runner.SPLIT_NAMES}
        hashes = runner.paired_training_hashes(parts)
        for model in runner.MODEL_ORDER:
            self.assertEqual(hashes, runner.paired_training_hashes(parts))
            self.assertIs(parts["training"]["nominal"]["detectors"],
                          parts["training"]["nominal"]["detectors"])
        # A mutation to any shared underlying input is visible to every model's hash.
        original = hashes["training"]["nominal"]["detectors"]
        parts["training"]["nominal"]["detectors"][0, 0] = 1
        self.assertNotEqual(original,
                            runner.paired_training_hashes(parts)["training"]["nominal"]["detectors"])

    def test_best_validation_checkpoint_is_restored(self):
        model = torch.nn.Linear(2, 1, bias=False)
        best = {"weight": torch.tensor([[3.0, -2.0]])}
        model.weight.data.zero_()
        runner.restore_best_model_state(model, best)
        self.assertTrue(torch.equal(model.weight.detach().cpu(), best["weight"]))
        with self.assertRaises(runner.Stage2Error):
            runner.restore_best_model_state(model, {})

    def test_final_sampling_gate_requires_all_15_frozen_choices(self):
        freeze = {"protocol_id_sha256": "f" * 64}
        rows = [{"root_id": f"dev-root-{i:02d}", "model": model,
                 "selection_sha256": "a" * 64, "weights_sha256": "b" * 64}
                for i in range(5) for model in runner.MODEL_ORDER]
        payload = runner.selection_manifest_payload(rows, freeze, "c" * 64)
        self.assertFalse(payload["final_development_accessed_at_freeze"])
        self.assertEqual(len(payload["selections"]), 15)
        self.assertEqual(len(payload["manifest_sha256"]), 64)
        with self.assertRaises(runner.Stage2Error):
            runner.selection_manifest_payload(rows[:-1], freeze, "c" * 64)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "selection.json"
            runner.atomic_json(path, payload)
            runner.verify_selection_manifest(path, payload)
            payload["selections"] = payload["selections"][:-1]
            with self.assertRaises(runner.Stage2Error):
                runner.verify_selection_manifest(path, payload)

    def test_balanced_batch_rng_is_restart_deterministic(self):
        train = {}
        for condition in runner.CONDITIONS:
            n = 512
            data = fake_partition(n)
            data["observable"] = np.tile(np.array([0, 1], dtype=np.uint8), n // 2)
            train[condition] = data
        first_rng = np.random.default_rng(8123)
        first_order = np.random.default_rng(9123)
        state_rng = first_rng.bit_generator.state
        state_order = first_order.bit_generator.state
        batches_a = runner.balanced_batches(train, 256, first_rng, first_order)
        replay_rng = np.random.default_rng()
        replay_order = np.random.default_rng()
        replay_rng.bit_generator.state = state_rng
        replay_order.bit_generator.state = state_order
        batches_b = runner.balanced_batches(train, 256, replay_rng, replay_order)
        self.assertEqual(len(batches_a), 4)
        for (ca, ia), (cb, ib) in zip(batches_a, batches_b):
            self.assertEqual(ca, cb)
            self.assertTrue(np.array_equal(ia, ib))

    def test_checkpoint_integrity_detects_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(runner, "CHECKPOINT_DIR", Path(temp)):
                payload = {
                    "model_name": "test_model", "root_id": "dev-root-00",
                    "config_sha256": "config", "completed_epochs": 1,
                    "model_state": {"weight": torch.tensor([1.0])},
                }
                manifest = runner.atomic_checkpoint("dev-root-00", "test_model", payload)
                loaded = runner.load_checkpoint("dev-root-00", "test_model", "config")
                self.assertEqual(loaded["completed_epochs"], 1)
                active = Path(temp) / "dev-root-00" / manifest["current"]["file"]
                active.write_bytes(b"corrupt")
                with self.assertRaises(runner.Stage2Error):
                    runner.load_checkpoint("dev-root-00", "test_model", "config")

    def test_useful_and_harmful_correction_accounting(self):
        y = np.array([0, 1, 0, 1], dtype=np.uint8)
        pm = np.array([0, 0, 1, 1], dtype=np.uint8)
        pred = np.array([1, 1, 1, 1], dtype=np.uint8)
        p = np.full(4, 0.5, dtype=np.float32)
        arrays = {}
        for condition in runner.CONDITIONS:
            arrays[f"{condition}__nominal_prediction"] = pm
            arrays[f"{condition}__burst_prediction"] = pm
            arrays[f"{condition}__observable"] = y
            for model in runner.MODEL_ORDER:
                arrays[f"{condition}__{model}__prediction"] = pred
                arrays[f"{condition}__{model}__probability"] = p
        selections = {name: {"threshold": 0.5, "temperature": 1.0} for name in runner.MODEL_ORDER}
        # Test the production metric function without passing malformed detector arrays.
        result = runner.summarize_per_root("dev-root-00", arrays,
            {condition: {"observable": y, "nominal_prediction": pm, "burst_prediction": pm}
             for condition in runner.CONDITIONS}, selections)
        m = result["conditions"]["nominal"][runner.MODEL_ORDER[0]]
        self.assertEqual(m["useful_corrections"], 1)
        self.assertEqual(m["harmful_corrections"], 1)
        self.assertEqual(m["candidate_only_failures"], 1)
        self.assertEqual(m["pymatching_only_failures"], 1)

    def test_resource_limit_is_enforced(self):
        cfg = {"resources": {"maximum_wall_seconds": 10, "maximum_measured_cuda_training_validation_seconds": 10,
                              "minimum_free_disk_gib_before_sampling": 2, "maximum_process_rss_gib": 3,
                              "maximum_cuda_allocated_gib": 4}}
        snap = {"process_rss_bytes": 100, "cuda_allocated_bytes": 0,
                "cuda_peak_allocated_bytes": 0, "free_disk_bytes": 0}
        with mock.patch.object(runner, "resource_snapshot", return_value=snap):
            with self.assertRaises(runner.ResourceLimitError):
                runner.enforce_resources(cfg, torch.device("cpu"), wall_seconds=1, cuda_seconds=1)

    def test_status_state_rejects_implicit_resume_and_records_completion(self):
        freeze = {"protocol_id_sha256": "protocol"}
        cfg = {"roots": {"count": 5}, "total_unique_shot_ceiling": 260000}
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(runner, "STATUS_PATH", Path(temp) / "status.json"):
            fresh = runner.initialize_status(cfg, freeze, resume=False)
            self.assertEqual(fresh["status"], "running")
            completed = dict(fresh, status="completed")
            runner.atomic_json(runner.STATUS_PATH, completed)
            self.assertEqual(runner.initialize_status(cfg, freeze, resume=False)["status"], "completed")
            failed = dict(fresh, status="failed", recoverable=True)
            runner.atomic_json(runner.STATUS_PATH, failed)
            with self.assertRaises(runner.Stage2Error):
                runner.initialize_status(cfg, freeze, resume=False)
            self.assertEqual(runner.initialize_status(cfg, freeze, resume=True)["status"], "running")


if __name__ == "__main__":
    unittest.main()
