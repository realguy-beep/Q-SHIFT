from __future__ import annotations

import json
import unittest
from pathlib import Path

from outputs.qshift_correlated_decoder_v1_4 import headroom_gate as g

PKG = Path(__file__).resolve().parents[1]


class HeadroomGateTests(unittest.TestCase):
    def test_summary_picks_floor_and_static_and_bounds(self) -> None:
        errors = {(True, 0.0): [50, 900, 1500], (False, 0.0): [10, 1000, 1800],
                  (True, 0.005): [60, 400, 600], (False, 0.005): [12, 950, 1700]}
        s = g.summarize(errors, 20000)
        self.assertEqual(s["floor_decoder"], {"correlations": False, "q": 0.0})
        self.assertEqual(s["static_best_decoder"], {"correlations": True, "q": 0.005})
        self.assertAlmostEqual(s["ceiling"], 1 - (10 / 20000) / (1000 / 40000))
        self.assertLess(s["ceiling_lower"], s["ceiling"])
        self.assertFalse(s["qualifies"])  # ceiling 0.98 but lower bound under 0.97

    def test_zero_floor_errors_still_bounded(self) -> None:
        s = g.summarize({(True, 0.0): [0, 3000, 5000]}, 20000)
        self.assertEqual(s["floor_errors"], 0)
        self.assertGreater(s["floor_ler_upper_975"], 0)
        self.assertTrue(s["qualifies"])

    def test_seeds_are_complete_disjoint_and_reproducible(self) -> None:
        committed = json.loads((PKG / "GATE_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(committed, g.prepare_seeds())
        self.assertEqual(len(committed["seeds"]), len(g.cells()) * len(g.QS))

    def test_recorded_gate_is_complete_and_consistent(self) -> None:
        # Phase A asserted the gate had not run; after the authorized run, check its record.
        record = json.loads((PKG / "HEADROOM_GATE.json").read_text(encoding="utf-8"))
        self.assertEqual(len(record["results"]), len(g.cells()))
        for r in record["results"]:
            errors = {(e["correlations"], e["q"]): e["errors_q0_q001_q002"] for e in r["errors_by_static_decoder"]}
            s = g.summarize(errors, r["shots_per_q"])
            self.assertEqual(s["qualifies"], r["qualifies"])
            self.assertEqual(s["floor_errors"], r["floor_errors"])
        self.assertFalse(any(r["qualifies"] for r in record["results"]))


if __name__ == "__main__":
    unittest.main()
