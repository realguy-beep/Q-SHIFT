from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from structured_decoder import (StructuredConv3DDecoder, PositionPreservingConv3DDecoder,
                                CoordinateChannelConv3DDecoder, DetectorCoordinateGridEncoder)
from structured_training import (REGIMES, _accumulate, _empty_accumulator,
                                 _correct_weighted_logits, _checkpoint_positive_weight, prediction_for,
                                 _fit_checkpoint_payload, _positive_weight,
                                 inventory_seed_values, make_development_inventory,
                                 scale_budget_allocation, restore_rng_state,
                                 screen_inventory, stream_batch, atomic_torch)
from seed_protocol import historical_seeds
from structured_protocol import build_inventory
from manager import WorkerManager
from simulator import prepare, sample, decode_matching
from structured_decoder import DetectorGridEncoder, apply_residual_correction, residual_training_target


class StructuredTrainingTests(unittest.TestCase):
    def test_positive_weight_logit_offset_is_removed_for_probabilities(self):
        p = torch.tensor([0.01, 0.1, 0.5, 0.9, 0.99], dtype=torch.float64)
        logits = torch.logit(p)
        weight = 17.0
        weighted_optimum = logits + np.log(weight)
        corrected = _correct_weighted_logits(weighted_optimum, weight)
        torch.testing.assert_close(torch.sigmoid(corrected), p, rtol=1e-12, atol=1e-12)

    def test_prediction_for_uses_corrected_weighted_probability(self):
        class FixedLogit(torch.nn.Module):
            def forward(self, x):
                return torch.zeros(len(x), dtype=torch.float32, device=x.device)

        d = np.zeros((4, 40), dtype=np.uint8)
        fixed = np.zeros(4, dtype=np.uint8)
        probability, correction = prediction_for(FixedLogit(), {"kind": "direct"}, d, fixed,
                                                  torch.device("cpu"), threshold=0.2,
                                                  positive_weight=9.0)
        np.testing.assert_allclose(probability, 0.1, atol=1e-7)
        np.testing.assert_array_equal(correction, np.zeros(4, dtype=np.uint8))

    def test_historical_checkpoint_weight_falls_back_to_fit_metadata(self):
        self.assertAlmostEqual(_checkpoint_positive_weight({}, {"cnn": {"positive_weight": 16.0}}, "cnn"), 16.0)
        self.assertIsNone(_checkpoint_positive_weight({}, {"cnn": {}}, "cnn"))
        self.assertEqual(_checkpoint_positive_weight({"positive_weight": 3.0},
                                                     {"cnn": {"positive_weight": 16.0}}, "cnn"), 3.0)

    def test_structured_cnn_preserves_round_grid_and_backpropagates(self):
        coordinates = {i: [float(i % 8), 0.0, float(i // 8)] for i in range(40)}
        model = StructuredConv3DDecoder(coordinates, channels=8, dropout=0.0)
        x = torch.zeros((3, 40), dtype=torch.float32)
        x[0, [0, 8, 16]] = 1
        result = model(x)
        self.assertEqual(tuple(result.shape), (3,))
        self.assertEqual(model.geometry.grid_shape, (5, 1, 8))
        self.assertEqual(int(model.geometry.occupancy.sum()), 40)
        result.sum().backward()
        self.assertTrue(all(p.grad is not None for p in model.parameters()))

    def test_actual_stim_detector_geometry_is_mapped_without_coordinate_loss(self):
        circuit, _, _, _, _, _ = prepare({"memory_basis": "z", "noise_regime": "balanced",
                                         "distance": 3, "rounds": 5, "gate_p": 0.003,
                                         "measurement_p": 0.003, "bias_ratio": 10.0,
                                         "device": "cpu"})
        coordinates = circuit.get_detector_coordinates()
        encoder = DetectorGridEncoder(coordinates)
        self.assertEqual(encoder.grid_shape, (6, 4, 4))
        self.assertEqual(int(encoder.occupancy.sum()), 40)
        eye = torch.eye(40, dtype=torch.float32)
        encoded = encoder(eye)
        self.assertEqual(tuple(encoded.shape), (40, 2, 6, 4, 4))
        time_i, y_i, x_i = encoder.time_indices, encoder.y_indices, encoder.x_indices
        recovered = encoded[torch.arange(40), 0, time_i, y_i, x_i]
        torch.testing.assert_close(recovered, torch.ones(40))
        self.assertTrue(torch.all(encoded[:, 1].sum(dim=(1, 2, 3)) == 40))

    def test_position_preserving_cnn_keeps_detector_grid_and_backpropagates(self):
        circuit, _, _, _, _, _ = prepare({"memory_basis": "z", "noise_regime": "balanced",
                                         "distance": 3, "rounds": 5, "gate_p": 0.003,
                                         "measurement_p": 0.003, "bias_ratio": 10.0,
                                         "device": "cpu"})
        coords = circuit.get_detector_coordinates()
        model = PositionPreservingConv3DDecoder(coords, channels=4, head_width=16, dropout=0.0)
        x = torch.randint(0, 2, (5, 40), dtype=torch.float32)
        logits = model(x)
        self.assertEqual(tuple(logits.shape), (5,))
        self.assertEqual(model.geometry.grid_shape, (6, 4, 4))
        self.assertGreater(sum(p.numel() for p in model.parameters()), 10_000)
        logits.sum().backward()
        self.assertTrue(all(p.grad is not None for p in model.parameters()))

    def test_coordinate_channel_cnn_preserves_stim_occupancy_and_coordinates(self):
        circuit, _, _, _, _, _ = prepare({"memory_basis": "z", "noise_regime": "balanced",
                                         "distance": 3, "rounds": 5, "gate_p": 0.003,
                                         "measurement_p": 0.003, "bias_ratio": 10.0,
                                         "device": "cpu"})
        coords = circuit.get_detector_coordinates()
        encoder = DetectorCoordinateGridEncoder(coords)
        eye = torch.eye(40, dtype=torch.float32)
        encoded = encoder(eye)
        self.assertEqual(tuple(encoded.shape), (40, 5, 6, 4, 4))
        self.assertEqual(int(encoder.occupancy.sum()), 40)
        ti, yi, xi = encoder.base.time_indices, encoder.base.y_indices, encoder.base.x_indices
        torch.testing.assert_close(encoded[torch.arange(40), 0, ti, yi, xi], torch.ones(40))
        self.assertTrue(torch.all(encoded[:, 1].sum(dim=(1, 2, 3)) == 40))
        empty = (encoder.occupancy[0, 0] == 0)
        self.assertTrue(torch.all(encoded[:, 2:, empty] == 0))
        model = CoordinateChannelConv3DDecoder(coords, channels=4, head_width=16, dropout=0.0)
        logits = model(torch.randint(0, 2, (3, 40), dtype=torch.float32))
        self.assertEqual(tuple(logits.shape), (3,))
        logits.sum().backward()
        self.assertTrue(all(p.grad is not None for p in model.parameters()))

    def test_stim_observable_alignment_and_xor_correction_convention(self):
        circuit, _, _, matching, _, _ = prepare({"memory_basis": "z", "noise_regime": "balanced",
                                                 "distance": 3, "rounds": 5, "gate_p": 0.003,
                                                 "measurement_p": 0.003, "bias_ratio": 10.0,
                                                 "device": "cpu"})
        detectors, observable = sample(circuit, 1_234_567, 128)
        predicted = decode_matching(matching, detectors)
        self.assertEqual(detectors.shape, (128, 40))
        self.assertEqual(observable.shape, (128,))
        self.assertEqual(predicted.shape, (128,))
        residual = residual_training_target(torch.as_tensor(predicted), torch.as_tensor(observable))
        corrected = apply_residual_correction(torch.as_tensor(predicted), (residual > 0).to(torch.uint8))
        torch.testing.assert_close(corrected, torch.as_tensor(observable))

    def test_development_seed_inventory_is_unique_and_separate(self):
        inventory = make_development_inventory(2000, 1000, batch_size=128, prior_allocations=[])
        self.assertTrue(inventory["passed"], inventory["collisions"])
        seeds = inventory_seed_values(inventory)
        self.assertEqual(len(seeds), inventory["unique_derived_seed_count"])
        self.assertFalse(seeds & historical_seeds())
        official = build_inventory()
        self.assertFalse(seeds & inventory_seed_values(official))
        screen = screen_inventory(inventory, prior_allocations=[], candidate_count=4)
        self.assertTrue(screen["passed"], screen["collisions"])
        self.assertEqual(len(screen["diagnostic_seeds"]), 3)

    def test_worker_has_no_test_sampling_path(self):
        with self.assertRaisesRegex(RuntimeError, "no test-sampling path"):
            stream_batch({}, {}, "test", REGIMES[0], 0, 1)

    def test_positive_weight_is_derived_from_training_prevalence_only(self):
        self.assertAlmostEqual(_positive_weight({"kind": "direct", "weighted": True},
                                                {"direct_prevalence": 0.1}), 9.0)
        self.assertIsNone(_positive_weight({"kind": "direct", "weighted": False},
                                           {"direct_prevalence": 0.01}))
        self.assertAlmostEqual(_positive_weight({"kind": "residual", "weighted": True},
                                                {"residual_prevalence": 0.2}), 4.0)

    def test_confusion_reports_positive_recall_and_all_negative_collapse(self):
        acc = _empty_accumulator()
        target = np.array([0, 0, 1, 1], dtype=np.uint8)
        probability = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        _accumulate(acc, target, probability)
        c = acc["confusion_by_threshold"]["0.5"]
        self.assertEqual(c, {"tn": 2, "fp": 0, "fn": 2, "tp": 0})
        self.assertEqual(acc["target_positive_count"], 2)

    def test_budget_ladder_is_bounded_and_keeps_test_reserved(self):
        for amount in (100_000, 1_000_000, 10_000_000, 100_000_000):
            allocation = scale_budget_allocation(amount)
            self.assertEqual(sum(allocation["training"].values()) +
                             sum(allocation["validation"].values()) +
                             sum(allocation["test_reserved_not_sampled"].values()), amount)
        with self.assertRaises(ValueError):
            scale_budget_allocation(1_000_000_000)

    def test_dashboard_manager_routes_structured_worker_without_replacing_legacy(self):
        self.assertEqual(WorkerManager.worker_script_for_config({"worker_kind": "legacy"}).name, "worker.py")
        self.assertEqual(WorkerManager.worker_script_for_config({"worker_kind": "structured_3d_cnn"}).name,
                         "structured_worker.py")
        with self.assertRaises(RuntimeError):
            WorkerManager.worker_script_for_config({"worker_kind": "other"})

    def test_checkpoint_resume_matches_uninterrupted_optimizer_and_rng(self):
        inputs = torch.arange(36, dtype=torch.float32).reshape(12, 3) / 36
        labels = torch.tensor([0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1], dtype=torch.float32)

        def make():
            model = nn.Sequential(nn.Linear(3, 7), nn.GELU(), nn.Dropout(0.25), nn.Linear(7, 1))
            opt = torch.optim.AdamW(model.parameters(), lr=0.002)
            sch = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=0)
            return model, opt, sch

        def one_step(model, opt, start, end):
            model.train()
            for i in range(start, end):
                opt.zero_grad(set_to_none=True)
                logits = model(inputs[i:i + 1]).squeeze(-1)
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, labels[i:i + 1])
                loss.backward()
                opt.step()

        torch.manual_seed(90210)
        baseline, baseline_opt, baseline_scheduler = make()
        one_step(baseline, baseline_opt, 0, 4)
        baseline_scheduler.step(0.4)
        one_step(baseline, baseline_opt, 4, 12)

        torch.manual_seed(90210)
        partial, partial_opt, partial_scheduler = make()
        one_step(partial, partial_opt, 0, 4)
        partial_scheduler.step(0.4)
        best = {k: v.detach().cpu().clone() for k, v in partial.state_dict().items()}
        payload = _fit_checkpoint_payload("test", "config-hash", partial, partial_opt,
                                          partial_scheduler, 0, 4, 4, 0.4, 0.5, 1,
                                          0, best, [], 9)
        with tempfile.TemporaryDirectory() as td:
            checkpoint = Path(td) / "atomic.pt"
            atomic_torch(payload, checkpoint)
            saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
            resumed, resumed_opt, resumed_scheduler = make()
            resumed.load_state_dict(saved["model_state"])
            resumed_opt.load_state_dict(saved["optimizer_state"])
            resumed_scheduler.load_state_dict(saved["scheduler_state"])
            restore_rng_state(saved["rng_state"], torch.device("cpu"))
            one_step(resumed, resumed_opt, 4, 12)
            for key, value in baseline.state_dict().items():
                self.assertTrue(torch.equal(value, resumed.state_dict()[key]), key)
            for key, value in baseline_opt.state_dict()["state"].items():
                for name, tensor in value.items():
                    other = resumed_opt.state_dict()["state"][key][name]
                    if torch.is_tensor(tensor):
                        self.assertTrue(torch.equal(tensor, other), f"optimizer {key}/{name}")


if __name__ == "__main__":
    unittest.main()
