"""No-sampling regression tests for the corrected detector-only pathway."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import json
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from outputs.strong_fixed_baselines_v2 import pooled_calibration_v2 as calibration
from outputs.strong_fixed_baselines_v2 import run_development_v2 as runner
from outputs.strong_fixed_baselines_v2 import freeze_pretest_v2


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
            "calibrate_pooled_static(\n        template_batches, detector_batches",
            source,
        )
        self.assertNotIn("final_cal_batches", source)
        self.assertIn("detector_batches.append(arrays[\"detectors\"])", source)

    def test_mocked_runner_calibration_stage_end_to_end_is_detector_only(self):
        """Exercise runner collection -> profile fit -> pooled estimate without Stim."""
        cfg = {
            "partitions": {"evaluation_roots_per_condition": 1},
            "circuit": {"probabilities": [0.0, 0.004, 0.008]},
            "decoders": {"calibration_shots_per_root": 2},
        }
        templates = [
            (0.0, np.zeros((3, 40), dtype=np.uint8)),
            (0.01, np.ones((3, 40), dtype=np.uint8)),
            (0.02, np.eye(40, dtype=np.uint8)[:3]),
        ]
        generated = {}
        stream_seeds = {0.0: 91000001, 0.004: 91000002, 0.008: 91000003}

        def fake_stream(_inventory, role, split, probability, root):
            self.assertEqual((role, split, root), ("calibration", "heldout_development", 0))
            return {"seed": stream_seeds[float(probability)], "shots": 2}

        def fake_sample(probability, seed, shots, _cfg, *, labels):
            self.assertFalse(labels)
            self.assertEqual(shots, 2)
            rows = np.full((shots, 40), int(probability > 0), dtype=np.uint8)
            generated[int(seed)] = rows
            return rows

        def fake_read(_path, _partition, _probability, _root, seed):
            return {"detectors": generated[int(seed)]}

        estimator = Mock()
        estimator.estimate.side_effect = lambda detectors: 0.00804
        fit_calls = []

        def capture_profile_fit(received_templates):
            fit_calls.append(received_templates)
            return estimator

        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(runner, "health"), \
             patch.object(runner, "stream_for", side_effect=fake_stream), \
             patch.object(runner, "sample_arrays", side_effect=fake_sample) as sampler, \
             patch.object(runner, "checkpoint") as checkpoint, \
             patch.object(runner, "read_data", side_effect=fake_read), \
             patch.object(runner, "sha256", return_value="a" * 64), \
             patch.object(runner, "record_latest_checkpoint"), \
             patch.object(calibration, "detector_profile_estimator", side_effect=capture_profile_fit):
            _model, p_hat, pooled, refs = runner.run_pooled_calibration_stage(
                Path(temporary), cfg, {"streams": "mocked"}, 0.0, templates
            )

        self.assertEqual(sampler.call_count, 3)
        self.assertEqual(checkpoint.call_count, 3)
        self.assertEqual(len(fit_calls), 1)
        fitted_templates = fit_calls[0]
        self.assertEqual([p for p, _ in fitted_templates], [0.0, 0.01, 0.02])
        for (_, observed), (_, expected) in zip(fitted_templates, templates):
            np.testing.assert_array_equal(observed, expected)
        expected_pool = np.concatenate([generated[stream_seeds[p]] for p in cfg["circuit"]["probabilities"]])
        np.testing.assert_array_equal(estimator.estimate.call_args.args[0], expected_pool)
        self.assertIsInstance(estimator.estimate.call_args.args[0], np.ndarray)
        self.assertEqual(pooled.shape, (6, 40))
        np.testing.assert_array_equal(pooled, expected_pool)
        self.assertEqual(p_hat, 0.00804)
        self.assertEqual([row["probability"] for row in refs], cfg["circuit"]["probabilities"])

    def test_ambiguous_calibration_commit_marker_fails_before_sampling(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            archive = run_dir / "heldout_development_calibration" / "p_0.000" / "root_000.npz"
            archive.parent.mkdir(parents=True)
            archive.with_suffix(archive.suffix + ".commit.json").write_text("{}", encoding="utf-8")
            cfg = {
                "partitions": {"evaluation_roots_per_condition": 1},
                "circuit": {"probabilities": [0.0]},
                "decoders": {"calibration_shots_per_root": 2},
            }
            with patch.object(runner, "health"), \
                 patch.object(runner, "stream_for", return_value={"seed": 910001}), \
                 patch.object(runner, "archive_path", return_value=archive), \
                 patch.object(runner, "load_checkpoint", side_effect=RuntimeError("ambiguous archive")), \
                 patch.object(runner, "sample_arrays") as sampler:
                with self.assertRaisesRegex(RuntimeError, "ambiguous archive"):
                    runner.run_pooled_calibration_stage(
                        run_dir, cfg, {}, 0.0,
                        [(0.0, np.zeros((2, 40), dtype=np.uint8)),
                         (0.02, np.ones((2, 40), dtype=np.uint8))],
                    )
            sampler.assert_not_called()

    def test_runner_rejects_persisted_calibration_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            cfg = {
                "partitions": {"evaluation_roots_per_condition": 1},
                "circuit": {"probabilities": [0.0]},
                "decoders": {"calibration_shots_per_root": 2},
            }
            detectors = np.zeros((2, 40), dtype=np.uint8)
            with patch.object(runner, "health"), \
                 patch.object(runner, "stream_for", return_value={"seed": 910001}), \
                 patch.object(runner, "sample_arrays", return_value=detectors), \
                 patch.object(runner, "checkpoint"), \
                 patch.object(runner, "read_data", return_value={
                     "detectors": detectors, "observable": np.zeros(2, dtype=np.uint8)
                 }), \
                 patch.object(runner, "sha256", return_value="a" * 64), \
                 patch.object(runner, "calibrate_pooled_static") as fit:
                with self.assertRaisesRegex(RuntimeError, "must be detector-only"):
                    runner.run_pooled_calibration_stage(
                        Path(temporary), cfg, {}, 0.0,
                        [(0.0, np.zeros((2, 40), dtype=np.uint8)),
                         (0.02, np.ones((2, 40), dtype=np.uint8))],
                    )
            fit.assert_not_called()

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

    def test_v2_candidate_freeze_verifies_but_is_not_sampling_authorization(self):
        freeze = freeze_pretest_v2.verify_freeze()
        self.assertFalse(freeze["sampling_authorized"])
        self.assertFalse(freeze["sampling_performed_at_freeze"])
        cfg = json.loads(freeze_pretest_v2.CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertFalse(cfg["execution"]["sampling_authorized"])
        with self.assertRaisesRegex(PermissionError, "not authorized for sampling"):
            runner.require_sampling_authorized(cfg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
