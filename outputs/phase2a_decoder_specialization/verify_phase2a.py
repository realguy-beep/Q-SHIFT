"""Read-only integrity and numerical verification of Phase 2A saved evidence."""
from __future__ import annotations
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
PREV = ROOT / "outputs" / "prototype_development"
sys.path.insert(0, str(PREV))
from experiment import REGIME_NAMES, decode_grid  # noqa: E402
from decoder_bank import build_bank  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> dict:
    freeze = json.loads((P / "FREEZE.json").read_text(encoding="utf-8"))
    frozen_hashes = {}
    for rel, expected in freeze["input_sha256"].items():
        path = ROOT / rel
        actual = sha256(path) if path.is_file() else None
        frozen_hashes[rel] = {"expected": expected, "actual": actual, "pass": actual == expected}
    assert all(x["pass"] for x in frozen_hashes.values()), "pretest freeze hash mismatch"

    with (P / "SEED_MANIFEST.csv").open(newline="", encoding="utf-8") as f:
        seeds = list(csv.DictReader(f))
    assert len(seeds) == 60
    seed_values = [int(x["seed"]) for x in seeds]
    assert len(set(seed_values)) == 60
    assert set(seed_values) == set(freeze["fresh_evaluation_seeds"])

    models = build_bank(distance=3, rounds=5)
    counts = np.zeros((3, 9), dtype=np.int64)
    shots = np.zeros(3, dtype=np.int64)
    per_root = []
    raw_hashes = {}
    pair_disagreement = np.zeros((3, 9, 9), dtype=np.int64)
    for entry in seeds:
        r, root, seed = int(entry["regime_index"]), int(entry["root_index"]), int(entry["seed"])
        path = P / entry["file"]
        raw_hashes[entry["file"]] = sha256(path)
        with np.load(path, allow_pickle=False) as z:
            d, y, pred = z["detectors"], z["observable"], z["predictions"]
            assert d.shape == (10_000, 40) and d.dtype == np.uint8
            assert y.shape == (10_000,) and y.dtype == np.uint8
            assert pred.shape == (9, 10_000) and pred.dtype == np.uint8
            assert set(np.unique(d)).issubset({0, 1})
            assert set(np.unique(y)).issubset({0, 1})
            assert set(np.unique(pred)).issubset({0, 1})
            assert int(z["regime_id"]) == r and int(z["root_index"]) == root and int(z["seed"]) == seed
            assert len(y) == int(entry["shots"])
            recomputed = decode_grid(models, d)
            assert np.array_equal(pred, recomputed), f"decoder predictions differ: {path.name}"
            err = pred ^ y[None, :]
            n = err.sum(axis=1).astype(np.int64)
            counts[r] += n
            shots[r] += len(y)
            pair_disagreement[r] += np.count_nonzero(pred[:, None, :] != pred[None, :, :], axis=2)
            per_root.append({"regime_index": r, "regime": REGIME_NAMES[r], "root_index": root,
                             "seed": seed, "shots": len(y), "decoder_errors": n.tolist()})

    assert shots.tolist() == [200_000, 200_000, 200_000]
    assert sum(shots) == 600_000
    # Reconcile both saved summary tables against recomputation from raw arrays.
    with (P / "PER_SEED_RESULTS.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 60 * 9
    for row in rows:
        r = REGIME_NAMES.index(row["regime"])
        root, dec = int(row["root_index"]), int(row["decoder_index"])
        raw = next(x for x in per_root if x["regime_index"] == r and x["root_index"] == root)
        assert int(row["errors"]) == raw["decoder_errors"][dec]
        assert int(row["shots"]) == raw["shots"]
    with (P / "PER_REGIME_DECODER_RESULTS.csv").open(newline="", encoding="utf-8") as f:
        regime_rows = list(csv.DictReader(f))
    assert len(regime_rows) == 27
    for row in regime_rows:
        r, dec = int(row["regime_index"]), int(row["decoder_index"])
        assert int(row["errors"]) == int(counts[r, dec])
        assert int(row["shots"]) == int(shots[r])

    result = json.loads((P / "PHASE2A_RESULTS.json").read_text(encoding="utf-8"))
    assert result["roots"] == 60 and result["shots"] == 600_000
    for row in result["regime_decoder_results"]:
        r, dec = int(row["regime_index"]), int(row["decoder_index"])
        assert int(row["errors"]) == int(counts[r, dec])
        assert int(row["shots"]) == int(shots[r])
    selection = json.loads((P / "SELECTION.json").read_text(encoding="utf-8"))
    best_global = int(selection["best_global_index"])
    selected_by_regime = [int(x) for x in selection["best_per_regime_indices"]]
    selected_errors = int(sum(counts[r, selected_by_regime[r]] for r in range(3)))
    pooled_errors = int(counts[:, best_global].sum())
    assert best_global == 1 and selected_by_regime == [1, 1, 1]
    assert pooled_errors == selected_errors == 4192
    assert counts[:, 4].sum() == 4203

    report = {
        "status": "PASS",
        "pretest_freeze_hashes": frozen_hashes,
        "freeze_precedes_sampling_by_filesystem_mtime": (P / "FREEZE.json").stat().st_mtime <= min((P / x["file"]).stat().st_mtime for x in seeds),
        "roots": len(seeds), "unique_seeds": len(set(seed_values)), "shots": int(shots.sum()),
        "shots_by_regime": {REGIME_NAMES[r]: int(shots[r]) for r in range(3)},
        "counts_by_regime_decoder": {REGIME_NAMES[r]: counts[r].tolist() for r in range(3)},
        "pooled_fixed_decoder_index": best_global, "pooled_fixed_errors": pooled_errors,
        "calibration_selected_per_regime_indices": selected_by_regime,
        "calibration_selected_per_regime_errors": selected_errors,
        "nominal_decoder_index_4_errors": int(counts[:, 4].sum()),
        "all_saved_predictions_independently_redecoded": True,
        "per_seed_csv_reconciled": True, "per_regime_csv_reconciled": True,
        "raw_bundle_sha256": raw_hashes,
        "disagreement_counts_by_regime": {REGIME_NAMES[r]: pair_disagreement[r].tolist() for r in range(3)},
        "limitations": ["Calibration-selection uncertainty has one saved calibration batch per regime; the supplementary shotwise interval is not a replicated seed-level selection-stability estimate.",
                        "Pretest order is supported by source ordering and filesystem modification times, not an external trusted timestamp.",
                        "Raw prediction re-decoding verifies test predictions, not a physical correction chain."],
    }
    (P / "PHASE2A_AUDIT_RESULTS.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: 60 roots, {int(shots.sum()):,} shots; fixed={pooled_errors}, calibrated={selected_errors}, nominal={int(counts[:,4].sum())}; all frozen hashes and predictions verified")
    return report


if __name__ == "__main__":
    main()
