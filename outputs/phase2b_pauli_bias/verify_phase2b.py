"""Independent post-run evidence audit for Phase 2B; does not import the analyzer."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from decoder_bank import build_bank, decode_bank
from noise_model import MEMORY_BASES, REGIMES

P = Path(__file__).resolve().parent
ROOT = P.parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    freeze = json.loads((P / "PRETEST_FREEZE.json").read_text(encoding="utf-8"))
    historical_freeze = P / "PRETEST_FREEZE_SUPERSEDED_1.json"
    assert historical_freeze.is_file()
    assert sha(historical_freeze) == freeze["supersedes"]["sha256"]
    frozen_hashes = {}
    for rel, expected in freeze["files_sha256"].items():
        path = ROOT / rel
        actual = sha(path) if path.is_file() else None
        frozen_hashes[rel] = {"expected": expected, "actual": actual, "pass": actual == expected}
    assert all(x["pass"] for x in frozen_hashes.values())

    with (P / "SEED_MANIFEST.csv").open(newline="", encoding="utf-8") as f:
        seed_rows = list(csv.DictReader(f))
    partition_seeds = {}
    for row in seed_rows:
        partition_seeds.setdefault(row["partition"], []).append(int(row["seed"]))
    flattened = [s for vals in partition_seeds.values() for s in vals]
    assert len(flattened) == len(set(flattened)) == 140
    assert len(partition_seeds["heldout"]) == 120
    assert len(partition_seeds["calibration"]) == 6
    assert len(partition_seeds["development_validation"]) == 6
    assert not (set(partition_seeds["heldout"]) & set(partition_seeds["calibration"]))
    scan = json.loads((P / "SEED_SCREENING.json").read_text(encoding="utf-8"))
    assert scan["collision_free_over_recoverable_records"] and not scan["historical_proposed_seed_matches"]
    assert scan["proposed_seed_count"] == 140

    selection = json.loads((P / "CALIBRATION_SELECTION.json").read_text(encoding="utf-8"))["selected_models"]
    banks = {b: build_bank(b, distance=3, rounds=5)[0] for b in MEMORY_BASES}
    root_rows = []
    counts = {(b, r): np.zeros(3, dtype=np.int64) for b in MEMORY_BASES for r in REGIMES}
    shots = {(b, r): 0 for b in MEMORY_BASES for r in REGIMES}
    b_candidate_only = {(b, r): 0 for b in MEMORY_BASES for r in REGIMES}
    b_a_only = {(b, r): 0 for b in MEMORY_BASES for r in REGIMES}
    disagreement = {(b, r): np.zeros((3, 3), dtype=np.int64) for b in MEMORY_BASES for r in REGIMES}
    raw_hashes = {}
    test_mtimes = []
    for basis in MEMORY_BASES:
        for regime in REGIMES:
            for root in range(20):
                path = P / "data" / "heldout" / f"test_{basis}_{regime}_root{root:02d}.npz"
                raw_hashes[path.relative_to(P).as_posix()] = sha(path)
                test_mtimes.append(path.stat().st_mtime)
                with np.load(path, allow_pickle=False) as z:
                    d, y, pred = z["detectors"], z["observable"], z["predictions"]
                    assert d.shape == (10000, 40) and d.dtype == np.uint8
                    assert y.shape == (10000,) and y.dtype == np.uint8
                    assert pred.shape == (3, 10000) and pred.dtype == np.uint8
                    assert set(np.unique(d)).issubset({0, 1})
                    assert set(np.unique(y)).issubset({0, 1})
                    assert set(np.unique(pred)).issubset({0, 1})
                    assert int(z["basis_id"]) == MEMORY_BASES.index(basis)
                    assert int(z["regime_id"]) == REGIMES.index(regime)
                    assert int(z["root_index"]) == root
                    expected_seed = freeze["seed_inventory"]["heldout"][MEMORY_BASES.index(basis)*60 + REGIMES.index(regime)*20 + root]
                    assert int(z["seed"]) == int(expected_seed)
                    assert np.array_equal(pred, decode_bank(banks[basis], d)), f"prediction mismatch {path.name}"
                    err = pred ^ y[None, :]
                    counts[(basis, regime)] += err.sum(axis=1).astype(np.int64)
                    shots[(basis, regime)] += len(y)
                    a = int(selection[basis]["global_index"])
                    b = int(selection[basis]["per_regime_indices"][regime])
                    b_candidate_only[(basis, regime)] += int(np.count_nonzero(err[b] & ~err[a]))
                    b_a_only[(basis, regime)] += int(np.count_nonzero(~err[b] & err[a]))
                    for i in range(3):
                        for j in range(3):
                            disagreement[(basis, regime)][i, j] += int(np.count_nonzero(pred[i] != pred[j]))
                    root_rows.append({"basis": basis, "regime": regime, "root_index": root,
                        "seed": int(z["seed"]), "shots": len(y),
                        "decoder_errors": [int(v) for v in err.sum(axis=1)]})
    assert sum(shots.values()) == 1_200_000
    assert min(test_mtimes) >= (P / "PRETEST_FREEZE.json").stat().st_mtime

    # Reconcile every row in the saved per-root table against recomputed NPZ values.
    with (P / "PER_ROOT_RESULTS.csv").open(newline="", encoding="utf-8") as f:
        csv_root_rows = list(csv.DictReader(f))
    assert len(csv_root_rows) == 120
    for row in csv_root_rows:
        src = next(x for x in root_rows if x["basis"] == row["basis"] and x["regime"] == row["regime"] and x["root_index"] == int(row["root_index"]))
        for i in range(3):
            assert int(row[f"decoder_{i}_errors"]) == src["decoder_errors"][i]

    with (P / "PER_REGIME_RESULTS.csv").open(newline="", encoding="utf-8") as f:
        saved_cells = list(csv.DictReader(f))
    assert len(saved_cells) == 6
    cell_errors = {}
    for row in saved_cells:
        key = (row["basis"], row["regime"])
        cell_errors[key] = counts[key].tolist()
        assert shots[key] == int(row["shots"]) == 200000
        a = int(selection[key[0]]["global_index"])
        b = int(selection[key[0]]["per_regime_indices"][key[1]])
        assert int(row["A_global_fixed_errors"]) == int(counts[key][a])
        assert int(row["B_regime_informed_errors"]) == int(counts[key][b])
        assert int(row["C_balanced_errors"]) == int(counts[key][1])
        assert int(row["B_minus_A_errors"]) == int(counts[key][b] - counts[key][a])

    oracle = json.loads((P / "ORACLE_HEADROOM.json").read_text(encoding="utf-8"))
    overall_A = sum(int(counts[(basis, regime)][int(selection[basis]["global_index"])]) for basis in MEMORY_BASES for regime in REGIMES)
    overall_B = sum(int(counts[(basis, regime)][int(selection[basis]["per_regime_indices"][regime])]) for basis in MEMORY_BASES for regime in REGIMES)
    overall_C = sum(int(counts[(basis, regime)][1]) for basis in MEMORY_BASES for regime in REGIMES)
    assert oracle["calibration_selected_global_fixed_errors"] == overall_A
    assert oracle["calibration_selected_regime_informed_errors"] == overall_B
    assert oracle["balanced_fixed_errors"] == overall_C
    stats = json.loads((P / "STATISTICAL_RESULTS.json").read_text(encoding="utf-8"))
    assert stats["primary"]["shots"] == 1_200_000 and stats["primary"]["roots"] == 120
    assert abs(stats["primary"]["effect_B_minus_A_equal_six_cell_mean"] - (overall_B - overall_A) / 1_200_000) < 1e-12

    corrected = P / "analyze_phase2b_verified.py"
    audit = {
        "status": "PASS_WITH_ANALYSIS_IMPLEMENTATION_CORRECTION",
        "heldout_roots": 120, "heldout_shots": 1_200_000,
        "heldout_predictions_independently_redecoded": True,
        "per_root_and_per_regime_csvs_reconciled": True,
        "overall_error_counts": {"A_global_fixed": overall_A, "B_regime_informed": overall_B,
                                 "C_balanced": overall_C},
        "B_minus_A_error_count": overall_B - overall_A,
        "frozen_pretest_hashes_pass": all(x["pass"] for x in frozen_hashes.values()),
        "original_pretest_freeze_preserved_and_superseded": True,
        "seed_partitions_unique": True, "seed_count": len(flattened),
        "historical_seed_scan_pass": True,
        "analysis_correction": {"original_frozen_analyzer": "analyze_phase2b.py",
                                "corrected_script": corrected.name, "corrected_script_sha256": sha(corrected),
                                "scientific_method_changed": False,
                                "details_file": "ANALYSIS_CORRECTION.md"},
        "raw_heldout_sha256": raw_hashes,
        "cell_error_totals": {f"{b}/{r}": counts[(b, r)].tolist() for b in MEMORY_BASES for r in REGIMES},
        "cell_prediction_disagreement_counts": {f"{b}/{r}": disagreement[(b, r)].tolist() for b in MEMORY_BASES for r in REGIMES},
        "primary_statistical_result": stats["primary"],
        "limitations": ["The per-regime diagnostic is supplied the known generating regime; it is not an adaptive policy.",
                        "The Stim custom-channel DEM requires an approximate-disjoint conversion; all bank models use the same documented approximation.",
                        "The channels are designed 10:1:1 sensitivity settings and are not hardware-calibrated.",
                        "The run tests stationary conditions between independent circuit shots, not within-circuit drift."],
    }
    (P / "PHASE2B_ANALYSIS_AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: independent audit; roots=120, shots=1,200,000, A={overall_A}, B={overall_B}, C={overall_C}; pretest hashes pass")


if __name__ == "__main__":
    main()
