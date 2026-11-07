from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))

import prepare_freeze
import run_sprint


class ResidualSprintTests(unittest.TestCase):
    def test_atomic_json_uses_a_complete_replace(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            run_sprint.atomic_json({"status": "ok", "shots": 3}, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")),
                             {"status": "ok", "shots": 3})
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_xor_label_and_correction_convention(self):
        obs = [1, 0, 0, 1]
        pm = [0, 0, 1, 1]
        residual = [o ^ p for o, p in zip(obs, pm)]
        corrected = [p ^ r for p, r in zip(pm, residual)]
        self.assertEqual(corrected, obs)
        m = run_sprint.confusion_metrics([1, 0, 1, 0], obs, pm)
        self.assertEqual(m["beneficial_corrections"], 1)
        self.assertEqual(m["harmful_corrections"], 1)
        self.assertEqual(m["candidate_only"], 1)
        self.assertEqual(m["pymatching_only"], 1)

    def test_wilson_bound_rejects_tiny_sample_and_accepts_stable_precision(self):
        alpha = 0.05 / 99
        self.assertLessEqual(run_sprint.wilson_lower(1, 1, alpha), 0.5)
        self.assertGreater(run_sprint.wilson_lower(99, 100, alpha), 0.5)

    def test_confidence_gate_falls_back_when_no_threshold_qualifies(self):
        data = {}
        probs = {}
        for regime in run_sprint.REGIMES:
            probs[regime] = [0.01, 0.02, 0.03, 0.04]
            data[regime] = {"pymatching": [0, 0, 0, 0], "observable": [0, 0, 0, 0]}
        selected = run_sprint.select_confidence_gate(probs, data, [0.01, 0.02, 0.03], 0.05)
        self.assertTrue(selected["fallback"])
        self.assertEqual(selected["threshold"], 1.01)

    def test_min_ler_threshold_is_validation_only_function(self):
        data = {}
        probs = {}
        for regime in run_sprint.REGIMES:
            probs[regime] = [0.9, 0.1]
            data[regime] = {"pymatching": [0, 0], "observable": [1, 0]}
        threshold, ler = run_sprint.select_min_ler_threshold(probs, data, [0.5, 0.95])
        self.assertEqual(threshold, 0.5)
        self.assertEqual(ler, 0.0)

    def test_inventory_allocates_disjoint_streams_without_test_split(self):
        cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
        inv = prepare_freeze.make_inventory(cfg)
        self.assertEqual(inv["derived_seed_count"], inv["unique_derived_seed_count"])
        self.assertEqual(len(inv["all_derived_seeds"]), len(set(inv["all_derived_seeds"])))
        self.assertTrue(all(x["split"] in run_sprint.ALLOWED_SPLITS for x in inv["streams"]))
        self.assertEqual(inv["unique_production_shots"], 1665000)

    def test_fixed_policy_inputs_have_no_test_partition(self):
        self.assertNotIn("test", run_sprint.ALLOWED_SPLITS)
        cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
        self.assertIn("prohibited", cfg["independent_test_access"])


if __name__ == "__main__":
    unittest.main()
