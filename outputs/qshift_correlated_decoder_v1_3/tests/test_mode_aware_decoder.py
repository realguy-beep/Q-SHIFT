from __future__ import annotations

import math
import unittest

import numpy as np

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (
    BurstEnumerationDecoder,
    build_base_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)
from outputs.qshift_correlated_decoder_v1_3.multi_prior import ModeAwareFiveFactor

PRIORS = {"zero": 0.0, "small": 0.0025, "mid": 0.01, "max": 0.02}


def fixture_syndromes() -> np.ndarray:
    events = extract_burst_events()
    rows = [np.zeros(40, dtype=np.uint8)]
    for event in events:
        row = np.zeros(40, dtype=np.uint8)
        row[list(event.detector_ids)] = 1
        rows.append(row)
    rng = np.random.default_rng(20261116)
    for _ in range(150):
        row = np.zeros(40, dtype=np.uint8)
        row[rng.choice(40, size=int(rng.integers(1, 8)), replace=False)] = 1
        rows.append(row)
    for event in events:
        row = np.zeros(40, dtype=np.uint8)
        row[list(event.detector_ids)] = 1
        row[rng.choice(40, size=2, replace=False)] ^= 1
        rows.append(row)
    return np.vstack(rows)


def reference_off(matching, events, syndrome, q) -> int:
    """Independent cost-consistent reference using PyMatching's own solution weight."""
    if q == 0.0:
        return int(np.asarray(matching.decode(syndrome, enable_correlations=False)).reshape(-1)[0])
    log_odds = math.log((1 - q) / q)
    best = None
    for mask in range(32):
        residual = syndrome.copy()
        logical = count = 0
        for i, event in enumerate(events):
            if (mask >> i) & 1:
                residual[list(event.detector_ids)] ^= 1
                logical ^= event.observable_flip
                count += 1
        pred, weight = matching.decode(residual, return_weight=True, enable_correlations=False)
        cand = (float(weight) + count * log_odds, count, mask, int(np.asarray(pred).reshape(-1)[0]) ^ logical)
        best = cand if best is None or cand < best else best
    return best[3]


class ModeAwareDecoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = extract_burst_events()
        cls.base = build_matching(build_decomposed_dem(build_base_circuit()))
        cls.x = fixture_syndromes()

    def test_correlations_on_is_bit_identical_to_frozen_decoder(self) -> None:
        got = ModeAwareFiveFactor(self.base, self.events, correlations=True).decode_rows(self.x, PRIORS)
        for name, q in PRIORS.items():
            ref = BurstEnumerationDecoder(self.base, self.events, q)
            np.testing.assert_array_equal(got[name][:, 0], [ref.decode_one(r) for r in self.x], err_msg=name)

    def test_correlations_off_matches_independent_return_weight_reference(self) -> None:
        got = ModeAwareFiveFactor(self.base, self.events, correlations=False).decode_rows(self.x, PRIORS)
        for name, q in PRIORS.items():
            expected = [reference_off(self.base, self.events, r, q) for r in self.x]
            np.testing.assert_array_equal(got[name][:, 0], expected, err_msg=name)

    def test_off_mode_cost_equals_pymatching_solution_weight(self) -> None:
        dec = ModeAwareFiveFactor(self.base, self.events, correlations=False)
        for row in self.x[:80]:
            for count, mask, cost, _ in dec.options(row):
                residual = row.copy()
                for i, event in enumerate(self.events):
                    if (mask >> i) & 1:
                        residual[list(event.detector_ids)] ^= 1
                _, weight = self.base.decode(residual, return_weight=True, enable_correlations=False)
                # PyMatching discretizes weights internally (~1e-7 relative here).
                self.assertLess(abs(cost - float(weight)), 1e-5)

    def test_on_mode_cost_mismatch_exists(self) -> None:
        # Documents the V1.1/V1.2 defect that motivated V1.3: with correlations ON the
        # chosen edges' static-weight sum is not the minimum static-weight solution.
        dec = ModeAwareFiveFactor(self.base, self.events, correlations=True)
        mismatches = 0
        for row in self.x:
            for _, mask, cost, _ in dec.options(row):
                residual = row.copy()
                for i, event in enumerate(self.events):
                    if (mask >> i) & 1:
                        residual[list(event.detector_ids)] ^= 1
                _, weight = self.base.decode(residual, return_weight=True, enable_correlations=False)
                mismatches += cost > float(weight) + 1e-3
        self.assertGreater(mismatches, 0)


if __name__ == "__main__":
    unittest.main()
