from __future__ import annotations

import re
import unittest
from unittest import mock

import numpy as np
import stim

from outputs.qshift_correlated_decoder_feasibility_v1.correlated_model import (
    BurstEnumerationDecoder,
    BURST_QUBITS,
    PROBE_PROBABILITY,
    BurstRateEstimator,
    build_base_circuit,
    build_candidate_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)


class DeterministicFeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = extract_burst_events()
        cls.base = build_base_circuit()
        cls.candidate = build_candidate_circuit(PROBE_PROBABILITY)
        cls.background_dem = build_decomposed_dem(cls.base)
        cls.candidate_dem = build_decomposed_dem(cls.candidate)
        cls.background = build_matching(cls.background_dem)
        cls.static = build_matching(cls.candidate_dem)
        cls.factor = BurstEnumerationDecoder(cls.background, cls.events, PROBE_PROBABILITY)

    def test_circuit_identity_and_multidetector_event_support(self):
        self.assertEqual(self.candidate.num_detectors, 40)
        self.assertEqual(self.candidate.num_observables, 1)
        self.assertEqual(BURST_QUBITS, (8, 12, 15))
        self.assertEqual(len(self.events), 5)
        self.assertTrue(all(len(event.detector_ids) == 3 for event in self.events))
        self.assertTrue(all(event.observable_flip == 0 for event in self.events))
        self.assertEqual([event.detector_ids for event in self.events], [
            (5, 7, 10), (13, 15, 18), (21, 23, 26), (29, 31, 34), (37, 38, 39)
        ])

    def test_no_sampler_is_needed_for_dem_and_decoder_construction(self):
        # These tests construct circuits and DEMs only; any accidental sampler
        # call from this path fails immediately.
        with mock.patch.object(stim.Circuit, "compile_detector_sampler",
                               side_effect=AssertionError("sampler forbidden")):
            circuit = build_candidate_circuit(PROBE_PROBABILITY)
            dem = build_decomposed_dem(circuit)
            matching = build_matching(dem)
        self.assertEqual(matching.num_detectors, 40)

    def test_py_matching_decomposition_retains_correlated_groups(self):
        lines = [line for line in str(self.candidate_dem).splitlines()
                 if line.startswith(f"error({PROBE_PROBABILITY:g}) ")]
        self.assertTrue(lines)
        self.assertTrue(any("^" in line for line in lines))

    def test_decoders_accept_binary_shapes_and_match_exact_fixture_contract(self):
        fixture = np.zeros((3, 40), dtype=np.uint8)
        for row, event in enumerate(self.events[:3]):
            fixture[row, list(event.detector_ids)] = 1
        pm = np.asarray(self.static.decode_batch(fixture, enable_correlations=True), dtype=np.uint8)
        factor = self.factor.decode_batch(fixture)
        self.assertEqual(pm.shape, (3, 1))
        self.assertEqual(factor.shape, (3, 1))
        self.assertTrue(np.isin(pm, [0, 1]).all())
        self.assertTrue(np.isin(factor, [0, 1]).all())

    def test_factor_representation_changes_valid_deterministic_decisions(self):
        # Compose permitted background DEM fault signatures with burst factors.
        # These are algebraic fixtures, not sampled detector events.
        background_lines = [line for line in str(self.background_dem).splitlines()
                            if line.startswith("error(")]
        patterns = []
        for line in background_lines[:100]:
            det_ids = [int(value) for value in re.findall(r"D(\d+)", line)]
            if not det_ids:
                continue
            base = np.zeros(40, dtype=np.uint8)
            base[det_ids] ^= 1
            patterns.append(base)
        self.assertEqual(len(patterns), 100)
        mismatches = 0
        checked = 0
        burst_masks = [0] + [1 << index for index in range(5)]
        for base in patterns:
            for mask in burst_masks:
                syndrome = base.copy()
                for index, event in enumerate(self.events):
                    if (mask >> index) & 1:
                        syndrome[list(event.detector_ids)] ^= 1
                pm_prediction = int(np.asarray(
                    self.static.decode(syndrome, enable_correlations=True)
                ).reshape(-1)[0])
                factor_prediction = self.factor.decode_one(syndrome)
                mismatches += pm_prediction != factor_prediction
                checked += 1
        self.assertEqual(checked, 600)
        self.assertGreater(mismatches, 0)

    def test_edge_fault_id_parity_matches_pymatching_decode(self):
        lines = [line for line in str(self.background_dem).splitlines() if line.startswith("error(")]
        checked = 0
        for line in lines[:100]:
            ids = [int(value) for value in re.findall(r"D(\d+)", line)]
            if not ids:
                continue
            syndrome = np.zeros(40, dtype=np.uint8)
            syndrome[ids] ^= 1
            edges = self.background.decode_to_edges_array(syndrome, enable_correlations=True)
            parity = 0
            for edge in edges:
                key = ((int(edge[0]), -1) if int(edge[1]) == -1
                       else tuple(sorted((int(edge[0]), int(edge[1])))))
                parity ^= self.factor.edge_logical_parity[key]
            direct = int(np.asarray(self.background.decode(syndrome, enable_correlations=True)).reshape(-1)[0])
            self.assertEqual(parity, direct)
            checked += 1
        self.assertEqual(checked, 100)
    def test_detector_only_estimator_contract(self):
        events = self.events
        rows = []
        targets = []
        # Deterministic contract fixture: monotone feature-frequency relation.
        for q, count in ((0.0, 0), (0.01, 10), (0.02, 20)):
            x = np.zeros((1000, 40), dtype=np.uint8)
            for i in range(count):
                event = events[i % len(events)]
                x[i, list(event.detector_ids)] = 1
            rows.append(x)
            targets.append(np.full(1000, q, dtype=np.float64))
        estimator = BurstRateEstimator(events).fit(np.vstack(rows), np.concatenate(targets))
        self.assertGreater(estimator.slope, 0)
        estimate = estimator.estimate(rows[1])
        self.assertTrue(0.0 <= estimate <= 0.02)


if __name__ == "__main__":
    unittest.main()
