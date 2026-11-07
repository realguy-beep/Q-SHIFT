from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "dashboard"))

from controller import CheckpointStore, assert_allowed_split  # noqa: E402
from experiment import balanced_epoch_batches, target_for  # noqa: E402
from prepare_freeze import make_inventory  # noqa: E402


class ControllerSafetyTests(unittest.TestCase):
    def test_inventory_is_complete_and_unique(self):
        config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
        inventory = make_inventory(config)
        values = []
        for stream in inventory["streams"]:
            values.extend(map(int, stream["seeds"]))
        for stream in inventory["dry_run_streams"]:
            values.append(int(stream["seed"]))
        for stream in inventory["model_streams"]:
            values.extend((int(stream["torch_seed"]), int(stream["sampling_seed"]), int(stream["shuffle_seed"])))
        values.extend(map(int, inventory["dry_run_model_rng_seeds"]))
        values.extend(map(int, inventory["circuit_diagnostic_seeds"]))
        values.extend(map(int, inventory["dry_run_circuit_diagnostic_seeds"]))
        self.assertEqual(len(values), inventory["proposed_derived_seed_count"])
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(inventory["unique_derived_seed_count"], len(set(values)))
        self.assertTrue(inventory["passed"], inventory["collisions"])

    def test_test_split_is_unavailable(self):
        for allowed in ("train", "monitor", "calibration", "threshold_selection", "final_development_evaluation"):
            assert_allowed_split(allowed)
        with self.assertRaises(RuntimeError):
            assert_allowed_split("test")

    def test_balanced_batches_use_exact_training_prefix_count(self):
        by_regime = {}
        for regime in ("x_biased", "balanced", "z_biased"):
            y = np.array([0] * 18 + [1] * 6, dtype=np.uint8)
            by_regime[regime] = {"observable": y, "pymatching": np.zeros_like(y)}
        sizes = {r: 23 for r in by_regime}
        batches = balanced_epoch_batches(by_regime, sizes, 8, np.random.default_rng(123))
        self.assertEqual(sum(len(ix) for _, ix in batches), 69)
        for regime, indices in batches:
            y = by_regime[regime]["observable"][indices]
            self.assertLessEqual(abs(int(y.sum()) - (len(y) - int(y.sum()))), 1)

    def test_residual_label_is_logical_xor_matching(self):
        data = {"observable": np.array([0, 1, 1, 0], dtype=np.uint8),
                "pymatching": np.array([1, 1, 0, 0], dtype=np.uint8)}
        np.testing.assert_array_equal(target_for(data, True), np.array([1, 0, 1, 0], dtype=np.uint8))

    def test_checkpoint_corruption_falls_back_to_previous_valid_slot(self):
        with tempfile.TemporaryDirectory() as td:
            store = CheckpointStore(Path(td))
            store.save("job", {"value": "first"})
            store.save("job", {"value": "second"})
            slots = []
            for meta_path in store.directory.glob("job.*.json"):
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta["sequence"] == 2:
                    slots.append(meta_path.with_suffix(".pt"))
            self.assertEqual(len(slots), 1)
            slots[0].write_bytes(b"corrupt")
            restored = store.load("job")
            self.assertEqual(restored["value"], "first")


if __name__ == "__main__":
    unittest.main()
