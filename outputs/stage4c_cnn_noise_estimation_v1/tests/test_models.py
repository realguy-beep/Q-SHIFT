import unittest

import numpy as np
import torch

from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.stage4c_cnn_noise_estimation_v1.models import (
    BurstProbabilityCNN, batch_feature_vector, detector_coordinate_map,
    encode_calibration_batch, parameter_count,
)
from outputs.stage4c_cnn_noise_estimation_v1.prepare_inventory import make_inventory


class Stage4CModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        circuit = build_spatial_burst_circuit(burst_probability=0.0)
        cls.coords = detector_coordinate_map(circuit.get_detector_coordinates())

    def test_real_stim_detector_grid_has_40_occupied_sites(self):
        self.assertEqual(len(self.coords), 40)
        self.assertEqual(set(self.coords), set(range(40)))
        self.assertEqual(len(set(self.coords.values())), 40)
        self.assertEqual(self.coords[8][0], self.coords[10][0])
        self.assertEqual(self.coords[8][1], self.coords[10][1])

    def test_pair_channel_uses_actual_pair_endpoints_and_mask(self):
        d = np.zeros((250, 40), dtype=np.uint8)
        d[:, 8] = 1
        d[:, 10] = 1
        x = encode_calibration_batch(d, self.coords)
        self.assertEqual(x.shape, (3, 6, 4, 4))
        a, b = self.coords[8], self.coords[10]
        self.assertEqual(x[0, a[0], a[1], a[2]], 1.0)
        self.assertEqual(x[0, b[0], b[1], b[2]], 1.0)
        self.assertEqual(x[1, a[0], a[1], a[2]], 1.0)
        self.assertEqual(x[1, b[0], b[1], b[2]], 1.0)
        self.assertEqual(x[2].sum(), 40.0)
        self.assertEqual(x[2, 0, 0, 0], float((0, 0, 0) in self.coords.values()))

    def test_batch_features_are_detector_only_and_binary_validated(self):
        d = np.zeros((250, 40), dtype=np.uint8)
        f = batch_feature_vector(d)
        self.assertEqual(f.shape, (45,))
        np.testing.assert_array_equal(f, np.zeros(45))
        with self.assertRaises(ValueError):
            encode_calibration_batch(np.zeros((250, 39), dtype=np.uint8), self.coords)
        bad = d.copy()
        bad[0, 0] = 2
        with self.assertRaises(ValueError):
            batch_feature_vector(bad)

    def test_cnn_output_is_single_normalized_probability(self):
        torch.set_num_threads(1)
        model = BurstProbabilityCNN().eval()
        x = torch.zeros((5, 3, 6, 4, 4), dtype=torch.float32)
        with torch.no_grad():
            y = model(x)
        self.assertEqual(tuple(y.shape), (5,))
        self.assertTrue(torch.isfinite(y).all())
        self.assertTrue(bool(torch.all((y >= 0) & (y <= 1))))
        self.assertLess(parameter_count(model), 10000)

    def test_seed_inventory_is_unique_and_within_stim_seed_range(self):
        inv = make_inventory()
        seeds = [int(s["seed"]) for s in inv["streams"]] + list(inv["analysis_rngs"].values())
        self.assertEqual(len(seeds), 554)
        self.assertEqual(len(set(seeds)), 554)
        self.assertLess(max(seeds), 2**32)
        self.assertEqual(inv["total_simulation_shots"], 277500)


if __name__ == "__main__":
    unittest.main()
