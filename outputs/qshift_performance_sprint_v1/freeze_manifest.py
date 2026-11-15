"""Write an allowlisted pre-sampling source freeze. No sampling is performed."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
FILES = [
    "AGENTS.md",
    ".gitignore",
    "qshift_core_v1/contracts.py",
    "qshift_core_v1/evaluation.py",
    "qshift_core_v1/pymatching_adapter.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/phase2b_pauli_bias/decoder_bank.py",
    "outputs/phase2b_pauli_bias/config.json",
    "outputs/phase2b_pauli_bias/PHASE2B_PROTOCOL.md",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/phase3a_correlated_noise_preflight/config.json",
    "outputs/phase3a_correlated_noise_preflight/CORRELATED_NOISE_HYPOTHESIS.md",
    "outputs/phase3a_correlated_noise_preflight/BASELINE_FAIRNESS_ANALYSIS.md",
    "outputs/qshift_performance_sprint_v1/EXPERIMENT_PROTOCOL.md",
    "outputs/qshift_performance_sprint_v1/README.md",
    "outputs/qshift_performance_sprint_v1/config.json",
    "outputs/qshift_performance_sprint_v1/seed_inventory.json",
    "outputs/qshift_performance_sprint_v1/estimator.py",
    "outputs/qshift_performance_sprint_v1/prepare_seed_inventory.py",
    "outputs/qshift_performance_sprint_v1/run_pilot.py",
    "outputs/qshift_performance_sprint_v1/analyze.py",
    "outputs/qshift_performance_sprint_v1/audit_saved_arrays.py",
    "outputs/qshift_performance_sprint_v1/freeze_manifest.py",
    "outputs/qshift_performance_sprint_v1/tests/test_deterministic.py",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    missing = [rel for rel in FILES if not (REPO / rel).is_file()]
    if missing:
        raise SystemExit(f"freeze inputs missing: {missing}")
    hashes = {rel: sha(REPO / rel) for rel in FILES}
    versions = {
        "python": sys.version,
        "stim": importlib.metadata.version("stim"),
        "pymatching": importlib.metadata.version("pymatching"),
        "numpy": importlib.metadata.version("numpy"),
        "psutil": importlib.metadata.version("psutil"),
    }
    manifest = {
        "schema": "qshift-performance-source-freeze-v1",
        "classification": "development-only; no sealed data",
        "base_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                                      capture_output=True, text=True, check=True).stdout.strip(),
        "files": hashes,
        "environment": versions,
        "manifest_rule": "explicit allowlist; source_manifest.json and PRETEST_FREEZE.json are not self-hashed; final committed HEAD is persisted in samples/run_start.json",
    }
    manifest_path = ROOT / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    freeze = {
        "schema": "qshift-performance-pretest-freeze-v1",
        "classification": "prospective development pilot; not confirmatory",
        "base_commit": manifest["base_commit"],
        "source_manifest_sha256": sha(manifest_path),
        "protocol_sha256": hashes["outputs/qshift_performance_sprint_v1/EXPERIMENT_PROTOCOL.md"],
        "config_sha256": hashes["outputs/qshift_performance_sprint_v1/config.json"],
        "seed_inventory_sha256": hashes["outputs/qshift_performance_sprint_v1/seed_inventory.json"],
        "source_files": hashes,
        "environment": versions,
        "sampling_authorization": "explicitly supplied by the current task for this bounded development pilot only",
    }
    (ROOT / "PRETEST_FREEZE.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"freeze": str(ROOT / "PRETEST_FREEZE.json"),
                      "source_manifest_sha256": sha(manifest_path),
                      "files": len(hashes), "environment": versions}, indent=2))


if __name__ == "__main__":
    main()