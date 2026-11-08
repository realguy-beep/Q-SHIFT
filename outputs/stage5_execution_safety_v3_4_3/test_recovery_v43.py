from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import atomic_safety_v43 as atomic
from recovery_v43 import (
    RecoveryValidationError,
    complete_evaluation_checkpoint,
    create_recovery_copy,
    reconstruct_status,
    root_filename,
    scan_archive_ledger,
    persist_reconstructed_status,
)

CHILD = HERE / "subprocess_fixture_v43.py"


def write_manual_npz(path: Path, arrays: dict):
    import io
    from atomic_safety_v43 import sha256_bytes
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(); np.savez_compressed(buf, **arrays)
    payload = buf.getvalue(); path.write_bytes(payload)
    marker = {"archive": path.name, "committed": True, "sha256": sha256_bytes(payload)}
    Path(str(path) + ".commit.json").write_text(json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return marker["sha256"]


def sample_arrays(prob, root, cal_seed, eval_seed, phase="evaluation_complete"):
    rng = np.random.default_rng(600000 + root)
    cal = rng.integers(0, 2, size=(4, 3), dtype=np.uint8)
    out = {"phase": np.asarray(phase), "calibration_detectors": cal,
           "probability": np.asarray(prob), "root": np.asarray(root),
           "seed_calibration": np.asarray(cal_seed)}
    if phase in {"evaluation_complete", "complete"}:
        out["evaluation_detectors"] = rng.integers(0, 2, size=(6, 3), dtype=np.uint8)
        out["observables"] = rng.integers(0, 2, size=(6,), dtype=np.uint8)
        out["seed_evaluation"] = np.asarray(eval_seed)
    if phase == "complete":
        out["p_hat"] = np.asarray(float(cal.mean()))
        out["predictions"] = np.stack([out["evaluation_detectors"][:, 0], out["evaluation_detectors"][:, 1]]).astype(np.uint8)
    return out


def seeds_for(*identities):
    return {tuple((float(p), int(r))): {"calibration": int(sc), "evaluation": int(se)}
            for p, r, sc, se in identities}


class RecoverySafetyV43Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qshift-v43-fixture-")
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_committed(self, run, p=0.1, root=1, sc=510001, se=510002, phase="evaluation_complete"):
        path = run / "roots" / root_filename(p, root)
        write_manual_npz(path, sample_arrays(p, root, sc, se, phase))
        return path

    def test_idempotent_reconstruction_counts_eval_complete_but_not_complete_roots(self):
        run = self.base / "run"; run.mkdir();
        mapping = seeds_for((0.1, 1, 510001, 510002), (0.2, 2, 520001, 520002), (0.3, 3, 530001, 530002))
        self.make_committed(run, 0.1, 1, 510001, 510002, "complete")
        self.make_committed(run, 0.2, 2, 520001, 520002, "evaluation_complete")
        self.make_committed(run, 0.3, 3, 530001, 530002, "calibration_complete")
        def independent(detectors, predictions):
            return np.array_equal(predictions, np.stack([detectors[:, 0], detectors[:, 1]]))
        def independent_estimator(cal, value):
            return abs(float(cal.mean()) - float(value)) <= 1e-12
        ledger = scan_archive_ledger(run, expected_seeds=mapping,
            expected_roots=[(0.1, 1), (0.2, 2), (0.3, 3)], detector_count=3,
            calibration_shots=4, evaluation_shots=6, prediction_arms=2,
            prediction_verifier=independent, estimator_verifier=independent_estimator)
        self.assertEqual((ledger["calibration_shots_generated"], ledger["evaluation_shots_generated"],
                          ledger["unique_shots_generated"], ledger["completed_roots"]), (12, 12, 24, 1))
        self.assertEqual(ledger["recoverable_evaluation_complete_roots"], [{"probability": 0.2, "root": 2}])
        stale = {"completed_roots": 900, "calibration_shots_generated": 0,
                 "evaluation_shots_generated": 0, "unique_shots_generated": 1,
                 "in_flight": {"kind": "evaluation", "p": 0.2, "root": 2}}
        rebuilt1 = reconstruct_status(stale, ledger)
        rebuilt2 = reconstruct_status(rebuilt1, ledger)
        self.assertEqual(rebuilt1, rebuilt2)
        self.assertEqual(rebuilt1["completed_roots"], 1)
        self.assertEqual(rebuilt1["unique_shots_generated"], 24)
        self.assertIsNone(rebuilt1["in_flight"])

    def test_inflight_without_matching_durable_archive_fails_closed(self):
        ledger = {"records": [], "calibration_shots_generated": 0, "evaluation_shots_generated": 0,
                  "unique_shots_generated": 0, "completed_roots": 0,
                  "recoverable_evaluation_complete_roots": [], "ledger_sha256": "x"}
        stale = {"in_flight": {"kind": "evaluation", "p": 0.1, "root": 1}}
        with self.assertRaisesRegex(RecoveryValidationError, "no corresponding durable checkpoint"):
            reconstruct_status(stale, ledger)

    def test_ledger_fails_closed_on_orphan_temp_or_unapplied_intent(self):
        run = self.base / "run"; run.mkdir()
        mapping = seeds_for((0.1, 1, 510001, 510002))
        self.make_committed(run, 0.1, 1, 510001, 510002)
        kwargs = dict(expected_seeds=mapping, expected_roots=[(0.1, 1)], detector_count=3,
                      calibration_shots=4, evaluation_shots=6, prediction_arms=2)
        orphan = run / ".qtmp-v43-orphan.tmp"; orphan.write_bytes(b"not committed")
        with self.assertRaisesRegex(RecoveryValidationError, "temporary exists"):
            scan_archive_ledger(run, **kwargs)
        orphan.unlink()
        intent_dir = run / ".stage5-v43-transactions" / "writes"; intent_dir.mkdir(parents=True)
        (intent_dir / "incomplete.json").write_text('{"format":"qshift-stage5-v43-write-intent"}', encoding="utf-8")
        with self.assertRaisesRegex(RecoveryValidationError, "unapplied write intent"):
            scan_archive_ledger(run, **kwargs)

    def test_duplicate_or_noncanonical_root_fails(self):
        run = self.base / "run"; run.mkdir()
        mapping = seeds_for((0.1, 1, 510001, 510002))
        self.make_committed(run, 0.1, 1, 510001, 510002)
        alias = run / "roots" / "root_p0.1000_r001.npz"
        write_manual_npz(alias, sample_arrays(0.1, 1, 510001, 510002))
        with self.assertRaisesRegex(RecoveryValidationError, "noncanonical root archive"):
            scan_archive_ledger(run, expected_seeds=mapping, expected_roots=[(0.1, 1)],
                detector_count=3, calibration_shots=4, evaluation_shots=6, prediction_arms=2)

    def test_seed_collision_and_unknown_checkpoint_phase_fail_closed(self):
        run = self.base / "run"; (run / "roots").mkdir(parents=True)
        colliding = seeds_for((0.1, 1, 510001, 510002), (0.2, 2, 510001, 520002))
        with self.assertRaisesRegex(RecoveryValidationError, "seed mapping contains collisions"):
            scan_archive_ledger(run, expected_seeds=colliding, expected_roots=[(0.1, 1), (0.2, 2)],
                detector_count=3, calibration_shots=4, evaluation_shots=6, prediction_arms=2)
        path = run / "roots" / root_filename(0.1, 1)
        write_manual_npz(path, sample_arrays(0.1, 1, 510001, 510002, "unknown"))
        with self.assertRaisesRegex(RecoveryValidationError, "unsupported checkpoint phase"):
            scan_archive_ledger(run, expected_seeds=seeds_for((0.1, 1, 510001, 510002)),
                expected_roots=[(0.1, 1)], detector_count=3,
                calibration_shots=4, evaluation_shots=6, prediction_arms=2)

    def test_prediction_and_commit_hash_corruption_fail_closed(self):
        run = self.base / "run"; run.mkdir()
        path = run / "roots" / root_filename(0.1, 1)
        write_manual_npz(path, sample_arrays(0.1, 1, 510001, 510002, "complete"))
        mapping = seeds_for((0.1, 1, 510001, 510002))
        with self.assertRaisesRegex(RecoveryValidationError, "prediction verification failed"):
            scan_archive_ledger(run, expected_seeds=mapping, expected_roots=[(0.1, 1)],
                detector_count=3, calibration_shots=4, evaluation_shots=6, prediction_arms=2,
                estimator_verifier=lambda cal, p: abs(float(cal.mean()) - p) < 1e-12,
                prediction_verifier=lambda det, pred: False)
        marker = Path(str(path) + ".commit.json")
        marker.write_text(json.dumps({"archive": path.name, "committed": True, "sha256": "0" * 64}), encoding="utf-8")
        with self.assertRaises(atomic.UncommittedCheckpointError):
            scan_archive_ledger(run, expected_seeds=mapping, expected_roots=[(0.1, 1)],
                detector_count=3, calibration_shots=4, evaluation_shots=6, prediction_arms=2,
                estimator_verifier=lambda cal, p: True,
                prediction_verifier=lambda det, pred: True)

    def test_recovery_copy_provenance_and_source_immutability(self):
        repo = self.base / "repo"; run = repo / "run"; (run / "roots").mkdir(parents=True)
        mapping = seeds_for((0.1, 1, 510001, 510002))
        self.make_committed(run, 0.1, 1, 510001, 510002)
        (run / "status.json").write_text(json.dumps({"status": "worker_failed", "in_flight": {"kind": "evaluation", "p": 0.1, "root": 1}}), encoding="utf-8")
        (run / ".stage5-worker.lock").write_bytes(b"x")
        rows = []
        for path in sorted(p for p in repo.rglob("*") if p.is_file()):
            rows.append({"path": path.relative_to(repo).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size})
        inventory_path = repo / "inventory.json"
        inventory = {"base_commit": "8c06750808582137f6a81e2170ad702a552594fb",
                     "file_count": len(rows), "files": rows}
        inventory_path.write_text(json.dumps(inventory, sort_keys=True), encoding="utf-8")
        before = {p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in repo.rglob("*") if p.is_file()}
        dest = self.base / "recovery-copy"
        prov = create_recovery_copy(run, dest, source_inventory_path=inventory_path,
                                    source_repository_root=repo)
        after = {p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in repo.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(prov["source_inventory_file_count_verified"], len(rows))
        self.assertEqual(prov["copied_file_count"], 3)
        self.assertIn(".stage5-worker.lock", prov["omitted_active_lock_and_owner_files"])
        self.assertFalse((dest / ".stage5-worker.lock").exists())
        self.assertEqual(hashlib.sha256((dest / "roots" / root_filename(0.1, 1)).read_bytes()).hexdigest(),
                         prov["copied_files"][f"roots/{root_filename(0.1, 1)}"])
        ledger = scan_archive_ledger(dest, expected_seeds=mapping, expected_roots=[(0.1, 1)],
            detector_count=3, calibration_shots=4, evaluation_shots=6, prediction_arms=2)
        status_path = dest / "status.json"
        stale_status = json.loads(status_path.read_text(encoding="utf-8"))
        persist_reconstructed_status(status_path, stale_status, ledger, run_dir=dest,
            deadline_monotonic=time.monotonic() + 5)
        first_status = status_path.read_bytes()
        reconciled = json.loads(first_status)
        self.assertEqual((reconciled["calibration_shots_generated"], reconciled["evaluation_shots_generated"],
                          reconciled["unique_shots_generated"], reconciled["completed_roots"]), (4, 6, 10, 0))
        persist_reconstructed_status(status_path, reconciled, ledger, run_dir=dest,
            deadline_monotonic=time.monotonic() + 5)
        self.assertEqual(status_path.read_bytes(), first_status)
        with self.assertRaises(FileExistsError):
            create_recovery_copy(run, dest, source_inventory_path=inventory_path,
                                 source_repository_root=repo)

    def test_complete_evaluation_checkpoint_without_resampling_and_idempotent_retry(self):
        run = self.base / "run"; run.mkdir()
        (run / "RECOVERY_PROVENANCE.json").write_text(json.dumps({
            "format": "qshift-stage5-v43-recovery-copy-provenance",
            "source_run_directory": str(self.base / "original-failed-run"),
            "source_inventory_sha256": "a" * 64,
        }), encoding="utf-8")
        path = self.make_committed(run, 0.1, 1, 510001, 510002)
        mapping = seeds_for((0.1, 1, 510001, 510002))
        calls = {"estimate": 0, "decode": 0}
        def estimate(cal):
            calls["estimate"] += 1
            return float(cal.mean())
        def decode(p_hat, detectors):
            calls["decode"] += 1
            return np.stack([detectors[:, 0], (detectors[:, 1] ^ (p_hat > 0.5)).astype(np.uint8)])
        # Independent check is separately derived and does not call the decoder callback.
        def independent_verifier(detectors, predictions):
            cal = np.load(path, allow_pickle=False)["calibration_detectors"]
            value = float(cal.mean())
            expected = np.stack([detectors[:, 0], (detectors[:, 1] ^ (value > 0.5)).astype(np.uint8)])
            return np.array_equal(predictions, expected)
        before = {"calibration": 4, "evaluation": 6}
        result = complete_evaluation_checkpoint(path, run_dir=run, expected_seeds=mapping,
            estimate_fn=estimate, decode_fn=decode, prediction_verifier=independent_verifier,
            deadline_monotonic=time.monotonic() + 10, detector_count=3, calibration_shots=4,
            evaluation_shots=6, prediction_arms=2)
        self.assertEqual(result["additional_samples_generated"], 0)
        self.assertEqual(result["calibration_rows_reused"], before["calibration"])
        self.assertEqual(result["evaluation_rows_reused"], before["evaluation"])
        self.assertEqual(result["state"], "complete")
        first_hash = atomic.sha256_file(path)
        again = complete_evaluation_checkpoint(path, run_dir=run, expected_seeds=mapping,
            estimate_fn=estimate, decode_fn=decode, prediction_verifier=independent_verifier,
            deadline_monotonic=time.monotonic() + 10, detector_count=3, calibration_shots=4,
            evaluation_shots=6, prediction_arms=2)
        self.assertEqual(again["state"], "already_complete")
        self.assertEqual(atomic.sha256_file(path), first_hash)

    def test_recovery_mutation_refuses_original_unmarked_directory(self):
        run = self.base / "unmarked"; run.mkdir()
        path = self.make_committed(run, 0.1, 1, 510001, 510002)
        with self.assertRaisesRegex(RecoveryValidationError, "provenance marker missing"):
            complete_evaluation_checkpoint(path, run_dir=run,
                expected_seeds=seeds_for((0.1, 1, 510001, 510002)),
                estimate_fn=lambda a: 0.2, decode_fn=lambda p, d: np.zeros((2, 6), dtype=np.uint8),
                prediction_verifier=lambda d, p: True,
                deadline_monotonic=time.monotonic() + 5, detector_count=3,
                calibration_shots=4, evaluation_shots=6, prediction_arms=2)

    def test_status_write_contention_two_real_subprocesses(self):
        run = self.base / "run"; run.mkdir()
        target = run / "status.json"; target.write_text('{"v":0}\n', encoding="utf-8")
        old_hash = atomic.sha256_file(target)
        payloads = []
        for i in range(2):
            expected = self.base / f"expected{i}"; expected.write_text(old_hash or "", encoding="ascii")
            payload = self.base / f"payload{i}"; payload.write_text(json.dumps({"v": i + 1}), encoding="utf-8")
            payloads.append((expected, payload, self.base / f"outcome{i}.json"))
        gate = self.base / "release.lock"
        ready = self.base / "held.ready"
        holder = subprocess.Popen([sys.executable, str(CHILD), "hold-lock", str(target), str(ready), str(gate)])
        try:
            deadline = time.monotonic() + 8
            while not ready.exists() and time.monotonic() < deadline: time.sleep(0.01)
            self.assertTrue(ready.exists(), "lock-holding child did not acquire status lock")
            writers = [subprocess.Popen([sys.executable, str(CHILD), "write-status", str(target), str(run), str(e), str(p), str(o)])
                       for e, p, o in payloads]
            for proc in writers:
                self.assertEqual(proc.wait(timeout=5), 2)
            states = [json.loads(o.read_text(encoding="utf-8"))["state"] for _, _, o in payloads]
            self.assertEqual(states, ["LockBusyError", "LockBusyError"])
            self.assertEqual(atomic.sha256_file(target), old_hash)
        finally:
            gate.write_text("release", encoding="utf-8")
            self.assertEqual(holder.wait(timeout=5), 0)
        # A later writer with the still-current expected hash succeeds exactly once.
        e, p, o = payloads[0]
        self.assertEqual(subprocess.run([sys.executable, str(CHILD), "write-status", str(target), str(run), str(e), str(p), str(o)], timeout=5).returncode, 0)
        self.assertEqual(json.loads(o.read_text(encoding="utf-8"))["state"], "written")

    def test_compare_and_swap_never_overwrites_newer_state(self):
        run = self.base / "cas"; run.mkdir()
        target = run / "status.json"; target.write_bytes(b'{"v":0}')
        old = atomic.sha256_file(target)
        atomic.atomic_write_bytes(target, b'{"v":1}', run_dir=run,
            expected_old_sha256=old, deadline_monotonic=time.monotonic() + 5)
        with self.assertRaises(atomic.ConcurrentStateError):
            atomic.atomic_write_bytes(target, b'{"v":2}', run_dir=run,
                expected_old_sha256=old, deadline_monotonic=time.monotonic() + 5)
        self.assertEqual(target.read_bytes(), b'{"v":1}')

    @unittest.skipUnless(os.name == "nt", "Windows sharing semantics required")
    def test_windows_transient_replace_retry_and_persistent_denial_preserve_exact_payload(self):
        run = self.base / "run"; run.mkdir()
        target = run / "status.json"; target.write_bytes(b'{"revision":1}\n')
        payload = b'{"revision":2,"complete":false}\n'
        original_replace = atomic.os.replace
        attempts = {"n": 0}
        def transient(src, dst):
            attempts["n"] += 1
            if attempts["n"] == 1:
                exc = PermissionError(5, "Access is denied")
                exc.winerror = 5
                raise exc
            return original_replace(src, dst)
        with mock.patch.object(atomic.os, "replace", side_effect=transient):
            result = atomic.atomic_write_bytes(target, payload, run_dir=run,
                expected_old_sha256=atomic.sha256_file(target), deadline_monotonic=time.monotonic() + 5,
                backoff=(0.001,))
        self.assertGreaterEqual(result["attempts"], 2)
        self.assertEqual(target.read_bytes(), payload)

        target.write_bytes(b'{"revision":3}\n')
        before = target.read_bytes()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                      ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateFileW(str(target), 0x80000000, 0x00000003, None, 3, 0x80, None)
        invalid = ctypes.c_void_p(-1).value
        self.assertNotEqual(handle, invalid, f"CreateFileW failed with {ctypes.get_last_error()}")
        try:
            with self.assertRaises(atomic.ReplaceRetryExhausted):
                atomic.atomic_write_bytes(target, payload, run_dir=run,
                    expected_old_sha256=atomic.sha256_file(target), deadline_monotonic=time.monotonic() + 5,
                    backoff=(0.01, 0.02))
            self.assertEqual(target.read_bytes(), before)
            events = [p for p in (run / ".stage5-v43-transactions" / "writes").glob("*.json")
                      if not p.name.endswith(".applied.json")]
            self.assertEqual(len(events), 2)
            pending = [p for p in run.glob(".qtmp-v43-*.tmp")]
            self.assertEqual(len(pending), 1)
            event = max(events, key=lambda p: p.stat().st_mtime_ns)
        finally:
            kernel.CloseHandle(handle)
        recovered = atomic.recover_write_intent(event, run_dir=run, deadline_monotonic=time.monotonic() + 5,
                                                backoff=(0.01,))
        self.assertEqual(recovered["state"], "recovered")
        self.assertEqual(target.read_bytes(), payload)

    @unittest.skipUnless(os.name == "nt", "Windows process termination semantics required")
    def test_subprocess_crashes_at_checkpoint_write_boundaries(self):
        stages = ["after_temp_fsync", "after_intent_fsync",
                  "after_archive_replace_before_sidecar", "after_commit_marker"]
        outcomes = {}
        for stage in stages:
            run = self.base / stage; (run / "roots").mkdir(parents=True)
            target = run / "roots" / "fixture.npz"
            proc = subprocess.run([sys.executable, str(CHILD), "crash-npz", str(run), str(target), stage], timeout=10)
            self.assertEqual(proc.returncode, 71, stage)
            if stage == "after_temp_fsync":
                self.assertFalse(target.exists())
                self.assertEqual(list((run / ".stage5-v43-transactions" / "writes").glob("*.json")) if (run / ".stage5-v43-transactions" / "writes").exists() else [], [])
                with self.assertRaises(atomic.UncommittedCheckpointError):
                    atomic.recover_npz_commit(target, run_dir=run, deadline_monotonic=time.monotonic() + 5)
                outcomes[stage] = "fail_closed_unjournaled_temp"
            else:
                result = atomic.recover_npz_commit(target, run_dir=run, deadline_monotonic=time.monotonic() + 5)
                self.assertEqual(atomic.verify_committed_npz(target), result["sha256"])
                with np.load(target, allow_pickle=False) as z:
                    self.assertEqual(z["payload"].tolist(), [1, 0, 1])
                outcomes[stage] = result["state"]
        self.assertEqual(outcomes["after_intent_fsync"], "marker_reconstructed_from_intent")
        self.assertEqual(outcomes["after_archive_replace_before_sidecar"], "marker_reconstructed_from_intent")
        self.assertEqual(outcomes["after_commit_marker"], "already_committed")

    @unittest.skipUnless(os.name == "nt", "Windows process termination semantics required")
    def test_crash_after_new_intent_supersedes_old_committed_checkpoint_safely(self):
        run = self.base / "update-run"; (run / "roots").mkdir(parents=True)
        target = run / "roots" / "fixture.npz"
        write_manual_npz(target, {"payload": np.asarray([0], dtype=np.uint8)})
        old = atomic.sha256_file(target)
        proc = subprocess.run([sys.executable, str(CHILD), "crash-update-npz", str(run), str(target), "after_intent_fsync"], timeout=10)
        self.assertEqual(proc.returncode, 71)
        self.assertNotEqual(atomic.sha256_file(target), "")
        result = atomic.recover_npz_commit(target, run_dir=run, deadline_monotonic=time.monotonic() + 5)
        self.assertEqual(result["state"], "marker_reconstructed_from_intent")
        self.assertNotEqual(result["sha256"], old)
        with np.load(target, allow_pickle=False) as z:
            self.assertEqual(z["payload"].tolist(), [1, 0, 1])
        self.assertEqual(atomic.verify_committed_npz(target), result["sha256"])


def estimate_reference(path):
    with np.load(path, allow_pickle=False) as z:
        return float(z["calibration_detectors"].mean())


def decode_reference(p_hat, detectors):
    return np.stack([detectors[:, 0], (detectors[:, 1] ^ (p_hat > 0.5)).astype(np.uint8)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
