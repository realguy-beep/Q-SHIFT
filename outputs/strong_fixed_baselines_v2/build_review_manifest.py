"""Build a lightweight source/documentation review manifest without sampling."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "REVIEW_CORRECTION_MANIFEST.json"

CURRENT_FILES = [
    "AGENTS.md",
    "outputs/strong_fixed_baselines_v2/README.md",
    "outputs/strong_fixed_baselines_v2/experiment_config_v2.json",
    "outputs/strong_fixed_baselines_v2/freeze_pretest_v2.py",
    "outputs/strong_fixed_baselines_v2/pooled_calibration_v2.py",
    "outputs/strong_fixed_baselines_v2/run_development_v2.py",
    "outputs/strong_fixed_baselines_v2/test_pooled_calibration_v2.py",
    "outputs/strong_fixed_baselines_v2/PROSPECTIVE_REPLICATION_PLAN_V1.md",
    "outputs/strong_fixed_baselines_v2/REVIEW_CORRECTIONS_V1.md",
    "outputs/strong_fixed_baselines_v2/build_review_manifest.py",
]
HISTORICAL_FILES = [
    "outputs/strong_fixed_baselines_v1/PRETEST_FREEZE_V14.json",
    "outputs/strong_fixed_baselines_v1/FINAL_EVIDENCE_MANIFEST.json",
    "outputs/strong_fixed_baselines_v1/POSTRUN_RECONSTRUCTION_FREEZE_V1.json",
    "outputs/strong_fixed_baselines_v1/POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json",
    "outputs/strong_fixed_baselines_v1/POSTRUN_RECONSTRUCTION_PROTOCOL_V1.md",
    "outputs/strong_fixed_baselines_v1/run_development.py",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def file_records(paths: list[str]) -> dict[str, dict[str, object]]:
    records = {}
    for rel in paths:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"required review artifact is missing: {rel}")
        records[rel] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    return records


def main() -> None:
    v14_path = ROOT / "outputs/strong_fixed_baselines_v1/PRETEST_FREEZE_V14.json"
    v14 = json.loads(v14_path.read_text(encoding="utf-8"))
    expected = v14.get("sha256", {}).get("outputs/strong_fixed_baselines_v1/run_development.py")
    actual = sha256(ROOT / "outputs/strong_fixed_baselines_v1/run_development.py")
    result = {
        "schema_version": 1,
        "purpose": "source-and-documentation review checkpoint; not a run-data re-audit",
        "reviewed_pr": "https://github.com/realguy-beep/Q-SHIFT/pull/1",
        "reviewed_commit": "2dad2f37456886ee32a6b3b1e05511f2ec5df893",
        "supervisor_comment": "https://github.com/realguy-beep/Q-SHIFT/pull/1#issuecomment-6796430085",
        "sampling_performed": False,
        "v2_sampling_authorized": False,
        "sealed_test_access": False,
        "raw_npz_replay_performed": False,
        "v2_seed_inventory_present": (ROOT / "outputs/strong_fixed_baselines_v2/seed_inventory_v2.json").exists(),
        "v2_pretest_freeze_present": (ROOT / "outputs/strong_fixed_baselines_v2/PRETEST_FREEZE_V2.json").exists(),
        "current_review_files": file_records(CURRENT_FILES),
        "historical_evidence_references": file_records(HISTORICAL_FILES),
        "historical_v1_runner_hash_check": {
            "expected_sha256_from_v14": expected,
            "observed_sha256": actual,
            "matches": expected == actual,
        },
        "limitations": [
            "Historical run archives are local/ignored and were not opened or rehashed in this source-only review.",
            "The existing evidence manifest and saved-array audit retain per-file hashes and reconstruction commands.",
            "This manifest does not certify a fresh replay of the historical NPZ evidence.",
        ],
    }
    if not result["historical_v1_runner_hash_check"]["matches"]:
        raise RuntimeError("historical v1 runner no longer matches the V14 hash")
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"current files hashed: {len(result['current_review_files'])}")
    print(f"historical references hashed: {len(result['historical_evidence_references'])}")
    print(f"v1 runner V14 hash match: {result['historical_v1_runner_hash_check']['matches']}")


if __name__ == "__main__":
    main()
