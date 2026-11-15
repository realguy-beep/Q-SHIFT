from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from outputs.qshift_correlated_decoder_feasibility_v1_1.analyze_saved import analyze


class SavedArrayAnalysisTests(unittest.TestCase):
    def test_paired_root_counts_and_decision_are_recomputed_from_arrays(self) -> None:
        source_inventory = Path(__file__).resolve().parents[1] / "seed_inventory.json"
        inventory = json.loads(source_inventory.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            eval_dir = run / "evaluation"
            eval_dir.mkdir()
            calls = []
            for qi, q in enumerate((0.0, 0.01, 0.02)):
                for ri in range(10):
                    detectors = np.zeros((2000, 40), dtype=np.uint8)
                    labels = np.zeros((2000, 1), dtype=np.uint8)
                    pred_a = np.zeros((2000, 1), dtype=np.uint8)
                    pred_a2 = np.zeros((2000, 1), dtype=np.uint8)
                    pred_b = np.zeros((2000, 1), dtype=np.uint8)
                    pred_c = np.zeros((2000, 1), dtype=np.uint8)
                    if q > 0:
                        pred_b[0, 0] = 1
                    target = eval_dir / f"eval_q{qi}_r{ri:02d}.npz"
                    np.savez_compressed(target, detectors=detectors, observables=labels,
                                        pred_A=pred_a, pred_A2=pred_a2, pred_B=pred_b, pred_C=pred_c)
                    key = f"evaluation:q{q:.2f}:root{ri:02d}"
                    calls.append({
                        "key": key,
                        "seed": inventory["seeds"][key],
                        "sample_id": hashlib.sha256(key.encode()).hexdigest(),
                        "archive": f"evaluation/{target.name}",
                        "archive_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        "archive_bytes": target.stat().st_size,
                        "shots": 2000,
                        "state": "committed",
                    })
            (run / "status.json").write_text(json.dumps({
                "state": "evaluation_complete_pending_independent_analysis",
                "sampler_calls_started": calls, "shots_started": 60000,
                "shots_committed": 60000,
            }), encoding="utf-8")
            (run / "execution_identity.json").write_text(json.dumps({
                "evaluation_labels_exposed_to_decoders": False,
            }), encoding="utf-8")
            (run / "models_frozen.json").write_text(json.dumps({"global_A_qhat": 0.01}), encoding="utf-8")
            (run / "calibration_diagnostics.json").write_text(json.dumps({
                "estimation_summary": {"0.0": {"mae": 0.0}, "0.01": {"mae": 0.0}, "0.02": {"mae": 0.0}},
            }), encoding="utf-8")
            result = analyze(run)
            self.assertEqual(result["evaluation_shots"], 60000)
            self.assertEqual(result["arm_totals"]["A"]["errors"], 0)
            self.assertEqual(result["arm_totals"]["B"]["errors"], 20)
            self.assertAlmostEqual(result["primary_estimand_B_minus_A_equal_weight_q0_01_q0_02"], 0.0005)
            self.assertEqual(result["decision"], "NO_GO")
            self.assertEqual(len(result["paired_archive_sha256"]), 30)


if __name__ == "__main__":
    unittest.main()
