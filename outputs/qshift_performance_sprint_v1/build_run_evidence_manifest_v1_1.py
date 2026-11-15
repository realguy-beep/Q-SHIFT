"""Hash committed summaries and local raw archives after the V1.1 run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
RECOVERY = SAMPLES / "recovery_v1_1"
OUTPUT = ROOT / "RUN_EVIDENCE_MANIFEST_V1_1_FINAL.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build() -> dict:
    expected_recovery = {"status.json", "run_start.json"}
    for i in range(5):
        for root in range(10):
            stem = f"eval_p{i}_r{root:02d}"
            expected_recovery.update({f"{stem}.npz", f"{stem}.commit.json"})
    actual_recovery = {p.name for p in RECOVERY.iterdir() if p.is_file()}
    if actual_recovery != expected_recovery:
        raise RuntimeError(f"unexpected recovery evidence files: {sorted(actual_recovery ^ expected_recovery)}")
    expected_original = {"status.json", "run_start.json", "trained_estimator.json", "training_detector_only.npz"}
    expected_original.update({f"cal_p{i}_r{root:02d}.npz" for i in range(5) for root in range(10)})
    actual_original = {p.name for p in SAMPLES.iterdir() if p.is_file()}
    if actual_original != expected_original:
        raise RuntimeError(f"original failed attempt contains unexpected/missing files: {sorted(actual_original ^ expected_original)}")
    paths = [
        ROOT / "EXPERIMENT_PROTOCOL.md", ROOT / "RECOVERY_V1_1_OPERATIONAL_AMENDMENT.md",
        ROOT / "RECOVERY_INPUT_INVENTORY_V1_1.json", ROOT / "RECOVERY_SOURCE_MANIFEST_V1_1.json",
        ROOT / "RECOVERY_SOURCE_MANIFEST_V1_1_PREVALIDATION.json", ROOT / "source_manifest.json",
        ROOT / "PRETEST_FREEZE.json", ROOT / "config.json", ROOT / "seed_inventory.json",
        ROOT / "calibration_estimates.json", ROOT / "root_results_v1_1.csv",
        ROOT / "analysis_v1_1.json", ROOT / "independent_audit_v1_1.json",
        ROOT / "PERFORMANCE_REPORT.md", ROOT / "REPRODUCE_V1_1.md", ROOT / "LIMITATIONS_V1_1.md",
        ROOT / "POSTRUN_VALIDATION_V1_1.md", ROOT / "tests" / "test_results_v1_1.py",
    ]
    paths.extend(SAMPLES / name for name in sorted(expected_original))
    paths.extend(RECOVERY / name for name in sorted(expected_recovery))
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise RuntimeError(f"evidence file missing: {missing}")
    entries = {}
    for path in paths:
        rel = path.relative_to(ROOT.parent.parent).as_posix()
        entries[rel] = {"sha256": digest(path), "bytes": path.stat().st_size,
                        "git_tracked": not ("/samples/" in f"/{rel}/")}
    manifest = {
        "schema": "qshift-performance-run-evidence-manifest-v1.1",
        "classification": "development-only; raw sample archives remain local and ignored",
        "execution_source_commit": "5e4af92b7730cf471d05fcd3af5baa75248539d3",
        "original_failed_status_sha256": digest(SAMPLES / "status.json"),
        "recovery_status_sha256": digest(RECOVERY / "status.json"),
        "recovery_unique_partition_count": 105,
        "recovery_unique_persisted_rows": 130000,
        "cumulative_sampler_calls": 106,
        "cumulative_returned_rows_including_replay": 132000,
        "evidence_builder_sha256": digest(Path(__file__)),
        "files": entries,
        "manifest_self_hash": "excluded",
    }
    if OUTPUT.exists():
        raise RuntimeError("evidence manifest already exists; refusing to overwrite")
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = build()
    print(json.dumps({"output": str(OUTPUT), "sha256": digest(OUTPUT),
                      "files": len(result["files"]), "bytes": sum(x["bytes"] for x in result["files"].values())}, indent=2))
