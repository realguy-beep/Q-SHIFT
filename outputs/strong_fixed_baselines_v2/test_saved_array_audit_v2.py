"""Fixture-only tests for the independent V2 saved-array auditor."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_saved_arrays_v2 as audit


class SavedArrayAuditTests(unittest.TestCase):
    def _archive(self, folder: Path, detectors: np.ndarray | None = None) -> Path:
        path = folder / "calibration" / "p_0.004" / "root_000.npz"
        path.parent.mkdir(parents=True, exist_ok=True)
        d = np.zeros((3, 40), dtype=np.uint8) if detectors is None else detectors
        metadata = {"partition": "calibration", "probability": 0.004, "root": 0,
                    "seed": 987654321, "shots": 3}
        np.savez_compressed(path, detectors=d, metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)))
        marker = {"schema_version": 1, "sha256": audit.sha256(path), "metadata": metadata}
        path.with_suffix(path.suffix + ".commit.json").write_text(json.dumps(marker), encoding="utf-8")
        return path

    def test_committed_detector_only_archive_is_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self._archive(Path(temporary))
            arrays, metadata = audit.verify_archive(
                path, expected_partition="calibration", expected_probability=0.004,
                expected_root=0, expected_seed=987654321, expected_shots=3,
                expected_arrays={"detectors"},
            )
        self.assertEqual(arrays["detectors"].shape, (3, 40))
        self.assertEqual(metadata["seed"], 987654321)

    def test_hash_and_archive_identity_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self._archive(Path(temporary))
            with path.open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                audit.verify_archive(
                    path, expected_partition="calibration", expected_probability=0.004,
                    expected_root=0, expected_seed=987654321, expected_shots=3,
                    expected_arrays={"detectors"},
                )

    def test_calibration_archive_with_labels_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cal.npz"
            path.parent.mkdir(parents=True, exist_ok=True)
            metadata = {"partition": "calibration", "probability": 0.004, "root": 0,
                        "seed": 987654321, "shots": 3}
            np.savez_compressed(path, detectors=np.zeros((3, 40), dtype=np.uint8),
                                observable=np.zeros(3, dtype=np.uint8),
                                metadata_json=np.asarray(json.dumps(metadata)))
            marker = {"schema_version": 1, "sha256": audit.sha256(path), "metadata": metadata}
            path.with_suffix(path.suffix + ".commit.json").write_text(json.dumps(marker), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "archive arrays"):
                audit.verify_archive(
                    path, expected_partition="calibration", expected_probability=0.004,
                    expected_root=0, expected_seed=987654321, expected_shots=3,
                    expected_arrays={"detectors"},
                )

    def test_detector_profile_reference_uses_only_detector_features(self):
        templates = [
            (0.0, np.zeros((4, 40), dtype=np.uint8)),
            (0.02, np.ones((4, 40), dtype=np.uint8)),
        ]
        profile = audit.fit_reference_profiles(templates)
        self.assertEqual(profile["means"].shape, (2, 45))
        estimate = audit.estimate_probability(profile, np.zeros((8, 40), dtype=np.uint8), 1e-5)
        self.assertTrue(0.0 <= estimate <= 0.02)
        with self.assertRaises(ValueError):
            audit.detector_features(np.zeros((4, 41), dtype=np.uint8))

    def test_paired_residual_counting(self):
        obs = np.asarray([0, 1, 1, 0], dtype=np.uint8)
        pred = np.asarray([0, 0, 1, 1], dtype=np.uint8)
        self.assertEqual(audit.root_errors(pred, obs), 2)

    def test_auditor_does_not_import_v2_runner_or_reporting(self):
        source = Path(audit.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import run_development_v2", source)
        self.assertNotIn("from outputs.strong_fixed_baselines_v2.run_development_v2", source)

    def test_auditor_rejects_paths_outside_v2_and_output_inside_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            external = Path(temporary)
            with self.assertRaisesRegex(ValueError, "contained under the V2"):
                audit.audit_run(external, external / "audit.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
