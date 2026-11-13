from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_text(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def main() -> None:
    inventory = json.loads((OUT / "SOURCE_INPUT_INVENTORY.json").read_text(encoding="utf-8"))
    source_ok = True
    for record in inventory["local_allowlisted_inputs"]:
        data = (ROOT / record["path"]).read_bytes()
        git_data = subprocess.run(
            ["git", "show", f"{inventory['base_commit']}:{record['path']}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        source_ok &= (
            sha(git_data) == record["sha256"]
            and len(git_data) == record["bytes"]
            and sha(data) == record["worktree_sha256"]
            and len(data) == record["worktree_bytes"]
            and canonical_text(data) == canonical_text(git_data)
        )
    for record in inventory["upstream_inputs_read_by_exact_git_object"]:
        data = subprocess.run(
            ["git", "show", f"{record['git_ref']}:{record['path']}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        source_ok &= sha(data) == record["sha256"] and len(data) == record["bytes"]

    manifest = json.loads((OUT / "PREFLIGHT_ARTIFACT_HASHES.json").read_text(encoding="utf-8"))
    artifact_ok = all(
        sha(canonical_text((OUT / item["path"]).read_bytes())) == item["sha256"]
        and len(canonical_text((OUT / item["path"]).read_bytes())) == item["bytes"]
        for item in manifest["files"]
    )
    staged_artifact_ok = all(
        sha(canonical_text(subprocess.run(
            ["git", "show", f":outputs/ns4a_v2_deterministic_preflight/{item['path']}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout)) == item["sha256"]
        and len(canonical_text(subprocess.run(
            ["git", "show", f":outputs/ns4a_v2_deterministic_preflight/{item['path']}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout)) == item["bytes"]
        for item in manifest["files"]
    )
    matrix = json.loads((OUT / "COMPATIBILITY_MATRIX.json").read_text(encoding="utf-8"))
    summary = json.loads((OUT / "VALIDATION_SUMMARY.json").read_text(encoding="utf-8"))
    config = json.loads((ROOT / "outputs/qshift_ns4a_pilot_protocol_v2/proposed_config_v2.json").read_text(encoding="utf-8"))
    matrix_ok = (
        len(matrix) == 12
        and all(row["circuit_construction"] == "PASS" for row in matrix)
        and all(row["dem_construction"] == "PASS" for row in matrix)
        and all(row["alias_guard"] == "PASS" for row in matrix)
        and all(row["pymatching_construction_and_fixture_decode"] == "PASS" for row in matrix)
        and all(row["bm_registration_and_construction"] == "BLOCKED_MISSING_DEPENDENCY" for row in matrix)
    )
    sparse = subprocess.run(
        ["git", "sparse-checkout", "list"], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.splitlines()
    expected_sparse = {"/" + item["path"] for item in inventory["local_allowlisted_inputs"]}
    expected_sparse.add("/outputs/ns4a_v2_deterministic_preflight/")
    sparse_ok = set(sparse) == expected_sparse
    boundary_ok = (
        config["sampling_authorized"] is False
        and config["sampling_performed"] is False
        and summary["counts"]["sampler_calls"] == 0
        and summary["counts"]["sampled_shots"] == 0
        and summary["counts"]["labels_read"] == 0
        and summary["counts"]["model_selections"] == 0
    )
    result = {
        "source_input_hashes": "PASS" if source_ok else "FAIL",
        "preflight_artifact_hashes": "PASS" if artifact_ok else "FAIL",
        "staged_blob_hashes": "PASS" if staged_artifact_ok else "FAIL",
        "12_candidate_matrix": "PASS" if matrix_ok else "FAIL",
        "sparse_allowlist_exact": "PASS" if sparse_ok else "FAIL",
        "no_sampling_boundary": "PASS" if boundary_ok else "FAIL",
        "overall": "PASS" if all((source_ok, artifact_ok, matrix_ok, sparse_ok, boundary_ok)) else "FAIL",
    }
    print(json.dumps(result, indent=2))
    result["overall"] = "PASS" if all((source_ok, artifact_ok, staged_artifact_ok, matrix_ok, sparse_ok, boundary_ok)) else "FAIL"
    if result["overall"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
