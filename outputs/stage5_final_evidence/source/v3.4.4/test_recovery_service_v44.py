from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import atomic_safety_v44 as atomic
import recovery_core_v44 as core
import recovery_service_v44 as service


class _Estimator:
    def estimate(self, detectors):
        return 0.0


def _build_decoder(probability):
    return (None, None, float(probability))


def _decode(decoder, detectors):
    return (np.asarray(detectors)[:, 0] ^ np.uint8(int(decoder)))


class RecoveryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qshift-v44-benchmark-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.source = self.repo / "outputs/stage5_secondary_inference_repair_v1/run"
        self.inventory = self.repo / "outputs/stage5_postfailure_forensics_v1/PRE_INVESTIGATION_SHA256.json"
        self.destination = self.repo / "outputs/recovery-copy"
        (self.source / "roots").mkdir(parents=True)
        self.inventory.parent.mkdir(parents=True)

        cal = np.zeros((3, 40), dtype=np.uint8)
        det = np.zeros((4, 40), dtype=np.uint8)
        obs = np.zeros((4,), dtype=np.uint8)
        archive = self.source / "roots/root_p0.000_r000.npz"
        arrays = {
            "phase": np.asarray("evaluation_complete"),
            "calibration_detectors": cal,
            "evaluation_detectors": det,
            "observables": obs,
            "probability": np.asarray(0.0),
            "root": np.asarray(0),
            "seed_calibration": np.asarray(314159),
            "seed_evaluation": np.asarray(271828),
        }
        atomic.write_committed_npz(archive, arrays, run_dir=self.source,
                                   expected_archive_sha256=None,
                                   expected_marker_sha256=None,
                                   deadline_monotonic=__import__("time").monotonic()+30)
        self.status = self.source / "status.json"
        self.status.write_text(json.dumps({
            "status": "worker_failed", "completed_roots": 0,
            "calibration_shots_generated": 3, "evaluation_shots_generated": 0,
            "unique_shots_generated": 3,
            "in_flight": {"kind": "evaluation", "p": 0.0, "root": 0},
        }), encoding="utf-8")
        for role in ("launcher", "worker", "auditor", "finalizer", "intent"):
            (self.source / f".stage5-{role}.lock").write_bytes(b"\0")

        # Inventory is complete but entirely disposable benchmark material.
        # The archive writer creates six lock/intent/applied-marker files.
        for i in range(251):
            p = self.repo / "benchmark_extra" / f"evidence_{i:03d}.txt"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"fixture-{i}\n", encoding="utf-8")
        files = []
        for p in sorted(x for x in self.repo.rglob("*") if x.is_file() and x != self.inventory):
            files.append({"path": p.relative_to(self.repo).as_posix(),
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                          "size_bytes": p.stat().st_size})
        self.assertEqual(len(files), 265)
        self.inventory.write_text(json.dumps({
            "base_commit": "8c06750808582137f6a81e2170ad702a552594fb",
            "file_count": len(files), "files": files,
        }), encoding="utf-8")

        self.old = (service.ROOT, service.SOURCE_RUN, service.SOURCE_INVENTORY)
        service.ROOT, service.SOURCE_RUN, service.SOURCE_INVENTORY = self.repo, self.source, self.inventory
        self.addCleanup(self._restore_constants)
        self.context = service.FrozenContext(
            probabilities=(0.0,), roots_per_condition=1,
            seeds={
                ("calibration_detector_only", 0.0, 0): 314159,
                ("paired_evaluation_detector_observable", 0.0, 0): 271828,
            }, estimator=_Estimator(), build_decoder=_build_decoder,
            decode_prediction=_decode, calibration_shots=3,
            evaluation_shots=4, detector_count=40, prediction_arms=3,
        )

    def _restore_constants(self):
        service.ROOT, service.SOURCE_RUN, service.SOURCE_INVENTORY = self.old

    def test_recovery_copy_completes_saved_evaluation_without_sampling(self):
        original_hashes = {p.relative_to(self.repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in self.source.rglob("*") if p.is_file()}
        provenance = service.prepare_recovery_copy(self.destination)
        self.assertEqual(provenance["source_inventory_file_count_verified"], 265)
        deadline = __import__("time").monotonic() + 60
        first = service.reconcile_recovery_copy(self.destination, self.context,
                                                deadline_monotonic=deadline)
        self.assertEqual(first["status"], "recovery_ready_no_sampling")
        self.assertEqual(first["new_samples"], 0)
        self.assertEqual(first["ledger"]["calibration_shots_generated"], 3)
        self.assertEqual(first["ledger"]["evaluation_shots_generated"], 4)
        self.assertEqual(first["ledger"]["completed_roots"], 1)
        self.assertEqual(first["finished_saved_checkpoints"][0]["additional_samples_generated"], 0)

        saved = self.destination / "roots/root_p0.000_r000.npz"
        with np.load(saved, allow_pickle=False) as z:
            self.assertEqual(str(z["phase"].item()), "complete")
            np.testing.assert_array_equal(z["predictions"], np.zeros((3, 4), dtype=np.uint8))
        status = json.loads((self.destination / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["status"], "recovery_ready_no_sampling")
        self.assertEqual(status["completed_roots"], 1)
        self.assertEqual(status["unique_shots_generated"], 7)
        self.assertIsNone(status["in_flight"])

        # Repeat to prove idempotency: same archive identity and no counter-add.
        checkpoint_hash = atomic.sha256_file(saved)
        second = service.reconcile_recovery_copy(self.destination, self.context,
                                                 deadline_monotonic=__import__("time").monotonic()+60)
        self.assertEqual(second["new_samples"], 0)
        self.assertEqual(atomic.sha256_file(saved), checkpoint_hash)
        status2 = json.loads((self.destination / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status2["unique_shots_generated"], 7)
        events = json.loads((self.destination / "RECOVERY_JOURNAL_V44.json").read_text(encoding="utf-8"))["events"]
        self.assertEqual(len({x["event_id"] for x in events}), len(events))

        # Every byte in the historical source remains unchanged.
        after = {p.relative_to(self.repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.source.rglob("*") if p.is_file()}
        self.assertEqual(after, original_hashes)

    def test_original_failed_run_is_never_a_recovery_target(self):
        with self.assertRaises(service.RecoveryServiceError):
            service.reconcile_recovery_copy(self.source, self.context)

    def test_tampered_recovery_copy_is_rejected(self):
        service.prepare_recovery_copy(self.destination)
        status_path = self.destination / "status.json"
        status_path.write_text("{}", encoding="utf-8")
        with self.assertRaises(service.RecoveryServiceError):
            service.check_recovery_provenance(self.destination)

    def test_duplicate_expected_root_is_rejected(self):
        service.prepare_recovery_copy(self.destination)
        with self.assertRaises(core.RecoveryValidationError):
            core.scan_archive_ledger(
                self.destination, expected_seeds=self.context.expected_seeds,
                expected_roots=[(0.0, 0), (0.0, 0)], detector_count=40,
                calibration_shots=3, evaluation_shots=4, prediction_arms=3,
                estimator_verifier=lambda _cal, _value: True,
            )

    def test_recovery_service_has_no_sampling_or_stage5_cli(self):
        source = (HERE / "recovery_service_v44.py").read_text(encoding="utf-8")
        self.assertNotIn("compile_detector_sampler", source)
        self.assertNotIn(".sample(", source)
        self.assertIn("This module exposes recovery-copy primitives only", source)

    def test_interrupted_checkpoint_commit_recovers_from_exact_intent(self):
        service.prepare_recovery_copy(self.destination)
        previous = os.environ.get("QSHIFT_STAGE5_V44_TEST_MODE")
        os.environ["QSHIFT_STAGE5_V44_TEST_MODE"] = "1"
        self.addCleanup(lambda: os.environ.pop("QSHIFT_STAGE5_V44_TEST_MODE", None)
                        if previous is None else os.environ.__setitem__("QSHIFT_STAGE5_V44_TEST_MODE", previous))

        def crash_between_archive_and_marker(stage):
            if stage == "after_archive_commit_before_sidecar":
                raise RuntimeError("benchmark injected interruption after archive replacement")

        with self.assertRaisesRegex(RuntimeError, "benchmark injected interruption"):
            service.reconcile_recovery_copy(
                self.destination, self.context,
                deadline_monotonic=__import__("time").monotonic()+60,
                _benchmark_fault=crash_between_archive_and_marker,
            )
        result = service.reconcile_recovery_copy(
            self.destination, self.context,
            deadline_monotonic=__import__("time").monotonic()+60,
        )
        self.assertEqual(result["status"], "recovery_ready_no_sampling")
        self.assertEqual(result["new_samples"], 0)
        self.assertEqual(result["ledger"]["completed_roots"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
