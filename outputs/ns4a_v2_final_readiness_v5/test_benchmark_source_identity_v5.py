"""Deterministic source-identity and authorization tests; no Stim sampler calls."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs/ns4a_v2_integrated_runner_v1"))
from qshift_ns4a_v2_runner.benchmark_identity_v5 import (  # noqa: E402
    AUTH_FIELDS,
    AUTH_REL,
    AUTH_SCHEMA,
    AUTH_SCOPE,
    AUTH_STATEMENT,
    PROTOCOL_REL,
    INVENTORY_REL,
    V5_MANIFEST_REL,
    IdentityError,
    check_clean_checkout,
    check_exact_head,
    load_approved_historical_seed_values,
    sha256_file,
    validate_authorization_payload,
    validate_v5_manifest_header,
    verify_execution_identity,
    verify_file_rows,
    verify_source_manifest_v5,
)


def _run(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()


def _git_repo(root: Path) -> str:
    root.mkdir(parents=True, exist_ok=True)
    _run(root, "init", "-q")
    _run(root, "config", "user.name", "Q-SHIFT test")
    _run(root, "config", "user.email", "qshift-test@example.invalid")
    tracked = root / "tracked.txt"
    tracked.write_text("frozen fixture\n", encoding="utf-8")
    _run(root, "add", "tracked.txt")
    _run(root, "commit", "-qm", "fixture")
    return _run(root, "rev-parse", "HEAD")


def _payload(commit: str) -> dict[str, object]:
    now = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
    return {
        "schema": AUTH_SCHEMA,
        "owner_id": "realguy-beep",
        "scope": AUTH_SCOPE,
        "approval_statement": AUTH_STATEMENT,
        "sampling_authorized": True,
        "source_commit": commit,
        "source_manifest_sha256": "1" * 64,
        "protocol_sha256": "2" * 64,
        "seed_inventory_sha256": "3" * 64,
        "created_utc": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "expires_utc": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
    }


class SourceIdentityV5Tests(unittest.TestCase):
    def test_current_v5_manifest_source_integrity(self) -> None:
        record = verify_source_manifest_v5(ROOT, ROOT / Path(*V5_MANIFEST_REL.split("/")))
        self.assertGreaterEqual(record["verified_file_count"], 70)
        self.assertEqual(record["manifest"]["final_commit_sha"], None)

    def test_approved_historical_seed_extract_matches_collision_screen(self) -> None:
        seeds = load_approved_historical_seed_values(ROOT)
        self.assertEqual(len(seeds), 2667)
        inventory = json.loads((ROOT / Path(*INVENTORY_REL.split("/"))).read_text(encoding="utf-8"))
        self.assertFalse(set(inventory["seed_by_condition"].values()) & seeds)

    def test_wrong_git_head_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            head = _git_repo(root)
            with self.assertRaises(IdentityError):
                check_exact_head(root, "0" * 40 if head != "0" * 40 else "f" * 40)

    def test_dirty_tracked_source_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_repo(root)
            (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
            with self.assertRaises(IdentityError):
                check_clean_checkout(root)

    def test_only_exact_untracked_owner_auth_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_repo(root)
            auth = root / Path(*AUTH_REL.split("/"))
            auth.parent.mkdir(parents=True)
            auth.write_text("owner payload fixture", encoding="utf-8")
            check_clean_checkout(root)
            (root / "unexpected.tmp").write_text("unexpected", encoding="utf-8")
            with self.assertRaises(IdentityError):
                check_clean_checkout(root)

    def test_incorrect_manifest_hash_rejected(self) -> None:
        payload = _payload("a" * 40)
        with self.assertRaises(IdentityError):
            validate_authorization_payload(payload, source_commit="a" * 40,
                source_manifest_sha256="f" * 64, protocol_sha256="2" * 64,
                seed_inventory_sha256="3" * 64, now_utc="2026-11-13T12:00:00Z")

    def test_exact_owner_payload_accepts_all_bound_hashes(self) -> None:
        payload = _payload("a" * 40)
        validate_authorization_payload(payload, source_commit="a" * 40,
            source_manifest_sha256="1" * 64, protocol_sha256="2" * 64,
            seed_inventory_sha256="3" * 64, now_utc="2026-11-13T12:00:00Z")

    def test_incorrect_inventory_hash_rejected(self) -> None:
        payload = _payload("a" * 40)
        with self.assertRaises(IdentityError):
            validate_authorization_payload(payload, source_commit="a" * 40,
                source_manifest_sha256="1" * 64, protocol_sha256="2" * 64,
                seed_inventory_sha256="f" * 64, now_utc="2026-11-13T12:00:00Z")

    def test_incorrect_protocol_hash_rejected(self) -> None:
        payload = _payload("a" * 40)
        with self.assertRaises(IdentityError):
            validate_authorization_payload(payload, source_commit="a" * 40,
                source_manifest_sha256="1" * 64, protocol_sha256="f" * 64,
                seed_inventory_sha256="3" * 64, now_utc="2026-11-13T12:00:00Z")

    def test_mismatched_owner_authorization_rejected(self) -> None:
        payload = _payload("a" * 40)
        payload["owner_id"] = "someone-else"
        with self.assertRaises(IdentityError):
            validate_authorization_payload(payload, source_commit="a" * 40,
                source_manifest_sha256="1" * 64, protocol_sha256="2" * 64,
                seed_inventory_sha256="3" * 64, now_utc="2026-11-13T12:00:00Z")

    def test_missing_owner_authorization_rejected(self) -> None:
        with self.assertRaises(IdentityError):
            verify_execution_identity(ROOT, authorization_path=ROOT / Path(*AUTH_REL.split("/")),
                manifest_path=ROOT / Path(*V5_MANIFEST_REL.split("/")),
                protocol_path=ROOT / Path(*PROTOCOL_REL.split("/")),
                inventory_path=ROOT / Path(*INVENTORY_REL.split("/")))

    def test_modified_benchmark_executable_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            executable = root / "benchmark_v5.py"
            executable.write_text("original\n", encoding="utf-8")
            rows = {"benchmark_v5.py": sha256_file(executable)}
            self.assertEqual(len(rows["benchmark_v5.py"]), 64)
            executable.write_text("modified\n", encoding="utf-8")
            with self.assertRaises(IdentityError):
                verify_file_rows(root, rows, {"benchmark_v5.py"})

    def test_invalid_or_superseded_manifest_rejected(self) -> None:
        bad_v4 = {"schema": "qshift-ns4a-v2-source-manifest-v1",
                  "readiness_revision": "NS-4A V2 final-readiness V4"}
        with self.assertRaises(IdentityError):
            validate_v5_manifest_header(bad_v4)
        bad_v5 = {"schema": "qshift-ns4a-v2-source-manifest-v5",
                  "readiness_revision": "NS-4A V2 exact source identity V5",
                  "source_base_commit": "bdc8cf327f747611f1015100dfefe0fb6bc24c47",
                  "manifest_self_reference_excluded": True,
                  "final_commit_sha": "0" * 40}
        with self.assertRaises(IdentityError):
            validate_v5_manifest_header(bad_v5)

    def test_owner_payload_schema_is_exact(self) -> None:
        payload = _payload("a" * 40)
        payload["extra"] = "not allowed"
        self.assertNotEqual(set(payload), AUTH_FIELDS)
        with self.assertRaises(IdentityError):
            validate_authorization_payload(payload, source_commit="a" * 40,
                source_manifest_sha256="1" * 64, protocol_sha256="2" * 64,
                seed_inventory_sha256="3" * 64, now_utc="2026-11-13T12:00:00Z")


if __name__ == "__main__":
    unittest.main(verbosity=2)
