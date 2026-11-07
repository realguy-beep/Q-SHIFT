"""Cross-root, development-only audit of observable-only confidence gates.

This script consumes only saved evidence from outputs/conditional_go_resolution.
It generates no Stim samples and writes no files outside this new pivot folder.
Evaluation labels are used only to form targets and score held-out roots in the
cross-validation loop; they are never included in the feature vectors.
"""
from __future__ import annotations

import csv
import ctypes
import json
import os
import platform
import time
from pathlib import Path

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut, LeaveOneOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "outputs" / "conditional_go_resolution"
RAW = SOURCE / "DEVELOPMENT_RAW_EVIDENCE.npz"
PER_ROOT_SOURCE = SOURCE / "UTILITY_PER_ROOT.csv"
REGIMES = ("data_heavy", "nominal", "measurement_heavy")
POOLED_INDEX = 1
LOGISTIC_C = 0.1  # Fixed before the cross-root score computation; not tuned here.
PROBABILITY_CUTOFF = 0.5  # Equal-cost decision rule, applied to out-of-root probabilities.


def process_memory() -> dict[str, int] | None:
    """Return process working set including native allocations on Windows."""
    if platform.system() != "Windows":
        return None

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    psapi = ctypes.WinDLL("Psapi.dll")
    get_process_memory = psapi.GetProcessMemoryInfo
    get_process_memory.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), ctypes.c_ulong]
    get_process_memory.restype = ctypes.c_bool
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    if not get_process_memory(handle, ctypes.byref(counters), counters.cb):
        return None
    return {
        "working_set_bytes": int(counters.WorkingSetSize),
        "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
    }


def read_source_rows() -> list[dict[str, str]]:
    with PER_ROOT_SOURCE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fit_model(x: np.ndarray, y: np.ndarray):
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(C=LOGISTIC_C, max_iter=2000, solver="lbfgs"),
    ).fit(x, y)


def main() -> None:
    started = time.perf_counter()
    memory_before = process_memory()
    z = np.load(RAW, allow_pickle=False)
    profiles = z["template_profiles"].astype(np.float64)
    cal = z["calibration_detectors"].astype(np.uint8)
    det = z["evaluation_detectors"].astype(np.uint8)
    obs = z["evaluation_observables"].astype(np.uint8)
    predictions = z["evaluation_predictions"].astype(np.uint8)
    source_rows = read_source_rows()

    assert cal.shape == (3, 8, 1024, 40)
    assert det.shape == (3, 8, 4096, 40)
    assert obs.shape == (3, 8, 4096)
    assert predictions.shape == (3, 8, 3, 4096)
    for arr in (cal, det, obs, predictions):
        assert np.isin(arr, (0, 1)).all()

    root_records: list[dict] = []
    shot_features: list[list[float]] = []
    shot_candidate_correct: list[bool] = []
    shot_groups: list[int] = []
    shot_regimes: list[int] = []
    shot_records: list[tuple[int, int, int, bool, float]] = []

    for row in source_rows:
        ri = REGIMES.index(row["regime"])
        root_i = int(row["root_index"])
        n_cal = len(cal[ri, root_i])
        counts = cal[ri, root_i].sum(axis=0, dtype=np.int64)
        scores = (
            counts[None, :] * np.log(profiles)
            + (n_cal - counts[None, :]) * np.log1p(-profiles)
        ).sum(axis=1)
        order = np.argsort(scores)[::-1]
        selected = int(order[0])
        margin = float(scores[order[0]] - scores[order[1]])
        selected_minus_pooled_cal_score = float(scores[selected] - scores[POOLED_INDEX])

        y = obs[ri, root_i]
        candidate_pred = predictions[ri, root_i, 0]
        pooled_pred = predictions[ri, root_i, 1]
        candidate_bad = candidate_pred != y
        pooled_bad = pooled_pred != y
        disagreements = candidate_pred != pooled_pred
        candidate_errors = int(candidate_bad.sum())
        pooled_errors = int(pooled_bad.sum())
        assert candidate_errors == int(row["selected_errors"])
        assert pooled_errors == int(row["pooled_errors"])
        assert selected == int(row["selected_grid_index"])

        root_records.append({
            "regime": row["regime"],
            "root_index": root_i,
            "group_id": ri * 8 + root_i,
            "selected_grid_index": selected,
            "calibration_top_minus_runnerup": margin,
            "calibration_selected_minus_pooled_score": selected_minus_pooled_cal_score,
            "shots": len(y),
            "candidate_errors": candidate_errors,
            "pooled_errors": pooled_errors,
            "candidate_minus_pooled_errors": candidate_errors - pooled_errors,
            "candidate_better_target": bool(candidate_errors < pooled_errors),
            "candidate_only_wrong": int(np.count_nonzero(candidate_bad & ~pooled_bad)),
            "pooled_only_wrong": int(np.count_nonzero(pooled_bad & ~candidate_bad)),
            "prediction_disagreements": int(disagreements.sum()),
        })

        # This feature is computed from the current detector vector under the
        # independent-marginal template approximation. It is not a calibrated
        # posterior and is not given any logical labels.
        shot_ll_delta = (
            det[ri, root_i] * np.log(profiles[selected] / profiles[POOLED_INDEX])
            + (1 - det[ri, root_i])
            * np.log((1 - profiles[selected]) / (1 - profiles[POOLED_INDEX]))
        ).sum(axis=1)
        syndrome_weight = det[ri, root_i].sum(axis=1, dtype=np.int64)
        for shot_i in np.flatnonzero(disagreements):
            shot_features.append([
                float(shot_ll_delta[shot_i]),
                float(syndrome_weight[shot_i]),
                margin,
                selected_minus_pooled_cal_score,
                float(selected),
            ])
            shot_candidate_correct.append(bool(not candidate_bad[shot_i]))
            shot_groups.append(ri * 8 + root_i)
            shot_regimes.append(ri)
            shot_records.append((ri, root_i, int(shot_i), bool(candidate_bad[shot_i]), float(shot_ll_delta[shot_i])))

    # Calibration-only block gate: features are computed solely on the
    # calibration prefix; labels from the corresponding held-out root are
    # excluded from that root's training fold.
    root_x = np.asarray([
        [r["calibration_top_minus_runnerup"], r["calibration_selected_minus_pooled_score"]]
        for r in root_records
    ], dtype=np.float64)
    root_y = np.asarray([r["candidate_better_target"] for r in root_records], dtype=np.int64)
    root_group_rows = np.arange(len(root_records))
    root_probability = np.empty(len(root_records), dtype=np.float64)
    for train, test in LeaveOneOut().split(root_x, root_y):
        root_probability[test] = fit_model(root_x[train], root_y[train]).predict_proba(root_x[test])[:, 1]
    root_uses_candidate = root_probability >= PROBABILITY_CUTOFF
    root_gate_errors = int(sum(
        (r["candidate_errors"] if root_uses_candidate[i] else r["pooled_errors"])
        for i, r in enumerate(root_records)
    ))

    # Shot-level gate: train on other calibration/evaluation roots only. At
    # inference, it would require both candidate and pooled predictions to
    # establish their disagreement, so it costs at least a second decode.
    shot_x = np.asarray(shot_features, dtype=np.float64)
    shot_y = np.asarray(shot_candidate_correct, dtype=np.int64)
    shot_group = np.asarray(shot_groups, dtype=np.int64)
    shot_regime = np.asarray(shot_regimes, dtype=np.int64)
    shot_probability = np.empty(len(shot_y), dtype=np.float64)
    logo = LeaveOneGroupOut()
    for train, test in logo.split(shot_x, shot_y, shot_group):
        shot_probability[test] = fit_model(shot_x[train], shot_y[train]).predict_proba(shot_x[test])[:, 1]
    shot_uses_candidate = shot_probability >= PROBABILITY_CUTOFF
    candidate_harm_when_applied = int(np.count_nonzero(shot_y[shot_uses_candidate] == 0))
    candidate_help_when_applied = int(np.count_nonzero(shot_y[shot_uses_candidate]))
    fallback_count = int(np.count_nonzero(~shot_uses_candidate))
    missed_candidate_wins = int(np.count_nonzero(shot_y[~shot_uses_candidate]))
    avoided_candidate_harms = int(np.count_nonzero(shot_y[~shot_uses_candidate] == 0))

    pooled_errors = int(sum(r["pooled_errors"] for r in root_records))
    selected_errors = int(sum(r["candidate_errors"] for r in root_records))
    total_shots = int(sum(r["shots"] for r in root_records))
    # On disagreements, candidate correctness means pooled fails and vice versa.
    per_shot_gate_errors = pooled_errors - int(shot_y.sum()) + candidate_harm_when_applied + missed_candidate_wins
    simple_likelihood_gate_candidate_choices = int(sum(
        1 for rec in shot_records if rec[4] > 0
    ))
    assert simple_likelihood_gate_candidate_choices == len(shot_records)

    per_root_csv = HERE / "GATE_PER_ROOT.csv"
    fields = list(root_records[0].keys()) + ["loo_candidate_better_probability", "gate_uses_candidate"]
    with per_root_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i, record in enumerate(root_records):
            writer.writerow({**record,
                             "loo_candidate_better_probability": float(root_probability[i]),
                             "gate_uses_candidate": bool(root_uses_candidate[i])})

    per_shot_csv = HERE / "GATE_DISAGREEMENT_SUMMARY.csv"
    by_regime = {}
    for ri, name in enumerate(REGIMES):
        idx = np.flatnonzero(shot_regime == ri)
        choose = shot_uses_candidate[idx]
        truth = shot_y[idx]
        by_regime[name] = {
            "disagreements": int(len(idx)),
            "candidate_correct": int(truth.sum()),
            "pooled_correct": int((~truth.astype(bool)).sum()),
            "gate_candidate_choices": int(choose.sum()),
            "gate_candidate_harms": int(np.count_nonzero(~truth[choose].astype(bool))),
            "gate_candidate_helps": int(np.count_nonzero(truth[choose].astype(bool))),
            "gate_fallback_choices": int((~choose).sum()),
        }
    with per_shot_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["regime", *next(iter(by_regime.values())).keys()])
        writer.writeheader()
        for name, row in by_regime.items():
            writer.writerow({"regime": name, **row})

    # Re-state the calibration-only and score-based comparators from the raw
    # arrays. The simple likelihood threshold selects the candidate on all
    # 225 disagreement instances in this dataset.
    errors = {
        "pooled_fixed_no_update": pooled_errors,
        "always_adaptive_equals_existing_calibration_selected": selected_errors,
        "calibration_confidence_gate_loo_0_5": root_gate_errors,
        "shot_confidence_gate_loo_root_0_5": per_shot_gate_errors,
        "simple_detector_loglik_delta_gt_0": selected_errors,
    }
    results = {
        "status": "development_only_retrospective_cross_root_analysis_not_confirmatory",
        "source": str(RAW.relative_to(REPO)).replace("\\", "/"),
        "versions": {"numpy": np.__version__, "scikit_learn": sklearn.__version__},
        "model": {"type": "StandardScaler + LogisticRegression", "C": LOGISTIC_C,
                  "threshold": PROBABILITY_CUTOFF, "threshold_rule": "fixed 0.5 equal-cost classification cutoff"},
        "data": {"roots": len(root_records), "shots": total_shots,
                 "disagreements": int(len(shot_records)),
                 "selected_vs_pooled_disagreement_rate": float(len(shot_records) / total_shots)},
        "paired_errors": errors,
        "ler": {k: float(v / total_shots) for k, v in errors.items()},
        "paired_discordance": {
            "candidate_only_wrong": int(sum(r["candidate_only_wrong"] for r in root_records)),
            "pooled_only_wrong": int(sum(r["pooled_only_wrong"] for r in root_records)),
        },
        "calibration_confidence_gate": {
            "features": ["calibration score top-runner-up margin", "selected-minus-pooled calibration score"],
            "out_of_root_auc": float(roc_auc_score(root_y, root_probability)),
            "out_of_root_brier": float(brier_score_loss(root_y, root_probability)),
            "constant_prevalence_brier": float(np.mean(root_y) * (1 - np.mean(root_y))),
            "candidate_better_roots": int(root_y.sum()),
            "candidate_worse_roots": int(sum(r["candidate_minus_pooled_errors"] > 0 for r in root_records)),
            "ties": int(sum(r["candidate_minus_pooled_errors"] == 0 for r in root_records)),
            "candidate_selected_roots": int(root_uses_candidate.sum()),
            "fallback_roots": int((~root_uses_candidate).sum()),
            "fallback_fraction": float((~root_uses_candidate).mean()),
            "harmful_selected_roots": int(sum(root_uses_candidate[i] and r["candidate_minus_pooled_errors"] > 0 for i, r in enumerate(root_records))),
            "helpful_selected_roots": int(sum(root_uses_candidate[i] and r["candidate_minus_pooled_errors"] < 0 for i, r in enumerate(root_records))),
            "candidate_errors_when_selected": int(sum(r["candidate_errors"] for i, r in enumerate(root_records) if root_uses_candidate[i])),
            "pooled_errors_on_fallback_roots": int(sum(r["pooled_errors"] for i, r in enumerate(root_records) if not root_uses_candidate[i])),
            "limitations": "24 roots only; classifier performance is cross-validated within one exploratory dataset; not an independent policy test."
        },
        "shot_confidence_gate": {
            "features": ["per-shot detector-marginal log-likelihood difference", "detector weight",
                         "calibration top-runner-up margin", "calibration selected-minus-pooled score", "selected decoder index"],
            "target": "candidate prediction correct conditional on candidate and pooled predictions disagree",
            "cross_validation": "leave-one-calibration/evaluation-root-out; all features for held-out root excluded from fit",
            "out_of_root_auc": float(roc_auc_score(shot_y, shot_probability)),
            "out_of_root_brier": float(brier_score_loss(shot_y, shot_probability)),
            "constant_prevalence_brier": float(np.mean(shot_y) * (1 - np.mean(shot_y))),
            "candidate_choices_on_disagreements": int(shot_uses_candidate.sum()),
            "fallback_choices_on_disagreements": fallback_count,
            "fallback_fraction_on_disagreements": float(fallback_count / len(shot_y)),
            "candidate_harms_when_applied": candidate_harm_when_applied,
            "candidate_helps_when_applied": candidate_help_when_applied,
            "candidate_harm_rate_when_applied": float(candidate_harm_when_applied / max(1, int(shot_uses_candidate.sum()))),
            "missed_candidate_wins_on_fallback": missed_candidate_wins,
            "avoided_candidate_harms_on_fallback": avoided_candidate_harms,
            "limitations": "Requires both decoder predictions before gating; increases decode work. Only 225 disagreement shots across 24 roots."
        },
        "simple_detector_likelihood_threshold": {
            "rule": "use calibrated candidate when its factorized detector-marginal log likelihood exceeds pooled model's",
            "candidate_choices_on_disagreements": simple_likelihood_gate_candidate_choices,
            "fallback_choices_on_disagreements": 0,
            "result": "identical to always-adaptive selection on this evidence; confidence score did not create selectivity"
        },
        "runtime": {"analysis_wall_seconds": float(time.perf_counter() - started),
                    "decode_latency": "not measurable from saved predictions; the gate analysis does not rerun the decoders"},
        "memory": {"decode_model_memory": "not measured; saved predictions omit native decoder object sizes",
                   "analysis_process_before_loading_npz": memory_before,
                   "analysis_process_after_analysis": process_memory(),
                   "interpretation": "Process-level Windows counters include Python, NumPy, scikit-learn and mapped arrays; they do not isolate a decoder or online gate."},
        "causality": {
            "features_use_only_detector_data": True,
            "calibration_gate_features_precede_evaluation_block": True,
            "shot_gate_uses_current_detector_only": True,
            "true_logical_labels_in_gate_features": False,
            "held_out_fold_labels_in_training": False,
            "hidden_regime_id_in_features": False,
            "regime_id_used_for_stratified_reporting_only": True,
        },
        "files": {"per_root": str(per_root_csv.name), "per_shot_summary": str(per_shot_csv.name)},
    }
    (HERE / "GATE_ANALYSIS_RESULTS.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
