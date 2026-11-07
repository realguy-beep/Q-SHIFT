from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from matching_investigation import (  # noqa: E402
    exact_dem_joint, make_custom_dem, parse_dem, posterior_metrics,
    transform_graphlike, local_restricted_decoder, decision_risk_from_array,
    reproduce_historical, audit_unsafe_separator_erasure,
)


class MatchingRepresentationTests(unittest.TestCase):
    def test_historical_two_qubit_toy_reproduces_exact_risks(self):
        r = reproduce_historical()
        self.assertAlmostEqual(r["exact_reference_risk"], 0.06, places=12)
        self.assertAlmostEqual(r["risk_by_decoder"]["pymatching_standard"], 0.1128, places=12)
        self.assertAlmostEqual(r["risk_by_decoder"]["separator_free_standard"], 0.06, places=12)
        self.assertTrue(r["categorical_vs_dem_map_all_four_agree"])
        self.assertEqual(r["categorical_exact_map_decisions"], r["independent_dem_exact_map_decisions"])

    def test_graphlike_transform_preserves_each_event_distribution(self):
        dem = make_custom_dem(2, 1, [
            (0.03, 3, 1, [(1, 1), (2, 0)]),
            (0.08, 1, 0, [(1, 0)]), (0.05, 2, 0, [(2, 0)]),
        ])
        transformed, record = transform_graphlike(dem)
        self.assertIsNotNone(transformed)
        self.assertTrue(record["accepted"])
        before = exact_dem_joint(dem.num_detectors, dem.num_observables, parse_dem(dem)[1])
        after = exact_dem_joint(transformed.num_detectors, transformed.num_observables, parse_dem(transformed)[1])
        self.assertTrue((abs(before-after) < 1e-14).all())

    def test_hyperedge_transform_is_rejected_not_silently_changed(self):
        dem = make_custom_dem(4, 1, [(0.07, 15, 1, [(3, 1), (12, 0)])])
        transformed, record = transform_graphlike(dem)
        self.assertIsNone(transformed)
        self.assertFalse(record["accepted"])
        self.assertEqual(record["unsupported_event_indices"], [0])

    def test_logical_only_event_is_rejected_from_graphlike_conversion(self):
        dem = make_custom_dem(0, 1, [(0.1, 0, 1, [(0, 1)])])
        transformed, record = transform_graphlike(dem)
        self.assertIsNone(transformed)
        self.assertFalse(record["accepted"])
        self.assertEqual(record["reason"], "logical-only event has no syndrome edge")

    def test_unchecked_four_detector_event_is_not_a_valid_graphlike_rewrite(self):
        dem = make_custom_dem(4, 1, [(0.07, 15, 1, [(3, 1), (12, 0)])])
        audit = audit_unsafe_separator_erasure(dem)
        self.assertEqual(audit["modes"]["standard"]["construction"], "accepted")
        self.assertEqual(audit["modes"]["standard"]["edges"], 0)
        self.assertEqual(audit["modes"]["correlated"]["construction"], "rejected")
        self.assertIn("undecomposed error instruction", audit["modes"]["correlated"]["exception"])

    def test_local_posterior_normalizes_and_tie_chooses_zero(self):
        dem = make_custom_dem(1, 1, [(0.5, 1, 0, [(1, 0)]), (0.5, 1, 1, [(1, 1)])])
        _, events = parse_dem(dem)
        pred, diag = local_restricted_decoder(1, 1, events, 1, fallback=1)
        self.assertTrue(diag["used"])
        self.assertAlmostEqual(sum(diag["conditional_posterior"]), 1.0)
        self.assertTrue(diag["tie"])
        self.assertEqual(pred, 0)

    def test_local_fallback_when_restricted_support_is_empty(self):
        dem = make_custom_dem(2, 1, [(0.1, 1, 0, [(1, 0)])])
        _, events = parse_dem(dem)
        pred, diag = local_restricted_decoder(2, 1, events, syndrome=2, fallback=1)
        self.assertFalse(diag["used"])
        self.assertEqual(pred, 1)

    def test_local_event_cap_fallback(self):
        dem = make_custom_dem(1, 1, [(0.01, 1, 0, [(1, 0)]) for _ in range(13)])
        _, events = parse_dem(dem)
        pred, diag = local_restricted_decoder(1, 1, events, syndrome=1, fallback=1, max_events=12)
        self.assertFalse(diag["used"])
        self.assertEqual(diag["reason"], "local event cap exceeded")
        self.assertEqual(pred, 1)

    def test_exact_dem_normalizes(self):
        dem = make_custom_dem(2, 1, [(0.2, 3, 1, [(1, 1), (2, 0)]), (0.1, 1, 0, [(1, 0)])])
        _, events = parse_dem(dem)
        joint = exact_dem_joint(2, 1, events)
        metrics = posterior_metrics(joint, 2, 1)
        self.assertAlmostEqual(metrics["mass"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
