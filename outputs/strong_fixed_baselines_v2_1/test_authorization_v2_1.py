"""No-sampling tests for V2.1 authorization and provenance.

Any OWNER_AUTHORIZED-shaped approval below is written only to a temporary
directory named SYNTHETIC_TEST_FIXTURE_ONLY and is never a project approval.
The runner's sampler is always mocked; Stim sampling is not invoked.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from outputs.strong_fixed_baselines_v2 import freeze_pretest_v2 as v2_freeze
from outputs.strong_fixed_baselines_v2_1 import authorization_v2_1 as auth
from outputs.strong_fixed_baselines_v2_1 import audit_saved_arrays_v2_1 as auditor
from outputs.strong_fixed_baselines_v2_1 import candidate_freeze_v2_1 as candidate_freeze
from outputs.strong_fixed_baselines_v2_1 import run_development_v2_1 as launcher

sys.path.insert(0, str(auth.ROOT / "outputs" / "strong_fixed_baselines_v1"))
import freeze_pretest as v1_freeze  # noqa: E402 - frozen V1 verifier uses its historical flat import.


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_record(expected: dict[str, str], inventory_sha: str) -> dict:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    record = {
        "schema_version": 1,
        "approval_status": "OWNER_AUTHORIZED",
        "approved_by": "realguy-beep",
        "approved_at_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_at_utc": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "approval_statement": (
            "I explicitly authorize the frozen Q-SHIFT V2 development experiment "
            "identified by the exact commit, freeze, configuration, seed inventory, and runner hashes in this record."
        ),
        "experiment_id": auth.EXPERIMENT_ID,
        "approved_commit_sha": expected["commit_sha"],
        "candidate_freeze_sha256": expected["candidate_freeze_sha256"],
        "original_freeze_sha256": expected["original_freeze_sha256"],
        "configuration_sha256": expected["configuration_sha256"],
        "seed_inventory_sha256": inventory_sha,
        "frozen_runner_sha256": expected["frozen_runner_sha256"],
        "authorized_launcher_sha256": expected["authorized_launcher_sha256"],
        "authorization_validator_sha256": expected["authorization_validator_sha256"],
        "candidate_freeze_verifier_sha256": expected["candidate_freeze_verifier_sha256"],
        "runtime_environment_sha256": expected["runtime_environment_sha256"],
    }
    return record


def json_write(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class AuthorizationV21Tests(unittest.TestCase):
    def test_no_real_owner_approval_record_is_present(self):
        self.assertFalse(auth.APPROVAL_PATH.exists())

    def expected_identity(self) -> dict[str, str]:
        return auth.expected_pre_inventory_identity()

    def test_missing_or_malformed_approval_fails_before_inventory(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            approval = Path(folder) / "approval.json"
            with patch.object(auth, "validate_inventory_binding", side_effect=AssertionError("inventory read")):
                with self.assertRaisesRegex(PermissionError, "missing"):
                    auth.authorize_launch(approval)
                approval.write_text("{invalid", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "malformed JSON"):
                    auth.authorize_launch(approval)

    def test_unauthorized_and_resume_launch_fail_before_inventory_or_sampler(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            approval = Path(folder) / "missing.json"
            sampler = Mock()
            with patch.object(auth, "validate_inventory_binding", side_effect=AssertionError("inventory read")), \
                 patch.object(launcher.frozen_runner, "sample_arrays", sampler), \
                 patch.dict(os.environ, {"QSHIFT_SKIP_AUTH": "1", "QSHIFT_AUTHORIZED": "1"}, clear=False):
                with self.assertRaisesRegex(PermissionError, "missing"):
                    launcher.launch(["--resume"], approval_path=approval, dispatch=lambda _path: sampler())
            sampler.assert_not_called()

    def test_unknown_cli_authorization_switch_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            with self.assertRaises(SystemExit):
                launcher.launch(["--authorize"], approval_path=Path(folder) / "missing.json")

    def test_resume_with_missing_identity_fails_before_dispatch(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            run_dir = Path(folder) / "run"
            run_dir.mkdir()
            dispatch = Mock()
            with patch.object(launcher, "RUN_DIR", run_dir), \
                 patch.object(auth, "authorize_launch", return_value=({}, {})):
                with self.assertRaisesRegex(RuntimeError, "lacks an execution identity"):
                    launcher.launch(["--resume"], run_dir=run_dir, dispatch=dispatch)
            dispatch.assert_not_called()

    def test_completed_run_cannot_be_relaunched(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            run_dir = Path(folder) / "run"
            run_dir.mkdir()
            (run_dir / "status.json").write_text('{"status":"completed"}', encoding="utf-8")
            dispatch = Mock()
            with patch.object(launcher, "RUN_DIR", run_dir), \
                 patch.object(auth, "authorize_launch", return_value=({}, {})):
                with self.assertRaisesRegex(RuntimeError, "already complete"):
                    launcher.launch(["--resume"], run_dir=run_dir, dispatch=dispatch)
            dispatch.assert_not_called()

    def test_provenance_is_create_only_and_resume_rejects_mismatch(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            run_dir = Path(folder) / "run"
            approval = Path(folder) / "SYNTHETIC_TEST_APPROVAL_FIXTURE.json"
            json_write(approval, {"fixture": "approval receipt"})
            identity = {"identity": "frozen fixture", "approval_record_sha256": sha(approval)}
            launcher.create_or_verify_run_provenance(run_dir, identity, approval)
            before = (run_dir / launcher.IDENTITY_NAME).read_bytes()
            self.assertEqual((run_dir / launcher.APPROVAL_RECEIPT_NAME).read_bytes(), approval.read_bytes())
            self.assertEqual((run_dir / launcher.IDENTITY_NAME).read_bytes(), before)
            with self.assertRaisesRegex(RuntimeError, "identity differs"):
                launcher.create_or_verify_run_provenance(
                    run_dir, {"identity": "tampered", "approval_record_sha256": sha(approval)}, approval
                )

    def test_pre_inventory_source_configuration_commit_and_freeze_mismatches_rejected(self):
        expected = {
            "commit_sha": "1" * 40,
            "candidate_freeze_sha256": "a" * 64,
            "original_freeze_sha256": "b" * 64,
            "configuration_sha256": "c" * 64,
            "frozen_runner_sha256": "d" * 64,
            "authorized_launcher_sha256": "e" * 64,
            "authorization_validator_sha256": "f" * 64,
            "candidate_freeze_verifier_sha256": "0" * 64,
            "runtime_environment_sha256": "7" * 64,
        }
        record = synthetic_record(expected, "9" * 64)
        for field in (
            "approved_commit_sha", "candidate_freeze_sha256", "original_freeze_sha256",
            "configuration_sha256", "frozen_runner_sha256", "authorized_launcher_sha256",
            "authorization_validator_sha256", "candidate_freeze_verifier_sha256",
            "runtime_environment_sha256",
        ):
            with self.subTest(field=field):
                altered = dict(record)
                altered[field] = "8" * (40 if field == "approved_commit_sha" else 64)
                with self.assertRaisesRegex(PermissionError, "stale or bound"):
                    auth.validate_pre_inventory_bindings(altered, expected)

    def test_changed_source_hash_fails_frozen_source_check(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            root = Path(folder)
            source = root / "runner.py"
            source.write_text("original source", encoding="utf-8")
            recorded = {"runner.py": sha(source)}
            candidate_freeze.verify_hash_map(root, recorded, {"runner.py"})
            source.write_text("modified source", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "missing or changed"):
                candidate_freeze.verify_hash_map(root, recorded, {"runner.py"})

    def test_modified_configuration_bytes_invalidate_approval_binding(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            config_path = Path(folder) / "config.json"
            config_path.write_text('{"noise":0.003}', encoding="utf-8")
            old_hash = sha(config_path)
            expected = {
                "commit_sha": "1" * 40,
                "candidate_freeze_sha256": "a" * 64,
                "original_freeze_sha256": "b" * 64,
                "configuration_sha256": old_hash,
                "frozen_runner_sha256": "d" * 64,
                "authorized_launcher_sha256": "e" * 64,
                "authorization_validator_sha256": "f" * 64,
                "candidate_freeze_verifier_sha256": "0" * 64,
                "runtime_environment_sha256": "7" * 64,
            }
            approval = synthetic_record(expected, "9" * 64)
            config_path.write_text('{"noise":0.004}', encoding="utf-8")
            expected["configuration_sha256"] = sha(config_path)
            with self.assertRaisesRegex(PermissionError, "configuration_sha256"):
                auth.validate_pre_inventory_bindings(approval, expected)

    def test_changed_inventory_rejected_after_explicit_approval_preamble(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            inventory = Path(folder) / "inventory.json"
            inventory.write_text('{"seed":1}', encoding="utf-8")
            record = {"seed_inventory_sha256": sha(inventory)}
            self.assertEqual(auth.validate_inventory_binding(record, inventory), sha(inventory))
            inventory.write_text('{"seed":2}', encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "inventory hash"):
                auth.validate_inventory_binding(record, inventory)

    def test_expired_and_malformed_owner_approvals_rejected(self):
        expected = {
            "commit_sha": "1" * 40, "candidate_freeze_sha256": "a" * 64,
            "original_freeze_sha256": "b" * 64, "configuration_sha256": "c" * 64,
            "frozen_runner_sha256": "d" * 64, "authorized_launcher_sha256": "e" * 64,
            "authorization_validator_sha256": "f" * 64,
            "candidate_freeze_verifier_sha256": "0" * 64,
            "runtime_environment_sha256": "7" * 64,
        }
        record = synthetic_record(expected, "9" * 64)
        expired_at = datetime.now(timezone.utc) - timedelta(hours=2)
        record["approved_at_utc"] = (expired_at - timedelta(hours=1)).isoformat()
        record["expires_at_utc"] = expired_at.isoformat()
        with self.assertRaisesRegex(PermissionError, "expired"):
            auth.validate_approval_preamble(record)
        record = synthetic_record(expected, "9" * 64)
        record["approval_status"] = "NOT_AUTHORIZED"
        with self.assertRaisesRegex(PermissionError, "not explicitly owner-authorized"):
            auth.validate_approval_preamble(record)

    def test_valid_synthetic_approval_reaches_mocked_sampler_only(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-") as folder:
            temp = Path(folder)
            approval = temp / "SYNTHETIC_TEST_APPROVAL_FIXTURE.json"
            run_dir = temp / "run"
            with patch.object(auth, "current_git_identity", return_value=("a" * 40, True)):
                expected = self.expected_identity()
            inventory_sha = sha(auth.INVENTORY_PATH)
            record = synthetic_record(expected, inventory_sha)
            json_write(approval, record)
            sampler = Mock(return_value=None)

            def mock_dispatch(_run_dir):
                sampler("mocked-only", 3)

            def mock_core_main():
                in_memory = launcher.frozen_runner.read_json(launcher.frozen_runner.CONFIG_PATH)
                self.assertIs(in_memory["execution"]["sampling_authorized"], True)
                self.assertIs(json.loads(auth.CONFIG_PATH.read_text(encoding="utf-8"))["execution"]["sampling_authorized"], False)
                self.assertFalse(v2_freeze.verify_freeze()["sampling_authorized"])
                launcher.frozen_runner.sample_arrays("mocked-only", 3, 2, {}, labels=False)

            with patch.object(auth, "current_git_identity", return_value=("a" * 40, True)), \
                 patch.object(launcher, "RUN_DIR", run_dir), \
                 patch.object(launcher.frozen_runner, "sample_arrays", sampler), \
                 patch.object(launcher.frozen_runner, "main", side_effect=mock_core_main):
                launcher.launch([], approval_path=approval, run_dir=run_dir)

            sampler.assert_called_once_with("mocked-only", 3)
            self.assertTrue((run_dir / launcher.IDENTITY_NAME).is_file())
            self.assertTrue((run_dir / launcher.APPROVAL_RECEIPT_NAME).is_file())
            self.assertFalse(any(run_dir.rglob("*.npz")))

    def test_historical_v1_and_stage5_metadata_hashes_still_verify(self):
        old_freeze = v2_freeze.verify_freeze()
        self.assertFalse(old_freeze["sampling_authorized"])
        v14 = json.loads((v1_freeze.HERE / "PRETEST_FREEZE_V14.json").read_text(encoding="utf-8"))
        v1_runner = v1_freeze.HERE / "run_development.py"
        expected_v1 = v14["sha256"]["outputs/strong_fixed_baselines_v1/run_development.py"]
        self.assertEqual(sha(v1_runner), expected_v1)
        stage5_rel = "outputs/stage5_secondary_inference_repair_v1/STAGE5_SAMPLE_SEED_INVENTORY.json"
        self.assertEqual(sha(auth.ROOT / stage5_rel), old_freeze["sha256"][stage5_rel])

    def test_auditor_requires_and_recognizes_approved_identity_without_bypassing_v2_freeze(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC_TEST_FIXTURE_ONLY-", dir=auth.ROOT / "outputs/strong_fixed_baselines_v2") as folder:
            fixture_dir = Path(folder)
            run_dir = fixture_dir / "run"
            run_dir.mkdir()
            with patch.object(auth, "current_git_identity", return_value=("a" * 40, True)):
                expected = auth.expected_pre_inventory_identity()
            record = synthetic_record(expected, sha(auth.INVENTORY_PATH))
            receipt = run_dir / launcher.APPROVAL_RECEIPT_NAME
            json_write(receipt, record)
            identity_seed = {**expected, "seed_inventory_sha256": record["seed_inventory_sha256"]}
            identity_seed["approval_record_sha256"] = sha(receipt)
            identity_seed["approved_by"] = record["approved_by"]
            identity_seed["approved_at_utc"] = record["approved_at_utc"]
            identity_record = launcher.build_execution_identity(identity_seed, record, sha(receipt))
            launcher.create_exclusive_json(run_dir / launcher.IDENTITY_NAME, identity_record)

            def mocked_saved_array_audit(_run_dir, _output):
                # This fixture proves that the adapter reaches the independent
                # V2 auditor only after identity and original freeze checks.
                v2_freeze.verify_freeze()
                return {"audit_status": "FIXTURE_ONLY"}

            with patch.object(auth, "current_git_identity", return_value=("a" * 40, True)), \
                 patch.object(auditor.base_audit, "audit_run", side_effect=mocked_saved_array_audit):
                result = auditor.audit_run(run_dir, fixture_dir / "fixture-audit.json")
            self.assertEqual(result["audit_status"], "FIXTURE_ONLY")
            self.assertEqual(result["approved_execution_identity"]["approved_by"], "realguy-beep")
            self.assertEqual(result["approved_execution_identity"]["approved_commit_sha"], "a" * 40)


if __name__ == "__main__":
    unittest.main(verbosity=2)
