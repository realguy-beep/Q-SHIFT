from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "ns4a_v2_integrated_runner_v1"))

from qshift_ns4a_v2_runner import benchmark_identity_v6 as identity  # noqa: E402


def prior_record() -> dict:
    return {"prior_attempt": {
        "source_commit": identity.SOURCE_BASE_COMMIT,
        "owner_authorization_sha256": identity.V5_AUTH_SHA256,
        "benchmark_id": identity.V5_FAILED_RUN_ID,
        "status": "STOPPED",
        "sampler_calls": 0,
        "shots": 0,
        "failure_message": "Windows process peak-working-set measurement failed.",
        "output_root_relative_path": "outputs/ns4a_v2_final_readiness_v5/benchmark_runs",
        "output_root_children": [identity.V5_FAILED_RUN_ID],
        "output_directory_relative_path": identity.V5_FAILED_RUN_REL,
        "output_files": 0,
        "output_bytes": 0,
    }}


class RecoveryIdentityTests(unittest.TestCase):
    def _temp_v5_attempt(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        auth = root / identity.V5_AUTH_REL
        auth.parent.mkdir(parents=True)
        auth.write_bytes(b"preserved V5 owner token fixture")
        old_run = root / identity.V5_FAILED_RUN_REL
        old_run.mkdir(parents=True)
        return temp, root, old_run

    def test_empty_zero_shot_v5_attempt_is_recognized(self):
        temp, root, _ = self._temp_v5_attempt()
        self.addCleanup(temp.cleanup)
        with patch.object(identity, "sha256_file", return_value=identity.V5_AUTH_SHA256):
            identity.verify_stopped_v5_attempt(root, prior_record())

    def test_nonempty_v5_attempt_is_not_recoverable_as_zero_shot(self):
        temp, root, old_run = self._temp_v5_attempt()
        self.addCleanup(temp.cleanup)
        (old_run / "unexpected.npz").write_bytes(b"fixture")
        with patch.object(identity, "sha256_file", return_value=identity.V5_AUTH_SHA256):
            with self.assertRaisesRegex(identity.IdentityErrorV6, "no longer empty"):
                identity.verify_stopped_v5_attempt(root, prior_record())

    def test_extra_v5_attempt_sibling_is_rejected(self):
        temp, root, old_run = self._temp_v5_attempt()
        self.addCleanup(temp.cleanup)
        (old_run.parent / "unexpected-attempt").mkdir()
        with patch.object(identity, "sha256_file", return_value=identity.V5_AUTH_SHA256):
            with self.assertRaisesRegex(identity.IdentityErrorV6, "unexpected attempts"):
                identity.verify_stopped_v5_attempt(root, prior_record())

    def test_changed_old_authorization_hash_is_rejected(self):
        temp, root, _ = self._temp_v5_attempt()
        self.addCleanup(temp.cleanup)
        with patch.object(identity, "sha256_file", return_value="0" * 64):
            with self.assertRaisesRegex(identity.IdentityErrorV6, "authorization evidence.*changed"):
                identity.verify_stopped_v5_attempt(root, prior_record())

    def test_v5_authorization_schema_cannot_authorize_v6(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        old_v5_payload = {
            "schema": "qshift-ns4a-v2-benchmark-authorization-v5",
            "owner_id": "realguy-beep", "scope": "bounded_benchmark_only",
            "approval_statement": "old V5 approval", "sampling_authorized": True,
            "source_commit": identity.SOURCE_BASE_COMMIT,
            "source_manifest_sha256": identity.V5_MANIFEST_SHA256,
            "protocol_sha256": "0" * 64, "seed_inventory_sha256": "1" * 64,
            "created_utc": now.isoformat().replace("+00:00", "Z"),
            "expires_utc": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        }
        with self.assertRaisesRegex(identity.IdentityErrorV6, "incomplete or contains extra fields"):
            identity.validate_authorization_v6(
                old_v5_payload, source_commit=identity.SOURCE_BASE_COMMIT,
                manifest_sha256="2" * 64, protocol_sha256="0" * 64,
                inventory_sha256="1" * 64, recovery_record_sha256="3" * 64,
            )

    def test_v6_payload_binds_recovery_record_hash_and_head(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        payload = {
            "schema": identity.AUTH_SCHEMA_V6,
            "owner_id": "realguy-beep", "scope": identity.AUTH_SCOPE_V6,
            "approval_statement": identity.AUTH_STATEMENT_V6, "sampling_authorized": True,
            "source_commit": "a" * 40, "source_manifest_sha256": "b" * 64,
            "protocol_sha256": "c" * 64, "seed_inventory_sha256": "d" * 64,
            "recovery_record_sha256": "e" * 64,
            "created_utc": now.isoformat().replace("+00:00", "Z"),
            "expires_utc": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        }
        identity.validate_authorization_v6(
            payload, source_commit="a" * 40, manifest_sha256="b" * 64,
            protocol_sha256="c" * 64, inventory_sha256="d" * 64,
            recovery_record_sha256="e" * 64,
        )
        with self.assertRaisesRegex(identity.IdentityErrorV6, "recovery_record_sha256"):
            identity.validate_authorization_v6(
                payload, source_commit="a" * 40, manifest_sha256="b" * 64,
                protocol_sha256="c" * 64, inventory_sha256="d" * 64,
                recovery_record_sha256="f" * 64,
            )

    def test_v6_payload_rejects_wrong_final_head(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        payload = {
            "schema": identity.AUTH_SCHEMA_V6,
            "owner_id": "realguy-beep", "scope": identity.AUTH_SCOPE_V6,
            "approval_statement": identity.AUTH_STATEMENT_V6, "sampling_authorized": True,
            "source_commit": "a" * 40, "source_manifest_sha256": "b" * 64,
            "protocol_sha256": "c" * 64, "seed_inventory_sha256": "d" * 64,
            "recovery_record_sha256": "e" * 64,
            "created_utc": now.isoformat().replace("+00:00", "Z"),
            "expires_utc": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        }
        with self.assertRaisesRegex(identity.IdentityErrorV6, "source_commit"):
            identity.validate_authorization_v6(
                payload, source_commit="f" * 40, manifest_sha256="b" * 64,
                protocol_sha256="c" * 64, inventory_sha256="d" * 64,
                recovery_record_sha256="e" * 64,
            )

    def test_new_run_root_is_distinct_from_preserved_v5_directory(self):
        self.assertNotEqual(identity.V6_RUN_ROOT_REL, str(Path(identity.V5_FAILED_RUN_REL).parent).replace("\\", "/"))
        self.assertNotIn("v5", identity.V6_RUN_ROOT_REL)


if __name__ == "__main__":
    unittest.main()
