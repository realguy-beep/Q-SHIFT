"""Read-only forensic audit of the failed initial run; never writes in run/."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pymatching

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path, expect: dict):
    marker_path = path.with_suffix(path.suffix + ".commit.json")
    if not path.is_file() or not marker_path.is_file():
        raise ValueError(f"missing committed sample archive: {path}")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    digest = sha(path)
    if marker.get("sha256") != digest:
        raise ValueError(f"archive hash mismatch: {path}")
    with np.load(path, allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    meta = json.loads(str(arrays.pop("metadata_json").item()))
    if marker.get("metadata") != meta or any(meta.get(k) != v for k, v in expect.items()):
        raise ValueError(f"archive metadata mismatch: {path}")
    return arrays, meta, digest, sha(marker_path)


def matcher(p: float, cfg: dict):
    c = cfg["circuit"]
    circuit = build_spatial_burst_circuit(
        memory_basis=c["memory_basis"], regime=c["regime"], distance=c["distance"], rounds=c["rounds"],
        gate_p=c["gate_p"], measurement_p=c["measurement_p"], bias_ratio=c["bias_ratio"],
        burst_probability=float(p), burst_pair=tuple(c["burst_pair"]),
    )
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    return pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)


def main() -> None:
    run = HERE / "run"
    outdir = HERE / "partial_failure_audit"
    outdir.mkdir(exist_ok=True)
    out = outdir / "FAILED_RUN_PARTIAL_AUDIT.json"
    if out.exists():
        raise FileExistsError(f"preserved partial audit already exists: {out}")
    cfg = json.loads((HERE / "experiment_config.json").read_text(encoding="utf-8"))
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    status_path = run / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") != "failed" or status.get("error_type") != "IndexError":
        raise ValueError("run status does not match the preserved failure being audited")
    pvals = list(map(float, cfg["circuit"]["probabilities"]))
    samples = []
    wrong_predictions = []
    hashes = {"status.json": sha(status_path)}
    unique = 0
    for p in map(float, cfg["decoders"]["profile_template_probabilities"]):
        seed = next(s for s in inv["streams"] if s["role"] == "profile_template" and float(s["probability"]) == p)
        path = run / "templates" / f"p_{p:.3f}.npz"
        a, meta, digest, marker_sha = load(path, {"partition": "templates", "probability": p, "root": None, "seed": int(seed["seed"]), "shots": 20_000})
        if a["detectors"].shape != (20_000, 40) or not np.isin(a["detectors"], (0, 1)).all():
            raise ValueError(f"template array invalid: {path}")
        unique += 20_000
        hashes[str(path.relative_to(HERE))] = digest
        hashes[str(path.relative_to(HERE)) + ".commit.json"] = marker_sha
    for p in pvals:
        for root in range(20):
            cal_seed = next(s for s in inv["streams"] if s["role"] == "calibration" and s["split"] == "selection" and float(s["probability"]) == p and s["root"] == root)
            score_seed = next(s for s in inv["streams"] if s["role"] == "scoring" and s["split"] == "selection" and float(s["probability"]) == p and s["root"] == root)
            cal_path = run / "selection_calibration" / f"p_{p:.3f}" / f"root_{root:03d}.npz"
            score_path = run / "selection" / f"p_{p:.3f}" / f"root_{root:03d}.npz"
            ca, _, ch, cmh = load(cal_path, {"partition": "selection_calibration", "probability": p, "root": root, "seed": int(cal_seed["seed"]), "shots": 2000})
            sc, _, sh, smh = load(score_path, {"partition": "selection", "probability": p, "root": root, "seed": int(score_seed["seed"]), "shots": 2500})
            if ca["detectors"].shape != (2000, 40) or sc["detectors"].shape != (2500, 40) or sc["observable"].shape != (2500,):
                raise ValueError("committed selection arrays have unexpected dimensions")
            if not np.isin(ca["detectors"], (0, 1)).all() or not np.isin(sc["detectors"], (0, 1)).all() or not np.isin(sc["observable"], (0, 1)).all():
                raise ValueError("non-binary committed selection array")
            unique += 4500
            pred_path = run / "selection_predictions" / f"p_{p:.3f}" / f"root_{root:03d}.npz"
            pr, _, ph, pmh = load(pred_path, {"partition": "selection_predictions", "probability": p, "root": root, "seed": int(score_seed["seed"]), "shots": 2500})
            if pr["candidate_predictions"].shape != (5, 2500):
                raise ValueError(f"expected preserved five-arm buggy output at {pred_path}")
            if not np.array_equal(pr["detectors"], sc["detectors"]) or not np.array_equal(pr["observable"], sc["observable"]):
                raise ValueError(f"prediction rows are not aligned to source sample: {pred_path}")
            expected = np.stack([matcher(q, cfg).decode_batch(sc["detectors"]).reshape(-1).astype(np.uint8) for q in pvals])
            if not np.array_equal(pr["candidate_predictions"], expected):
                raise ValueError(f"stored five-arm predictions cannot be independently reproduced: {pred_path}")
            wrong_predictions.append({"p": p, "root": root, "shape": list(pr["candidate_predictions"].shape), "sha256": ph})
            for path, digest, marker_sha in ((cal_path,ch,cmh),(score_path,sh,smh),(pred_path,ph,pmh)):
                hashes[str(path.relative_to(HERE))] = digest
                hashes[str(path.relative_to(HERE)) + ".commit.json"] = marker_sha
    score_json = run / "selection_scores.json"
    hashes[str(score_json.relative_to(HERE))] = sha(score_json)
    npz = list(run.rglob("*.npz"))
    if len(npz) != 303 or len(wrong_predictions) != 100 or unique != 510_000:
        raise ValueError(f"partial run coverage mismatch: npz={len(npz)}, wrongpred={len(wrong_predictions)}, shots={unique}")
    if (run / "validation").exists() or (run / "evaluation").exists():
        raise ValueError("unexpected validation or final evaluation archives present")
    result = {
        "audit_status": "RAW_SELECTION_STREAMS_VALID_PREDICTION_SCHEMA_INVALID",
        "original_status_preserved": status,
        "unique_sample_shots_verified": unique,
        "archive_counts": {"templates": 3, "selection_calibration": 100, "selection_samples": 100,
                           "invalid_five_arm_prediction_archives": len(wrong_predictions), "all_npz": len(npz)},
        "study_final_evaluation_shots": 0,
        "validation_shots": 0,
        "bug_diagnosis": "runner passed five generating-condition p values into candidate decoder scoring, producing shape (5,2500) instead of frozen candidate-grid shape (9,2500); index failure occurred before baseline selection",
        "wrong_prediction_archives": wrong_predictions,
        "file_sha256": hashes,
        "recovery_policy": "leave original run untouched; copy only verified template and selection calibration/scoring sample archives to a distinct recovery directory; recompute candidate predictions from all nine frozen DEMs there; never copy or overwrite the invalid prediction outputs or selection_scores.json",
    }
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("audit_status", "unique_sample_shots_verified", "archive_counts", "study_final_evaluation_shots")}, indent=2))


if __name__ == "__main__":
    main()
