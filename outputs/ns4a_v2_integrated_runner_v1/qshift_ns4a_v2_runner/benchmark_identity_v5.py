"""Fail-closed source, checkout, and owner-authorization binding for NS-4A V2.

The V5 manifest deliberately does not contain the final commit SHA. The owner
authorization created after publication binds that SHA to the V5 manifest,
protocol, and benchmark inventory hashes, avoiding a self-referential commit.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

SOURCE_BASE_COMMIT = "bdc8cf327f747611f1015100dfefe0fb6bc24c47"
V4_MANIFEST_SHA256 = "96288e6d3b57f602699cc934fb4311f76b0d58c71e763c3b35aaade3be6108b9"
V4_MANIFEST_REL = "outputs/ns4a_v2_final_readiness_v1/SOURCE_HASH_MANIFEST_V4.json"
V5_MANIFEST_REL = "outputs/ns4a_v2_final_readiness_v5/SOURCE_HASH_MANIFEST_V5.json"
PROTOCOL_REL = "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_PROTOCOL.json"
INVENTORY_REL = "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_INVENTORY_V1.json"
AUTH_REL = "outputs/ns4a_v2_final_readiness_v5/BENCHMARK_OWNER_APPROVAL_V5.json"
COLLISION_REPORT_REL = "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_COLLISION_SCREEN_V1_FINAL.json"
BENCHMARK_NAMESPACE = "qshift-ns4a-v2-execution-readiness-benchmark-v1"
AUTH_SCHEMA = "qshift-ns4a-v2-benchmark-authorization-v5"
AUTH_SCOPE = "bounded_benchmark_only"
AUTH_STATEMENT = (
    "I, realguy-beep, explicitly authorize only the bounded NS-4A V2 execution-readiness benchmark "
    "for the exact source commit and hashes named in this authorization payload."
)
EXPECTED_CONDITIONS = (
    "balanced_no_burst",
    "x_biased_no_burst",
    "z_biased_no_burst",
    "balanced_burst_0.005",
    "balanced_burst_0.010",
    "balanced_burst_0.015",
)
AUTH_FIELDS = frozenset({
    "schema", "owner_id", "scope", "approval_statement", "sampling_authorized",
    "source_commit", "source_manifest_sha256", "protocol_sha256",
    "seed_inventory_sha256", "created_utc", "expires_utc",
})

V5_ADDITIONAL_PATHS = frozenset({
    V4_MANIFEST_REL,
    "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_COLLISION_SCREEN_V1.json",
    "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_COLLISION_SCREEN_V1_CORRECTED.json",
    "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_COLLISION_SCREEN_V1_CORRECTED2.json",
    COLLISION_REPORT_REL,
    INVENTORY_REL,
    "outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/benchmark_identity_v5.py",
    "outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/benchmark_v5.py",
    "outputs/ns4a_v2_final_readiness_v5/build_source_manifest_v5.py",
    "outputs/ns4a_v2_final_readiness_v5/verify_source_manifest_v5.py",
    "outputs/ns4a_v2_final_readiness_v5/test_benchmark_source_identity_v5.py",
    "outputs/ns4a_v2_final_readiness_v5/run_benchmark_v5.py",
})
REQUIRED_LOCK_PATH = "outputs/ns4a_v2_lockmatched_env_recovery_v1/requirements-ns3b.lock.txt"


class IdentityError(RuntimeError):
    """A source, checkout, authorization, or seed-identity invariant failed."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _inside(root: Path, rel: str) -> Path:
    p = PurePosixPath(rel)
    if p.is_absolute() or ".." in p.parts or "\\" in rel:
        raise IdentityError(f"unsafe manifest path: {rel!r}")
    target = (root / Path(*p.parts)).resolve()
    if root.resolve() not in target.parents:
        raise IdentityError(f"manifest path escapes repository: {rel!r}")
    return target


def _run_git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()
    except Exception as exc:
        raise IdentityError(f"git identity check failed for {args[0]!r}.") from exc


def git_head(root: str | Path) -> str:
    return _run_git(Path(root).resolve(), "rev-parse", "HEAD")


def check_exact_head(root: str | Path, expected_commit: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise IdentityError("authorization source_commit must be a full lowercase Git SHA-1.")
    if git_head(root) != expected_commit:
        raise IdentityError("Git HEAD differs from the owner-authorized source commit.")


def check_clean_checkout(root: str | Path) -> None:
    """Require no tracked changes and permit only the exact local owner token path.

    All benchmark seed and collision evidence is committed and hash-covered.
    The only approved pre-run untracked file is the owner-created authorization
    payload. Run outputs are created only after this check and are not an
    approved pre-existing untracked path.
    """
    repo = Path(root).resolve()
    tracked_auth = subprocess.run(
        ["git", "ls-files", "--error-unmatch", AUTH_REL], cwd=repo,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if tracked_auth.returncode == 0:
        raise IdentityError("owner authorization must remain a local, untracked file.")
    status = _run_git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    # Git's -z output can include NULs; check_output(text=True) preserves them.
    entries = [item for item in status.split("\0") if item]
    unexpected: list[str] = []
    for entry in entries:
        code, _, raw_path = entry[:2], entry[2:3], entry[3:]
        path = raw_path.replace("\\", "/")
        if code == "??" and path == AUTH_REL:
            continue
        unexpected.append(entry)
    if unexpected:
        raise IdentityError("worktree is not clean except for the exact owner-authorization file.")
    # Explicit checks guard staged and unstaged tracked content even if status parsing changes.
    for args in (("diff", "--quiet", "HEAD", "--"), ("diff", "--cached", "--quiet", "HEAD", "--")):
        proc = subprocess.run(["git", *args], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if proc.returncode != 0:
            raise IdentityError("tracked source worktree or index is dirty.")


def _manifest_rows(manifest: Mapping[str, Any]) -> dict[str, str]:
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise IdentityError("V5 manifest files must be a list.")
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise IdentityError("V5 manifest contains a malformed file row.")
        path, digest = row["path"], row["sha256"]
        if not isinstance(path, str) or not re.fullmatch(r"[0-9a-f]{64}", str(digest)) or path in result:
            raise IdentityError("V5 manifest contains duplicate or invalid file identity.")
        result[path] = digest
    return result


def source_tree_digest(rows: Mapping[str, str]) -> str:
    material = [{"path": p, "sha256": rows[p]} for p in sorted(rows)]
    return sha256_bytes(_canonical(material))


def validate_v5_manifest_header(manifest: Mapping[str, Any]) -> None:
    if (manifest.get("schema") != "qshift-ns4a-v2-source-manifest-v5"
            or manifest.get("readiness_revision") != "NS-4A V2 exact source identity V5"):
        raise IdentityError("manifest is not the reviewed V5 source-identity manifest.")
    if manifest.get("source_base_commit") != SOURCE_BASE_COMMIT:
        raise IdentityError("V5 manifest is not based on the approved starting commit.")
    if manifest.get("manifest_self_reference_excluded") is not True:
        raise IdentityError("V5 manifest must declare its noncircular self-reference rule.")
    if manifest.get("commit_binding") != "owner authorization source_commit must equal exact current Git HEAD":
        raise IdentityError("V5 manifest does not declare the exact post-commit owner binding.")
    if manifest.get("final_commit_sha") is not None:
        raise IdentityError("the committed manifest must not embed a circular final commit SHA.")
    if "source_commit" in manifest:
        raise IdentityError("final source commit belongs only in the post-commit owner authorization.")


def verify_file_rows(repository_root: str | Path, rows: Mapping[str, str], expected_paths: set[str]) -> None:
    root = Path(repository_root).resolve()
    if set(rows) != expected_paths:
        raise IdentityError("manifest has missing or unexpected source/evidence paths.")
    for path, expected in rows.items():
        target = _inside(root, path)
        if not target.is_file() or sha256_file(target) != expected:
            raise IdentityError(f"source/evidence hash failed: {path}")


def verify_source_manifest_v5(repository_root: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    expected_manifest = _inside(root, V5_MANIFEST_REL)
    if Path(manifest_path).resolve() != expected_manifest:
        raise IdentityError("only the versioned V5 manifest path is accepted.")
    try:
        raw = expected_manifest.read_bytes()
        manifest = json.loads(raw)
    except Exception as exc:
        raise IdentityError("V5 source manifest is missing or malformed.") from exc
    if not isinstance(manifest, dict):
        raise IdentityError("V5 source manifest must be a JSON object.")
    validate_v5_manifest_header(manifest)

    v4_path = _inside(root, V4_MANIFEST_REL)
    if sha256_file(v4_path) != V4_MANIFEST_SHA256:
        raise IdentityError("historical V4 manifest hash changed.")
    try:
        v4 = json.loads(v4_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise IdentityError("historical V4 manifest is unreadable.") from exc
    if manifest.get("parent_v4_manifest_sha256") != V4_MANIFEST_SHA256:
        raise IdentityError("V5 manifest does not bind the unchanged V4 manifest.")
    base_rows = {str(row["path"]): str(row["sha256"]) for row in v4.get("files", [])}
    expected_paths = set(base_rows) | set(V5_ADDITIONAL_PATHS)
    rows = _manifest_rows(manifest)
    if type(manifest.get("file_count")) is not int or len(rows) != manifest.get("file_count"):
        raise IdentityError("V5 manifest has missing or unexpected source/evidence paths.")
    for path, digest in base_rows.items():
        if rows.get(path) != digest:
            raise IdentityError(f"V5 changes a historical V4 source binding: {path}")
    if REQUIRED_LOCK_PATH not in rows:
        raise IdentityError("V5 manifest omits the pinned dependency lock.")
    if manifest.get("source_tree_sha256") != source_tree_digest(rows):
        raise IdentityError("V5 source-tree digest does not match its file rows.")
    if (manifest.get("dependency_lock_path") != REQUIRED_LOCK_PATH
            or manifest.get("dependency_lock_sha256") != rows.get(REQUIRED_LOCK_PATH)):
        raise IdentityError("V5 manifest does not bind the exact pinned dependency lock.")
    expected_untracked_policy = {
        "approved_seed_inventory_and_collision_evidence": "tracked and included in files",
        "only_pre_run_untracked_path": AUTH_REL,
        "authorization_file": "validated by exact schema and hash bindings; excluded from source file set",
        "unexpected_untracked_or_any_tracked_changes": "reject",
        "benchmark_output_directory_must_be_absent_before_start": True,
    }
    if manifest.get("untracked_policy") != expected_untracked_policy:
        raise IdentityError("V5 untracked-file policy changed or weakens source integrity.")
    verify_file_rows(root, rows, expected_paths)
    if manifest.get("sampling_authorized") is not False or manifest.get("sampling_performed") is not False:
        raise IdentityError("source manifest may not authorize or record sampling.")
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_bytes(raw),
        "source_tree_sha256": source_tree_digest(rows),
        "verified_file_count": len(rows),
        "files": rows,
    }


def _utc_seconds(value: Any, name: str) -> float:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise IdentityError(f"{name} must be a UTC timestamp ending in Z.")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc).timestamp()
    except ValueError as exc:
        raise IdentityError(f"{name} is malformed.") from exc


def validate_authorization_payload(
    authorization: Mapping[str, Any], *, source_commit: str, source_manifest_sha256: str,
    protocol_sha256: str, seed_inventory_sha256: str, now_utc: str | None = None,
) -> None:
    if set(authorization) != AUTH_FIELDS:
        raise IdentityError("owner authorization fields are incomplete or contain unsupported fields.")
    expected = {
        "schema": AUTH_SCHEMA,
        "owner_id": "realguy-beep",
        "scope": AUTH_SCOPE,
        "approval_statement": AUTH_STATEMENT,
        "sampling_authorized": True,
        "source_commit": source_commit,
        "source_manifest_sha256": source_manifest_sha256,
        "protocol_sha256": protocol_sha256,
        "seed_inventory_sha256": seed_inventory_sha256,
    }
    for key, value in expected.items():
        if authorization.get(key) != value:
            raise IdentityError(f"owner authorization {key} does not match the reviewed execution identity.")
    created = _utc_seconds(authorization.get("created_utc"), "created_utc")
    expires = _utc_seconds(authorization.get("expires_utc"), "expires_utc")
    now = _utc_seconds(now_utc, "now_utc") if now_utc else datetime.now(timezone.utc).timestamp()
    if not created <= now <= expires or expires - created > 86_400:
        raise IdentityError("owner authorization is not current or exceeds the 24-hour validity window.")


def verify_execution_identity(
    repository_root: str | Path, *, authorization_path: str | Path,
    manifest_path: str | Path, protocol_path: str | Path, inventory_path: str | Path,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    for supplied, expected in (
        (manifest_path, V5_MANIFEST_REL), (protocol_path, PROTOCOL_REL),
        (inventory_path, INVENTORY_REL), (authorization_path, AUTH_REL),
    ):
        if Path(supplied).resolve() != _inside(root, expected):
            raise IdentityError(f"execution input must use the reviewed path {expected}.")
    if not Path(authorization_path).is_file():
        raise IdentityError("owner authorization file is missing.")
    try:
        auth = json.loads(Path(authorization_path).read_text(encoding="utf-8"))
        protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
        inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise IdentityError("execution identity JSON input is missing or malformed.") from exc
    if not all(isinstance(x, dict) for x in (auth, protocol, inventory)):
        raise IdentityError("execution identity inputs must be JSON objects.")
    manifest_record = verify_source_manifest_v5(root, manifest_path)
    protocol_sha = sha256_file(protocol_path)
    inventory_sha = sha256_file(inventory_path)
    check_exact_head(root, str(auth.get("source_commit", "")))
    check_clean_checkout(root)
    validate_authorization_payload(
        auth, source_commit=git_head(root),
        source_manifest_sha256=manifest_record["manifest_sha256"],
        protocol_sha256=protocol_sha, seed_inventory_sha256=inventory_sha,
    )
    if protocol.get("schema") != "qshift-ns4a-v2-benchmark-protocol-v1":
        raise IdentityError("benchmark protocol identity is not V1.")
    if inventory.get("schema") != "qshift-ns4a-v2-benchmark-seed-inventory-v1":
        raise IdentityError("benchmark seed inventory identity is not V1.")
    seeds = inventory.get("seed_by_condition")
    if (inventory.get("namespace") != BENCHMARK_NAMESPACE
            or inventory.get("scientific_seed_allocation") is not False
            or inventory.get("numeric_seeds_allocated") is not True
            or inventory.get("sampling_authorized") is not False
            or not isinstance(seeds, dict) or set(seeds) != set(EXPECTED_CONDITIONS)
            or any(type(v) is not int or not 0 <= v <= 2**63 - 1 for v in seeds.values())
            or len(set(seeds.values())) != 6):
        raise IdentityError("benchmark seed inventory is incomplete or has invalid scope.")
    run_root = _inside(root, "outputs/ns4a_v2_final_readiness_v5/benchmark_runs")
    if run_root.exists():
        raise IdentityError("V5 benchmark output root already exists; refusing reuse or implicit recovery.")
    return {
        "source_commit": git_head(root),
        "source_manifest_sha256": manifest_record["manifest_sha256"],
        "source_tree_sha256": manifest_record["source_tree_sha256"],
        "protocol_sha256": protocol_sha,
        "seed_inventory_sha256": inventory_sha,
        "authorization_sha256": sha256_file(authorization_path),
        "benchmark_id": hashlib.sha256(
            (git_head(root) + manifest_record["manifest_sha256"] + protocol_sha + inventory_sha).encode()
        ).hexdigest()[:16],
    }


HISTORICAL_SEED_PATHS = (
    "outputs/phase2b_pauli_bias/SEED_MANIFEST.csv",
    "outputs/phase2b_pauli_bias/SEED_SCREENING.json",
    "outputs/phase4b_replication/PER_SEED_RESULTS.csv",
    "outputs/phase4c_strong_baselines/DEVELOPMENT_PER_SEED.csv",
    "outputs/phase4c_strong_baselines/stage2/STAGE2_SEED_INVENTORY.json",
    "outputs/phase4c_strong_baselines/stage2/STAGE2_SEED_INVENTORY_AMENDED.json",
    "outputs/correlation_pilot/SEED_INVENTORY.json",
    "outputs/headroom_feasibility/SEED_INVENTORY.json",
    "outputs/headroom_feasibility/HISTORICAL_SEED_SCAN.json",
)


def load_approved_historical_seed_values(repository_root: str | Path) -> set[int]:
    """Read only the already approved numeric seed columns/containers.

    No outcome columns, detector arrays, or Stage 5 paths are opened. The
    extraction is checked against the preserved final collision-screen report
    and exact Git blob identities before the values can be used by the runner.
    """
    root = Path(repository_root).resolve()
    screen_path = _inside(root, COLLISION_REPORT_REL)
    try:
        screen = json.loads(screen_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise IdentityError("approved seed collision-screen evidence is missing or malformed.") from exc
    if screen.get("schema") != "qshift-ns4a-v2-benchmark-seed-collision-screen-v1-final":
        raise IdentityError("seed collision-screen evidence is not the final corrected report.")
    records = {row.get("path"): row for row in screen.get("approved_metadata_sources", []) if isinstance(row, dict)}
    if set(records) != set(HISTORICAL_SEED_PATHS):
        raise IdentityError("approved historical seed metadata allowlist is incomplete or changed.")

    per_source_values: dict[str, list[int]] = {}
    for rel in HISTORICAL_SEED_PATHS:
        _inside(root, rel)
        record = records[rel]
        current_blob = _run_git(root, "rev-parse", f"HEAD:{rel}")
        if current_blob != record.get("git_blob_oid"):
            raise IdentityError(f"approved historical seed source Git identity changed: {rel}")
        try:
            raw_source = subprocess.check_output(["git", "show", f"HEAD:{rel}"], cwd=root)
        except Exception as exc:
            raise IdentityError(f"approved historical seed source cannot be read from its recorded Git object: {rel}") from exc
        values: list[int] = []
        fields: set[str] = set()
        if rel.endswith(".csv"):
            try:
                reader = csv.reader(io.StringIO(raw_source.decode("utf-8-sig")))
                header = next(reader, None)
                if header is None:
                    raise IdentityError(f"approved seed CSV has no header: {rel}")
                if rel.endswith("SEED_MANIFEST.csv"):
                    wanted = {"seed"}
                elif rel.endswith("PER_SEED_RESULTS.csv"):
                    wanted = {"seed_root"}
                else:
                    wanted = {"seed"}
                cols = [(i, name) for i, name in enumerate(header) if name in wanted]
                if {name for _, name in cols} != wanted:
                    raise IdentityError(f"approved seed CSV field contract changed: {rel}")
                for row in reader:
                    for i, name in cols:
                        if i >= len(row):
                            raise IdentityError(f"approved seed CSV row is malformed: {rel}")
                        value = row[i]
                        if not re.fullmatch(r"[+-]?\d+", value.strip()):
                            raise IdentityError(f"approved seed field is not an integer: {rel}")
                        values.append(int(value.strip()))
                        fields.add(name)
            except IdentityError:
                raise
            except Exception as exc:
                raise IdentityError(f"approved seed CSV is unreadable: {rel}") from exc
        else:
            try:
                doc = json.loads(raw_source.decode("utf-8"))
            except Exception as exc:
                raise IdentityError(f"approved seed JSON is unreadable: {rel}") from exc

            def add(value: Any, field: str) -> None:
                if type(value) is not int or not 0 <= value <= 2**63 - 1:
                    raise IdentityError(f"approved seed value is invalid in {rel}")
                values.append(value)
                fields.add(field)

            if rel.endswith("SEED_SCREENING.json"):
                for value in doc.get("proposed_seed_values", []):
                    add(value, "proposed_seed_values[]")
            elif "/stage2/" in rel:
                for group, entries in doc.get("roots", {}).items():
                    for value in entries:
                        add(value, f"roots.{group}[]")
                for group, entries in doc.get("derived_seeds", {}).items():
                    for value in entries:
                        add(value, f"derived_seeds.{group}[]")
                for group in ("template", "diagnostic"):
                    for value in doc.get(group, []):
                        add(value, f"{group}[]")
            elif rel.endswith("correlation_pilot/SEED_INVENTORY.json"):
                for row in doc.get("root_seeds", []):
                    if not isinstance(row, dict):
                        raise IdentityError(f"approved root-seed record is malformed: {rel}")
                    add(row.get("seed"), "root_seeds[].seed")
                for key, value in doc.get("auxiliary_seeds", {}).items():
                    add(value, f"auxiliary_seeds.{key}")
                for value in doc.get("candidate_values_screened", []):
                    add(value, "candidate_values_screened[]")
            elif rel.endswith("headroom_feasibility/SEED_INVENTORY.json"):
                for group, rows in doc.items():
                    if isinstance(rows, list):
                        for row in rows:
                            if isinstance(row, dict) and "seed" in row:
                                add(row["seed"], f"{group}[].seed")
            elif rel.endswith("HISTORICAL_SEED_SCAN.json"):
                for value in doc.get("recoverable_unique_seed_values", []):
                    add(value, "recoverable_unique_seed_values[]")
                for row in doc.get("evidence", []):
                    if not isinstance(row, dict):
                        raise IdentityError(f"historical seed evidence record is malformed: {rel}")
                    add(row.get("seed"), "evidence[].seed")
            else:
                raise IdentityError(f"no approved JSON seed-field map exists for {rel}")

        if any(type(value) is not int or not 0 <= value <= 2**63 - 1 for value in values):
            raise IdentityError(f"approved seed values are out of range: {rel}")
        distinct = sorted(set(values))
        digest = sha256_bytes(_canonical(distinct))
        if (sorted(fields) != record.get("permitted_seed_fields")
                or len(values) != record.get("seed_values_extracted_count")
                or len(distinct) != record.get("distinct_seed_values_count")
                or digest != record.get("selected_seed_values_sha256")):
            raise IdentityError(f"approved seed extraction differs from frozen screening evidence: {rel}")
        per_source_values[rel] = distinct

    union = sorted({seed for values in per_source_values.values() for seed in values})
    if (len(union) != screen.get("historical_distinct_seed_count")
            or sha256_bytes(_canonical(union)) != screen.get("historical_seed_values_sha256")):
        raise IdentityError("approved historical seed union differs from the preserved collision screen.")
    return set(union)
