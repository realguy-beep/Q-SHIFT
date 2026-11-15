"""Read-only verification/inventory of V1 committed training and calibration artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> dict:
    status_path = SAMPLES / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    expected_message = "Decoder mapping keys must match each decoder's metadata name."
    if (status.get("status") != "incomplete" or status.get("error_type") != "ValueError"
            or status.get("error_message") != expected_message
            or status.get("sampler_calls_started") != 56
            or status.get("shots_started") != 32000):
        raise SystemExit("failed-attempt state does not match the narrowly approved V1.1 recovery case")
    train_path = SAMPLES / "training_detector_only.npz"
    with np.load(train_path, allow_pickle=False) as d:
        x = np.asarray(d["detectors"], dtype=np.uint8)
        y = np.asarray(d["p_targets"], dtype=np.float64)
    if x.shape != (5000, 40) or y.shape != (5000,):
        raise SystemExit("training partition is incomplete or malformed")
    entries = [{
        "path": "samples/training_detector_only.npz", "sha256": sha(train_path),
        "bytes": train_path.stat().st_size, "detector_rows": len(x), "target_rows": len(y),
    }]
    calibration_rows = 0
    for i in range(5):
        for r in range(10):
            path = SAMPLES / f"cal_p{i}_r{r:02d}.npz"
            with np.load(path, allow_pickle=False) as d:
                a = np.asarray(d["detectors"], dtype=np.uint8)
            if a.shape != (500, 40) or not np.isin(a, [0, 1]).all():
                raise SystemExit(f"calibration archive malformed p{i}/r{r:02d}")
            calibration_rows += len(a)
            entries.append({
                "path": f"samples/cal_p{i}_r{r:02d}.npz", "sha256": sha(path),
                "bytes": path.stat().st_size, "detector_rows": len(a),
                "p_index": i, "root": r,
            })
    if calibration_rows != 25000:
        raise SystemExit("calibration total is not 25,000 rows")
    eval_archives = []
    for i in range(5):
        for r in range(10):
            stem = f"eval_p{i}_r{r:02d}"
            if (SAMPLES / f"{stem}.npz").exists() or (SAMPLES / f"{stem}.commit.json").exists():
                eval_archives.append(stem)
    if eval_archives:
        raise SystemExit(f"unexpected evaluation archives in original attempt: {eval_archives}")
    estimates_path = ROOT / "calibration_estimates.json"
    estimates = json.loads(estimates_path.read_text(encoding="utf-8"))
    expected_estimates = 50
    if len(estimates.get("estimates", [])) != expected_estimates:
        raise SystemExit("calibration estimate count mismatch")
    report = {
        "schema": "qshift-performance-recovery-input-inventory-v1.1",
        "original_attempt_status_sha256": sha(status_path),
        "original_attempt_status": status,
        "training_and_calibration_archives": entries,
        "training_rows": len(x),
        "calibration_rows": calibration_rows,
        "calibration_estimates_sha256": sha(estimates_path),
        "calibration_estimate_rows": len(estimates["estimates"]),
        "persisted_evaluation_archives": 0,
        "original_uncommitted_eval_call": {
            "partition": "eval:p0:r00",
            "seed_label": "eval:p0:r00",
            "rows_reported_started": 2000,
            "archive_or_prediction_persisted": False,
            "recovery": "replay the same deterministic partition seed; do not substitute a seed",
        },
        "status_counter_deviation": "original status claims 32,000 verified rows; only 30,000 training/calibration rows are persisted",
        "total_inventory_entries": len(entries),
    }
    out = ROOT / "RECOVERY_INPUT_INVENTORY_V1_1.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "training_rows": len(x),
                      "calibration_rows": calibration_rows, "archives": len(entries),
                      "evaluation_archives": 0}, indent=2))
    return report


if __name__ == "__main__":
    main()