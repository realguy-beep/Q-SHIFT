"""No-sampling tests for the candidate V2 seed allocation."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from outputs.strong_fixed_baselines_v2.prepare_seed_inventory_v2 import allocate, collect_large_ints


class SeedInventoryTests(unittest.TestCase):
    def test_allocation_is_unique_disjoint_by_role_and_matches_frozen_budget(self):
        config = json.loads(Path(__file__).with_name("experiment_config_v2.json").read_text(encoding="utf-8"))
        streams = allocate(config)
        seeds = [row["seed"] for row in streams]
        self.assertEqual(len(seeds), len(set(seeds)))
        included_shots = sum(int(row["shots"]) for row in streams if row["included_in_allocation"])
        self.assertEqual(included_shots, config["allocation"]["unique_shots"])
        roles = {(row["role"], row["split"]) for row in streams}
        for required in (
            ("profile_template", "templates"),
            ("calibration", "selection"), ("scoring", "selection"),
            ("calibration", "validation"), ("scoring", "validation"),
            ("calibration", "heldout_development"), ("evaluation", "heldout_development"),
            ("bootstrap_validation", "validation_analysis"),
            ("bootstrap_results", "heldout_development_analysis"),
        ):
            self.assertIn(required, roles)
        self.assertFalse(config["execution"]["sampling_authorized"])

    def test_metadata_collision_scanner_collects_large_int_and_string_tokens(self):
        values = set()
        collect_large_ints({"seed": 12345678, "nested": ["19000000001", 42]}, values)
        self.assertEqual(values, {12345678, 19000000001})


if __name__ == "__main__":
    unittest.main(verbosity=2)
