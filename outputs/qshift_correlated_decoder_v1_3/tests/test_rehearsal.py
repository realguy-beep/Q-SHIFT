"""End-to-end interface rehearsal (fake sampler; no Stim sampler, no V1 data needed)."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import BurstRateEstimator, extract_burst_events
from outputs.qshift_correlated_decoder_v1_3 import contract as K
from outputs.qshift_correlated_decoder_v1_3.analyze_saved import analyze
from outputs.qshift_correlated_decoder_v1_3.rehearsal import REHEARSAL_ALLOCATION, fake_sampler, rehearse


def frozen_like_estimator() -> BurstRateEstimator:
    est = BurstRateEstimator(extract_burst_events())
    est.slope, est.intercept = 0.8800000000000001, 0.000666666666666673
    est.training_condition_rates = {}
    return est


class RehearsalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.result = rehearse(cls.work, frozen_like_estimator())
        cls.run_dir = cls.work / "rehearsal_run"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def load(self, name: str) -> dict:
        return json.loads((self.run_dir / name).read_text(encoding="utf-8"))

    def test_pipeline_completes_and_writes_every_final_file(self) -> None:
        status = self.load(K.FILE_STATUS)
        self.assertEqual(status["state"], K.STATE_COMPLETED)
        for name in (K.FILE_IDENTITY, K.FILE_MODELS, K.FILE_CALIBRATION, K.FILE_TRAINING,
                     K.FILE_ANALYSIS, K.FILE_PAIRED_CSV, K.FILE_MANIFEST):
            self.assertTrue((self.run_dir / name).is_file(), name)
        a = REHEARSAL_ALLOCATION
        self.assertEqual(status["eval_shots_committed"], a.eval_shots)
        self.assertEqual(status["calibration_shots_committed"], a.calibration_shots)
        self.assertEqual(len(status["sampler_calls_started"]), a.sampler_calls)
        self.assertEqual(self.load(K.FILE_MANIFEST)["decision"], self.result["decision"])

    def test_runner_writes_every_key_the_analyzer_requires(self) -> None:
        models = self.load(K.FILE_MODELS)
        for key in K.MODEL_REQUIRED_KEYS:
            self.assertIn(key, models)
        self.assertIn(K.KEY_ESTIMATION_SUMMARY, self.load(K.FILE_CALIBRATION))
        self.assertIs(self.load(K.FILE_IDENTITY)[K.KEY_LABELS_EXPOSED], False)

    def test_archives_hold_all_arms_and_calibration_holds_detectors_only(self) -> None:
        with np.load(self.run_dir / K.DIR_EVALUATION / K.eval_archive_name(1, 0)) as archive:
            self.assertEqual(set(archive.files), {"detectors", "observables", *(K.pred_member(x) for x in K.ARMS)})
        with np.load(self.run_dir / K.DIR_CALIBRATION / K.calibration_archive_name(2, 3)) as archive:
            self.assertEqual(archive.files, ["detectors"])

    def test_independent_reanalysis_to_separate_dir_is_identical_and_leaves_run_unchanged(self) -> None:
        before = {p.name: p.read_bytes() for p in self.run_dir.iterdir() if p.is_file()}
        out = self.work / "reanalysis"
        again = analyze(self.run_dir, out, allocation=REHEARSAL_ALLOCATION)
        self.assertEqual(again, self.result)
        self.assertEqual((out / K.FILE_PAIRED_CSV).read_bytes(), (self.run_dir / K.FILE_PAIRED_CSV).read_bytes())
        self.assertEqual({p.name: p.read_bytes() for p in self.run_dir.iterdir() if p.is_file()}, before)

    def test_missing_model_key_fails_before_any_output(self) -> None:
        copy = self.work / "broken_copy"
        shutil.copytree(self.run_dir, copy)
        for name in (K.FILE_ANALYSIS, K.FILE_PAIRED_CSV):
            (copy / name).unlink()
        status = json.loads((copy / K.FILE_STATUS).read_text(encoding="utf-8"))
        status["state"] = K.STATE_READY_FOR_ANALYSIS
        (copy / K.FILE_STATUS).write_text(json.dumps(status), encoding="utf-8")
        models = json.loads((copy / K.FILE_MODELS).read_text(encoding="utf-8"))
        models["tau_A2sw"] = models.pop(K.KEY_TAU)  # the V1.1 defect class: misnamed key
        (copy / K.FILE_MODELS).write_text(json.dumps(models), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, K.KEY_TAU):
            analyze(copy, allocation=REHEARSAL_ALLOCATION)
        self.assertFalse((copy / K.FILE_ANALYSIS).exists())
        self.assertFalse((copy / K.FILE_PAIRED_CSV).exists())

    def test_frozen_recount_script_matches_analysis(self) -> None:
        from outputs.qshift_correlated_decoder_v1_3.recount_from_scratch import main as recount
        self.assertEqual(recount([str(self.run_dir)]), 0)

    def test_analysis_refuses_mismatched_allocation(self) -> None:
        with self.assertRaisesRegex(ValueError, "allocation"):
            analyze(self.run_dir, self.work / "wrong_alloc", allocation=K.FROZEN_ALLOCATION)


class CalibrationGateTests(unittest.TestCase):
    def test_gate_failure_stops_before_any_evaluation_sample(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, "condition-order gate"):
                rehearse(Path(temp), frozen_like_estimator(), sampler=fake_sampler(burst_scale=0.0))
            run = Path(temp) / "rehearsal_run"
            status = json.loads((run / K.FILE_STATUS).read_text(encoding="utf-8"))
            self.assertEqual(status["state"], K.STATE_FAILED)
            self.assertEqual(status["eval_shots_committed"], 0)
            self.assertFalse(any(c["phase"] == "evaluation" for c in status["sampler_calls_started"]))
            self.assertFalse((run / K.DIR_EVALUATION).exists())
            self.assertFalse((run / K.FILE_MODELS).exists())


if __name__ == "__main__":
    unittest.main()
