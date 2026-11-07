"""Hash audit outputs and referenced pilot evidence without modifying sources."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PILOT = ROOT / "outputs" / "correlation_pilot"
PHASE2B = ROOT / "outputs" / "phase2b_pauli_bias"
MANIFEST = OUT / "MANIFEST.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def entry(path: Path, base: Path) -> dict:
    return {"path": path.relative_to(base).as_posix(),
            "size_bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> None:
    input_paths = [
        PILOT / "config.json", PILOT / "PILOT_EXECUTION_PROTOCOL.md",
        PILOT / "PRETEST_FREEZE.json", PILOT / "RESULTS.json",
        PILOT / "PER_ROOT_RESULTS.csv", PILOT / "PER_STRATUM_RESULTS.csv",
        PILOT / "DECODER_DISAGREEMENTS.csv", PILOT / "AGGREGATE_RECOMPUTATION.json",
        PILOT / "CHECKPOINT_HASHES.json", PILOT / "MANIFEST.json",
        PHASE2B / "config.json", PHASE2B / "PHASE2B_PROTOCOL.md",
        PHASE2B / "CALIBRATION_SELECTION.json", PHASE2B / "noise_model.py",
        PHASE2B / "decoder_bank.py", PHASE2B / "NOISE_MODEL_SPECIFICATION.md",
    ]
    input_paths += sorted((PILOT / "checkpoints").glob("*.npz"))
    input_paths += sorted((PHASE2B / "dems").glob("*.dem"))
    input_paths += sorted((PHASE2B / "dems").glob("*.stim"))
    missing = [str(p) for p in input_paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing referenced evidence: " + ", ".join(missing))
    outputs = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path == MANIFEST or "__pycache__" in path.parts or path.name.endswith(".tmp"):
            continue
        outputs.append(entry(path, OUT))
    data = {
        "audit_status": "PASS_READ_ONLY_SAVED_DATA_AUDIT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "pilot_modified": False,
        "new_simulation_shots": 0,
        "input_evidence_count": len(input_paths),
        "input_evidence": [entry(p, ROOT) for p in input_paths],
        "audit_output_count_excluding_manifest_and_pycache": len(outputs),
        "audit_output_bytes": sum(x["size_bytes"] for x in outputs),
        "audit_outputs": outputs,
        "manifest_self_hash": "excluded by definition; all other audit files are hashed",
        "coverage_note": "Hashes establish integrity for the listed files only. The audit relies on recovered pilot artifacts and cannot recreate unavailable latent fault histories or unrecorded historical RNG use."
    }
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)
    print(json.dumps({"status": data["audit_status"], "inputs": len(input_paths),
                      "outputs": len(outputs), "checkpoints": len(list((PILOT / "checkpoints").glob('*.npz'))),
                      "pilot_modified": False}, indent=2))


if __name__ == "__main__":
    main()
