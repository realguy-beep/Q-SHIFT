"""B2 contract tests (no sampling)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import b2  # noqa: E402
import prepare_dev_seeds as PB  # noqa: E402


class B2SeedTests(unittest.TestCase):
    def test_complete_disjoint_screened(self):
        s = json.loads((PKG / "B2_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(b2.all_keys("dev")))
        self.assertEqual(len(s["seeds"]), 500 + 312)
        self.assertEqual(set(s["rehearsal_seeds"]), set(b2.all_keys("rehearsal")))
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(s["seeds"]))
        self.assertFalse(ev & rh)
        screened, _ = PB.screened_values()
        pb = json.loads((PKG / "DEV_SEEDS.json").read_text(encoding="utf-8"))
        screened |= set(pb["seeds"].values()) | set(pb["rehearsal_seeds"].values())
        self.assertFalse((ev | rh) & screened)

    def test_constants(self):
        self.assertEqual((b2.N_NULL, b2.NULL_SHOTS, b2.TAU_MAX), (500, 12_000, 3_000.0))
        self.assertTrue(all(k.startswith("d5ls:b2:") for k in b2.all_keys("dev")))


if __name__ == "__main__":
    unittest.main()
