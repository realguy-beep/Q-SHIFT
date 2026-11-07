from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulator import prepare
from structured_decoder import DetectorCoordinateGridEncoder


class PositionPreservingDecoderTests(unittest.TestCase):
    def test_coordinate_channels_follow_real_stim_detector_ids(self):
        circuit, _, _, _, _, _ = prepare({"memory_basis": "z", "noise_regime": "balanced",
                                         "distance": 3, "rounds": 5, "gate_p": 0.003,
                                         "measurement_p": 0.003, "bias_ratio": 10.0,
                                         "device": "cpu"})
        coordinates = circuit.get_detector_coordinates()
        encoder = DetectorCoordinateGridEncoder(coordinates)
        encoded = encoder(torch.eye(40, dtype=torch.float32))
        self.assertEqual(tuple(encoded.shape), (40, 5, 6, 4, 4))
        ti, yi, xi = encoder.base.time_indices, encoder.base.y_indices, encoder.base.x_indices
        occupancy = encoded[0, 1]
        self.assertEqual(int(occupancy.sum()), 40)
        raw_axes = [[float(coordinates[i][2]) for i in range(40)],
                    [float(coordinates[i][1]) for i in range(40)],
                    [float(coordinates[i][0]) for i in range(40)]]
        for channel, values in enumerate(raw_axes, start=2):
            lo, hi = min(values), max(values)
            expected = np.zeros(40) if hi == lo else np.asarray([2 * (v - lo) / (hi - lo) - 1 for v in values])
            actual = encoded[torch.arange(40), channel, ti, yi, xi].numpy()
            np.testing.assert_allclose(actual, expected, atol=1e-7)
        empty = occupancy == 0
        self.assertTrue(torch.all(encoded[:, 2:, empty] == 0))


if __name__ == "__main__":
    unittest.main()
