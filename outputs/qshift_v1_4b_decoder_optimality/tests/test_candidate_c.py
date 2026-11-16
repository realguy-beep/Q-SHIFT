from __future__ import annotations

import math
import unittest

import numpy as np

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
from outputs.qshift_v1_4b_decoder_optimality.candidate_c import CorrelatedConsistentFiveFactor

SPEC = m.CodeSpec()
EVENTS = m.extract_burst_events(SPEC, m.burst_qubits(SPEC, "scaled_v1"))
BASE = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(SPEC)))


class CandidateCTests(unittest.TestCase):
    def test_pure_burst_syndromes_decode_to_their_logical_effect(self) -> None:
        dec = CorrelatedConsistentFiveFactor(BASE, EVENTS)
        for event in EVENTS:
            row = np.zeros((1, 40), dtype=np.uint8)
            row[0, list(event.detector_ids)] = 1
            self.assertEqual(int(dec.decode_rows(row, 0.02)[0]), event.observable_flip)

    def test_q0_path_equals_plain_correlated_matching(self) -> None:
        rng = np.random.default_rng(3)
        x = (rng.random((50, 40)) < 0.04).astype(np.uint8)
        dec = CorrelatedConsistentFiveFactor(BASE, EVENTS)
        expected = np.asarray(BASE.decode_batch(x, enable_correlations=True)).reshape(-1)
        np.testing.assert_array_equal(dec.decode_rows(x, 0.0), expected)

    def test_mask_choice_uses_correlated_weight_and_burst_log_odds(self) -> None:
        rng = np.random.default_rng(4)
        x = (rng.random((20, 40)) < 0.04).astype(np.uint8)
        q = 0.01
        lam = math.log((1 - q) / q)
        dec = CorrelatedConsistentFiveFactor(BASE, EVENTS)
        got = dec.decode_rows(x, q)
        for row, g in zip(x, got):
            scored = []
            for mask in range(32):
                res = row.copy()
                k = 0
                for j, e in enumerate(EVENTS):
                    if (mask >> j) & 1:
                        res[list(e.detector_ids)] ^= 1
                        k += 1
                p, w = BASE.decode(res, return_weight=True, enable_correlations=True)
                scored.append((float(w) + k * lam, k, mask, int(np.asarray(p).reshape(-1)[0])))
            self.assertEqual(int(g), min(scored)[3])


if __name__ == "__main__":
    unittest.main()
