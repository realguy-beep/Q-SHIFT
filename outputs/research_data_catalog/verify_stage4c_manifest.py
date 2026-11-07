"""Read-only SHA-256 verifier for the explicitly scoped Stage 4C manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "outputs/stage4c_cnn_noise_estimation_v1/EVIDENCE_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad = []
    for relative, expected in manifest["files_sha256"].items():
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            bad.append(f"unsafe manifest path: {relative}")
            continue
        path = ROOT / rel
        if not path.is_file():
            bad.append(f"missing: {relative}")
        elif sha256(path) != expected:
            bad.append(f"hash mismatch: {relative}")
    named_raw = manifest["raw_evidence_files_local_ignored"]
    if any("independent_test" in p.lower() or "sealed_test" in p.lower() for p in named_raw):
        bad.append("manifest raw evidence scope unexpectedly mentions sealed-test material")
    freeze = ROOT / "outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json"
    if sha256(freeze) != manifest["freeze_sha256"]:
        bad.append("Stage 4C freeze hash mismatch")
    if manifest["audit_status"] != "PASS" or manifest["independent_test_accessed"] is not False:
        bad.append("manifest audit or test-seal status is not acceptable")
    if manifest["total_unique_shots"] != 277_500 or manifest["completed_evaluation_roots"] != 35:
        bad.append("manifest shot/root totals differ from the completed Stage 4C allocation")
    if bad:
        raise SystemExit("FAIL\n" + "\n".join(bad))
    print(f"PASS Stage 4C evidence manifest: {len(manifest['files_sha256'])} hashes, "
          f"{len(named_raw)} local raw files, {manifest['total_unique_shots']} shots, "
          f"{manifest['completed_evaluation_roots']} evaluation roots")


if __name__ == "__main__":
    main()
