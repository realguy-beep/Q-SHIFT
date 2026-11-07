from __future__ import annotations
import csv
import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
P2B = HERE.parent / "phase2b_pauli_bias"
sys.path.insert(0, str(P2B))
from noise_model import MEMORY_BASES, REGIMES  # noqa: E402

DECODER_ORDER = ["pm_x", "pm_balanced", "pm_z", "ref_x", "ref_balanced", "ref_z"]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    freeze = json.loads((HERE / "PILOT_FREEZE.json").read_text())
    for rel, expected in freeze["files_sha256"].items():
        path = HERE.parent.parent / Path(rel)
        assert path.is_file() and sha256(path) == expected, f"frozen hash mismatch: {rel}"
    seed_audit = json.loads((HERE / "SEED_COLLISION_AUDIT.json").read_text())
    assert seed_audit["proposed_seeds_unique"] and seed_audit["collisions_absent"]
    assert not seed_audit["read_failures"]
    run = json.loads((HERE / "PILOT_RUN.json").read_text())
    selection = json.loads((HERE / "CALIBRATION_SELECTION.json").read_text())
    reported = json.loads((HERE / "PHASE2C_RESULTS.json").read_text())
    assert len(run["roots"]) == 24 and run["total_test_shots"] == 120000

    matchers = {}
    forests = {}
    for basis in MEMORY_BASES:
        matchers[basis] = [pymatching.Matching.from_detector_error_model(
            stim.DetectorErrorModel.from_file(str(HERE / "dems" / f"dem_{basis}_{regime}.dem")),
            enable_correlations=True) for regime in REGIMES]
        for regime in REGIMES:
            forests[(basis, regime)] = joblib.load(HERE / "models" / f"reference_{basis}_{regime}.joblib")

    raw_counts = {"phase2b_regime_matched": 0, "phase2b_balanced_fixed": 0,
                  "reference_global_fixed": 0, "reference_regime_informed": 0}
    shot_counts = 0
    cell_counts = {}
    root_csv = {(r["basis"], r["generating_regime"], int(r["root_index"])): r
                for r in csv.DictReader((HERE / "PER_ROOT_RESULTS.csv").open(encoding="utf-8"))}
    assert len(root_csv) == 24
    run_by_path = {r["file"].replace("\\", "/"): r for r in run["roots"]}
    cal_recomputed = {}
    for basis in MEMORY_BASES:
        matrix = np.zeros((len(REGIMES), len(REGIMES)), dtype=np.int64)
        for gen_idx, regime in enumerate(REGIMES):
            path = HERE / "data" / f"calibration_{basis}_{regime}.npz"
            with np.load(path, allow_pickle=False) as z:
                d, y = np.asarray(z["detectors"], dtype=np.uint8), np.asarray(z["observable"], dtype=np.uint8)
            for j, assumed in enumerate(REGIMES):
                matrix[gen_idx, j] = np.count_nonzero(forests[(basis, assumed)].predict(d) ^ y)
        recorded = np.asarray(selection["calibration_matrix"][basis]["errors"], dtype=np.int64)
        assert np.array_equal(matrix, recorded), f"calibration error matrix mismatch for {basis}"
        global_choice = int(np.flatnonzero(matrix.sum(axis=0) == matrix.sum(axis=0).min())[0])
        regime_choices = [int(np.flatnonzero(row == row.min())[0]) for row in matrix]
        assert global_choice == selection["global_fixed_reference_index_by_basis"][basis]
        assert regime_choices == [selection["regime_informed_reference_index_by_cell"][f"{basis}/{r}"] for r in REGIMES]
        cal_recomputed[basis] = {"matrix": matrix.tolist(), "global_choice": global_choice,
                                 "regime_choices": regime_choices}

    root_hashes = []
    for basis in MEMORY_BASES:
        for regime in REGIMES:
            cell_errors = {name: 0 for name in DECODER_ORDER}
            for root in range(4):
                rel = f"data/pilot/pilot_{basis}_{regime}_root{root:02}.npz"
                path = HERE / rel
                run_rec = run_by_path[rel]
                assert sha256(path) == run_rec["sha256"], f"raw hash mismatch {rel}"
                with np.load(path, allow_pickle=False) as z:
                    d = np.asarray(z["detectors"], dtype=np.uint8)
                    y = np.asarray(z["observable"], dtype=np.uint8)
                    stored = np.asarray(z["predictions"], dtype=np.uint8)
                    order = [str(x) for x in z["decoder_order"].tolist()]
                    seed = int(z["seed"])
                assert order == DECODER_ORDER and d.shape == (5000, 40) and y.shape == (5000,)
                assert stored.shape == (6, 5000) and np.isin(stored, (0, 1)).all() and np.isin(y, (0, 1)).all()
                assert seed == int(run_rec["seed"])
                recomputed = [np.asarray(m.decode_batch(d, enable_correlations=True), dtype=np.uint8)[:, 0]
                              for m in matchers[basis]]
                recomputed += [forests[(basis, r)].predict(d) for r in REGIMES]
                recomputed = np.stack(recomputed)
                assert np.array_equal(stored, recomputed), f"prediction mismatch {rel}"
                for i, name in enumerate(DECODER_ORDER):
                    err = int(np.count_nonzero(stored[i] ^ y))
                    cell_errors[name] += err
                    expected = int(root_csv[(basis, regime, root)][f"errors_{name}"])
                    assert err == expected, f"per-root CSV mismatch {rel}/{name}"
                pm_idx = REGIMES.index(regime)
                global_idx = int(selection["global_fixed_reference_index_by_basis"][basis])
                specific_idx = int(selection["regime_informed_reference_index_by_cell"][f"{basis}/{regime}"])
                raw_counts["phase2b_regime_matched"] += int(np.count_nonzero(stored[pm_idx] ^ y))
                raw_counts["phase2b_balanced_fixed"] += int(np.count_nonzero(stored[1] ^ y))
                raw_counts["reference_global_fixed"] += int(np.count_nonzero(stored[3 + global_idx] ^ y))
                raw_counts["reference_regime_informed"] += int(np.count_nonzero(stored[3 + specific_idx] ^ y))
                shot_counts += len(y)
                root_hashes.append({"file": rel, "sha256": sha256(path), "seed": seed})
            cell_counts[f"{basis}/{regime}"] = cell_errors

    assert shot_counts == 120000
    for name, errors in raw_counts.items():
        aggregate = reported["aggregate_policy_results"][name]
        assert errors == aggregate["errors"], f"aggregate error mismatch: {name}"
        assert shot_counts == aggregate["shots"]
    assert reported["primary"]["difference"] == 0.0
    audit = {
        "status": "PASS",
        "verified_root_count": len(root_hashes), "verified_test_shots": shot_counts,
        "raw_prediction_redecode_exact": True,
        "calibration_matrices_recomputed_exactly": cal_recomputed,
        "aggregate_errors_recomputed": raw_counts,
        "cell_candidate_errors_recomputed": cell_counts,
        "raw_root_hashes": root_hashes,
        "freeze_hashes_pass": True,
        "seed_collision_audit_pass": True,
        "notes": ["This verification reads raw bundles directly and does not import analyze_phase2c.py.",
                  "Test observables are used only for residual recomputation and score verification, not model selection."]
    }
    (HERE / "INDEPENDENT_VERIFICATION.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS: independently re-decoded 24 roots / {shot_counts} shots; errors={raw_counts}")


if __name__ == "__main__":
    main()
