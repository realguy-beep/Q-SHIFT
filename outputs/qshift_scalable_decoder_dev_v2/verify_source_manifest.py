"""Verify the explicit V2 source/evidence inventory without running research code."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / "SOURCE_MANIFEST.json"

# Fixed allowlist: the manifest is intentionally self-excluded. No directory
# traversal or dynamic file discovery is used by this verifier.
V2_PATHS = [
    "outputs/qshift_scalable_decoder_dev_v2/README.md",
    "outputs/qshift_scalable_decoder_dev_v2/PROTOCOL.md",
    "outputs/qshift_scalable_decoder_dev_v2/ROOT_CAUSE_REPORT.md",
    "outputs/qshift_scalable_decoder_dev_v2/DETERMINISTIC_RESULTS.md",
    "outputs/qshift_scalable_decoder_dev_v2/NEXT_METHOD_RECOMMENDATION.md",
    "outputs/qshift_scalable_decoder_dev_v2/VALIDATION_SUMMARY.md",
    "outputs/qshift_scalable_decoder_dev_v2/V1_6B_REPRODUCIBILITY_CLOSURE.md",
    "outputs/qshift_scalable_decoder_dev_v2/TASK_CHECKPOINT.md",
    "outputs/qshift_scalable_decoder_dev_v2/factor_bp_v2.py",
    "outputs/qshift_scalable_decoder_dev_v2/exact_reference.py",
    "outputs/qshift_scalable_decoder_dev_v2/test_factor_bp_v2.py",
    "outputs/qshift_scalable_decoder_dev_v2/run_fixtures_v2.py",
    "outputs/qshift_scalable_decoder_dev_v2/trace_diagnostics_v2.py",
    "outputs/qshift_scalable_decoder_dev_v2/period2_diagnostic.py",
    "outputs/qshift_scalable_decoder_dev_v2/check_alternatives.py",
    "outputs/qshift_scalable_decoder_dev_v2/CONVERGENCE_DIAGNOSTICS.json",
    "outputs/qshift_scalable_decoder_dev_v2/PERIOD2_DIAGNOSTICS.json",
    "outputs/qshift_scalable_decoder_dev_v2/fixture_results.json",
    "outputs/qshift_scalable_decoder_dev_v2/fixture_results_post_edge_fix.json",
    "outputs/qshift_scalable_decoder_dev_v2/fixture_results_final.json",
    "outputs/qshift_scalable_decoder_dev_v2/repeatability_check.json",
    "outputs/qshift_scalable_decoder_dev_v2/repeatability_check_final.json",
    "outputs/qshift_scalable_decoder_dev_v2/verify_source_manifest.py",
]

# Directly used or explicitly compared repository sources. These are hashed
# as dependencies/context, not copied or modified by V2.
DEPENDENCY_PATHS = [
    "outputs/qshift_scalable_decoder_dev_v1/PROTOCOL.md",
    "outputs/qshift_scalable_decoder_dev_v1/FEASIBILITY_REPORT.md",
    "outputs/qshift_scalable_decoder_dev_v1/factor_bp.py",
    "outputs/qshift_scalable_decoder_dev_v1/run_fixtures.py",
    "outputs/qshift_correlated_decoder_v1_4/model_v14.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/qshift_v1_4b_decoder_optimality/mld.py",
    "outputs/qshift_v1_6b_replay_verification_v1/REPLAY_REPORT.md",
    "outputs/qshift_v1_6b_replay_verification_v1/result.json",
    "outputs/qshift_v1_6b_calibration_reconstruction_v1/REPORT.md",
    "outputs/qshift_v1_6b_calibration_reconstruction_v1/reconstruct.py",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(path: str) -> str:
    completed = subprocess.run(
        ["git", "hash-object", "--path", path, path], cwd=ROOT,
        check=True, capture_output=True, text=True,
    )
    return completed.stdout.strip()


def entry(path: str, role: str) -> dict:
    data = (ROOT / Path(path)).read_bytes()
    return {
        "path": path,
        "role": role,
        "byte_length": len(data),
        "worktree_sha256": sha256(data),
        "git_blob_sha1_clean_filter": git_blob(path),
    }


def build_manifest() -> dict:
    entries = [entry(path, "v2_source_protocol_test_or_evidence") for path in V2_PATHS]
    entries += [entry(path, "historical_read_only_dependency_or_context") for path in DEPENDENCY_PATHS]
    return {
        "manifest_version": "qshift-scalable-decoder-v2-source-manifest-v1",
        "purpose": "Integrity inventory; no sampling or held-out evaluation.",
        "manifest_self_hash": "EXCLUDED_TO_AVOID_SELF_REFERENCE",
        "protocol_commit": "4948bc43b442f651a4d845dd249980a68cbf0bce",
        "implementation_commit": "674993b502e13015c3bd8cbc595a97b1c48b9456",
        "entries": entries,
    }


def verify() -> int:
    if not MANIFEST.is_file():
        print(f"FAIL missing manifest: {MANIFEST}")
        return 1
    recorded = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = build_manifest()
    if recorded != actual:
        recorded_by_path = {item["path"]: item for item in recorded.get("entries", [])}
        actual_by_path = {item["path"]: item for item in actual["entries"]}
        differences = [path for path in sorted(set(recorded_by_path) | set(actual_by_path))
                       if recorded_by_path.get(path) != actual_by_path.get(path)]
        print("FAIL source manifest mismatch")
        for path in differences:
            print(path)
        return 1
    print(f"PASS {len(actual['entries'])} explicit file identities; manifest self-hash excluded")
    return 0


def write_once() -> int:
    if MANIFEST.exists():
        print(f"REFUSED manifest already exists: {MANIFEST}")
        return 2
    payload = json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n"
    with MANIFEST.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
    print(f"WROTE {MANIFEST}")
    return 0


def refresh_reviewed() -> int:
    """Refresh the not-yet-frozen inventory after an intentional package edit."""
    payload = json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n"
    temporary = MANIFEST.with_suffix(".json.tmp")
    if temporary.exists():
        print(f"REFUSED pre-existing temporary manifest: {temporary}")
        return 2
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, MANIFEST)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    print(f"REFRESHED {MANIFEST}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-once", action="store_true",
                        help="create the absent manifest once; does not overwrite")
    parser.add_argument("--refresh-reviewed", action="store_true",
                        help="atomically refresh after an intentional package edit")
    args = parser.parse_args()
    if args.write_once and args.refresh_reviewed:
        parser.error("choose only one manifest write mode")
    try:
        if args.write_once:
            return write_once()
        if args.refresh_reviewed:
            return refresh_reviewed()
        return verify()
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"FAIL verification error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
