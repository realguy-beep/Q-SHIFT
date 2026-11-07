from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
from torch import nn

from outputs.cnn_stage3_residual_gate_v1 import run_stage3 as runner

HERE = Path(__file__).resolve().parents[1]


class TinyResidual(nn.Module):
    def forward(self, detectors, nominal_prediction):
        return detectors[:, 0] * 2.0 - nominal_prediction


def sample_arrays() -> dict[str, np.ndarray]:
    return {"detectors": np.zeros((4, 40), dtype=np.uint8),
            "observable": np.array([0, 1, 1, 0], dtype=np.uint8),
            "nominal_prediction": np.array([0, 0, 1, 1], dtype=np.uint8),
            "burst_prediction": np.array([0, 1, 0, 1], dtype=np.uint8)}


class Stage3RegressionTests(unittest.TestCase):
    def test_residual_xor_and_final_xor_semantics(self):
        arrays = sample_arrays()
        residual = runner.residual_target(arrays)
        np.testing.assert_array_equal(residual, np.array([0, 1, 0, 1], dtype=np.uint8))
        np.testing.assert_array_equal(arrays["nominal_prediction"] ^ residual, arrays["observable"])

    def test_binary_and_shape_validation(self):
        arrays = sample_arrays()
        runner.validate_arrays(arrays, 4)
        arrays["observable"][0] = 2
        with self.assertRaises(runner.Stage3Error):
            runner.validate_arrays(arrays)
        arrays = sample_arrays()
        arrays["detectors"] = np.zeros((4, 39), dtype=np.uint8)
        with self.assertRaises(runner.Stage3Error):
            runner.validate_arrays(arrays)

    def test_seed_inventory_is_unique_and_partitions_are_disjoint(self):
        inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
        seeds = [int(x["seed"]) for x in inventory["streams"]]
        self.assertEqual(len(seeds), 46)
        self.assertEqual(len(set(seeds)), len(seeds))
        stream_seeds = [int(x["seed"]) for x in inventory["streams"] if x["kind"] == "stim_sample_stream"]
        self.assertEqual(len(stream_seeds), 30)
        self.assertEqual(len(set(stream_seeds)), 30)
        audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
        self.assertFalse(set(seeds) & set(audit.get("historical_seed_values", [])))
        self.assertFalse(inventory["independent_test_seed_allocated"])

    def test_sampler_and_balanced_batches_are_reproducible_and_balanced(self):
        labels = np.array([1] + [0] * 599, dtype=np.uint8)
        a = runner.balanced_batches(labels, 256, np.random.default_rng(7), np.random.default_rng(8))
        b = runner.balanced_batches(labels, 256, np.random.default_rng(7), np.random.default_rng(8))
        self.assertEqual(len(a), 3)
        for x, y in zip(a, b):
            np.testing.assert_array_equal(x, y)
            self.assertEqual(int(labels[x].sum()), (len(x) + 1) // 2)

    def test_inference_signature_excludes_labels_and_privileged_burst_info(self):
        params = set(inspect.signature(runner.infer_candidate).parameters)
        self.assertEqual(params, {"model", "arrays", "prevalence", "temperature", "threshold", "device"})
        arrays = sample_arrays()
        model = TinyResidual()
        d = arrays["detectors"].copy()
        d[:, 0] = np.array([0, 1, 0, 1], dtype=np.uint8)
        arrays["detectors"] = d
        first = runner.infer_candidate(model, arrays, 0.2, 1.0, 0.5, torch.device("cpu"))[2]
        arrays["observable"] = arrays["observable"] ^ 1
        arrays["burst_prediction"] = arrays["burst_prediction"] ^ 1
        second = runner.infer_candidate(model, arrays, 0.2, 1.0, 0.5, torch.device("cpu"))[2]
        np.testing.assert_array_equal(first, second)

    def test_correction_accounting_counts_true_paired_events(self):
        fixed = np.array([0, 0, 1, 1], dtype=np.uint8)
        truth = np.array([0, 1, 1, 0], dtype=np.uint8)
        candidate = np.array([1, 1, 1, 0], dtype=np.uint8)
        actual = runner.correction_metrics(candidate, fixed, truth)
        self.assertEqual(actual["errors"], 1)
        self.assertEqual(actual["candidate_only_failures"], 1)
        self.assertEqual(actual["fixed_only_failures"], 2)
        self.assertEqual(actual["prediction_disagreements"], 3)
        self.assertEqual(actual["useful_corrections"], 2)
        self.assertEqual(actual["harmful_corrections"], 1)
        self.assertAlmostEqual(actual["correction_precision"], 2 / 3)

    def test_global_threshold_is_selected_only_from_passed_threshold_partitions(self):
        # The API accepts only a root->threshold partition mapping; final data
        # cannot be accidentally supplied as a separate positional argument.
        self.assertEqual(set(inspect.signature(runner.choose_global_threshold).parameters),
                         {"threshold_probs", "roots", "grid"})
        arrays_a = {"observable": np.array([1, 0], np.uint8), "nominal_prediction": np.zeros(2, np.uint8)}
        arrays_b = {"observable": np.array([0, 1], np.uint8), "nominal_prediction": np.zeros(2, np.uint8)}
        payload = {"r0": {"arrays": arrays_a, "probability": np.array([0.9, 0.1])},
                   "r1": {"arrays": arrays_b, "probability": np.array([0.1, 0.9])}}
        threshold, scores = runner.choose_global_threshold(payload, ("r0", "r1"), [0.2, 0.5, 0.8])
        self.assertIn(threshold, [0.2, 0.5, 0.8])
        self.assertEqual(len(scores), 3)

    def test_final_development_partitions_are_rejected_from_selection(self):
        allowed = {"training", "monitor", "probability_calibration", "threshold_selection"}
        good = {root: {key: {runner.TRAIN_CONDITION: {}} for key in allowed} for root in runner.ROOT_IDS}
        runner.validate_selection_partitions(good)
        bad = {root: dict(value) for root, value in good.items()}
        bad[runner.ROOT_IDS[0]]["final_development_evaluation"] = {runner.TRAIN_CONDITION: {}}
        with self.assertRaisesRegex(runner.Stage3Error, "forbidden partitions"):
            runner.validate_selection_partitions(bad)

    def test_verified_checkpoint_restoration(self):
        torch.manual_seed(123)
        original = nn.Linear(3, 1)
        expected_state = {k: v.detach().clone() for k, v in original.state_dict().items()}
        expected_hash = runner.digest_state(expected_state)
        replacement = nn.Linear(3, 1)
        with torch.no_grad():
            replacement.weight.zero_()
            replacement.bias.zero_()
        runner.restore_state_verified(replacement, expected_state, expected_hash)
        for key, value in replacement.state_dict().items():
            torch.testing.assert_close(value, expected_state[key])
        with self.assertRaises(runner.Stage3Error):
            runner.restore_state_verified(replacement, expected_state, "0" * 64)

    def test_atomic_checkpoint_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.pt"
            model = nn.Linear(2, 1)
            digest = runner.atomic_torch_save(path, {"model_state": model.state_dict()})
            self.assertEqual(digest, runner.file_sha256(path))
            restored = torch.load(path, map_location="cpu", weights_only=False)
            replica = nn.Linear(2, 1)
            replica.load_state_dict(restored["model_state"])
            for a, b in zip(model.parameters(), replica.parameters()):
                torch.testing.assert_close(a, b)

    def test_resource_guard_enforces_wall_time(self):
        cfg = {"resources": {"maximum_wall_seconds": 0, "maximum_measured_cuda_training_seconds": 10,
            "maximum_process_rss_gib": 99, "maximum_cuda_allocated_gib": 99, "minimum_free_disk_gib": 0}}
        with self.assertRaisesRegex(runner.Stage3Error, "wall-time limit"):
            runner.enforce_resources(cfg, torch.device("cpu"), runner.time.perf_counter() - 1, 0)
        cfg["resources"]["maximum_wall_seconds"] = 1
        with self.assertRaisesRegex(runner.Stage3Error, "wall-time limit"):
            runner.enforce_resources(cfg, torch.device("cpu"), runner.time.perf_counter(), 0,
                                     wall_offset_seconds=2)

    def test_policy_hash_is_frozen_before_final_labels(self):
        # The policy record's construction is structurally separated from the
        # final sampling function; the latter accepts only a previously made policy.
        params = set(inspect.signature(runner.generate_final_and_score).parameters)
        self.assertEqual(params, {"cfg", "context", "inventory", "device", "runtime", "status",
                                 "selections", "global_threshold", "policy"})
        self.assertTrue((HERE / "CNN_STAGE3_PROTOCOL.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
