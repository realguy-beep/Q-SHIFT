import sys
import unittest
from pathlib import Path

import numpy as np
import pymatching
import stim

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulator import (build_isolated_burst_circuit, build_matching,
                       build_spatial_burst_circuit)


class CorrelatedNoisePreflightTests(unittest.TestCase):
    def test_geometry_and_round_injection_preserve_detectors(self):
        base = build_spatial_burst_circuit(gate_p=0, measurement_p=0, burst_probability=0)
        burst = build_spatial_burst_circuit(gate_p=0, measurement_p=0, burst_probability=0.02)
        self.assertEqual((base.num_detectors, base.num_observables), (40, 1))
        self.assertEqual((burst.num_detectors, burst.num_observables), (40, 1))
        # Stim canonicalizes CORRELATED_ERROR to its short mnemonic `E`.
        self.assertEqual(sum(x.name == "E" for x in burst), 5)
        self.assertEqual(sum(x.name == "MR" for x in burst), 5)

    def test_zero_noise_and_zero_correlation_limits(self):
        c = build_spatial_burst_circuit(gate_p=0, measurement_p=0, burst_probability=0)
        d, o = c.compile_detector_sampler(seed=2503002002).sample(64, separate_observables=True)
        self.assertFalse(np.any(d))
        self.assertFalse(np.any(o))

    def test_isolated_common_cause_is_cross_location_correlated(self):
        c = build_isolated_burst_circuit(0.1)
        a = c.compile_sampler(seed=2503002001).sample(2048).astype(np.uint8)
        self.assertTrue(np.array_equal(a[:, 0], a[:, 1]))
        self.assertGreater(int(a[:, 0].sum()), 0)
        self.assertLess(int(a[:, 0].sum()), len(a))
        self.assertGreater(float(np.corrcoef(a.T)[0, 1]), 0.99)

    def test_seed_reproducibility_for_surface_circuit(self):
        c = build_spatial_burst_circuit(gate_p=0.003, measurement_p=0.003,
                                        burst_probability=0.01)
        d1, o1 = c.compile_detector_sampler(seed=2503002003).sample(128, separate_observables=True)
        d2, o2 = c.compile_detector_sampler(seed=2503002003).sample(128, separate_observables=True)
        self.assertTrue(np.array_equal(d1, d2))
        self.assertTrue(np.array_equal(o1, o2))

    def test_same_dem_builds_both_matching_modes_with_paired_predictions(self):
        c = build_spatial_burst_circuit(gate_p=0.003, measurement_p=0.003,
                                        burst_probability=0.01)
        dem_off, m_off = build_matching(c, enable_correlations=False)
        dem_on, m_on = build_matching(c, enable_correlations=True)
        self.assertEqual(str(dem_off), str(dem_on))
        self.assertEqual((dem_on.num_detectors, dem_on.num_observables), (40, 1))
        d, obs = c.compile_detector_sampler(seed=2503002004).sample(64, separate_observables=True)
        p_off = m_off.decode_batch(d).reshape(-1, 1)
        p_on = m_on.decode_batch(d).reshape(-1, 1)
        self.assertEqual(p_off.shape, obs.shape)
        self.assertEqual(p_on.shape, obs.shape)
        self.assertEqual(m_off.num_detectors, m_on.num_detectors)


if __name__ == "__main__":
    unittest.main()
