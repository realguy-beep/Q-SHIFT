"""Build a SHA-256 manifest for this feasibility prototype and read-only inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / "MANIFEST.json"
EXTERNAL_REFERENCES = [
    "outputs/phase2b_pauli_bias/CIRCUIT_VALIDATION.json",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/phase2b_pauli_bias/PHASE2B_PROTOCOL.md",
    "outputs/phase2b_pauli_bias/config.json",
    "outputs/phase2b_pauli_bias/PRETEST_FREEZE.json",
    "outputs/phase2b_pauli_bias/SHA256_MANIFEST.json",
    "outputs/dem_feasibility_gate/DEM_CONSTRUCTION_AUDIT.md",
    "outputs/dem_feasibility_gate/DEM_CONSTRUCTION_RESULTS.json",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    local = {}
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path == MANIFEST or "__pycache__" in path.parts:
            continue
        local[path.relative_to(HERE).as_posix()] = {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
    external = {}
    for relative in EXTERNAL_REFERENCES:
        path = ROOT / Path(relative)
        if path.is_file():
            external[relative] = {"sha256": sha256(path), "bytes": path.stat().st_size}
        else:
            external[relative] = {"status": "MISSING"}
    result = {
        "purpose": "Categorical decoder feasibility prototype evidence manifest",
        "local_files": local,
        "read_only_source_references": external,
        "execution_accounting": {
            "stochastic_shots_generated": 0,
            "deterministic_forced_fault_configurations_checked_by_stim": 320,
            "phase2b_evaluation_shots_generated": 0,
        },
        "historical_artifacts_modified": [],
    }
    MANIFEST.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST}")
    print(f"Hashed {len(local)} local files and {sum(v.get('status') != 'MISSING' for v in external.values())}/{len(external)} external references")


if __name__ == "__main__":
    main()
