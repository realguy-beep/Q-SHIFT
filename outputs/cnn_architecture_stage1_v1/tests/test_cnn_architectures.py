from __future__ import annotations

import unittest

import torch

from dashboard.structured_decoder import apply_residual_correction, residual_training_target
from outputs.cnn_architecture_stage1_v1.cnn_architectures import (
    FactorizedSpatialTemporalResidualCNN,
    ResidualPositionCNNV2,
    build_candidate,
    parameter_count,
)
from outputs.phase2b_pauli_bias.noise_model import build_circuit


def real_coordinates():
    circuit = build_circuit("z", "balanced", distance=3, rounds=5,
                            gate_p=0.003, measurement_p=0.003)
    coordinates = circuit.get_detector_coordinates()
    return {int(k): tuple(float(v) for v in coords) for k, coords in coordinates.items()}


class CNNArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coordinates = real_coordinates()

    def test_actual_stim_geometry_is_bijective_and_preserved(self):
        self.assertEqual(len(self.coordinates), 40)
        self.assertEqual(sorted(self.coordinates), list(range(40)))
        self.assertEqual(len(set(self.coordinates.values())), 40)
        for cls in (ResidualPositionCNNV2, FactorizedSpatialTemporalResidualCNN):
            model = cls(self.coordinates, dropout=0.0).eval()
            self.assertEqual(model.geometry.grid_shape, (6, 4, 4))
            self.assertEqual(int(model.geometry.occupancy.sum().item()), 40)

    def test_candidates_have_finite_logits_and_gradients_on_real_grid(self):
        torch.manual_seed(1973040112)
        detectors = torch.zeros((4, 40), dtype=torch.float32)
        detectors[1, [0, 3, 17]] = 1
        detectors[2, [2, 12, 39]] = 1
        detectors[3, [4, 9, 21, 36]] = 1
        matching = torch.tensor([0, 0, 1, 1], dtype=torch.float32)
        for cls in (ResidualPositionCNNV2, FactorizedSpatialTemporalResidualCNN):
            model = cls(self.coordinates, dropout=0.0)
            logits = model(detectors, matching)
            self.assertEqual(tuple(logits.shape), (4,))
            self.assertTrue(torch.isfinite(logits).all().item())
            labels = torch.tensor([0, 1, 0, 1], dtype=torch.float32)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, labels)
            loss.backward()
            self.assertTrue(torch.isfinite(loss).item())
            self.assertTrue(all(p.grad is None or torch.isfinite(p.grad).all().item()
                                for p in model.parameters()))
            self.assertTrue(any(p.grad is not None and torch.any(p.grad != 0).item()
                                for p in model.parameters()))

    def test_parameter_counts_stay_near_existing_residual_cnn(self):
        expected_baseline = 13_429  # saved 750K autonomous-run job metadata
        counts = [parameter_count(ResidualPositionCNNV2(self.coordinates)),
                  parameter_count(FactorizedSpatialTemporalResidualCNN(self.coordinates))]
        self.assertTrue(all(7_000 <= count <= 14_500 for count in counts), counts)
        self.assertTrue(all(abs(count - expected_baseline) / expected_baseline < 0.5
                            for count in counts), counts)

    def test_matching_conditioned_residual_target_and_xor_convention(self):
        observable = torch.tensor([0, 1, 0, 1], dtype=torch.uint8)
        matching = torch.tensor([0, 0, 1, 1], dtype=torch.uint8)
        target = residual_training_target(matching, observable)
        self.assertEqual(target.to(torch.uint8).tolist(), [0, 1, 1, 0])
        correction = torch.tensor([0, 1, 1, 0], dtype=torch.uint8)
        final_prediction = apply_residual_correction(matching, correction)
        self.assertEqual(final_prediction.tolist(), observable.tolist())

    def test_pm_input_shape_validation_and_factory(self):
        model = build_candidate("factorized_spatiotemporal_residual", self.coordinates)
        x = torch.zeros((2, 40))
        with self.assertRaises(ValueError):
            model(x, torch.zeros((3,)))
        with self.assertRaises(ValueError):
            build_candidate("unknown", self.coordinates)

    def test_fixed_seed_initialization_is_repeatable(self):
        torch.manual_seed(1973040113)
        first = ResidualPositionCNNV2(self.coordinates, dropout=0.0).eval()
        torch.manual_seed(1973040113)
        second = ResidualPositionCNNV2(self.coordinates, dropout=0.0).eval()
        x = torch.zeros((2, 40))
        pm = torch.tensor([0, 1])
        with torch.inference_mode():
            a = first(x, pm)
            b = second(x, pm)
        self.assertTrue(torch.equal(a, b))


if __name__ == "__main__":
    unittest.main()
