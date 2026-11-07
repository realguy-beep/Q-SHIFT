"""Read-only audit of a completed dashboard run; creates no simulation shots."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from models import DirectMLP, ResidualMLP
from qshift_stats import compare_predictions
from simulator import decode_matching, model_identity, prepare


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(run_dir: Path) -> dict:
    run_dir = run_dir.resolve()
    cfg = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    evidence_path = run_dir / metadata["test_evidence_path"]
    checkpoint_path = run_dir / "checkpoint.pt"
    assert sha256_file(evidence_path) == metadata["test_evidence_sha256"], "test evidence SHA-256 mismatch"
    assert sha256_file(checkpoint_path) == metadata["checkpoint_sha256"], "checkpoint SHA-256 mismatch"
    plan = metadata["seed_plan"]
    assert metadata["seed_screen"]["passed"], "saved seed screen did not pass"
    assert plan["shots"] == {"train": cfg["training_shots"], "validation": cfg["validation_shots"], "test": cfg["test_shots"]}
    saved_inventory = json.loads((run_dir / "seed_inventory.json").read_text(encoding="utf-8"))
    assert saved_inventory["plan"] == plan and saved_inventory["screen"]["passed"]
    canonical_config = json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical_config).hexdigest() == metadata["config_sha256"], "canonical config hash mismatch"

    circuit, _, dem, matching, fixed_index, _ = prepare(cfg)
    identity = model_identity(circuit, dem)
    assert identity["circuit_sha256"] == metadata["circuit_sha256"], "circuit hash mismatch"
    assert identity["dem_sha256"] == metadata["dem_sha256"], "DEM hash mismatch"
    assert fixed_index == metadata["phase2b_fixed_decoder_index"], "fixed decoder index mismatch"

    with np.load(evidence_path, allow_pickle=False) as npz:
        evidence = {key: np.asarray(npz[key]) for key in npz.files}
    d, y = evidence["detectors"], evidence["observable"]
    n = int(cfg["test_shots"])
    assert d.shape == (n, circuit.num_detectors) and d.dtype == np.uint8
    assert y.shape == (n,) and y.dtype == np.uint8 and np.isin(y, [0, 1]).all()
    assert np.isin(d, [0, 1]).all()
    assert np.array_equal(evidence["identity_no_decode"], np.zeros(n, dtype=np.uint8))
    for key in ("pymatching", "direct_neural"):
        assert evidence[key].shape == (n,) and np.isin(evidence[key], [0, 1]).all(), f"invalid {key} array"
    stored_residual = evidence["pymatching_neural_residual"]
    if cfg["model_selection"] == "direct_plus_residual":
        assert stored_residual.shape == (n,) and np.isin(stored_residual, [0, 1]).all()
    else:
        assert stored_residual.shape == (0,), "residual predictions should be absent for direct-only runs"

    reddecoded = decode_matching(matching, d)
    assert np.array_equal(reddecoded, evidence["pymatching"]), "stored PyMatching predictions differ from independent decode"
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    assert checkpoint["config_sha256"] == metadata["config_sha256"], "checkpoint configuration hash mismatch"
    expected_steps = (int(cfg["training_shots"]) + int(cfg["batch_size"]) - 1) // int(cfg["batch_size"])
    assert checkpoint["training_samples_processed"] == int(cfg["training_shots"]), "checkpoint train counter mismatch"
    assert checkpoint["completed_steps"] == expected_steps, "checkpoint step counter mismatch"
    direct = DirectMLP()
    direct.load_state_dict(checkpoint["direct_state"])
    direct.eval()
    x = torch.from_numpy(d.astype(np.float32))
    with torch.inference_mode():
        direct_predictions = (torch.sigmoid(direct(x)) >= 0.5).to(torch.uint8).numpy()
    assert np.array_equal(direct_predictions, evidence["direct_neural"]), "stored direct predictions do not match saved model checkpoint"

    predictions = {"identity_no_decode": evidence["identity_no_decode"], "pymatching": evidence["pymatching"],
                   "direct_neural": evidence["direct_neural"]}
    if cfg["model_selection"] == "direct_plus_residual":
        residual = ResidualMLP()
        residual.load_state_dict(checkpoint["residual_state"])
        residual.eval()
        with torch.inference_mode():
            correction = (torch.sigmoid(residual(x, torch.from_numpy(reddecoded.astype(np.float32)))) >= 0.5).to(torch.uint8).numpy()
        regenerated_residual = np.bitwise_xor(reddecoded, correction)
        assert np.array_equal(regenerated_residual, stored_residual), "stored residual predictions do not match saved model checkpoint"
        predictions["pymatching_neural_residual"] = stored_residual
    recomputed = compare_predictions(y, predictions)
    assert recomputed == metadata["metrics"], "saved metric aggregates do not match evidence arrays"
    validation_path = run_dir / "validation_evidence.npz"
    with np.load(validation_path, allow_pickle=False) as npz:
        val = {key: np.asarray(npz[key]) for key in npz.files}
    val_y, val_d = val["observable"], val["detectors"]
    assert val_d.shape == (int(cfg["validation_shots"]), circuit.num_detectors)
    assert val_y.shape == (int(cfg["validation_shots"]),) and np.isin(val_y, [0, 1]).all()
    val_matching = decode_matching(matching, val_d)
    assert np.array_equal(val_matching, val["pymatching"]), "saved validation PyMatching predictions differ from independent decode"
    with torch.inference_mode():
        val_direct = (torch.sigmoid(direct(torch.from_numpy(val_d.astype(np.float32)))) >= 0.5).to(torch.uint8).numpy()
    assert np.array_equal(val_direct, val["direct"]), "saved validation direct predictions differ from saved model checkpoint"
    if cfg["model_selection"] == "direct_plus_residual":
        with torch.inference_mode():
            val_correction = (torch.sigmoid(residual(torch.from_numpy(val_d.astype(np.float32)),
                                                       torch.from_numpy(val_matching.astype(np.float32)))) >= 0.5).to(torch.uint8).numpy()
        assert np.array_equal(np.bitwise_xor(val_matching, val_correction), val["residual"]), \
            "saved validation residual predictions differ from saved model checkpoint"
    db_path = run_dir.parents[1] / "qshift_dashboard.sqlite3"
    if db_path.is_file():
        import storage
        stored_run = storage.get_run(metadata["run_id"], db_path=db_path)
        assert stored_run and stored_run["status"] == "completed", "SQLite run record is missing or not completed"
        assert stored_run["state"]["status"] == "completed", "SQLite nested run state is inconsistent"
        assert stored_run["state"]["summary"]["metrics"] == recomputed, "SQLite summary differs from saved evidence"
        assert stored_run["state"]["progress"]["training_samples_processed"] == int(cfg["training_shots"]), \
            "SQLite training progress counter mismatch"
    tracked_sources = {}
    for name, expected in metadata.get("dashboard_source_hashes", {}).items():
        source_path = Path(__file__).resolve().with_name(name)
        actual = sha256_file(source_path)
        assert actual == expected, f"dashboard source hash changed since the run: {name}"
        tracked_sources[name] = actual
    from simulator import PHASE2B
    for name, expected in metadata.get("phase2b_source_hashes", {}).items():
        source_path = PHASE2B / name
        actual = sha256_file(source_path)
        assert actual == expected, f"Phase 2B source hash changed since the run: {name}"
        tracked_sources[f"phase2b/{name}"] = actual
    run_files = {}
    for name in ("config.json", "seed_inventory.json", "checkpoint.pt", "validation_evidence.npz",
                 "test_evidence.npz", "run_metadata.json"):
        file_path = run_dir / name
        run_files[name] = sha256_file(file_path)
    return {
        "status": "PASS", "run_id": metadata["run_id"], "test_shots": n,
        "circuit_sha256": metadata["circuit_sha256"], "dem_sha256": metadata["dem_sha256"],
        "test_evidence_sha256": metadata["test_evidence_sha256"],
        "checkpoint_sha256": metadata["checkpoint_sha256"], "metrics": recomputed,
        "verified": ["config and evidence hashes", "seed partition metadata", "frozen circuit and DEM",
                     "validation/test detector-label shapes", "stored validation/test PyMatching predictions",
                     "validation/test neural predictions against saved checkpoint", "paired metrics",
                     "SQLite terminal state and aggregate", "dashboard source hashes"],
        "validation_shots": int(len(val_y)), "validation_ler": {
            "pymatching": int(np.count_nonzero(val["pymatching"] ^ val_y)) / len(val_y),
            "direct_neural": int(np.count_nonzero(val["direct"] ^ val_y)) / len(val_y),
            "pymatching_neural_residual": int(np.count_nonzero(val["residual"] ^ val_y)) / len(val_y)
            if val["residual"].size else None,
        },
        "artifact_hashes": run_files,
        "verified_dashboard_source_hashes": tracked_sources,
        "scope_note": "Verifies this finite smoke-test run only; it is not an independent-root performance study.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path, default=None,
                        help="Write the verification JSON here (default: independent_verification.json in the run directory).")
    args = parser.parse_args()
    result = audit(args.run_dir)
    output = args.output or (args.run_dir / "independent_verification.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    result["verification_report"] = str(output.resolve())
    manifest_path = args.run_dir / "run_manifest.json"
    manifest = {"schema_version": 1, "created_after_run": True, "run_id": result["run_id"],
                "evidence_sha256": result["artifact_hashes"],
                "verification_report_sha256": sha256_file(output),
                "verified_source_sha256": result["verified_dashboard_source_hashes"],
                "audit_time_source_sha256": {
                    name: sha256_file(Path(__file__).resolve().with_name(name))
                    for name in ("app.py", "manager.py", "storage.py", "run_smoke.py",
                                 "verify_run.py", "benchmark_saved_inference.py")},
                "provenance_note": "Raw run outputs and run_metadata are generated by the trainer; this manifest and independent_verification are audit-time files."}
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    result["run_manifest"] = str(manifest_path.resolve())
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
