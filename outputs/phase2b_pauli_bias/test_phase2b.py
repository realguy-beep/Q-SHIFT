from __future__ import annotations
import unittest

import numpy as np

from decoder_bank import build_bank, decode_bank
from noise_model import (DEFAULT_GATE_P, DEFAULT_MEAS_P, MEMORY_BASES, REGIMES,
                         build_circuit, circuit_noise_record, one_qubit_probabilities,
                         two_qubit_probabilities)


class Phase2BTests(unittest.TestCase):
    def test_equal_total_channel_mass_and_bias_order(self):
        for regime in REGIMES:
            p1 = one_qubit_probabilities(regime)
            p2 = two_qubit_probabilities(regime)
            self.assertAlmostEqual(sum(p1), DEFAULT_GATE_P, places=14)
            self.assertAlmostEqual(sum(p2), DEFAULT_GATE_P, places=14)
        self.assertGreater(one_qubit_probabilities("x_biased")[0], one_qubit_probabilities("x_biased")[2])
        self.assertAlmostEqual(*one_qubit_probabilities("balanced")[:2], places=14)
        self.assertGreater(one_qubit_probabilities("z_biased")[2], one_qubit_probabilities("z_biased")[0])

    def test_circuit_keeps_geometry_and_expected_noise_locations(self):
        for basis in MEMORY_BASES:
            for regime in REGIMES:
                circuit, record = circuit_noise_record(basis, regime)
                self.assertEqual((circuit.num_detectors, circuit.num_observables), (40, 1))
                self.assertGreater(record["flattened_instruction_counts"]["PAULI_CHANNEL_1"], 0)
                self.assertGreater(record["flattened_instruction_counts"]["PAULI_CHANNEL_2"], 0)
                self.assertNotIn("DEPOLARIZE1", str(circuit))
                self.assertNotIn("DEPOLARIZE2", str(circuit))
                self.assertAlmostEqual(record["2q_pauli_probability_sum"], DEFAULT_GATE_P, places=14)
                self.assertEqual(record["measurement_flip_probability"], DEFAULT_MEAS_P)

    def test_noiseless_behavior_and_basic_noise_sensitivity(self):
        for basis in MEMORY_BASES:
            circuit = build_circuit(basis, "balanced", gate_p=0, measurement_p=0)
            d, y = circuit.compile_detector_sampler(seed=87990001).sample(16, separate_observables=True)
            self.assertFalse(np.any(d))
            self.assertFalse(np.any(y))
            noisy = build_circuit(basis, "balanced")
            d, _ = noisy.compile_detector_sampler(seed=87990001).sample(1500, separate_observables=True)
            self.assertGreater(int(np.count_nonzero(d)), 0)

    def test_dem_bank_construction_and_paired_decode(self):
        for basis in MEMORY_BASES:
            models, records = build_bank(basis)
            self.assertEqual([r["assumed_regime"] for r in records], list(REGIMES))
            self.assertTrue(all(r["detectors"] == 40 for r in records))
            self.assertTrue(all(r["logical_fault_ids"] == [0] for r in records))
            circuit = build_circuit(basis, "balanced")
            d, _ = circuit.compile_detector_sampler(seed=87990001).sample(64, separate_observables=True)
            preds = decode_bank(models, d)
            self.assertEqual(preds.shape, (3, 64))
            self.assertTrue(set(np.unique(preds)).issubset({0, 1}))

    def test_seeded_stim_sampling_is_reproducible(self):
        circuit = build_circuit("z", "x_biased")
        a = circuit.compile_detector_sampler(seed=87990001).sample(32, separate_observables=True)
        b = circuit.compile_detector_sampler(seed=87990001).sample(32, separate_observables=True)
        self.assertTrue(np.array_equal(a[0], b[0]))
        self.assertTrue(np.array_equal(a[1], b[1]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
