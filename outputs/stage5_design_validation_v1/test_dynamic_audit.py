import json
import unittest
from pathlib import Path

from audit_dynamic import expected_root_keys, expected_totals

HERE = Path(__file__).resolve().parent


class DynamicAuditAllocationTests(unittest.TestCase):
    def test_256_root_allocation_cardinality(self):
        cfg = json.loads((HERE / "PROPOSED_256_ALLOCATION.json").read_text(encoding="utf-8"))
        keys = expected_root_keys(cfg["probabilities"], cfg["roots_per_probability"])
        normalized = {
            "probabilities": cfg["probabilities"],
            "roots_per_probability": cfg["roots_per_probability"],
            "calibration_shots_per_root": cfg["calibration_shots_per_root"],
            "paired_evaluation_shots_per_root": cfg["paired_evaluation_shots_per_root"],
        }
        self.assertEqual(len(keys), 1280)
        self.assertEqual(len(set(keys)), 1280)
        self.assertEqual(keys[255], (0.0, 255))
        self.assertEqual(keys[256], (0.004, 0))
        self.assertEqual(keys[-1], (0.016, 255))
        self.assertEqual(expected_totals(normalized), {
            "roots": 1280, "calibration_shots": 2_560_000,
            "evaluation_shots": 3_200_000, "unique_shots": 5_760_000,
        })

    def test_dynamic_audit_does_not_retain_v2_500_archive_limit(self):
        keys = expected_root_keys([0, .004, .008, .012, .016], 256)
        self.assertEqual(len(keys), 1280)
        self.assertNotEqual(len(keys), 500)

    def test_candidate_allocation_is_not_v2_config_mutation(self):
        v2 = json.loads((HERE.parents[0] / "stage5_preexecution_v1/STAGE5_V2_CONFIG.json").read_text(encoding="utf-8"))
        candidate = json.loads((HERE / "PROPOSED_256_ALLOCATION.json").read_text(encoding="utf-8"))
        self.assertEqual(v2["evaluation"]["roots_per_condition"], 100)
        self.assertEqual(candidate["roots_per_probability"], 256)
        self.assertEqual(candidate["status"], "allocation candidate only; not an execution freeze")


if __name__ == "__main__":
    unittest.main()
