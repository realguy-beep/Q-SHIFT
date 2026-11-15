from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import stim
from unittest import mock

from outputs.qshift_correlated_decoder_feasibility_v1.analyze_saved import analyze_run
from outputs.qshift_correlated_decoder_feasibility_v1.run_pilot import dry_run


class SavedArrayAuditTests(unittest.TestCase):
    def make_fixture(self, root: Path):
        (root / "evaluation").mkdir(parents=True)
        (root / "calibration").mkdir()
        per_root = {}
        for qi, q in enumerate((0.0, 0.01, 0.02)):
            for ri in range(10):
                y = np.zeros((2000, 1), dtype=np.uint8)
                pred_a = y.copy()
                pred_b = y.copy()
                if qi == 0:
                    pred_a[:20] = 1
                    pred_b[:20] = 1
                else:
                    pred_a[:200] = 1
                    pred_b[:150] = 1
                pred_a2 = pred_b.copy()
                pred_c = y.copy()
                np.savez_compressed(root / "evaluation" / f"eval_q{qi}_r{ri:02d}.npz",
                    detectors=np.zeros((2000, 40), dtype=np.uint8), observables=y,
                    pred_A=pred_a, pred_A2=pred_a2, pred_B=pred_b, pred_C=pred_c)
                per_root[f"q{qi}_r{ri:02d}"] = q
        (root / "calibration" / "diagnostics.json").write_text(json.dumps({
            "per_root_qhat": {k: v for k, v in per_root.items()}
        }), encoding="utf-8")
        (root / "models_frozen.json").write_text(json.dumps({"global_A_q": 0.01}), encoding="utf-8")

    def test_recomputes_paired_primary_and_zero_gate_from_saved_arrays(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            inventory = {"seeds": {"statistics:primary-bootstrap": 41,
                                    "statistics:zero-bootstrap": 42}}
            result = analyze_run(root, inventory, bootstrap_replicates=200)
            self.assertEqual(result["decision"], "GO_DEVELOPMENT_ONLY")
            self.assertAlmostEqual(result["primary_estimand_B_minus_A"], -0.025)
            self.assertEqual(result["arm_totals"]["A"]["shots"], 60000)
            self.assertEqual(result["arm_totals"]["B"]["shots"], 60000)
            self.assertEqual(len(result["evaluation_archive_sha256"]), 30)
            self.assertEqual(result["q0_B_minus_A_one_sided_95_percentile_bounds"]["upper_95th"], 0.0)

    def test_frozen_allocation_arithmetic(self):
        config_path = Path(__file__).parents[1] / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        allocation = config["allocation"]
        self.assertEqual(allocation["training_shots_total"] + allocation["calibration_shots_total"] + allocation["evaluation_shots_total"], 78000)
        self.assertEqual(allocation["sampler_calls"], 63)
        self.assertEqual(config["environment"]["psutil"], "7.2.2")

    def test_missing_archive_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evaluation").mkdir()
            with self.assertRaisesRegex(ValueError, "missing evaluation archive"):
                analyze_run(root, {"seeds": {"statistics:primary-bootstrap": 1,
                                               "statistics:zero-bootstrap": 2}}, bootstrap_replicates=10)

    def test_runner_refuses_sampling_outside_watchdog(self):
        from outputs.qshift_correlated_decoder_feasibility_v1.run_pilot import execute
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "only under the Windows wall-clock wrapper"):
                execute({}, {}, "0" * 40)
    def test_dry_run_reports_zero_sampler_calls(self):
        from outputs.qshift_correlated_decoder_feasibility_v1 import run_pilot
        config = json.loads((Path(run_pilot.__file__).parent / "config.json").read_text(encoding="utf-8"))
        inventory = json.loads((Path(run_pilot.__file__).parent / "seed_inventory.json").read_text(encoding="utf-8"))
        # Circuit and DEM construction are deterministic; sampler invocation is not part of dry-run.
        with mock.patch.object(stim.Circuit, "compile_detector_sampler", side_effect=AssertionError("sampler forbidden")):
            dry_run(config, inventory)


if __name__ == "__main__":
    unittest.main()
