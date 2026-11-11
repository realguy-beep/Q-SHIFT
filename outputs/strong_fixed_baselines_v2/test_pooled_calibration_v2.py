"""No-sampling regression tests for the corrected detector-only pathway."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pooled_calibration_v2 as calibration
import run_development_v2 as runner
import freeze_pretest_v2


class CorrectedPooledCalibrationTests(unittest.TestCase):
    def test_profile_fit_receives_templates_and_estimate_receives_pooled_detectors(self):
        templates = [
            (0.0, np.zeros((3, 40), dtype=np.uint8)),
            (0.01, np.ones((4, 40), dtype=np.uint8)),
            (0.02, np.eye(40, dtype=np.uint8)[:5]),
        ]
        calibration_batches = [
            np.zeros((2, 40), dtype=np.uint8),
            np.ones((3, 40), dtype=np.uint8),
        ]
        pooled = np.concatenate(calibration_batches)
        estimator = Mock()
        estimator.estimate.return_value = 0.00804

        with patch.object(calibration, "detector_profile_estimator", return_value=estimator) as fit:
            returned_estimator, p_hat, returned_pooled = calibration.calibrate_pooled_static(
                templates, calibration_batches
            )

        fit.assert_called_once()
        fitted_batches = fit.call_args.args[0]
        self.assertEqual([p for p, _ in fitted_batches], [0.0, 0.01, 0.02])
        for (_, actual), (_, expected) in zip(fitted_batches, templates):
            np.testing.assert_array_equal(actual, expected)
        estimator.estimate.assert_called_once()
        np.testing.assert_array_equal(estimator.estimate.call_args.args[0], pooled)
        self.assertIs(returned_estimator, estimator)
        self.assertEqual(p_hat, 0.00804)
        np.testing.assert_array_equal(returned_pooled, pooled)

    def test_generating_condition_tagged_calibration_is_rejected(self):
        estimator = Mock()
        detector_batch = np.zeros((3, 40), dtype=np.uint8)
        with self.assertRaisesRegex(TypeError, "condition-tagged calibration input is forbidden"):
            calibration.estimate_pooled_probability(estimator, [(0.004, detector_batch)])
        estimator.estimate.assert_not_called()

    def test_bad_shapes_and_nonbinary_values_fail_closed(self):
        with self.assertRaises(ValueError):
            calibration.fit_template_profiles([(0.0, np.zeros((4, 39), dtype=np.uint8))])
        estimator = Mock()
        with self.assertRaises(ValueError):
            calibration.estimate_pooled_probability(estimator, [np.full((2, 40), 2, dtype=np.uint8)])
        estimator.estimate.assert_not_called()

    def test_corrected_runner_uses_detector_only_calibration_path(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn(
            "calibrate_pooled_static(\n            template_batches, final_calibration_detector_batches",
            source,
        )
        self.assertNotIn("final_cal_batches", source)
        self.assertIn("final_calibration_detector_batches.append(arrays[\"detectors\"])", source)

    def test_candidate_runner_is_sampling_disabled_by_default(self):
        config_path = Path(__file__).with_name("experiment_config_v2.json")
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertFalse(cfg["execution"]["sampling_authorized"])
        with self.assertRaisesRegex(PermissionError, "not authorized for sampling"):
            runner.require_sampling_authorized(cfg)

    def test_full_runner_refuses_before_inventory_or_sampler_access(self):
        cfg_path = runner.CONFIG_PATH
        inv_path = runner.INVENTORY_PATH
        original_read_json = runner.read_json
        def read_config_only(path):
            if path == cfg_path:
                return json.loads(Path(cfg_path).read_text(encoding="utf-8"))
            if path == inv_path:
                raise AssertionError("candidate runner must stop before reading a seed inventory")
            return original_read_json(path)
        with patch.object(runner, "read_json", side_effect=read_config_only), \
             patch.object(runner, "sample_arrays") as sampler, \
             patch("sys.argv", ["run_development_v2.py"]):
            with self.assertRaisesRegex(PermissionError, "not authorized for sampling"):
                runner.main()
        sampler.assert_not_called()

    def test_v2_freeze_is_required_and_missing_freeze_fails_closed(self):
        self.assertFalse(freeze_pretest_v2.FREEZE_PATH.exists())
        with self.assertRaisesRegex(RuntimeError, "review candidate"):
            freeze_pretest_v2.verify_freeze()


if __name__ == "__main__":
    unittest.main(verbosity=2)
