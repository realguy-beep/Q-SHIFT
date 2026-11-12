"""Create the lightweight NS-1 source/documentation engineering manifest."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE_COMMIT = "022588c7e9513d923da0b7f342a6199e34873b38"
PATHS = [
    "qshift_core_v1/circuit_identity.py",
    "dashboard/tests/test_circuit_identity_v1.py",
    "qshift_core_v1/contracts.py",
    "qshift_core_v1/controller.py",
    "qshift_core_v1/evaluation.py",
    "dashboard/simulator.py",
    "dashboard/configuration.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/phase2b_pauli_bias/decoder_bank.py",
    "outputs/phase2b_pauli_bias/CALIBRATION_SELECTION.json",
    "outputs/core_system_upgrade_v1_1/NS0_ENGINEERING_READINESS.md",
    "outputs/core_system_upgrade_v1_1/V2_4_HOLD_CONFIRMATION.md",
    "outputs/core_system_upgrade_v1_1/V2_4_HOLD_AUDIT.json",
    "outputs/core_system_upgrade_v1_1/MANIFEST.json",
    "outputs/core_system_upgrade_ns1_v1/NS1_CIRCUIT_IDENTITY_CONTRACT.md",
    "outputs/core_system_upgrade_ns1_v1/NS1_COMPATIBILITY_TEST_REPORT.md",
    "outputs/core_system_upgrade_ns1_v1/NS1_EXTERNAL_DECODER_INTERFACE.md",
    "outputs/core_system_upgrade_ns1_v1/NS1_UNRESOLVED_QUESTIONS.md",
    "outputs/core_system_upgrade_ns1_v1/REPRODUCE.md",
    "outputs/core_system_upgrade_ns1_v1/NS1_EVIDENCE_SCOPE_INCIDENT_REPORT.md",
    "outputs/core_system_upgrade_ns1_v1/NS1_CONTROLLED_RECOVERY_REPORT.md",
    "outputs/core_system_upgrade_ns1_v1/NS1_ENGINEERING_MANIFEST.json",
    "outputs/core_system_upgrade_ns1_v1/create_manifest.py",
    "outputs/core_system_upgrade_ns1_v1/verify_manifest.py",
]


def sha256(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".py", ".md", ".json", ".txt"}:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    files = []
    for relative in PATHS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Required NS-1 manifest input is missing: {relative}")
        normalized_size = path.stat().st_size
        if path.suffix.lower() in {".py", ".md", ".json", ".txt"}:
            normalized_size = len(path.read_bytes().replace(b"\r\n", b"\n"))
        files.append({"path": relative, "sha256": sha256(path), "bytes": normalized_size})
    try:
        import numpy
        import pymatching
        import stim
        versions = {"python": sys.version.split()[0], "platform": platform.platform(),
                    "numpy": numpy.__version__, "pymatching": pymatching.__version__,
                    "stim": stim.__version__}
    except ImportError as exc:
        raise RuntimeError("Create this manifest in the installed Q-SHIFT project environment.") from exc
    manifest = {
        "schema_version": 2,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "workstream": "NS-1 circuit identity and decoder compatibility engineering",
        "branch_base_commit": BASE_COMMIT,
        "status": "engineering-only; evidence-scope deviation disclosed; no sampling or decoder experiment",
        "sampling_performed": False,
        "training_performed": False,
        "search_output_contained_protected_outcome_content": False,
        "complete_protected_non_access_established": False,
        "accessed_file_inventory": "unknown; see NS1_EVIDENCE_SCOPE_INCIDENT_REPORT.md",
        "evidence_scope_deviation_disclosed": True,
        "v2_4_status": "HOLD; historical evidence not modified",
        "runtime_versions": versions,
        "files": files,
        "manifest_note": "Explicit source/documentation allowlist only; this is not a scientific freeze. It records the incident disclosure and does not assert that protected data were not accessed. REVIEW_HANDOFF.md is outside this local incident package.",
    }
    target = OUT / "NS1_ENGINEERING_MANIFEST_V2.json"
    temporary = target.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temporary.replace(target)
    print(f"Wrote {target} with {len(files)} SHA-256 entries.")


if __name__ == "__main__":
    main()
