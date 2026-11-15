"""Copy only verified raw streams out of the preserved failed run."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def audit_key(path: Path, root: Path = HERE) -> str:
    """Match the native path spelling preserved by audit_partial_run.py."""
    return str(path.relative_to(root))


def seed_for(inv: dict, role: str, split: str, p: float | None, root: int | None) -> dict:
    hits = [s for s in inv["streams"] if s["role"] == role and s["split"] == split and s["root"] == root
            and (s["probability"] is None if p is None else float(s["probability"]) == float(p))]
    if len(hits) != 1:
        raise ValueError(f"seed mapping mismatch for {role}/{split}/{p}/{root}")
    return hits[0]


def verify_archive(src: Path, audit: dict, expected: dict, shape: tuple[int, ...]) -> dict:
    # Audit keys preserve the native Windows separators used when the audit
    # was written; do not normalize one side without normalizing both.
    rel = audit_key(src)
    recorded = audit["file_sha256"].get(rel)
    if not recorded or sha(src) != recorded:
        raise ValueError(f"partial audit hash mismatch: {src}")
    marker = src.with_suffix(src.suffix + ".commit.json")
    marker_rel = rel + ".commit.json"
    if audit["file_sha256"].get(marker_rel) != sha(marker):
        raise ValueError(f"partial marker hash mismatch: {marker}")
    m = json.loads(marker.read_text(encoding="utf-8"))
    with np.load(src, allow_pickle=False) as z:
        a = {k: z[k] for k in z.files}
    meta = json.loads(str(a.pop("metadata_json").item()))
    if m.get("sha256") != recorded or m.get("metadata") != meta or any(meta.get(k) != v for k, v in expected.items()):
        raise ValueError(f"source checkpoint metadata mismatch: {src}")
    if a["detectors"].shape != shape or not np.isin(a["detectors"], (0, 1)).all():
        raise ValueError(f"source detector shape/content invalid: {src}")
    if "observable" in a and (a["observable"].shape != (shape[0],) or not np.isin(a["observable"], (0, 1)).all()):
        raise ValueError(f"source observable shape/content invalid: {src}")
    return {"sha256": recorded, "marker_sha256": sha(marker), "shots": shape[0]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=HERE / "run")
    ap.add_argument("--target", type=Path, default=HERE / "run_recovery_v2")
    args = ap.parse_args()
    source, target = args.source.resolve(), args.target.resolve()
    partial_path = HERE / "partial_failure_audit" / "FAILED_RUN_PARTIAL_AUDIT.json"
    audit = json.loads(partial_path.read_text(encoding="utf-8"))
    if audit.get("audit_status") != "RAW_SELECTION_STREAMS_VALID_PREDICTION_SCHEMA_INVALID":
        raise ValueError("independent partial-run audit did not pass the expected classification")
    original_status = json.loads((source / "status.json").read_text(encoding="utf-8"))
    if original_status.get("status") != "failed":
        raise ValueError("original run must remain in failed status")
    cfg = json.loads((HERE / "experiment_config.json").read_text(encoding="utf-8"))
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    if target.exists() and (target / "RECOVERY_PROVENANCE.json").exists():
        raise FileExistsError("recovery provenance already exists; copy has already finalized")
    expected_target_files: set[str] = set()
    for p in map(float, cfg["decoders"]["profile_template_probabilities"]):
        rel = Path("templates") / f"p_{p:.3f}.npz"
        expected_target_files.update({str(rel), str(rel) + ".commit.json"})
    for p in map(float, cfg["circuit"]["probabilities"]):
        for root in range(int(cfg["partitions"]["selection_roots_per_condition"])):
            for partition in ("selection_calibration", "selection"):
                rel = Path(partition) / f"p_{p:.3f}" / f"root_{root:03d}.npz"
                expected_target_files.update({str(rel), str(rel) + ".commit.json"})
    if target.exists():
        actual = {str(path.relative_to(target)) for path in target.rglob("*") if path.is_file()}
        unexpected = actual - expected_target_files
        if unexpected:
            raise RuntimeError(f"recovery target contains unexpected files: {sorted(unexpected)[:5]}")
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    unique_shots = 0

    def copy_one(src: Path, dest: Path, expected: dict, shape: tuple[int, ...]) -> None:
        nonlocal unique_shots
        verified = verify_archive(src, audit, expected, shape)
        dest.parent.mkdir(parents=True, exist_ok=True)
        src_marker = src.with_suffix(src.suffix + ".commit.json")
        dest_marker = dest.with_suffix(dest.suffix + ".commit.json")
        if dest.exists() or dest_marker.exists():
            if not (dest.is_file() and dest_marker.is_file()):
                raise RuntimeError(f"partial recovery-copy pair is ambiguous: {dest}")
            if sha(dest) != verified["sha256"] or sha(dest_marker) != verified["marker_sha256"]:
                raise RuntimeError(f"existing recovery copy failed hash verification: {dest}")
        else:
            shutil.copy2(src, dest)
            shutil.copy2(src_marker, dest_marker)
        if sha(dest) != verified["sha256"] or sha(dest_marker) != verified["marker_sha256"]:
            raise RuntimeError(f"copy integrity mismatch: {dest}")
        copied.append({"source": str(src.relative_to(HERE)).replace("\\", "/"),
                       "target": str(dest.relative_to(target)).replace("\\", "/"),
                       **verified})
        unique_shots += verified["shots"]

    for p in map(float, cfg["decoders"]["profile_template_probabilities"]):
        seed = seed_for(inv, "profile_template", "templates", p, None)
        src = source / "templates" / f"p_{p:.3f}.npz"
        dst = target / "templates" / f"p_{p:.3f}.npz"
        copy_one(src, dst, {"partition": "templates", "probability": p, "root": None,
                           "seed": int(seed["seed"]), "shots": 20_000}, (20_000, 40))
    for p in map(float, cfg["circuit"]["probabilities"]):
        for root in range(int(cfg["partitions"]["selection_roots_per_condition"])):
            for role, partition, shots in (("calibration", "selection_calibration", 2000),
                                           ("scoring", "selection", 2500)):
                seed = seed_for(inv, role, "selection", p, root)
                src = source / partition / f"p_{p:.3f}" / f"root_{root:03d}.npz"
                dst = target / partition / f"p_{p:.3f}" / f"root_{root:03d}.npz"
                copy_one(src, dst, {"partition": partition, "probability": p, "root": root,
                                   "seed": int(seed["seed"]), "shots": shots}, (shots, 40))
    if unique_shots != 510_000 or len(copied) != 203:
        raise RuntimeError(f"recovery copy coverage mismatch: {unique_shots} shots, {len(copied)} archives")
    provenance = {
        "schema_version": 1,
        "recovery_copy_created_without_sampling": True,
        "original_run_status_preserved": True,
        # audit_partial_run.py intentionally stores status under this short key;
        # archive paths retain their run-relative native Windows spelling.
        "source_run_status_sha256": audit["file_sha256"]["status.json"],
        "source_partial_audit_sha256": sha(partial_path),
        "source_freeze_v6_sha256": sha(HERE / "PRETEST_FREEZE_V6.json"),
        "active_recovery_freeze": "PRETEST_FREEZE_V12.json",
        "copied_valid_unique_shots": unique_shots,
        "copied_archive_count": len(copied),
        "copied_raw_archive_hashes": copied,
        "excluded_source_outputs": {
            "selection_predictions": "100 preserved five-output arrays do not match the frozen nine-candidate bank; retained only in original failed directory, will be regenerated from copied detector samples in the recovery directory",
            "selection_scores.json": "hash preserved in original failure audit; invalid five-candidate aggregates are not copied",
            "status.json": "failed original run state is not copied; new status starts separately for the continuation",
        },
        "new_study_shots_generated_by_copy": 0,
        "stage5_shots_generated": 0,
        "sealed_test_access": False,
    }
    (target / "RECOVERY_PROVENANCE.json").write_text(json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "RECOVERY_COPY_READY_NO_SAMPLING", "copied_shots": unique_shots,
                      "copied_archives": len(copied), "target": str(target),
                      "source_untouched": True}, indent=2))


if __name__ == "__main__":
    main()
