from __future__ import annotations

import unittest

import numpy as np

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
    BurstEnumerationDecoder,
    build_base_circuit,
    build_candidate_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)


class DeterministicModelTests(unittest.TestCase):
    def test_circuit_dem_and_decoder_contract_without_sampling(self) -> None:
        events = extract_burst_events()
        self.assertEqual(len(events), 5)
        self.assertEqual(len({event.detector_ids for event in events}), 5)
        self.assertTrue(all(len(event.detector_ids) == 3 for event in events))
        self.assertEqual([event.observable_flip for event in events], [0, 0, 0, 0, 0])
        for q in (0.0, 0.01, 0.02):
            circuit = build_candidate_circuit(q)
            self.assertEqual(circuit.num_detectors, 40)
            self.assertEqual(circuit.num_observables, 1)
            dem = build_decomposed_dem(circuit)
            self.assertEqual(dem.num_detectors, 40)
            self.assertEqual(dem.num_observables, 1)
            matching = build_matching(dem)
            result = matching.decode(np.zeros(40, dtype=np.uint8), enable_correlations=True)
            self.assertEqual(np.asarray(result).reshape(-1).tolist(), [0])

    def test_factor_decoder_accepts_batch_and_returns_binary_observables(self) -> None:
        events = extract_burst_events()
        matching = build_matching(build_decomposed_dem(build_base_circuit()))
        decoder = BurstEnumerationDecoder(matching, events, 0.01)
        fixture = np.zeros((3, 40), dtype=np.uint8)
        fixture[1, list(events[0].detector_ids)] = 1
        prediction = decoder.decode_batch(fixture)
        self.assertEqual(prediction.shape, (3, 1))
        self.assertEqual(prediction.dtype, np.uint8)
        self.assertTrue(np.isin(prediction, [0, 1]).all())

    def test_paired_factor_evaluation_matches_independent_calls(self) -> None:
        events = extract_burst_events()
        matching = build_matching(build_decomposed_dem(build_base_circuit()))
        fixtures = np.zeros((8, 40), dtype=np.uint8)
        for row in range(1, len(fixtures)):
            fixtures[row, (row * 3) % 40] = 1
            fixtures[row, (row * 7 + 2) % 40] ^= 1
            if row % 2:
                fixtures[row, list(events[(row - 1) % len(events)].detector_ids)] ^= 1
        for q1, q2 in ((0.0, 0.01), (0.01, 0.02), (0.02, 0.02), (0.0, 0.0)):
            first = BurstEnumerationDecoder(matching, events, q1)
            second = BurstEnumerationDecoder(matching, events, q2)
            paired1, paired2 = first.decode_pair_batch(fixtures, second)
            np.testing.assert_array_equal(paired1, first.decode_batch(fixtures))
            np.testing.assert_array_equal(paired2, second.decode_batch(fixtures))


if __name__ == "__main__":
    unittest.main()
