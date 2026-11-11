"""Audit and copy a committed partial run into an isolated resume directory.

This utility samples nothing. It fails closed on any uncommitted, malformed,
unexpected, duplicated, or modified source artifact before creating the target.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pymatching

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from freeze_pretest import verify_freeze
from experiment_core import atomic_json


PARTITIONS = {
    "templates": ("profile_template", "templates", 20_000, "detectors"),
    "selection_calibration": ("calibration", "selection", 2_000, "calibration"),
    "selection": ("scoring", "selection", 2_500, "scoring"),
    "selection_predictions": ("scoring", "selection", 2_500, "predictions"),
    "validation_calibration": ("calibration", "validation", 2_000, "calibration"),
    "validation": ("scoring", "validation", 2_500, "scoring"),
    "validation_predictions": ("scoring", "validation", 2_500, "predictions"),
    "heldout_development_calibration": ("calibration", "heldout_development", 2_000, "calibration"),
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def seed_row(inv: dict, role: str, split: str, p: float | None, root: int | None) -> dict:
    rows = [s for s in inv["streams"] if s["role"] == role and s["split"] == split and s["root"] == root
            and (s["probability"] is None if p is None else float(s["probability"]) == float(p))]
    if len(rows) != 1:
        raise ValueError(f"seed inventory mapping is not unique: {role}/{split}/{p}/{root}")
    return rows[0]


def build_candidate_models(cfg: dict) -> tuple[list[float], list[pymatching.Matching]]:
    c = cfg["circuit"]
    d = c["dem"]
    probabilities = list(map(float, cfg["decoders"]["static_candidate_grid"]))
    models = []
    for q in probabilities:
        circuit = build_spatial_burst_circuit(
            memory_basis=c["memory_basis"], regime=c["regime"], distance=int(c["distance"]),
            rounds=int(c["rounds"]), gate_p=float(c["gate_p"]), measurement_p=float(c["measurement_p"]),
            bias_ratio=float(c["bias_ratio"]), burst_probability=q, burst_pair=tuple(c["burst_pair"]),
        )
        dem = circuit.detector_error_model(
            decompose_errors=bool(d["decompose_errors"]),
            approximate_disjoint_errors=bool(d["approximate_disjoint_errors"]),
        )
        if (circuit.num_detectors, circuit.num_observables) != (40, 1):
            raise ValueError("candidate model circuit has unexpected detector/observable dimensions")
        models.append(pymatching.Matching.from_detector_error_model(
            dem, enable_correlations=bool(d["enable_correlations"])))
    return probabilities, models


def audit_source(source: Path, cfg: dict, inv: dict) -> dict:
    if (source / ".run.lock").exists():
        raise RuntimeError("source run still has a lock; do not copy a live run")
    status_path = source / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") not in {"running", "failed"} or int(status.get("final_evaluation_shots", 0)) != 0:
        raise RuntimeError("source status is not the expected incomplete pre-evaluation state")
    for path in source.rglob("*"):
        if path.is_file() and (path.name.endswith(".tmp") or path.name.endswith(".copying")):
            raise RuntimeError(f"source contains a temporary file: {path}")
    npz_files = sorted(source.rglob("*.npz"))
    if any(path.relative_to(source).parts[0] == "evaluation" for path in npz_files):
        raise RuntimeError("source unexpectedly contains final evaluation samples")
    probs, models = build_candidate_models(cfg)
    score_rows: dict[str, dict[tuple[float, int], dict]] = {}
    score_records = {}
    for partition in ("selection", "validation"):
        path = source / f"{partition}_scores.json"
        if not path.is_file():
            raise RuntimeError(f"missing completed {partition} score record")
        record = json.loads(path.read_text(encoding="utf-8"))
        rows = record.get("per_root", [])
        score_rows[partition] = {(float(r["probability"]), int(r["root"])): r for r in rows}
        if len(score_rows[partition]) != len(rows) or len(rows) != len(cfg["circuit"]["probabilities"]) * int(cfg["partitions"][f"{partition}_roots_per_condition"]):
            raise RuntimeError(f"{partition} score rows have duplicate or missing roots")
        score_records[partition] = record

    hashes: dict[str, str] = {"status.json": sha(status_path)}
    stream_shots: dict[int, int] = {}
    predictions_redecoded = 0
    archive_inventory = []
    files = set(npz_files)
    if not npz_files:
        raise RuntimeError("source has no committed arrays")
    for path in npz_files:
        rel = path.relative_to(source)
        if not rel.parts or rel.parts[0] not in PARTITIONS:
            raise RuntimeError(f"unexpected source archive partition: {rel}")
        partition = rel.parts[0]
        role, split, shots, kind = PARTITIONS[partition]
        marker = path.with_suffix(path.suffix + ".commit.json")
        if not marker.is_file():
            raise RuntimeError(f"uncommitted source archive: {rel}")
        marker_data = json.loads(marker.read_text(encoding="utf-8"))
        digest = sha(path)
        marker_digest = sha(marker)
        if marker_data.get("sha256") != digest:
            raise RuntimeError(f"source archive hash mismatch: {rel}")
        with np.load(path, allow_pickle=False) as z:
            arrays = {name: z[name] for name in z.files}
        meta = json.loads(str(arrays.pop("metadata_json").item()))
        if marker_data.get("metadata") != meta or meta.get("partition") != partition or int(meta.get("shots", -1)) != shots:
            raise RuntimeError(f"source metadata/marker mismatch: {rel}")
        p = None if meta.get("probability") is None else float(meta["probability"])
        root = None if meta.get("root") is None else int(meta["root"])
        expected_seed = seed_row(inv, role, split, p, root)
        if int(meta.get("seed", -1)) != int(expected_seed["seed"]):
            raise RuntimeError(f"source seed mapping mismatch: {rel}")
        seed = int(expected_seed["seed"])
        if kind == "predictions":
            source_partition = "selection" if partition.startswith("selection") else "validation"
            sample_path = source / source_partition / f"p_{p:.3f}" / f"root_{root:03d}.npz"
            with np.load(sample_path, allow_pickle=False) as z:
                sample_d, sample_o = z["detectors"], z["observable"]
            d, o, pred = arrays.get("detectors"), arrays.get("observable"), arrays.get("candidate_predictions")
            if d is None or o is None or pred is None or pred.shape != (len(probs), shots):
                raise RuntimeError(f"candidate prediction shape invalid: {rel}")
            if not np.array_equal(d, sample_d) or not np.array_equal(o, sample_o):
                raise RuntimeError(f"candidate predictions are not paired to source scoring samples: {rel}")
            if meta.get("source_archive_sha256") != sha(sample_path):
                raise RuntimeError(f"prediction source hash mismatch: {rel}")
            independently_decoded = np.stack([np.asarray(m.decode_batch(d)).reshape(-1).astype(np.uint8) for m in models])
            if not np.array_equal(pred, independently_decoded):
                raise RuntimeError(f"candidate prediction re-decode mismatch: {rel}")
            row = score_rows[source_partition][(p, root)]
            errors = (pred ^ o[None, :]).sum(axis=1).astype(int).tolist()
            if row.get("errors_by_grid") != errors:
                raise RuntimeError(f"saved score row mismatch: {rel}")
            predictions_redecoded += int(pred.size)
        else:
            d = arrays.get("detectors")
            if d is None or d.shape != (shots, 40) or not np.isin(d, (0, 1)).all():
                raise RuntimeError(f"detector array invalid: {rel}")
            if kind == "scoring":
                o = arrays.get("observable")
                if o is None or o.shape != (shots,) or not np.isin(o, (0, 1)).all():
                    raise RuntimeError(f"observable array invalid: {rel}")
            if seed in stream_shots:
                raise RuntimeError(f"duplicate source sample seed: {seed}")
            stream_shots[seed] = shots
        hashes[str(rel)] = digest
        hashes[str(rel) + ".commit.json"] = marker_digest
        archive_inventory.append({"path": str(rel), "sha256": digest, "marker_sha256": marker_digest,
                                 "partition": partition, "seed": seed, "shots": shots})
    for partition in ("selection", "validation"):
        actual_totals = {q: {"errors": 0, "shots": 0} for q in probs}
        for (p, root), row in score_rows[partition].items():
            pred_path = source / f"{partition}_predictions" / f"p_{p:.3f}" / f"root_{root:03d}.npz"
            with np.load(pred_path, allow_pickle=False) as z:
                n = int(z["observable"].size)
                err = (z["candidate_predictions"] ^ z["observable"][None, :]).sum(axis=1).astype(int)
            for i, q in enumerate(probs):
                actual_totals[q]["errors"] += int(err[i])
                actual_totals[q]["shots"] += n
        saved_totals = score_records[partition].get("totals", {})
        for q in probs:
            saved = saved_totals.get(str(q), {})
            if int(saved.get("errors", -1)) != actual_totals[q]["errors"] or int(saved.get("shots", -1)) != actual_totals[q]["shots"]:
                raise RuntimeError(f"{partition} aggregate score mismatch for candidate p={q}")
    expected_roots = int(cfg["partitions"]["selection_roots_per_condition"])
    if sum(1 for r in score_rows["selection"] if r[0] == 0.0) != expected_roots:
        raise RuntimeError("selection zero-burst root count mismatch")
    total_unique_shots = sum(stream_shots.values())
    if len(npz_files) != 958 or len(stream_shots) != 758 or total_unique_shots != 1_670_000:
        raise RuntimeError(f"partial run coverage mismatch: {len(npz_files)} archives, {len(stream_shots)} sample streams, {total_unique_shots} shots")
    if predictions_redecoded != 4_500_000:
        raise RuntimeError(f"candidate prediction verification coverage mismatch: {predictions_redecoded}")
    hashes["selection_scores.json"] = sha(source / "selection_scores.json")
    hashes["validation_scores.json"] = sha(source / "validation_scores.json")
    hashes["BASELINE_SELECTION_FREEZE.json"] = sha(source / "BASELINE_SELECTION_FREEZE.json")
    hashes["RECOVERY_PROVENANCE.json"] = sha(source / "RECOVERY_PROVENANCE.json")
    return {
        "audit_status": "PASS_INCOMPLETE_NO_FINAL_EVALUATION",
        "source_run": str(source),
        "source_status": status,
        "archive_count": len(npz_files),
        "committed_archive_and_marker_count": len(archive_inventory),
        "unique_sample_streams": len(stream_shots),
        "unique_sample_shots": total_unique_shots,
        "candidate_grid": probs,
        "selection_roots": len(score_rows["selection"]),
        "validation_roots": len(score_rows["validation"]),
        "candidate_prediction_values_independently_redecoded": predictions_redecoded,
        "final_evaluation_shots": 0,
        "archive_inventory": archive_inventory,
        "file_sha256": hashes,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=HERE / "run_recovery_v3")
    parser.add_argument("--target", type=Path, default=HERE / "run_recovery_v4")
    args = parser.parse_args()
    verify_freeze()
    source, target = args.source.resolve(), args.target.resolve()
    if target.exists():
        raise FileExistsError(f"recovery target must be absent: {target}")
    cfg = json.loads((HERE / "experiment_config.json").read_text(encoding="utf-8"))
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    audit = audit_source(source, cfg, inv)
    audit_path = HERE / "RECOVERY_V3_INDEPENDENT_AUDIT.json"
    if audit_path.exists():
        if json.loads(audit_path.read_text(encoding="utf-8")) != json.loads(json.dumps(audit, sort_keys=True, allow_nan=False)):
            raise RuntimeError(f"immutable recovery audit differs from source: {audit_path}")
    else:
        atomic_json(audit_path, audit)
    source_files = [p for p in source.rglob("*") if p.is_file() and p.name != ".run.lock"]
    target.mkdir(parents=True)
    copied = []
    try:
        for src in source_files:
            rel = src.relative_to(source)
            if rel.as_posix() in {"status.json"}:
                continue
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            if sha(src) != sha(dest):
                raise RuntimeError(f"recovery copy hash mismatch: {rel}")
            copied.append({"path": str(rel), "sha256": sha(src)})
        source_status = json.loads((source / "status.json").read_text(encoding="utf-8"))
        source_status_sha = sha(source / "status.json")
        recovered_status = dict(source_status)
        recovered_status.update({"status": "ready_to_resume", "phase": "recovery_copy_verified",
                                 "recovered_from": source.name,
                                 "recovery_source_status_sha256": source_status_sha,
                                 "final_evaluation_shots": 0, "updated_unix": time.time()})
        atomic_json(target / "status.json", recovered_status)
        copy_manifest = {
            "status": "COPY_VERIFIED_NO_SAMPLING",
            "source_run": source.name,
            "source_status_sha256": source_status_sha,
            "source_audit_sha256": sha(audit_path),
            "active_freeze": "PRETEST_FREEZE_V14.json",
            "copied_files": copied,
            "recovered_status_sha256": sha(target / "status.json"),
            "reused_unique_sample_streams": audit["unique_sample_streams"],
            "reused_unique_sample_shots": audit["unique_sample_shots"],
            "new_shots_generated": 0,
            "final_evaluation_shots": 0,
            "sealed_test_access": False,
        }
        atomic_json(target / "RECOVERY_COPY_MANIFEST.json", copy_manifest)
        print(json.dumps({"status": copy_manifest["status"], "source_audit": str(audit_path),
                          "archive_count": audit["archive_count"], "unique_shots": audit["unique_sample_shots"],
                          "redecoded_predictions": audit["candidate_prediction_values_independently_redecoded"],
                          "target": str(target)}, indent=2))
    except Exception:
        raise


if __name__ == "__main__":
    main()
