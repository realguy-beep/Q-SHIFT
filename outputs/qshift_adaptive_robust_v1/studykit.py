"""Shared helpers for future study runners in this package (added in the 2026-11-20 polish pass).

Frozen studies (DEV2 through AD1) keep their own copies of this logic and do not import this module; it exists so
the next study's freeze, prepare and run scripts do not have to copy it again. No sampling, no decoding.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PKG = "outputs/qshift_adaptive_robust_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump_json(path: Path, obj) -> None:
    """Canonical JSON (sorted keys, indent 2, LF, trailing newline), as every study artifact uses."""
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_once_json(path: Path, obj) -> None:
    """Write-once record: refuse to overwrite."""
    path = Path(path)
    if path.exists():
        raise SystemExit(f"{path.name} exists; records are write-once")
    dump_json(path, obj)


def freeze_hashes(files) -> dict:
    """Map each repo-relative path to its SHA-256; every input must exist."""
    out = {}
    for rel in files:
        p = REPO / rel
        if not p.is_file():
            raise FileNotFoundError(f"freeze input missing: {rel}")
        out[rel] = sha256(p)
    return out


def freeze_doc(schema: str, study: str, files, run_phrase: str) -> dict:
    """The non-circular freeze document, in the format used since DEV2."""
    hashes = freeze_hashes(files)
    return {
        "schema": schema, "study": study, "branch": "codex/qshift-adaptive-robust-v1", "files": hashes,
        "file_count": len(hashes),
        "non_circular_binding": "Excludes its own digest and the commit SHA; runs require --expected-head = the commit "
                                "containing this file, a clean tree, and every hash above (checked by each job).",
        "sampling_authorization": f"None. Owner must separately authorize '{run_phrase}' on this commit.",
        "study_samples_before_freeze": 0}


def write_freeze(name: str, schema: str, study: str, files, run_phrase: str) -> Path:
    """Write <NAME>_FREEZE.json; refuses to overwrite an existing freeze."""
    path = ROOT / f"{name}_FREEZE.json"
    write_once_json(path, freeze_doc(schema, study, files, run_phrase))
    return path


def check_freeze(path: Path) -> list[str]:
    """Return the files whose current bytes differ from (or are missing versus) a freeze JSON."""
    fz = json.loads(Path(path).read_text(encoding="utf-8"))
    bad = []
    for rel, h in fz["files"].items():
        p = REPO / rel
        if not p.is_file() or sha256(p) != h:
            bad.append(rel)
    return bad


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout.strip()


def tree_clean() -> bool:
    return subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout.strip() == ""


def require_frozen_head(freeze: Path, expected_head: str) -> None:
    """The run guard every study uses: expected head, clean tree, and every frozen hash intact."""
    if git_head() != expected_head:
        raise SystemExit(f"HEAD {git_head()} != expected {expected_head}")
    if not tree_clean():
        raise SystemExit("working tree not clean")
    bad = check_freeze(freeze)
    if bad:
        raise SystemExit(f"frozen files changed: {bad}")
