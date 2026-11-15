from __future__ import annotations

import unittest

import numpy as np

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
    BurstEnumerationDecoder,
    build_base_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)
from outputs.qshift_correlated_decoder_v1_2.multi_prior import MultiPriorFiveFactor


def fixture_syndromes() -> np.ndarray:
    """Deterministic, sampler-free syndromes: burst signatures, pairs, sparse random."""
    events = extract_burst_events()
    rows = [np.zeros(40, dtype=np.uint8)]
    for event in events:
        row = np.zeros(40, dtype=np.uint8)
        row[list(event.detector_ids)] = 1
        rows.append(row)
    for a in range(0, 40, 3):
        row = np.zeros(40, dtype=np.uint8)
        row[a] = 1
        row[(a + 7) % 40] = 1
        rows.append(row)
    rng = np.random.default_rng(20261115)
    for _ in range(120):
        row = np.zeros(40, dtype=np.uint8)
        row[rng.choice(40, size=int(rng.integers(1, 7)), replace=False)] = 1
        rows.append(row)
    for event in events:  # burst plus background noise
        row = np.zeros(40, dtype=np.uint8)
        row[list(event.detector_ids)] = 1
        row[rng.choice(40, size=2, replace=False)] ^= 1
        rows.append(row)
    return np.vstack(rows)


class MultiPriorTests(unittest.TestCase):
    def test_bit_identical_to_frozen_decoder_for_every_prior(self) -> None:
        events = extract_burst_events()
        base = build_matching(build_decomposed_dem(build_base_circuit()))
        x = fixture_syndromes()
        priors = {"zero": 0.0, "small": 0.0025, "pooled": 0.010166666666666657,
                  "mid": 0.0125, "max": 0.02}
        got = MultiPriorFiveFactor(base, events).decode_rows(x, priors)
        for name, q in priors.items():
            ref = BurstEnumerationDecoder(base, events, q)
            expected = np.asarray([ref.decode_one(row) for row in x], dtype=np.uint8)
            np.testing.assert_array_equal(got[name][:, 0], expected, err_msg=name)
            self.assertEqual(got[name].shape, (len(x), 1))
            self.assertEqual(got[name].dtype, np.uint8)

    def test_rejects_out_of_range_prior(self) -> None:
        base = build_matching(build_decomposed_dem(build_base_circuit()))
        decoder = MultiPriorFiveFactor(base, extract_burst_events())
        with self.assertRaises(ValueError):
            decoder.decode_rows(np.zeros((1, 40), dtype=np.uint8), {"bad": 0.03})


if __name__ == "__main__":
    unittest.main()
