"""Hash, dependency, and owner-authorization checks for a future production run."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from qshift_ns4a_v2_deterministic.seed_plan import validate_seed_inventory
from qshift_core_v1.research_adapters.beliefmatching_adapter_ns3b import (
    UPSTREAM_CORE_SOURCE_SHA256_LF,
)


OWNER_ID = "realguy-beep"
EXPERIMENT_ID = "qshift-ns4a-v2"
EXECUTION_RUN_DIRECTORY = "outputs/ns4a_v2_integrated_runner_v1/production_run"
AUTHORIZATION_STATEMENT = (
    "I, realguy-beep, explicitly authorize execution of the frozen Q-SHIFT NS-4A V2 "
    "304,000-shot development experiment bound to the exact immutable execution manifest."
)


class IntegrityError(RuntimeError):
    """A protocol/source/environment/authorization binding failed closed."""


def execution_output_path(repository_root: str | Path, relative: str) -> Path:
    """Return only the dedicated V2 run path, never a caller-selected output."""
    if relative != EXECUTION_RUN_DIRECTORY:
        raise IntegrityError("Execution output must use the dedicated NS-4A V2 path; arbitrary paths are prohibited.")
    root = Path(repository_root).resolve()
    path = (root / relative).resolve()
    if root not in path.parents:
        raise IntegrityError("Execution output escapes the repository root.")
    return path


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def runtime_fingerprint(lock_path: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[3]
    lock = Path(lock_path) if lock_path is not None else repo_root / "outputs" / "ns4a_v2_lockmatched_env_recovery_v1" / "requirements-ns3b.lock.txt"
    if not lock.is_file():
        raise IntegrityError("Pinned NS-3B dependency lock is missing.")
    distributions: dict[str, str] = {}
    editable_rows: list[tuple[str, str]] = []
    for raw_line in lock.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-e "):
            editable_rows.append((line, line.split("#egg=", 1)[1] if "#egg=" in line else ""))
            continue
        if "==" not in line:
            raise IntegrityError(f"Unsupported or unpinned dependency-lock entry: {line!r}.")
        name, expected_version = line.split("==", 1)
        try:
            actual_version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise IntegrityError(f"Required locked distribution {name!r} is absent.") from exc
        if actual_version != expected_version:
            raise IntegrityError(f"Locked dependency {name} requires {expected_version}, found {actual_version}.")
        distributions[name.lower().replace("_", "-")] = actual_version
    if len(editable_rows) != 1 or editable_rows[0][1] != "beliefmatching":
        raise IntegrityError("Lock must contain exactly the pinned editable BeliefMatching dependency.")
    editable_line = editable_rows[0][0]
    expected_commit = "4458c278bbec273c8c1a26411dadccc49222f8ef"
    if f"@{expected_commit}" not in editable_line:
        raise IntegrityError("BeliefMatching lock entry does not pin the approved upstream commit.")
    try:
        direct_url = json.loads(importlib.metadata.distribution("beliefmatching").read_text("direct_url.json"))
        editable = direct_url["dir_info"].get("editable") is True
        if "vcs_info" in direct_url:
            actual_commit = direct_url["vcs_info"]["commit_id"]
            provenance_kind = "editable-vcs-install"
        else:
            parsed = urlparse(direct_url["url"])
            if parsed.scheme != "file" or not editable:
                raise ValueError("editable install has neither VCS nor local-checkout provenance")
            checkout_text = url2pathname(unquote(parsed.path))
            checkout = Path(checkout_text)
            if not checkout.is_dir():
                raise ValueError("editable checkout directory is absent")
            head = subprocess.run(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=False,
            )
            origin = subprocess.run(
                ["git", "-C", str(checkout), "remote", "get-url", "origin"],
                capture_output=True, text=True, check=False,
            )
            dirty = subprocess.run(
                ["git", "-C", str(checkout), "status", "--porcelain"],
                capture_output=True, text=True, check=False,
            )
            if (head.returncode or origin.returncode or dirty.returncode or dirty.stdout.strip()
                    or origin.stdout.strip().rstrip("/") != "https://github.com/oscarhiggott/BeliefMatching.git"):
                raise ValueError("local editable checkout has unexpected origin, dirty files, or invalid Git state")
            actual_commit = head.stdout.strip()
            core_source = checkout / "src" / "beliefmatching" / "belief_matching.py"
            if not core_source.is_file():
                raise ValueError("pinned upstream core implementation file is absent")
            core_source_sha = hashlib.sha256(core_source.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            provenance_kind = "editable-clean-local-checkout"
        if "vcs_info" in direct_url:
            distribution = importlib.metadata.distribution("beliefmatching")
            source_root = Path(distribution.locate_file("beliefmatching")).resolve()
            core_source = source_root / "belief_matching.py"
            if not core_source.is_file():
                raise ValueError("pinned upstream core implementation file is absent")
            core_source_sha = hashlib.sha256(core_source.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    except Exception as exc:
        raise IntegrityError("Installed BeliefMatching editable provenance is unavailable or unverifiable.") from exc
    if actual_commit != expected_commit or not editable:
        raise IntegrityError("Installed BeliefMatching provenance differs from the pinned upstream source.")
    if core_source_sha != UPSTREAM_CORE_SOURCE_SHA256_LF:
        raise IntegrityError("Installed BeliefMatching core implementation digest differs from the reviewed adapter provenance.")
    python = platform.python_version()
    if python != "3.12.10":
        raise IntegrityError(f"Python must be exactly 3.12.10, found {python}.")
    if distributions.get("numpy") != "2.2.6" or distributions.get("stim") != "1.16.0" or distributions.get("pymatching") != "2.4.0":
        raise IntegrityError("Core Stim/PyMatching/NumPy versions differ from the approved environment.")
    return {
        "python": python,
        "distributions": dict(sorted(distributions.items())),
        "locked_distribution_count": len(distributions),
        "beliefmatching_upstream_commit": actual_commit,
        "beliefmatching_editable_install": editable,
        "beliefmatching_provenance_kind": provenance_kind,
        "beliefmatching_core_source_sha256_lf": core_source_sha,
        "dependency_lock_sha256": sha256_file(lock),
        "platform": platform.platform(),
        "executable": sys.executable,
    }


def verify_source_manifest(path: str | Path, *, repository_root: str | Path) -> dict[str, Any]:
    manifest_path = Path(path).resolve()
    root = Path(repository_root).resolve()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise IntegrityError("Source hash manifest is missing or invalid JSON.") from exc
    entries = payload.get("files")
    if payload.get("schema") != "qshift-ns4a-v2-source-manifest-v1" or not isinstance(entries, list) or not entries:
        raise IntegrityError("Unsupported or incomplete source hash manifest.")
    seen: set[str] = set()
    for row in entries:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise IntegrityError("Each source manifest entry must contain exactly path and sha256.")
        rel = row["path"]
        if not isinstance(rel, str) or rel in seen or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise IntegrityError("Source manifest path is unsafe or duplicated.")
        seen.add(rel)
        target = (root / rel).resolve()
        if root not in target.parents:
            raise IntegrityError(f"Source path escaped repository root: {rel}.")
        if not target.is_file() or sha256_file(target) != row["sha256"]:
            raise IntegrityError(f"Source hash mismatch or missing file: {rel}.")
    return {"payload": payload, "manifest_sha256": sha256_file(manifest_path), "verified_files": len(entries)}


@dataclass(frozen=True)
class AuthorizedExecution:
    manifest: dict[str, Any]
    seed_inventory: dict[str, Any]
    dem_identity_manifest: dict[str, Any]
    root_seeds: dict[tuple[str, str, int], int]
    analysis_seeds: dict[str, int]
    execution_manifest_sha256: str
    seed_inventory_sha256: str


def load_authorized_execution(
    execution_manifest_path: str | Path,
    authorization_path: str | Path,
    *, repository_root: str | Path,
) -> AuthorizedExecution:
    """Validate the separate owner authorization; never called by dry-run mode."""
    root = Path(repository_root).resolve()
    manifest_path = Path(execution_manifest_path).resolve()
    approval_path = Path(authorization_path).resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise IntegrityError("A final execution manifest and separate owner authorization are both required.") from exc
    if not isinstance(manifest, dict) or not isinstance(approval, dict):
        raise IntegrityError("Execution manifest and approval must be JSON objects.")
    expected_approval_fields = {
        "schema", "owner_id", "experiment_id", "sampling_authorized", "execution_manifest_sha256",
        "authorization_statement", "authorized_utc",
    }
    if set(approval) != expected_approval_fields:
        raise IntegrityError("Owner approval fields do not exactly match the frozen schema.")
    manifest_sha = sha256_file(manifest_path)
    if (approval.get("schema") != "qshift-ns4a-v2-owner-authorization-v1"
            or approval.get("owner_id") != OWNER_ID
            or approval.get("experiment_id") != EXPERIMENT_ID
            or approval.get("sampling_authorized") is not True
            or approval.get("execution_manifest_sha256") != manifest_sha
            or approval.get("authorization_statement") != AUTHORIZATION_STATEMENT):
        raise IntegrityError("Owner authorization does not explicitly bind this exact experiment manifest.")
    try:
        timestamp = datetime.fromisoformat(approval["authorized_utc"].replace("Z", "+00:00"))
    except Exception as exc:
        raise IntegrityError("Authorization timestamp must be an ISO-8601 UTC timestamp.") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
        raise IntegrityError("Authorization timestamp must explicitly use UTC.")

    required = {
        "schema", "status", "experiment_id", "sampling_authorized", "git_commit",
        "protocol_path", "protocol_sha256", "source_manifest_path", "source_manifest_sha256",
        "seed_inventory_path", "seed_inventory_sha256", "historical_seed_screen_path",
        "historical_seed_screen_sha256", "dem_identity_manifest_path", "dem_identity_manifest_sha256",
        "runtime_fingerprint", "runtime_fingerprint_sha256",
        "output_directory", "resource_limits",
    }
    if (set(manifest) != required or manifest.get("schema") != "qshift-ns4a-v2-execution-manifest-v1"
            or manifest.get("status") != "frozen_for_owner_authorization"
            or manifest.get("experiment_id") != EXPERIMENT_ID
            or manifest.get("sampling_authorized") is not True):
        raise IntegrityError("Execution manifest is incomplete or not an explicitly frozen authorized candidate.")
    if not isinstance(manifest["git_commit"], str) or len(manifest["git_commit"]) != 40:
        raise IntegrityError("Execution manifest must bind a full Git commit SHA.")

    def explicit_file(relative: Any, expected_hash: Any, label: str) -> Path:
        if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise IntegrityError(f"{label} path must be a repository-relative path.")
        target = (root / relative).resolve()
        if root not in target.parents or not target.is_file():
            raise IntegrityError(f"{label} file is absent or escapes repository root.")
        if not isinstance(expected_hash, str) or sha256_file(target) != expected_hash:
            raise IntegrityError(f"{label} hash does not match the execution manifest.")
        return target

    protocol_path = explicit_file(manifest["protocol_path"], manifest["protocol_sha256"], "protocol")
    source_path = explicit_file(manifest["source_manifest_path"], manifest["source_manifest_sha256"], "source manifest")
    sources = verify_source_manifest(source_path, repository_root=root)
    if sources["manifest_sha256"] != manifest["source_manifest_sha256"]:
        raise IntegrityError("Source manifest identity changed after verification.")
    seed_path = explicit_file(manifest["seed_inventory_path"], manifest["seed_inventory_sha256"], "seed inventory")
    history_path = explicit_file(manifest["historical_seed_screen_path"], manifest["historical_seed_screen_sha256"], "historical seed screen")
    dem_path = explicit_file(manifest["dem_identity_manifest_path"], manifest["dem_identity_manifest_sha256"], "DEM identity manifest")
    config = json.loads(protocol_path.read_text(encoding="utf-8"))
    if (config.get("schema") != "qshift-ns4a-proposed-pilot-v2"
            or config.get("status") != "PROSPECTIVE_REVISION_NOT_AUTHORIZED"
            or config.get("sampling_authorized") is not False
            or config.get("sampling_performed") is not False
            or config.get("sealed_test_access") is not False):
        raise IntegrityError("The original V2 scientific configuration must remain prospective, unsampled, and sealed.")
    if config.get("experiment", {}).get("allocation", {}).get("total_unique_shots") != 304_000:
        raise IntegrityError("Protocol allocation is not exactly the frozen 304,000 shots.")
    if config.get("experiment", {}).get("arms") is None:
        raise IntegrityError("Protocol lost the five-arm evaluation declaration.")
    seed_inventory = json.loads(seed_path.read_text(encoding="utf-8"))
    history = json.loads(history_path.read_text(encoding="utf-8"))
    dem_manifest = json.loads(dem_path.read_text(encoding="utf-8"))
    if (dem_manifest.get("schema") != "qshift-ns4a-v2-dem-identity-manifest-v1"
            or tuple(dem_manifest.get("conditions", ())) != (
                "balanced_no_burst", "x_biased_no_burst", "z_biased_no_burst",
                "balanced_burst_0.005", "balanced_burst_0.010", "balanced_burst_0.015",
            )):
        raise IntegrityError("DEM identity manifest is incomplete or has a changed six-condition order.")
    if not isinstance(dem_manifest.get("by_condition"), dict) or set(dem_manifest["by_condition"]) != set(dem_manifest["conditions"]):
        raise IntegrityError("DEM identity manifest must declare all six candidate DEMs.")
    if history.get("historical_coverage_complete") is not True or not isinstance(history.get("seeds"), list):
        raise IntegrityError("Historical seed-screen evidence is incomplete; collision screening fails closed.")
    checked = validate_seed_inventory(
        seed_inventory,
        historical_seeds=history["seeds"],
        historical_coverage_complete=True,
    )
    if checked["selection_roots"] != 48 or checked["evaluation_roots"] != 60 or checked["total_unique_seed_values"] != 114:
        raise IntegrityError("Seed inventory does not contain the complete, disjoint V2 stream roster.")
    environment = runtime_fingerprint()
    if environment != manifest["runtime_fingerprint"] or canonical_sha256(environment) != manifest["runtime_fingerprint_sha256"]:
        raise IntegrityError("Installed runtime differs from the immutable execution manifest.")
    limits = manifest["resource_limits"]
    execution_output_path(root, manifest["output_directory"])
    if (not isinstance(limits, dict) or limits.get("wall_clock_seconds") != 1800
            or limits.get("peak_rss_bytes") != 2_147_483_648
            or limits.get("free_disk_reserve_bytes") != 1_073_741_824):
        raise IntegrityError("Execution resource limits differ from the V2 proposed limits.")
    seed_roots = {
        (entry["partition"], entry["condition_id"], entry["root_index"]): entry["seed"]
        for entry in seed_inventory["root_seeds"]
    }
    analysis = {entry["stream"]: entry["seed"] for entry in seed_inventory["analysis_seeds"]}
    return AuthorizedExecution(
        manifest, seed_inventory, dem_manifest, seed_roots, analysis,
        manifest_sha, manifest["seed_inventory_sha256"]
    )
