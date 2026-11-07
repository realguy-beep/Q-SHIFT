"""Hash this feasibility audit and verify referenced historical manifests."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PILOT = ROOT / "outputs" / "correlation_pilot"
MECHANISM = ROOT / "outputs" / "correlation_mechanism_audit"
PHASE2B = ROOT / "outputs" / "phase2b_pauli_bias"
MANIFEST_PATH = OUT / "MANIFEST.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def add_file(store: dict[str, dict], path: Path, kind: str, expected: str | None = None) -> None:
    rel = path.relative_to(ROOT).as_posix()
    actual = sha256(path) if path.is_file() else None
    store[rel] = {"path": rel, "kind": kind, "expected_sha256": expected,
                  "actual_sha256": actual,
                  "matches": actual == expected if expected is not None else actual is not None,
                  "size_bytes": path.stat().st_size if path.is_file() else None}


def main() -> None:
    evidence: dict[str, dict] = {}
    # Verify every file listed in the historical pilot manifest, not just the manifest file.
    pilot_manifest_path = PILOT / "MANIFEST.json"
    pilot_manifest = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    add_file(evidence, pilot_manifest_path, "historical_pilot_manifest")
    for item in pilot_manifest["files"]:
        path = PILOT / item["path"]
        add_file(evidence, path, "historical_pilot_artifact", item["sha256"])
    # Include all Phase 2B files recorded in the original pilot pre-test freeze.
    pilot_freeze = json.loads((PILOT / "PRETEST_FREEZE.json").read_text(encoding="utf-8"))
    add_file(evidence, PILOT / "PRETEST_FREEZE.json", "original_pilot_pretest_freeze")
    for rel, expected in pilot_freeze["sha256"].items():
        add_file(evidence, ROOT / rel, "original_frozen_dependency", expected)
    # Verify previous mechanism-audit manifest and all its hashed evidence/outputs.
    mechanism_manifest_path = MECHANISM / "MANIFEST.json"
    mechanism_manifest = json.loads(mechanism_manifest_path.read_text(encoding="utf-8"))
    add_file(evidence, mechanism_manifest_path, "prior_mechanism_audit_manifest")
    for item in mechanism_manifest["audit_outputs"]:
        add_file(evidence, MECHANISM / item["path"], "prior_mechanism_audit_output", item["sha256"])
    # Explicitly include the frozen Phase 2B model source and documentation.
    for name in ("noise_model.py", "decoder_bank.py", "config.json", "PHASE2B_PROTOCOL.md",
                 "CALIBRATION_SELECTION.json", "NOISE_MODEL_SPECIFICATION.md"):
        p = PHASE2B / name
        add_file(evidence, p, "phase2b_generator_or_protocol")

    mismatches = [p for p, e in evidence.items() if not e["matches"]]
    outputs = []
    for p in sorted(OUT.rglob("*")):
        if not p.is_file() or p == MANIFEST_PATH or "__pycache__" in p.parts or p.name.endswith(".tmp"):
            continue
        outputs.append({"path": p.relative_to(OUT).as_posix(), "size_bytes": p.stat().st_size,
                        "sha256": sha256(p)})
    data = {
        "status": "PASS_HASH_AUDIT" if not mismatches else "FAIL_HASH_AUDIT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "simulation_shots_generated": 0,
        "historical_pilot_modified": False,
        "prior_pilot_manifest_file_count": len(pilot_manifest["files"]),
        "prior_mechanism_manifest_output_count": len(mechanism_manifest["audit_outputs"]),
        "referenced_evidence_count_unique_paths": len(evidence),
        "hash_mismatches": mismatches,
        "referenced_evidence": list(evidence.values()),
        "new_output_count_excluding_manifest_and_pycache": len(outputs),
        "new_output_bytes": sum(x["size_bytes"] for x in outputs),
        "new_outputs": outputs,
        "manifest_self_hash": "excluded by definition; all other files in this directory are hashed"
    }
    tmp = MANIFEST_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST_PATH)
    print(json.dumps({"status": data["status"], "evidence_paths": len(evidence),
                      "mismatches": len(mismatches), "outputs": len(outputs),
                      "pilot_files": len(pilot_manifest["files"])}, indent=2))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
