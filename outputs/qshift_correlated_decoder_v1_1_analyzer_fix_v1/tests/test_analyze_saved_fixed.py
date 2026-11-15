from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from outputs.qshift_correlated_decoder_v1_1_analyzer_fix_v1.analyze_saved_fixed import (
    MODELS_GLOBAL_QHAT_KEY,
    V1_1_PACKAGE,
    analyze,
)

FROZEN_ANALYZER_SHA256 = "d6720b879cbef01f9c9a62ad103e930e5214129c615c4b0ade5e202320296239"


def build_fixture_run(run: Path, models: dict) -> None:
    """Synthetic 30-root run: all arms correct except B errs once per nonzero root."""
    inventory = json.loads((V1_1_PACKAGE / "seed_inventory.json").read_text(encoding="utf-8"))
    eval_dir = run / "evaluation"
    eval_dir.mkdir()
    calls = []
    for qi, q in enumerate((0.0, 0.01, 0.02)):
        for ri in range(10):
            zeros = np.zeros((2000, 1), dtype=np.uint8)
            pred_b = zeros.copy()
            if q > 0:
                pred_b[0, 0] = 1
            target = eval_dir / f"eval_q{qi}_r{ri:02d}.npz"
            np.savez_compressed(target, detectors=np.zeros((2000, 40), dtype=np.uint8),
                                observables=zeros, pred_A=zeros, pred_A2=zeros,
                                pred_B=pred_b, pred_C=zeros)
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
        "sampler_calls_started": calls, "shots_started": 60000, "shots_committed": 60000,
    }), encoding="utf-8")
    (run / "execution_identity.json").write_text(json.dumps({
        "evaluation_labels_exposed_to_decoders": False,
    }), encoding="utf-8")
    (run / "models_frozen.json").write_text(json.dumps(models), encoding="utf-8")
    (run / "calibration_diagnostics.json").write_text(json.dumps({
        "estimation_summary": {"0.0": {"mae": 0.0}, "0.01": {"mae": 0.0}, "0.02": {"mae": 0.0}},
    }), encoding="utf-8")


class FixedSavedArrayAnalysisTests(unittest.TestCase):
    def test_runner_key_is_accepted_and_scores_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            # The exact key the frozen runner wrote in attempt_001/models_frozen.json.
            build_fixture_run(run, {"A_global_qhat": 0.01})
            result = analyze(run)
            self.assertEqual(result["evaluation_shots"], 60000)
            self.assertEqual(result["arm_totals"]["A"]["errors"], 0)
            self.assertEqual(result["arm_totals"]["B"]["errors"], 20)
            self.assertAlmostEqual(result["primary_estimand_B_minus_A_equal_weight_q0_01_q0_02"], 0.0005)
            self.assertEqual(result["decision"], "NO_GO")
            self.assertEqual(len(result["paired_archive_sha256"]), 30)
            self.assertEqual(result["A_global_qhat"], 0.01)
            self.assertTrue((run / "analysis.json").is_file())

    def test_legacy_misnamed_key_fails_before_writing_outputs(self) -> None:
        # Regression for V1.1 attempt_001 (KeyError: 'global_A_qhat' after the CSV was written).
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            build_fixture_run(run, {"global_A_qhat": 0.01})
            with self.assertRaisesRegex(ValueError, "A_global_qhat"):
                analyze(run)
            self.assertFalse((run / "paired_results.csv").exists())
            self.assertFalse((run / "analysis.json").exists())

    def test_output_dir_leaves_run_dir_unwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run, out = Path(temp) / "run", Path(temp) / "out"
            run.mkdir()
            build_fixture_run(run, {"A_global_qhat": 0.01})
            before = {p.name for p in run.iterdir()}
            analyze(run, out)
            self.assertEqual({p.name for p in run.iterdir()}, before)
            self.assertTrue((out / "analysis.json").is_file())
            self.assertTrue((out / "paired_results.csv").is_file())

    def test_frozen_runner_writes_the_key_this_analyzer_reads(self) -> None:
        source = (V1_1_PACKAGE / "run_eval.py").read_text(encoding="utf-8")
        self.assertIn(f'"{MODELS_GLOBAL_QHAT_KEY}": global_q', source)

    def test_frozen_v1_1_analyzer_is_unmodified(self) -> None:
        digest = hashlib.sha256((V1_1_PACKAGE / "analyze_saved.py").read_bytes()).hexdigest()
        self.assertEqual(digest, FROZEN_ANALYZER_SHA256)


if __name__ == "__main__":
    unittest.main()
