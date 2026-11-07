"""Independent numerical audit of the bounded Phase feasibility arrays.

This verifier does not import the experiment runner or its aggregation code.
It reads saved NPZ/CSV/JSON evidence and independently rebuilds PyMatching.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
GRID = [(g, m) for g in (0.001, 0.003, 0.006) for m in (0.001, 0.003, 0.006)]
REGIMES = [("data_heavy", 0.006, 0.001), ("nominal", 0.003, 0.003),
           ("measurement_heavy", 0.001, 0.006)]


def make_model(g, m):
    c = stim.Circuit.generated("surface_code:rotated_memory_z", distance=3, rounds=5,
                               after_clifford_depolarization=g,
                               before_measure_flip_probability=m)
    return pymatching.Matching.from_detector_error_model(c.detector_error_model(decompose_errors=True))


def decode(matcher, det):
    pred = np.asarray(matcher.decode_batch(det), dtype=np.uint8)
    if pred.ndim == 2:
        assert pred.shape == (len(det), 1)
        pred = pred[:, 0]
    assert pred.shape == (len(det),)
    assert np.isin(pred, (0, 1)).all()
    return pred


def choose(det, profiles):
    n = len(det)
    count = det.sum(axis=0, dtype=np.int64)
    score = (count[None, :] * np.log(profiles) + (n-count)[None, :] * np.log1p(-profiles)).sum(axis=1)
    return int(np.argmax(score))


def schedule_max(blocks, refp, refn, window=4):
    best = 0.0
    for end in range(window - 1, len(blocks)):
        w = blocks[end-window+1:end+1].reshape(-1, blocks.shape[-1])
        p = w.mean(axis=0)
        var = np.maximum(refp*(1-refp)*(1/len(w)+1/refn), 1e-12)
        best = max(best, float((np.abs(p-refp)/np.sqrt(var)).max()))
    return best


def main():
    result = json.loads((HERE / "DEVELOPMENT_CHECKS.json").read_text(encoding="utf-8"))
    with np.load(HERE / "DEVELOPMENT_RAW_EVIDENCE.npz", allow_pickle=False) as z:
        raw = {k: z[k] for k in z.files}
    assert raw["template_profiles"].shape == (9, 40)
    assert raw["template_detectors"].shape == (9, 2048, 40)
    assert raw["calibration_detectors"].shape == (3, 8, 1024, 40)
    assert raw["evaluation_detectors"].shape == (3, 8, 4096, 40)
    assert raw["evaluation_observables"].shape == (3, 8, 4096)
    assert raw["evaluation_predictions"].shape == (3, 8, 3, 4096)
    assert raw["stationary_reference_detectors"].ndim == 2
    for name in ("calibration_detectors", "evaluation_detectors", "evaluation_observables",
                 "evaluation_predictions", "template_detectors", "stationary_reference_detectors",
                 "stationary_threshold_calibration_blocks", "stationary_validation_blocks"):
        assert np.isin(raw[name], (0, 1)).all(), f"nonbinary values in {name}"
    recomputed_profiles = (raw["template_detectors"].sum(axis=1, dtype=np.int64) + 0.5) / (2048 + 1.0)
    np.testing.assert_array_equal(recomputed_profiles, raw["template_profiles"])

    rows = list(csv.DictReader((HERE / "UTILITY_PER_ROOT.csv").open(encoding="utf-8", newline="")))
    assert len(rows) == 24
    models = [make_model(*params) for params in GRID]
    fixed_pool = models[1]
    fixed_nominal = models[4]
    per_regime = {}
    prediction_checks = 0
    for ri, (regime, gp, mp) in enumerate(REGIMES):
        sub = [x for x in rows if x["regime"] == regime]
        assert len(sub) == 8
        errors = {"selected": 0, "pooled": 0, "nominal": 0}
        paired = {"selected_only_wrong": 0, "pooled_only_wrong": 0,
                  "prediction_disagreements": 0}
        shots = 0
        for root, row in enumerate(sub):
            choice = choose(raw["calibration_detectors"][ri, root], raw["template_profiles"])
            assert choice == int(row["selected_grid_index"]), f"calibration choice mismatch {regime}/{root}"
            selected_model = make_model(*GRID[choice])
            d = raw["evaluation_detectors"][ri, root]
            y = raw["evaluation_observables"][ri, root]
            p_sel, p_pool, p_nom = decode(selected_model, d), decode(fixed_pool, d), decode(fixed_nominal, d)
            np.testing.assert_array_equal(p_sel, raw["evaluation_predictions"][ri, root, 0])
            np.testing.assert_array_equal(p_pool, raw["evaluation_predictions"][ri, root, 1])
            np.testing.assert_array_equal(p_nom, raw["evaluation_predictions"][ri, root, 2])
            prediction_checks += 3
            got = [int(np.count_nonzero(p_sel != y)), int(np.count_nonzero(p_pool != y)), int(np.count_nonzero(p_nom != y))]
            expected = [int(row["selected_errors"]), int(row["pooled_errors"]), int(row["nominal_errors"])]
            assert got == expected, f"root aggregate mismatch {regime}/{root}: {got} != {expected}"
            errors["selected"] += got[0]
            errors["pooled"] += got[1]
            errors["nominal"] += got[2]
            paired["selected_only_wrong"] += int(np.count_nonzero((p_sel != y) & (p_pool == y)))
            paired["pooled_only_wrong"] += int(np.count_nonzero((p_sel == y) & (p_pool != y)))
            paired["prediction_disagreements"] += int(np.count_nonzero(p_sel != p_pool))
            shots += len(y)
        per_regime[regime] = {"shots": shots, "errors": errors, "paired": paired,
                              "selected_minus_pooled_ler": (errors["selected"] - errors["pooled"]) / shots}
    aggregate_errors = {k: sum(v["errors"][k] for v in per_regime.values())
                        for k in ("selected", "pooled", "nominal")}
    aggregate_paired = {k: sum(v["paired"][k] for v in per_regime.values())
                        for k in ("selected_only_wrong", "pooled_only_wrong", "prediction_disagreements")}
    aggregate_shots = sum(v["shots"] for v in per_regime.values())

    stat = result["trigger_false_update_check"]
    ref = raw["stationary_reference_detectors"]
    refp = (ref.sum(axis=0, dtype=np.int64) + 0.5) / (len(ref) + 1.0)
    train = raw["stationary_threshold_calibration_blocks"]
    valid = raw["stationary_validation_blocks"]
    assert train.shape[:3] == (100, 12, 128) and valid.shape[:3] == (100, 12, 128)
    train_max = np.asarray([schedule_max(x, refp, len(ref)) for x in train])
    valid_max = np.asarray([schedule_max(x, refp, len(ref)) for x in valid])
    thresh = float(np.quantile(train_max, 0.95, method="higher"))
    assert abs(thresh - stat["threshold_max_z"]) < 1e-12
    alarms = int(np.count_nonzero(valid_max > thresh))
    assert alarms == stat["validation_false_update_schedules"]
    trigger_rows = list(csv.DictReader((HERE / "TRIGGER_SCHEDULE_MAXIMA.csv").open(encoding="utf-8", newline="")))
    assert len(trigger_rows) == 200
    recorded = {(x["split"], int(x["seed"])): float(x["schedule_max_stat"]) for x in trigger_rows}
    seeds = json.loads((HERE / "SEED_SCREEN.json").read_text(encoding="utf-8"))["seed_namespace"]
    for split, ids, values in (
        ("threshold_calibration", seeds["stationary_threshold_calibration"], train_max),
        ("independent_validation", seeds["stationary_threshold_validation"], valid_max),
    ):
        for seed, value in zip(ids, values):
            assert abs(recorded[(split, int(seed))] - float(value)) < 1e-12

    recomputed = {
        "status": "PASS" if prediction_checks == 72 and alarms == stat["validation_false_update_schedules"] else "FAIL",
        "raw_npz_arrays": {k: {"shape": list(v.shape), "dtype": str(v.dtype)} for k, v in raw.items()},
        "binary_array_validation": "PASS",
        "template_profile_recomputation": "PASS",
        "calibration_choice_recomputations": 24,
        "prediction_redecodings": prediction_checks,
        "prediction_redecoding_match": "PASS",
        "per_regime_error_counts": per_regime,
        "aggregate_shots": aggregate_shots,
        "aggregate_error_counts": aggregate_errors,
        "aggregate_ler": {k: v / aggregate_shots for k, v in aggregate_errors.items()},
        "aggregate_paired": aggregate_paired,
        "aggregate_selected_minus_pooled_ler": (aggregate_errors["selected"] - aggregate_errors["pooled"]) / aggregate_shots,
        "trigger_schedule_recomputations": 200,
        "trigger_threshold_recomputed": thresh,
        "trigger_false_updates_recomputed": alarms,
        "trigger_recomputation_match": "PASS",
        "paired_samples": "PASS: every comparator re-decoded the same saved detector arrays and observable labels",
        "versions": {"stim": stim.__version__, "pymatching": pymatching.__version__, "numpy": np.__version__},
    }
    (HERE / "INDEPENDENT_VERIFICATION.json").write_text(json.dumps(recomputed, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(recomputed, indent=2))


if __name__ == "__main__":
    main()
