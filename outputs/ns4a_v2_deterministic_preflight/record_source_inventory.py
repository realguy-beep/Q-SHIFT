from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
UPSTREAM_COMMIT = "e4ff201e3db18a2d18e7474bef4a83542eaa3da8"
BASE_COMMIT = "612c5e1381d75ca069bc6952d057c798ab10e9ab"
LOCAL_INPUTS = [
    "outputs/phase4b_replication/PHASE4B_PROTOCOL.md",
    "outputs/phase4c_strong_baselines/PHASE4C_STAGE1_PROTOCOL.md",
    "outputs/phase4c_strong_baselines/run_stage1.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/qshift_ns4a_pilot_protocol_v2/NS4A_PROTOCOL_REVISION_V2.md",
    "outputs/qshift_ns4a_pilot_protocol_v2/proposed_config_v2.json",
    "outputs/qshift_ns4a_pilot_protocol_v2/NS4A_REVISION_INPUTS.json",
    "qshift_core_v1/__init__.py",
    "qshift_core_v1/contracts.py",
    "qshift_core_v1/circuit_identity.py",
    "qshift_core_v1/decoder_runtime_v2.py",
    "qshift_core_v1/pymatching_adapter.py",
    "qshift_core_v1/sampling_model_identity.py",
    "qshift_core_v1/research_adapters/__init__.py",
    "qshift_core_v1/research_adapters/beliefmatching_adapter_ns3b.py",
    "qshift_core_v1/research_adapters/beliefmatching_integration_ns2d.py",
    "qshift_core_v1/baselines.py",
    "qshift_core_v1/controller.py",
    "qshift_core_v1/evaluation.py",
]
UPSTREAM_INPUTS = [
    "outputs/qshift_ns3_decoder_research/ns3b_beliefmatching/beliefmatching_adapter.py",
    "outputs/qshift_ns3_decoder_research/ns3b_beliefmatching/requirements-ns3b.lock.txt",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(ref: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=ROOT, check=True, stdout=subprocess.PIPE
    )
    return result.stdout


def main() -> None:
    local = []
    for rel in LOCAL_INPUTS:
        worktree_data = (ROOT / rel).read_bytes()
        git_data = git_blob(BASE_COMMIT, rel)
        normalized_worktree = worktree_data.replace(b"\r\n", b"\n")
        normalized_git = git_data.replace(b"\r\n", b"\n")
        local.append(
            {
                "path": rel,
                "sha256": digest(git_data),
                "bytes": len(git_data),
                "worktree_sha256": digest(worktree_data),
                "worktree_bytes": len(worktree_data),
                "normalized_worktree_matches_git_blob": normalized_worktree == normalized_git,
            }
        )

    upstream = []
    for rel in UPSTREAM_INPUTS:
        data = git_blob(UPSTREAM_COMMIT, rel)
        upstream.append(
            {
                "git_ref": UPSTREAM_COMMIT,
                "path": rel,
                "sha256": digest(data),
                "bytes": len(data),
            }
        )

    adapter_path = "qshift_core_v1/research_adapters/beliefmatching_adapter_ns3b.py"
    adapter_sha = next(item["sha256"] for item in local if item["path"] == adapter_path)
    upstream_adapter_sha = next(
        item["sha256"]
        for item in upstream
        if item["path"].endswith("/beliefmatching_adapter.py")
    )

    inventory = {
        "schema": "qshift-ns4a-v2-preflight-source-inventory-v1",
        "purpose": "Exact allowlisted inputs for deterministic source/circuit/DEM/decoder compatibility preflight.",
        "base_commit": BASE_COMMIT,
        "branch": "codex/ns4a-v2-deterministic-preflight",
        "sparse_checkout_mode": "non-cone",
        "sampling_performed": False,
        "protected_outcomes_accessed": False,
        "stage5_accessed": False,
        "local_allowlisted_inputs": local,
        "upstream_inputs_read_by_exact_git_object": upstream,
        "adapter_copy_matches_upstream_blob": adapter_sha == upstream_adapter_sha,
        "adapter_sha256": adapter_sha,
        "upstream_adapter_sha256": upstream_adapter_sha,
        "source_count": len(local) + len(upstream),
        "note": "Only listed local paths and the listed blobs at the exact upstream commit were read for source provenance. No historical outcome files were opened.",
    }
    with (OUT / "SOURCE_INPUT_INVENTORY.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as f:
        f.write(json.dumps(inventory, indent=2) + "\n")
    print(json.dumps({
        "local_input_count": len(local),
        "upstream_input_count": len(upstream),
        "adapter_copy_matches_upstream_blob": inventory["adapter_copy_matches_upstream_blob"],
        "adapter_sha256": adapter_sha,
        "lock_sha256": next(item["sha256"] for item in upstream if item["path"].endswith(".txt")),
        "inventory": str(OUT / "SOURCE_INPUT_INVENTORY.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
