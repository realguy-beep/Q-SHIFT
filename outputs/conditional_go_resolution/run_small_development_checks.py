"""Bounded development-only false-update and decoder-utility feasibility checks.

No confirmatory stream is generated.  All generated samples are independent of
the historical Q-SHIFT phases and the selected policies never see observables.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path

import numpy as np
import scipy.stats
import stim
import pymatching

from decoder_rebuild_fixture import build_version, decode

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE
GRID = [(g, m) for g in (0.001, 0.003, 0.006) for m in (0.001, 0.003, 0.006)]
REGIMES = {
    "data_heavy": (0.006, 0.001),
    "nominal": (0.003, 0.003),
    "measurement_heavy": (0.001, 0.006),
}
# New feasibility-only namespace, screened against recoverable text artifacts.
SEEDS = {
    "fixture": [99870001, 99870002, 99870003],
    "templates": list(range(99871001, 99871010)),
    "calibration": [99872001 + 100 * r + k for r in range(3) for k in range(8)],
    "evaluation": [99873001 + 100 * r + k for r in range(3) for k in range(8)],
    "stationary_reference": [99874001],
    "stationary_threshold_calibration": list(range(99874101, 99874201)),
    "stationary_threshold_validation": list(range(99874301, 99874401)),
    "bootstrap": [99875001],
}


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def seed_screen() -> dict:
    seeds = [int(s) for vals in SEEDS.values() for s in vals]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("new feasibility seeds collide internally")
    search_root = REPO / "outputs"
    exact = re.compile(r"(?<!\d)(?:" + "|".join(map(str, sorted(seeds, key=lambda x: len(str(x)), reverse=True))) + r")(?!\d)")
    scanned, hits = [], []
    for p in search_root.rglob("*"):
        if not p.is_file() or HERE in p.parents or p.suffix.lower() not in {".json", ".csv", ".md", ".py", ".txt", ".log"}:
            continue
        scanned.append(str(p.relative_to(REPO)))
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in exact.finditer(content):
            hits.append({"file": str(p.relative_to(REPO)), "seed": int(m.group())})
    if hits:
        raise RuntimeError(f"feasibility seed collision(s): {hits[:10]}")
    return {
        "seed_namespace": SEEDS,
        "unique_new_seeds": len(seeds),
        "internal_unique": True,
        "historical_text_files_scanned": len(scanned),
        "historical_text_file_list": scanned,
        "exact_value_collisions": hits,
        "coverage_limit": "Text-readable output artifacts only; opaque binary archives were not decoded for seed fields.",
    }


def circuit(gate_p: float, meas_p: float, rounds: int = 5) -> stim.Circuit:
    return stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=3, rounds=rounds,
        after_clifford_depolarization=gate_p,
        before_measure_flip_probability=meas_p,
    )


def sample(gate_p: float, meas_p: float, seed: int, shots: int, rounds: int = 5):
    c = circuit(gate_p, meas_p, rounds)
    det, obs = c.compile_detector_sampler(seed=int(seed)).sample(
        shots, separate_observables=True
    )
    if det.shape != (shots, c.num_detectors) or obs.shape != (shots, 1):
        raise RuntimeError("Stim sample dimensions differ from circuit metadata")
    return det.astype(np.uint8), obs[:, 0].astype(np.uint8), c


def profile(det: np.ndarray) -> np.ndarray:
    return (det.sum(axis=0, dtype=np.int64) + 0.5) / (len(det) + 1.0)


def choose_from_detectors(det: np.ndarray, profiles: np.ndarray) -> int:
    """Finite-bank detector-marginal likelihood; observables are absent by API."""
    n = len(det)
    counts = det.sum(axis=0, dtype=np.int64)
    scores = (counts[None, :] * np.log(profiles) +
              (n - counts)[None, :] * np.log1p(-profiles)).sum(axis=1)
    return int(np.argmax(scores))  # deterministic lowest-index tie break


def exact_cp(k: int, n: int, alpha: float = 0.05):
    low = 0.0 if k == 0 else float(scipy.stats.beta.ppf(alpha / 2, k, n - k + 1))
    high = 1.0 if k == n else float(scipy.stats.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return [low, high]


def trigger_stat(blocks: np.ndarray, ref_p: np.ndarray, ref_n: int, window: int = 4) -> float:
    """Max absolute studentized detector-marginal change over all overlapping windows."""
    maxima = []
    n_per = blocks.shape[1]
    for end in range(window - 1, len(blocks)):
        w = blocks[end - window + 1:end + 1].reshape(-1, blocks.shape[2])
        p = w.mean(axis=0)
        var = np.maximum(ref_p * (1 - ref_p) * (1 / len(w) + 1 / ref_n), 1e-12)
        z = np.abs(p - ref_p) / np.sqrt(var)
        maxima.append(float(z.max()))
    return max(maxima, default=0.0)


def stationary_schedules(seed_list: list[int], ref_p: np.ndarray, ref_n: int,
                         blocks_n: int = 12, shots_per_block: int = 128,
                         window: int = 4):
    c = circuit(0.003, 0.003, rounds=5)
    maxima = []
    raw_schedules = []
    for seed in seed_list:
        det = c.compile_detector_sampler(seed=int(seed)).sample(
            blocks_n * shots_per_block
        ).astype(np.uint8)
        blocks = det.reshape(blocks_n, shots_per_block, c.num_detectors)
        stat = trigger_stat(blocks, ref_p, ref_n, window)
        maxima.append(stat)
        raw_schedules.append(blocks)
    return np.asarray(maxima, dtype=np.float64), np.stack(raw_schedules)


def run_trigger_check() -> dict:
    start = time.perf_counter()
    ref, _, c = sample(0.003, 0.003, SEEDS["stationary_reference"][0], 8192)
    rp = profile(ref)
    train, train_raw = stationary_schedules(SEEDS["stationary_threshold_calibration"], rp, len(ref))
    # One full-schedule familywise threshold: the maximum over every detector and
    # every overlapping trailing-window look in each schedule is the calibration unit.
    threshold = float(np.quantile(train, 0.95, method="higher"))
    valid, valid_raw = stationary_schedules(SEEDS["stationary_threshold_validation"], rp, len(ref))
    alarms = int(np.count_nonzero(valid > threshold))
    schedule_rows = [
        {"split": split, "seed": int(seed), "schedule_max_stat": float(value),
         "familywise_alarm": bool(value > threshold), "threshold": threshold}
        for split, seeds, vals in (
            ("threshold_calibration", SEEDS["stationary_threshold_calibration"], train),
            ("independent_validation", SEEDS["stationary_threshold_validation"], valid),
        )
        for seed, value in zip(seeds, vals)
    ]
    return {
        "procedure": "empirical 95th-percentile threshold on schedule-maximum statistic; one accepted update maximum per 12-block schedule",
        "stationary_condition": {"gate_p": 0.003, "measurement_p": 0.003, "distance": 3, "rounds": 5},
        "reference_shots": len(ref),
        "detectors": int(c.num_detectors),
        "blocks_per_schedule": 12,
        "shots_per_block": 128,
        "overlapping_window_blocks": 4,
        "checks_per_schedule": 9,
        "threshold_calibration_schedules": len(train),
        "validation_schedules": len(valid),
        "threshold_max_z": threshold,
        "train_schedule_max_quantiles": {str(q): float(np.quantile(train, q)) for q in (0.5, 0.9, 0.95, 0.99)},
        "validation_false_update_schedules": alarms,
        "validation_false_update_rate": alarms / len(valid),
        "validation_exact_binomial_95_ci": exact_cp(alarms, len(valid)),
        "threshold_passes_target_5pct_on_validation": alarms / len(valid) <= 0.05,
        "stationary_validation_max_stat_quantiles": {str(q): float(np.quantile(valid, q)) for q in (0.5, 0.9, 0.95, 0.99)},
        "seed_calibration_validation_disjoint": not set(SEEDS["stationary_threshold_calibration"]) & set(SEEDS["stationary_threshold_validation"]),
        "runtime_seconds": time.perf_counter() - start,
        "schedule_rows": schedule_rows,
        "raw_trigger_arrays": {
            "reference_detectors": ref,
            "threshold_calibration_blocks": train_raw,
            "validation_blocks": valid_raw,
        },
        "limitations": [
            "This controls one event-triggered update (the first alarm) per fixed-length schedule; repeated post-update resets require a separate whole-policy stationary calibration.",
            "The max statistic uses detector marginal Bernoulli approximations and does not test identifiability of all DEM parameters.",
            "100 validation schedules give a feasibility estimate, not a precise tail guarantee; the exact interval is reported.",
        ],
    }


def bootstrap_stratified(diffs_by_regime: dict[str, list[float]], draws=20000, seed=99875001):
    rng = np.random.default_rng(seed)
    keys = list(REGIMES)
    arrays = {k: np.asarray(diffs_by_regime[k], dtype=np.float64) for k in keys}
    vals = np.empty(draws, dtype=np.float64)
    for i in range(draws):
        means = []
        for k in keys:
            a = arrays[k]
            means.append(float(a[rng.integers(0, len(a), size=len(a))].mean()))
        vals[i] = float(np.mean(means))
    return [float(x) for x in np.quantile(vals, [0.025, 0.975])]


def run_utility_check() -> dict:
    started = time.perf_counter()
    bank = []
    profiles = []
    template_detectors = np.zeros((9, 2048, 40), dtype=np.uint8)
    template_rows = []
    for i, (gp, mp) in enumerate(GRID):
        det, _, c = sample(gp, mp, SEEDS["templates"][i], 2048)
        template_detectors[i] = det
        profiles.append(profile(det))
        model = pymatching.Matching.from_detector_error_model(
            c.detector_error_model(decompose_errors=True)
        )
        bank.append((gp, mp, model, c.num_detectors, c.num_observables))
        template_rows.append({"decoder_grid_index": i, "gate_p": gp, "measurement_p": mp,
                              "template_shots": len(det), "detectors": c.num_detectors,
                              "observables": c.num_observables})
    profiles_arr = np.stack(profiles)
    pooled_index, nominal_index = 1, 4  # frozen Stage-1 pooled point and nominal point
    root_rows = []
    cal_detectors = np.zeros((3, 8, 1024, 40), dtype=np.uint8)
    eval_detectors = np.zeros((3, 8, 4096, 40), dtype=np.uint8)
    eval_observables = np.zeros((3, 8, 4096), dtype=np.uint8)
    eval_predictions = np.zeros((3, 8, 3, 4096), dtype=np.uint8)
    by_regime = {r: [] for r in REGIMES}
    for ri, (regime, (gp, mp)) in enumerate(REGIMES.items()):
        for root in range(8):
            cal_seed = SEEDS["calibration"][ri * 8 + root]
            eval_seed = SEEDS["evaluation"][ri * 8 + root]
            cal_det, _, cal_c = sample(gp, mp, cal_seed, 1024)
            # The selector receives only detector samples. Build the selected graph
            # after selection to exercise parameter-to-DEM-to-Matching reconstruction.
            choice = choose_from_detectors(cal_det, profiles_arr)
            cal_detectors[ri, root] = cal_det
            est_gp, est_mp = GRID[choice]
            eval_det, obs, eval_c = sample(gp, mp, eval_seed, 4096)
            eval_detectors[ri, root] = eval_det
            eval_observables[ri, root] = obs
            if cal_c.num_detectors != eval_c.num_detectors or cal_c.num_observables != 1:
                raise RuntimeError("calibration/evaluation circuit schema mismatch")
            selected_model = pymatching.Matching.from_detector_error_model(
                circuit(est_gp, est_mp).detector_error_model(decompose_errors=True)
            )
            pooled_model = bank[pooled_index][2]
            nominal_model = bank[nominal_index][2]
            p_sel = decode(type("V", (), {"matching": selected_model})(), eval_det)
            p_pool = decode(type("V", (), {"matching": pooled_model})(), eval_det)
            p_nom = decode(type("V", (), {"matching": nominal_model})(), eval_det)
            eval_predictions[ri, root, 0] = p_sel
            eval_predictions[ri, root, 1] = p_pool
            eval_predictions[ri, root, 2] = p_nom
            err_sel = p_sel != obs
            err_pool = p_pool != obs
            err_nom = p_nom != obs
            cand_only = int(np.count_nonzero(err_sel & ~err_pool))
            pool_only = int(np.count_nonzero(~err_sel & err_pool))
            diff = float(err_sel.mean() - err_pool.mean())
            by_regime[regime].append(diff)
            root_rows.append({
                "regime": regime,
                "root_index": root,
                "calibration_seed": cal_seed,
                "evaluation_seed": eval_seed,
                "calibration_shots": len(cal_det),
                "evaluation_shots": len(eval_det),
                "selected_grid_index": choice,
                "selected_gate_p": est_gp,
                "selected_measurement_p": est_mp,
                "heldout_labels_accessed_by_selector": False,
                "selected_errors": int(err_sel.sum()),
                "selected_ler": float(err_sel.mean()),
                "pooled_fixed_index": pooled_index,
                "pooled_errors": int(err_pool.sum()),
                "pooled_ler": float(err_pool.mean()),
                "nominal_fixed_index": nominal_index,
                "nominal_errors": int(err_nom.sum()),
                "nominal_ler": float(err_nom.mean()),
                "selected_vs_pooled_prediction_disagreements": int(np.count_nonzero(p_sel != p_pool)),
                "selected_only_wrong": cand_only,
                "pooled_only_wrong": pool_only,
                "paired_delta_ler_selected_minus_pooled": diff,
            })
    regime_results = {}
    for regime in REGIMES:
        rows = [r for r in root_rows if r["regime"] == regime]
        ns = sum(r["evaluation_shots"] for r in rows)
        sel_err = sum(r["selected_errors"] for r in rows)
        pool_err = sum(r["pooled_errors"] for r in rows)
        regime_results[regime] = {
            "roots": len(rows), "shots": ns,
            "calibration_selected_errors": sel_err,
            "calibration_selected_ler": sel_err / ns,
            "pooled_fixed_errors": pool_err,
            "pooled_fixed_ler": pool_err / ns,
            "equal_paired_delta_ler_mean_root": float(np.mean(by_regime[regime])),
            "mean_candidate_only_wrong_per_root": float(np.mean([r["selected_only_wrong"] for r in rows])),
            "mean_pooled_only_wrong_per_root": float(np.mean([r["pooled_only_wrong"] for r in rows])),
            "selected_models": {str(i): sum(r["selected_grid_index"] == i for r in rows) for i in range(9)},
        }
    equal_delta = float(np.mean([regime_results[r]["equal_paired_delta_ler_mean_root"] for r in REGIMES]))
    return {
        "status": "small_development_feasibility_only",
        "circuit": "Stim rotated_memory_z, distance 3, rounds 5, native after-Clifford depolarization and before-measurement flip",
        "grid_order": [{"index": i, "gate_p": gp, "measurement_p": mp} for i, (gp, mp) in enumerate(GRID)],
        "grid_indices": {"data_heavy": 6, "nominal": 4, "measurement_heavy": 2},
        "baseline_definitions": {
            "pooled_fixed": {"index": pooled_index, "parameters": list(GRID[pooled_index]), "source": "frozen Phase 4C Stage 1 PHASE4C_BASELINE_FREEZE.json"},
            "nominal_fixed": {"index": nominal_index, "parameters": list(GRID[nominal_index])},
        },
        "template_rows": template_rows,
        "raw_utility_arrays": {
            "template_detectors": template_detectors,
            "template_profiles": profiles_arr,
            "calibration_detectors": cal_detectors,
            "evaluation_detectors": eval_detectors,
            "evaluation_observables": eval_observables,
            "evaluation_predictions": eval_predictions,
        },
        "root_count": len(root_rows),
        "total_calibration_shots": sum(r["calibration_shots"] for r in root_rows),
        "total_paired_evaluation_shots": sum(r["evaluation_shots"] for r in root_rows),
        "per_regime": regime_results,
        "equal_regime_paired_delta_ler_calibration_selected_minus_pooled": equal_delta,
        "equal_regime_seed_stratified_bootstrap_95_ci": bootstrap_stratified(by_regime),
        "seed_stratified_bootstrap_draws": 20000,
        "seed_stratified_bootstrap_seed": SEEDS["bootstrap"][0],
        "seed_disjointness": {
            "template_calibration_evaluation": len(set(SEEDS["templates"]) & (set(SEEDS["calibration"]) | set(SEEDS["evaluation"]))) == 0,
            "calibration_evaluation": len(set(SEEDS["calibration"]) & set(SEEDS["evaluation"])) == 0,
        },
        "interpretation": "Model choice is based on a finite candidate grid and detector marginals alone. This tests whether detector-fit plus graph reconstruction can alter predictions and paired logical outcomes; it does not test a continuous estimator or a dynamic policy.",
        "runtime_seconds_including_bank_templates_and_evaluation": time.perf_counter() - started,
    }, root_rows


def main():
    started = time.perf_counter()
    screening = seed_screen()
    trigger = run_trigger_check()
    utility, roots = run_utility_check()
    raw = {
        "stationary_reference_detectors": trigger["raw_trigger_arrays"]["reference_detectors"],
        "stationary_threshold_calibration_blocks": trigger["raw_trigger_arrays"]["threshold_calibration_blocks"],
        "stationary_validation_blocks": trigger["raw_trigger_arrays"]["validation_blocks"],
        **utility["raw_utility_arrays"],
    }
    np.savez_compressed(OUT / "DEVELOPMENT_RAW_EVIDENCE.npz", **raw)
    trigger_rows = trigger.pop("schedule_rows")
    trigger.pop("raw_trigger_arrays")
    utility.pop("raw_utility_arrays")
    result = {
        "versions": {"python_numpy": np.__version__, "stim": stim.__version__, "pymatching": pymatching.__version__},
        "seed_screen": screening,
        "seed_screen_summary": {k: v for k, v in screening.items() if k != "historical_text_file_list"},
        "trigger_false_update_check": trigger,
        "decoder_utility_check": utility,
        "total_seed_count": screening["unique_new_seeds"],
        "actual_stim_shots": (
            trigger["reference_shots"]
            + (trigger["threshold_calibration_schedules"] + trigger["validation_schedules"])
              * trigger["blocks_per_schedule"] * trigger["shots_per_block"]
            + utility["total_calibration_shots"] + utility["total_paired_evaluation_shots"]
            + sum(r["template_shots"] for r in utility["template_rows"])
        ),
        "wall_seconds": time.perf_counter() - started,
    }
    (OUT / "DEVELOPMENT_CHECKS.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (OUT / "UTILITY_PER_ROOT.csv").open("w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=list(roots[0]))
        writer.writeheader()
        writer.writerows(roots)
    with (OUT / "TRIGGER_SCHEDULE_MAXIMA.csv").open("w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=list(trigger_rows[0]))
        writer.writeheader()
        writer.writerows(trigger_rows)
    (OUT / "SEED_SCREEN.json").write_text(json.dumps(screening, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "seed_screen"}, indent=2))


if __name__ == "__main__":
    main()
