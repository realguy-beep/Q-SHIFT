"""V6 source and stopped-attempt binding for NS-4A benchmark recovery.

The old V5 authorization is only hash-checked as incident evidence. It is not
parsed as authorization and cannot authorize V6 execution.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .benchmark_identity_v5 import (
    IdentityError,
    _inside,
    check_exact_head,
    git_head,
    load_approved_historical_seed_values,
    sha256_file,
)

SOURCE_BASE_COMMIT = "32c8c88b18f09f06fd4779e6f0a9a849d81cc279"
V5_MANIFEST_REL = "outputs/ns4a_v2_final_readiness_v5/SOURCE_HASH_MANIFEST_V5.json"
V5_MANIFEST_SHA256 = "c3debd93346f6b04c3acc0d514f52e3b973f76c9f1b3dfb7867285d9df31403d"
V5_AUTH_REL = "outputs/ns4a_v2_final_readiness_v5/BENCHMARK_OWNER_APPROVAL_V5.json"
V5_AUTH_SHA256 = "328a384298f4a2f4ca13b81ff683a9ec49dedf8d3edbcd9f11cf826c06eb0947"
V5_FAILED_RUN_REL = "outputs/ns4a_v2_final_readiness_v5/benchmark_runs/3eb8d077109e8d2a"
V5_FAILED_RUN_ID = "3eb8d077109e8d2a"
V6_MANIFEST_REL = "outputs/ns4a_v2_final_readiness_v6/SOURCE_HASH_MANIFEST_V6.json"
V6_RECOVERY_RECORD_REL = "outputs/ns4a_v2_final_readiness_v6/STOPPED_ATTEMPT_RECORD_V6.json"
V6_PROTOCOL_REL = "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_PROTOCOL.json"
V6_INVENTORY_REL = "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_INVENTORY_V1.json"
V6_AUTH_REL = "outputs/ns4a_v2_final_readiness_v6/BENCHMARK_OWNER_APPROVAL_V6.json"
V6_RUN_ROOT_REL = "outputs/ns4a_v2_final_readiness_v6/benchmark_runs"
V6_LOCK_REL = "outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt"
V6_COLLISION_REL = "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_COLLISION_SCREEN_V1_FINAL.json"
V6_SOURCE_DIR = "outputs/ns4a_v2_final_readiness_v6"
AUTH_SCHEMA_V6 = "qshift-ns4a-v2-benchmark-recovery-authorization-v6"
AUTH_SCOPE_V6 = "bounded_benchmark_recovery_only"
AUTH_STATEMENT_V6 = (
    "I, realguy-beep, explicitly authorize one bounded NS-4A V2 execution-readiness "
    "benchmark recovery attempt for the exact V6 source commit and hashes named in this payload."
)
AUTH_FIELDS_V6 = frozenset({
    "schema", "owner_id", "scope", "approval_statement", "sampling_authorized",
    "source_commit", "source_manifest_sha256", "protocol_sha256",
    "seed_inventory_sha256", "recovery_record_sha256", "created_utc", "expires_utc",
})
BENCHMARK_NAMESPACE = "qshift-ns4a-v2-execution-readiness-benchmark-v1"
CONDITIONS = (
    "balanced_no_burst", "x_biased_no_burst", "z_biased_no_burst",
    "balanced_burst_0.005", "balanced_burst_0.010", "balanced_burst_0.015",
)


class IdentityErrorV6(RuntimeError):
    """V6 identity or stopped-attempt recovery validation failed."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relpath(root: Path, rel: str) -> Path:
    p = PurePosixPath(rel)
    if p.is_absolute() or ".." in p.parts or "\\" in rel:
        raise IdentityErrorV6(f"unsafe manifest path: {rel!r}")
    target = (root / Path(*p.parts)).resolve()
    if root.resolve() not in target.parents:
        raise IdentityErrorV6(f"manifest path escapes repository: {rel!r}")
    return target


def _canonical_source_tree(rows: Mapping[str, str]) -> str:
    payload = json.dumps(sorted(rows.items()), separators=(",", ":"), ensure_ascii=False).encode()
    return _sha(payload)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise IdentityErrorV6(f"{label} is missing or invalid JSON.") from exc
    if not isinstance(value, dict):
        raise IdentityErrorV6(f"{label} must be a JSON object.")
    return value


def _manifest_rows(document: Mapping[str, Any]) -> dict[str, str]:
    files = document.get("files")
    if not isinstance(files, list):
        raise IdentityErrorV6("V6 manifest file list is invalid.")
    rows: dict[str, str] = {}
    for row in files:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise IdentityErrorV6("V6 manifest row has an unsupported shape.")
        path, digest = row["path"], row["sha256"]
        if (not isinstance(path, str) or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest) or path in rows):
            raise IdentityErrorV6("V6 manifest contains an invalid or duplicate row.")
        rows[path] = digest
    return rows


def verify_source_manifest_v6(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    manifest_path = _relpath(root, V6_MANIFEST_REL)
    manifest = _load_json(manifest_path, "V6 source manifest")
    if manifest.get("schema") != "qshift-ns4a-v2-source-manifest-v6":
        raise IdentityErrorV6("source manifest schema is not V6.")
    if manifest.get("source_base_commit") != SOURCE_BASE_COMMIT:
        raise IdentityErrorV6("V6 source base commit differs from the approved V5 commit.")
    if manifest.get("parent_v5_manifest_sha256") != V5_MANIFEST_SHA256:
        raise IdentityErrorV6("V6 does not bind the accepted V5 manifest.")
    if manifest.get("commit_binding") != "V6 owner authorization source_commit equals exact current Git HEAD":
        raise IdentityErrorV6("V6 non-circular commit binding declaration is missing.")
    if manifest.get("commit_sha_embedded") is not False:
        raise IdentityErrorV6("V6 manifest must not embed its own final commit SHA.")

    v5_path = _relpath(root, V5_MANIFEST_REL)
    if sha256_file(v5_path) != V5_MANIFEST_SHA256:
        raise IdentityErrorV6("accepted V5 manifest hash changed.")
    v5 = _load_json(v5_path, "accepted V5 source manifest")
    parent_rows = _manifest_rows(v5)
    rows = _manifest_rows(manifest)
    expected_paths = set(parent_rows) | {V5_MANIFEST_REL}
    expected_paths.update(manifest.get("v6_files", []))
    if set(rows) != expected_paths:
        raise IdentityErrorV6("V6 manifest file inventory is incomplete or unexpected.")
    if manifest.get("file_count") != len(rows):
        raise IdentityErrorV6("V6 manifest file count is inconsistent.")
    if manifest.get("source_tree_sha256") != _canonical_source_tree(rows):
        raise IdentityErrorV6("V6 source-tree digest mismatch.")
    for rel, expected in rows.items():
        try:
            actual = sha256_file(_relpath(root, rel))
        except OSError as exc:
            raise IdentityErrorV6(f"manifest source file is unavailable: {rel}") from exc
        if actual != expected:
            raise IdentityErrorV6(f"manifest source hash mismatch: {rel}")
    record = _load_json(_relpath(root, V6_RECOVERY_RECORD_REL), "V6 recovery record")
    if manifest.get("recovery_record_sha256") != rows.get(V6_RECOVERY_RECORD_REL):
        raise IdentityErrorV6("V6 manifest does not bind the stopped-attempt record.")
    if record.get("schema") != "qshift-ns4a-v2-stopped-attempt-record-v6":
        raise IdentityErrorV6("stopped-attempt record schema is invalid.")
    return {
        "manifest_sha256": sha256_file(manifest_path),
        "source_tree_sha256": manifest["source_tree_sha256"],
        "rows": rows,
        "recovery_record_sha256": rows[V6_RECOVERY_RECORD_REL],
    }


def check_clean_checkout_v6(repository_root: str | Path) -> None:
    """Allow only the preserved V5 token and the new V6 owner token untracked."""
    root = Path(repository_root).resolve()
    allowed = {V5_AUTH_REL, V6_AUTH_REL}
    for rel in allowed:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel], cwd=root,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if tracked.returncode == 0:
            raise IdentityErrorV6(f"authorization file must remain untracked: {rel}")
    try:
        raw = subprocess.check_output(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root,
        ).decode("utf-8", errors="strict")
    except Exception as exc:
        raise IdentityErrorV6("cannot verify V6 worktree state.") from exc
    unexpected = []
    for entry in (item for item in raw.split("\0") if item):
        code, path = entry[:2], entry[3:].replace("\\", "/")
        if code == "??" and path in allowed:
            continue
        unexpected.append(entry)
    if unexpected:
        raise IdentityErrorV6("worktree contains unapproved tracked or untracked changes.")
    for args in (("diff", "--quiet", "HEAD", "--"), ("diff", "--cached", "--quiet", "HEAD", "--")):
        result = subprocess.run(["git", *args], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            raise IdentityErrorV6("tracked source or index is dirty.")


def _utc_seconds(value: Any, field: str) -> float:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise IdentityErrorV6(f"{field} must be an RFC3339 UTC timestamp ending in Z.")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc).timestamp()
    except ValueError as exc:
        raise IdentityErrorV6(f"{field} is malformed.") from exc


def validate_authorization_v6(
    auth: Mapping[str, Any], *, source_commit: str, manifest_sha256: str,
    protocol_sha256: str, inventory_sha256: str, recovery_record_sha256: str,
) -> None:
    if set(auth) != AUTH_FIELDS_V6:
        raise IdentityErrorV6("V6 authorization schema is incomplete or contains extra fields.")
    expected = {
        "schema": AUTH_SCHEMA_V6,
        "owner_id": "realguy-beep",
        "scope": AUTH_SCOPE_V6,
        "approval_statement": AUTH_STATEMENT_V6,
        "sampling_authorized": True,
        "source_commit": source_commit,
        "source_manifest_sha256": manifest_sha256,
        "protocol_sha256": protocol_sha256,
        "seed_inventory_sha256": inventory_sha256,
        "recovery_record_sha256": recovery_record_sha256,
    }
    for key, value in expected.items():
        if auth.get(key) != value:
            raise IdentityErrorV6(f"V6 authorization {key} is not bound to the reviewed recovery identity.")
    created, expires = _utc_seconds(auth.get("created_utc"), "created_utc"), _utc_seconds(auth.get("expires_utc"), "expires_utc")
    now = datetime.now(timezone.utc).timestamp()
    if not created <= now <= expires or expires - created > 86_400:
        raise IdentityErrorV6("V6 owner authorization is expired, not yet valid, or exceeds 24 hours.")


def verify_stopped_v5_attempt(repository_root: str | Path, record: Mapping[str, Any]) -> None:
    root = Path(repository_root).resolve()
    prior = record.get("prior_attempt")
    if not isinstance(prior, dict):
        raise IdentityErrorV6("V6 recovery record lacks prior-attempt provenance.")
    expected = {
        "source_commit": SOURCE_BASE_COMMIT,
        "owner_authorization_sha256": V5_AUTH_SHA256,
        "benchmark_id": V5_FAILED_RUN_ID,
        "status": "STOPPED",
        "sampler_calls": 0,
        "shots": 0,
        "failure_message": "Windows process peak-working-set measurement failed.",
        "output_root_relative_path": "outputs/ns4a_v2_final_readiness_v5/benchmark_runs",
        "output_root_children": [V5_FAILED_RUN_ID],
        "output_directory_relative_path": V5_FAILED_RUN_REL,
        "output_files": 0,
        "output_bytes": 0,
    }
    for key, value in expected.items():
        if prior.get(key) != value:
            raise IdentityErrorV6(f"preserved V5 stopped-attempt record differs at {key}.")
    old_auth = _relpath(root, V5_AUTH_REL)
    if not old_auth.is_file() or sha256_file(old_auth) != V5_AUTH_SHA256:
        raise IdentityErrorV6("preserved V5 authorization evidence is missing or changed.")
    old_run = _relpath(root, V5_FAILED_RUN_REL)
    old_parent = old_run.parent
    if old_run.is_symlink() or not old_run.is_dir():
        raise IdentityErrorV6("preserved V5 failed-attempt directory is missing or unsafe.")
    entries = list(old_run.iterdir())
    if entries:
        raise IdentityErrorV6("V5 stopped-attempt directory is no longer empty; refusing recovery.")
    siblings = sorted(p.name for p in old_parent.iterdir())
    if siblings != [V5_FAILED_RUN_ID]:
        raise IdentityErrorV6("V5 failed-attempt root contains unexpected attempts or artifacts.")


def verify_execution_identity_v6(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    auth_path = _relpath(root, V6_AUTH_REL)
    manifest_record = verify_source_manifest_v6(root)
    record = _load_json(_relpath(root, V6_RECOVERY_RECORD_REL), "V6 recovery record")
    verify_stopped_v5_attempt(root, record)
    if not auth_path.is_file():
        raise IdentityErrorV6("new V6 owner authorization is missing.")
    auth = _load_json(auth_path, "V6 owner authorization")
    protocol_path, inventory_path = _relpath(root, V6_PROTOCOL_REL), _relpath(root, V6_INVENTORY_REL)
    protocol, inventory = _load_json(protocol_path, "benchmark protocol"), _load_json(inventory_path, "benchmark seed inventory")
    current_head = git_head(root)
    check_exact_head(root, str(auth.get("source_commit", "")))
    check_clean_checkout_v6(root)
    protocol_sha, inventory_sha = sha256_file(protocol_path), sha256_file(inventory_path)
    validate_authorization_v6(
        auth, source_commit=current_head,
        manifest_sha256=manifest_record["manifest_sha256"],
        protocol_sha256=protocol_sha, inventory_sha256=inventory_sha,
        recovery_record_sha256=manifest_record["recovery_record_sha256"],
    )
    if protocol.get("schema") != "qshift-ns4a-v2-benchmark-protocol-v1":
        raise IdentityErrorV6("V6 must use the unchanged approved V1 benchmark protocol.")
    seeds = inventory.get("seed_by_condition")
    if (inventory.get("schema") != "qshift-ns4a-v2-benchmark-seed-inventory-v1"
            or inventory.get("namespace") != BENCHMARK_NAMESPACE
            or inventory.get("scientific_seed_allocation") is not False
            or inventory.get("numeric_seeds_allocated") is not True
            or inventory.get("sampling_authorized") is not False
            or not isinstance(seeds, dict) or set(seeds) != set(CONDITIONS)
            or any(type(value) is not int or not 0 <= value <= 2**63 - 1 for value in seeds.values())
            or len(set(seeds.values())) != 6):
        raise IdentityErrorV6("V6 requires the unchanged six-seed benchmark inventory.")
    run_root = _relpath(root, V6_RUN_ROOT_REL)
    if run_root.exists():
        raise IdentityErrorV6("V6 output root already exists; refusing retry or implicit resume.")
    binding = "|".join((current_head, manifest_record["manifest_sha256"], protocol_sha, inventory_sha,
                        manifest_record["recovery_record_sha256"], "V6"))
    benchmark_id = hashlib.sha256(binding.encode()).hexdigest()[:16]
    return {
        "source_commit": current_head,
        "source_manifest_sha256": manifest_record["manifest_sha256"],
        "source_tree_sha256": manifest_record["source_tree_sha256"],
        "protocol_sha256": protocol_sha,
        "seed_inventory_sha256": inventory_sha,
        "recovery_record_sha256": manifest_record["recovery_record_sha256"],
        "authorization_sha256": sha256_file(auth_path),
        "benchmark_id": benchmark_id,
    }
