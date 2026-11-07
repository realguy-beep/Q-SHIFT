import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class ValidationSeedTests(unittest.TestCase):
    def test_validation_streams_are_unique_and_outside_stage5_range(self):
        inv = json.loads((HERE / "VALIDATION_SEED_INVENTORY.json").read_text(encoding="utf-8"))
        proposed = inv["analysis_rngs"]["welch_scenario_seeds"] + inv["analysis_rngs"]["bootstrap_t_scenario_seeds"] + [inv["analysis_rngs"]["p0_safety_seed"]]
        proposed += inv["preflight_fixture_seeds_already_consumed"] + [x["seed"] for x in inv["benchmark_streams"]]
        self.assertEqual(len(proposed), len(set(proposed)))
        self.assertEqual(inv["historical_seed_collision_count"], 0)
        self.assertFalse(inv["stage5_evaluation_seed_namespace_used"])
        self.assertFalse(inv["sealed_test_accessed"])
        self.assertFalse(any(4_240_000_001 <= x <= 4_240_001_002 for x in proposed))

    def test_benchmark_stream_partition_is_disjoint(self):
        inv = json.loads((HERE / "VALIDATION_SEED_INVENTORY.json").read_text(encoding="utf-8"))
        rows = inv["benchmark_streams"]
        self.assertEqual(len(rows), 100)
        calibration = {x["seed"] for x in rows if x["kind"] == "calibration_detector_only"}
        evaluation = {x["seed"] for x in rows if x["kind"] == "paired_evaluation_detector_observable"}
        self.assertEqual(len(calibration), 50)
        self.assertEqual(len(evaluation), 50)
        self.assertFalse(calibration & evaluation)


if __name__ == "__main__":
    unittest.main()
