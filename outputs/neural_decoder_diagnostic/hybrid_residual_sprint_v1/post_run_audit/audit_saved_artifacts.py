"""Read-only inventory/provenance audit for the sprint's terminal run state.

This never samples, trains, resumes, or opens independent-test artifacts.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

AUDIT_DIR = Path(__file__).resolve().parent
BASE = AUDIT_DIR.parent
REPO = BASE.parents[2]
RUN = BASE / "run"
REGIMES = ("x_biased", "balanced", "z_biased")
SPLITS = ("train", "monitor", "calibration", "threshold_selection", "final_development_evaluation")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(ok: bool, message: str):
    if not ok:
        raise AssertionError(message)


def main():
    cfg = load(BASE / "config.json")
    inv = load(BASE / "SEED_INVENTORY.json")
    freeze = load(BASE / "FREEZE.json")
    progress = load(RUN / "PROGRESS.json")
    results = load(RUN / "RESULTS.json")
    error = load(RUN / "ERROR.json")
    require(progress.get("independent_test_access") == 0 and results.get("independent_test_access") == 0,
            "Run/results do not record independent-test isolation.")
    require(progress.get("status") == "failed", "Expected the preserved terminal controller failure.")
    require(progress.get("current_phase") == "final_evaluation" and len(progress.get("completed_jobs", [])) == 30,
            "Run did not reach all final evaluation jobs.")
    require(len(progress.get("selection_jobs", [])) == 30, "Not all 30 model/policy selections were frozen.")
    require("Independent evidence verifier failed" in error.get("error", "") and
            "Run is not complete: sampling" in error.get("error", ""),
            "Terminal failure differs from the known verifier lifecycle-order failure.")
    require(not (RUN / "sprint.lock").exists(), "Controller lock remains; do not treat run as terminal.")
    require(inv.get("passed") and inv.get("seed_collision_audit_passed") and
            inv.get("derived_seed_count") == inv.get("unique_derived_seed_count") and
            not inv.get("historical_collisions"), "Frozen seed inventory failed.")
    require("test" not in cfg.get("independent_test_access", "").lower() or
            "prohibited" in cfg.get("independent_test_access", "").lower(),
            "Independent-test guard is absent from configuration.")
    require(not any("test" in x.get("split", "").lower() for x in inv.get("streams", [])),
            "Forbidden test stream appears in the new inventory.")
    require(sha(BASE / "config.json") == freeze["config_sha256"] and
            sha(BASE / "EXPERIMENT_PROTOCOL.md") == freeze["protocol_sha256"] and
            sha(BASE / "SEED_INVENTORY.json") == freeze["seed_inventory_sha256"],
            "Frozen config/protocol/inventory hash mismatch.")
    frozen_sources = []
    for rel, digest in freeze.get("source_sha256", {}).items():
        p = BASE / rel if (BASE / rel).is_file() else REPO / rel
        require(p.is_file() and sha(p) == digest, f"Frozen source hash mismatch: {rel}")
        frozen_sources.append({"path": rel, "sha256": digest})

    stream_map = {(int(x["root"]), x["regime"], x["split"]): x for x in inv["streams"]}
    actual_seed_ids, data_files, split_shots = [], [], {s: 0 for s in SPLITS}
    shot_sizes = {
        "train": max(map(int, cfg["sampling"]["train_budgets_per_regime_root"])),
        "monitor": int(cfg["sampling"]["monitor_shots_per_regime_root"]),
        "calibration": int(cfg["sampling"]["calibration_shots_per_regime_root"]),
        "threshold_selection": int(cfg["sampling"]["threshold_selection_shots_per_regime_root"]),
        "final_development_evaluation": int(cfg["sampling"]["final_development_shots_per_regime_root"]),
    }
    for root in range(int(cfg["roots"])):
        for split in SPLITS:
            stem = f"final_root_{root:02d}" if split == "final_development_evaluation" else f"{split}_root_{root:02d}"
            archive, meta_path = RUN / "data" / f"{stem}.npz", RUN / "data" / f"{stem}.json"
            require(archive.is_file() and meta_path.is_file(), f"Missing data archive/metadata: {stem}")
            meta = load(meta_path)
            require(meta.get("archive_sha256") == sha(archive), f"Archive hash mismatch: {stem}")
            require(meta.get("root") == root and meta.get("split") == split and
                    meta.get("independent_test_access") == 0, f"Data identity/scope mismatch: {stem}")
            with np.load(archive, allow_pickle=False) as z:
                require(len(z.files) == len(REGIMES) * 3, f"Unexpected data schema: {stem}")
                for regime in REGIMES:
                    expected_n = shot_sizes[split]
                    d, y, pm = (z[f"detectors__{regime}"], z[f"observable__{regime}"],
                                z[f"pymatching__{regime}"])
                    require(d.shape == (expected_n, 40) and y.shape == (expected_n,) and pm.shape == (expected_n,),
                            f"Data shape mismatch: {stem}/{regime}")
                    require(all(np.isfinite(a).all() and np.all((a == 0) | (a == 1)) for a in (d, y, pm)),
                            f"Nonbinary/nonfinite data: {stem}/{regime}")
                    expected_stream = stream_map[(root, regime, split)]
                    recorded = meta.get("seed_streams", {}).get(regime, {})
                    require(recorded.get("seeds") == expected_stream["seeds"] and
                            int(recorded.get("shots", -1)) == expected_n,
                            f"Recorded seed allocation mismatch: {stem}/{regime}")
                    actual_seed_ids.extend(recorded["seeds"])
                    split_shots[split] += expected_n
            data_files.extend([{"path": str(archive.relative_to(BASE)), "sha256": sha(archive), "shots": meta["shots"]},
                               {"path": str(meta_path.relative_to(BASE)), "sha256": sha(meta_path)}])
    allocated_data_seeds = [s for stream in inv["streams"] for s in stream["seeds"]]
    require(set(actual_seed_ids) == set(allocated_data_seeds), "Saved data seeds differ from frozen stream inventory.")
    require(len(actual_seed_ids) == len(set(actual_seed_ids)), "Duplicate RNG seed among saved data partitions.")
    production_total = sum(split_shots.values())
    require(production_total == 1_665_000 == int(results["unique_production_shots"]),
            f"Production shot accounting mismatch: {production_total}")

    selections, checkpoints, predictions = [], [], []
    for root in range(int(cfg["roots"])):
        for strategy in cfg["models"]["strategies"]:
            for size in cfg["sampling"]["train_budgets_per_regime_root"]:
                jid = f"root{root:02d}_{strategy}_{int(size)}"
                sp = RUN / "selections" / f"{jid}.json"
                sel = load(sp)
                require(sel.get("final_development_evaluation_accessed") is False and sel.get("job_id") == jid,
                        f"Selection identity/leakage guard mismatch: {jid}")
                wp = RUN / "checkpoints" / f"{jid}.weights.pt"
                require(wp.is_file() and sha(wp) == sel.get("weights_sha256"), f"Selected weights mismatch: {jid}")
                state = RUN / "checkpoints" / f"{jid}.state.pt"
                state_meta = state.with_suffix(state.suffix + ".json")
                require(state.is_file() and state_meta.is_file(), f"Training state checkpoint missing: {jid}")
                sm = load(state_meta)
                require(sha(state) == sm.get("sha256") and state.stat().st_size == int(sm.get("bytes", -1)),
                        f"Optimizer checkpoint integrity mismatch: {jid}")
                selections.append({"path": str(sp.relative_to(BASE)), "sha256": sha(sp), "job_id": jid,
                                   "weight_sha256": sha(wp)})
                checkpoints.append({"path": str(state.relative_to(BASE)), "sha256": sha(state),
                                    "metadata": str(state_meta.relative_to(BASE))})
                pred = RUN / "predictions" / f"{jid}.npz"
                pred_meta = pred.with_suffix(".json")
                require(pred.is_file() and pred_meta.is_file(), f"Evaluation prediction evidence missing: {jid}")
                pm = load(pred_meta)
                require(sha(pred) == pm.get("archive_sha256") and pm.get("selection_sha256") == sha(sp) and
                        pm.get("independent_test_access") == 0, f"Prediction integrity/selection binding mismatch: {jid}")
                with np.load(pred, allow_pickle=False) as z:
                    require(all(f"observable__{r}" in z and f"pymatching__{r}" in z and
                                f"residual_target__{r}" in z for r in REGIMES),
                            f"Prediction archive missing paired arrays: {jid}")
                predictions.append({"path": str(pred.relative_to(BASE)), "sha256": sha(pred), "job_id": jid})

    with (RUN / "PAIRED_EVALUATION.csv").open("r", encoding="utf-8", newline="") as f:
        paired_rows = list(csv.DictReader(f))
    with (RUN / "TRAINING_RESULTS.csv").open("r", encoding="utf-8", newline="") as f:
        train_rows = list(csv.DictReader(f))
    require(len(paired_rows) == 135 and len(train_rows) == 30 and len(results.get("summary", [])) == 9,
            "Evaluation/training summary coverage is incomplete.")
    require(progress.get("committed_unique_shots") == production_total and
            progress.get("sampling_attempted_shots") == production_total,
            "Progress shot counters differ from saved partitions.")
    require(results.get("unique_total_shots_including_preflight") == 1_665_384 and
            progress.get("unique_diagnostic_shots") == 384, "Diagnostic/production count mismatch.")

    audit = {
        "status": "SAVED_EVIDENCE_INVENTORY_PASS; CONTROLLER_FAILED_FINAL_VERIFICATION",
        "controller_status": progress["status"],
        "controller_pid_recorded": progress.get("pid"),
        "terminal_error": error.get("error"),
        "failure_classification": "The final independent verifier was called while PROGRESS.status was still 'sampling'; its first assertion requires 'completed'. The runner writes completed status only after the verifier returns. Saved production/evaluation artifacts exist, but controller completion status and CHECKPOINT_MANIFEST.json were not committed.",
        "production_shots": production_total,
        "unique_total_shots_including_preflight": 1_665_384,
        "per_split_shots": split_shots,
        "roots": int(cfg["roots"]), "selection_records": len(selections),
        "training_checkpoints": len(checkpoints), "prediction_archives": len(predictions),
        "paired_evaluation_rows": len(paired_rows), "training_result_rows": len(train_rows),
        "result_policy_summaries": len(results["summary"]),
        "all_data_hashes_and_seed_maps_valid": True,
        "all_selected_weight_hashes_valid": True,
        "all_optimizer_checkpoint_hashes_valid": True,
        "all_prediction_archive_hashes_and_selection_bindings_valid": True,
        "independent_test_access": 0,
        "frozen_source_hashes_checked": len(frozen_sources),
        "paired_evaluation_sha256": sha(RUN / "PAIRED_EVALUATION.csv"),
        "results_sha256": sha(RUN / "RESULTS.json"),
        "training_csv_sha256": sha(RUN / "TRAINING_RESULTS.csv"),
        "data_files": data_files, "selections": selections,
        "checkpoints": checkpoints, "predictions": predictions,
        "frozen_source_hashes": frozen_sources,
    }
    out = AUDIT_DIR / "SAVED_ARTIFACTS_AUDIT.json"
    out.write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: audit[k] for k in ("status", "production_shots", "per_split_shots", "selection_records",
        "training_checkpoints", "prediction_archives", "paired_evaluation_rows", "training_result_rows",
        "result_policy_summaries", "all_data_hashes_and_seed_maps_valid", "all_selected_weight_hashes_valid",
        "all_optimizer_checkpoint_hashes_valid", "all_prediction_archive_hashes_and_selection_bindings_valid",
        "independent_test_access", "frozen_source_hashes_checked", "failure_classification")}, indent=2))


if __name__ == "__main__":
    main()
