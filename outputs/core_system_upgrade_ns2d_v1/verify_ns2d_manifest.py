"""Verify NS-2D local evidence and the published NS-3B provenance manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def contained_file(root: Path, relative: str) -> Path:
    base = root.resolve(strict=True)
    target = (base / relative).resolve(strict=True)
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError(f"Manifest path is not a regular file beneath its root: {relative}")
    return target


def check_entries(
    root: Path,
    entries: list[dict],
    *,
    check_size: bool,
    hash_field: str = "sha256",
) -> list[str]:
    errors = []
    for entry in entries:
        relative = entry.get("path")
        try:
            path = contained_file(root, relative)
            actual_hash = sha256(path)
            if actual_hash != entry.get(hash_field):
                errors.append(f"SHA-256 mismatch: {relative}")
            if check_size and path.stat().st_size != entry.get("size_bytes"):
                errors.append(f"Byte-size mismatch: {relative}")
        except (OSError, TypeError, ValueError) as exc:
            errors.append(f"Invalid/missing file {relative!r}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--research-root", type=Path, required=True,
        help="Root of published codex/ns3b-beliefmatching-research worktree",
    )
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    errors: list[str] = []
    local_manifest: dict = {}

    local_manifest_path = repo_root / "outputs/core_system_upgrade_ns2d_v1/NS2D_ENGINEERING_MANIFEST.json"
    try:
        local_manifest = json.loads(local_manifest_path.read_text(encoding="utf-8"))
        errors.extend(check_entries(repo_root, local_manifest["files"], check_size=True))
        branch = subprocess.run(
            ["git", "-C", str(repo_root), "branch", "--show-current"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        if branch != local_manifest["integration_branch"]:
            errors.append(f"Integration branch mismatch: {branch}")
        merge_base = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "HEAD", local_manifest["engineering_base_commit"]],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        if merge_base != local_manifest["engineering_base_commit"]:
            errors.append(f"Integration branch is not based on the required engineering commit: {merge_base}")
        research_git = subprocess.run(
            ["git", "-C", str(args.research_root.resolve(strict=True)), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        if research_git != local_manifest["research_commit"]:
            errors.append(f"Research worktree HEAD mismatch: {research_git}")
        research_parent = subprocess.run(
            ["git", "-C", str(args.research_root.resolve(strict=True)), "rev-list", "--parents", "-n", "1", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip().split()
        if len(research_parent) != 2 or research_parent[1] != local_manifest["engineering_base_commit"]:
            errors.append("Published research commit does not have the required exact engineering parent")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Local engineering manifest failure: {exc}")
    except subprocess.CalledProcessError as exc:
        errors.append(f"Cannot verify research worktree commit: {exc.stderr.strip()}")

    research_root = args.research_root.resolve(strict=True)
    research_out = research_root / "outputs/qshift_ns3_decoder_research"
    try:
        source_manifest_path = research_out / "SOURCE_MANIFEST.json"
        if sha256(source_manifest_path) != local_manifest["source_manifest_sha256"]:
            errors.append("Published SOURCE_MANIFEST.json hash differs from the recorded hash")
        published = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        errors.extend(check_entries(research_out, published["files"], check_size=True))
        errors.extend(check_entries(repo_root, published["unchanged_base_dependencies"], check_size=False))
        errors.extend(check_entries(
            research_root, published["publication_copy_transformations"],
            check_size=False, hash_field="published_sha256",
        ))
        for relative in published["publication_authored_files"]:
            path = contained_file(research_root, relative)
            if path.suffix.lower() != ".md":
                errors.append(f"Publication-authored artifact is not Markdown: {relative}")
        adapter = contained_file(research_out, "ns3b_beliefmatching/beliefmatching_adapter.py")
        expected = "702dc36ef4dedd38347b0e78541d1d2d2ff063c2462dbab29aa2095f583c2106"
        if sha256(adapter) != expected:
            errors.append("Published adapter does not match the requested SHA-256")
        local_adapter = contained_file(repo_root, "qshift_core_v1/research_adapters/beliefmatching_adapter_ns3b.py")
        if sha256(local_adapter) != expected:
            errors.append("Imported adapter does not match the requested SHA-256")
        lock = contained_file(repo_root, "outputs/core_system_upgrade_ns2d_v1/requirements-ns3b.lock.txt")
        published_lock = contained_file(research_out, "ns3b_beliefmatching/requirements-ns3b.lock.txt")
        if sha256(lock) != local_manifest["dependency_lock_sha256"]:
            errors.append("Local dependency lock differs from its recorded SHA-256")
        if sha256(lock) != sha256(published_lock):
            errors.append("Copied dependency lock differs from the published NS-3B lock")
        print(f"Published source-manifest entries: {len(published['files'])}")
        print(f"Unchanged base dependency entries: {len(published['unchanged_base_dependencies'])}")
        print(f"Documented Markdown copy transformations: {len(published['publication_copy_transformations'])}")
        print(f"Publication-authored Markdown files: {len(published['publication_authored_files'])}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Published NS-3B provenance failure: {exc}")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    local_count = len(local_manifest["files"])
    print(f"PASS: {local_count} local engineering files and published provenance checks verify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
