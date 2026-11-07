"""Standard-library tests for the Q-SHIFT headroom pilot (no pytest dependency)."""
from __future__ import annotations

import unittest

import numpy as np

from headroom import (
    build_decoder, detector_count, fit_detector_model, native_circuit,
    paired_root_effect, pauli_circuit, pauli_probabilities, residual_errors,
    select_calibration,
)
from run_pilot import assess_headroom_gate, bank_specs, make_seed_inventory


class HeadroomTests(unittest.TestCase):
    def test_distance_basis_circuit_and_matching_schema(self):
        for distance in (3, 5, 7):
            for memory in ("x", "z"):
                with self.subTest(distance=distance, memory=memory):
                    circuit = native_circuit(memory, distance, 0.003, 0.003)
                    self.assertEqual(circuit.num_detectors, detector_count(distance))
                    self.assertEqual(circuit.num_observables, 1)
                    model, dem, correlated = build_decoder(circuit, "native")
                    self.assertEqual(model.num_detectors, circuit.num_detectors)
                    self.assertEqual(model.num_fault_ids, 1)
                    self.assertEqual(dem.num_detectors, circuit.num_detectors)
                    self.assertFalse(correlated)

    def test_biased_pauli_channel_mass_and_dem(self):
        for regime in ("x_biased", "balanced", "z_biased"):
            with self.subTest(regime=regime):
                p1, p2 = pauli_probabilities(regime, 0.003, 10.0)
                self.assertAlmostEqual(sum(p1), 0.003, places=14)
                self.assertAlmostEqual(sum(p2), 0.003, places=14)
                circuit = pauli_circuit("z", 3, regime, 0.003, 0.003)
                self.assertEqual(circuit.num_detectors, 24)
                self.assertEqual(circuit.num_observables, 1)
                model, dem, correlated = build_decoder(circuit, "pauli_biased")
                self.assertEqual(model.num_detectors, 24)
                self.assertEqual(dem.num_observables, 1)
                self.assertTrue(correlated)

    def test_calibration_selection_tie_and_paired_discordances(self):
        labels = np.zeros(4, dtype=np.uint8)
        predictions = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.uint8)
        residuals = residual_errors(labels, predictions)
        row = {"residuals": residuals, "predictions": predictions}
        effect = paired_root_effect({"r": [row]}, "r", 0, 1, 2000, 123)
        self.assertEqual(effect["specialist_only_wrong"], 1)
        self.assertEqual(effect["pooled_only_wrong"], 1)
        self.assertEqual(effect["prediction_disagreements"], 2)

        cal = {
            "a": [{"residuals": np.zeros((2, 8), dtype=np.uint8)}],
            "b": [{"residuals": np.zeros((2, 8), dtype=np.uint8)}],
        }
        selected = select_calibration(cal, ["a", "b"], 2)
        self.assertEqual(selected["pooled_fixed_index"], 0)
        self.assertEqual(selected["regime_specialist_indices"], {"a": 0, "b": 0})

    def test_detector_marginal_fit_tie(self):
        detectors = np.zeros((10, 3), dtype=np.uint8)
        profiles = np.full((4, 3), 0.25)
        self.assertEqual(fit_detector_model(detectors, profiles), 0)

    @staticmethod
    def _synthetic_gate_results(pair_by_distance):
        banks = []
        for family in ("native", "pauli_biased"):
            for memory in ("x", "z"):
                for distance in (3, 5, 7):
                    pair = pair_by_distance.get(distance)
                    choices = {"a": 0, "b": 0, "c": 0}
                    if pair is not None:
                        choices[pair[0]] = 1
                        choices[pair[1]] = 2
                    regimes = {}
                    for regime in choices:
                        eligible = pair is not None and regime in pair
                        regimes[regime] = {
                            "specialist_calibration_selection_probability": 0.95 if eligible else 0.1,
                            "relative_reduction": 0.10 if eligible else 0.0,
                            "difference_ler": -0.001 if eligible else 0.0,
                            "roots_favoring_specialist": 5 if eligible else 0,
                            "root_bootstrap_ci95": [-0.002, -0.0001] if eligible else [-0.001, 0.001],
                        }
                    banks.append({
                        "family": family, "memory": memory, "distance": distance,
                        "regimes": regimes, "regime_specialist_indices": choices,
                        "pooled_fixed_index": 0,
                    })
        return banks

    def test_headroom_gate_requires_same_regime_pair_replicated(self):
        results = assess_headroom_gate(self._synthetic_gate_results({
            3: ("a", "b"), 5: ("a", "c")
        }))
        self.assertFalse(results["passed"])
        results = assess_headroom_gate(self._synthetic_gate_results({
            3: ("a", "b"), 5: ("a", "b")
        }))
        self.assertTrue(results["passed"])

    def test_seed_inventory_unique(self):
        inventory = make_seed_inventory(bank_specs(), set())
        self.assertEqual(inventory["proposed_seed_count"], inventory["unique_proposed_seed_count"])
        self.assertEqual(inventory["proposed_seed_count"], 516)


if __name__ == "__main__":
    unittest.main()
