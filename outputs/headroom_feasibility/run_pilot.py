"""Run the frozen bounded multi-distance headroom feasibility pilot."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import platform
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pymatching
import stim

from headroom import (
    PAULI_REGIMES, bootstrap_choice_probabilities, build_decoder,
    candidate_metadata, decode, detector_count, detector_profiles,
    fit_detector_model, marginal_scores, native_circuit, pauli_circuit,
    paired_root_effect, residual_errors, scan_historical_seeds,
    select_calibration, sha256_file,
)

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
START = time.perf_counter()
SHOT_COUNTS = {"template": 0, "calibration": 0, "evaluation": 0,
               "noiseless_diagnostic": 0, "sensitivity_diagnostic": 0,
               "benchmark": 0}
TIMINGS = {"model_build_seconds": 0.0, "template_seconds": 0.0,
           "calibration_seconds": 0.0, "evaluation_seconds": 0.0,
           "independent_redecode_seconds": 0.0}
try:
    import psutil
    PROCESS = psutil.Process()
except Exception:
    psutil = None
    PROCESS = None
PEAK_RSS = 0


class PilotStop(RuntimeError):
    pass


def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def atomic_npz(path: Path, **arrays):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.stem + ".tmp.npz")
    np.savez_compressed(temp, **arrays)
    os.replace(temp, path)


def memory_rss():
    global PEAK_RSS
    if PROCESS is not None:
        rss = int(PROCESS.memory_info().rss)
        PEAK_RSS = max(PEAK_RSS, rss)
        return rss
    return None


def check_resources(extra_shots: int = 0):
    elapsed = time.perf_counter() - START
    if elapsed > CFG["resource_caps"]["wall_seconds"]:
        raise PilotStop(f"wall cap exceeded at {elapsed:.1f} seconds")
    rss = memory_rss()
    if rss is not None and rss > CFG["resource_caps"]["peak_rss_bytes"]:
        raise PilotStop(f"RSS cap exceeded: {rss} bytes")
    if sum(SHOT_COUNTS.values()) + extra_shots > CFG["resource_caps"]["planned_max_total_shots"]:
        raise PilotStop("planned total-shot cap would be exceeded")


def bank_specs():
    native_grid = [tuple(v) for v in CFG["native_candidate_grid_order"]]
    specs = []
    for family in ("native", "pauli_biased"):
        regimes = list(CFG["native_regimes"]) if family == "native" else list(CFG["pauli_regimes"])
        candidates = native_grid if family == "native" else list(CFG["pauli_channel_candidate_order"])
        for distance in CFG["distances"]:
            for memory in CFG["memory_bases"]:
                specs.append({
                    "family": family, "distance": int(distance), "memory": memory,
                    "regimes": regimes, "candidates": candidates,
                    "key": f"{family}_d{distance}_{memory}",
                })
    return specs


def generating_circuit(spec, regime):
    if spec["family"] == "native":
        gate_p, meas_p = CFG["native_regimes"][regime]
        return native_circuit(spec["memory"], spec["distance"], gate_p, meas_p)
    return pauli_circuit(
        spec["memory"], spec["distance"], regime,
        CFG["pauli_gate_probability"], CFG["pauli_measurement_probability"],
        CFG["pauli_bias_ratio"],
    )


def candidate_circuit(spec, candidate):
    if spec["family"] == "native":
        return native_circuit(spec["memory"], spec["distance"], candidate[0], candidate[1])
    return pauli_circuit(
        spec["memory"], spec["distance"], candidate,
        CFG["pauli_gate_probability"], CFG["pauli_measurement_probability"],
        CFG["pauli_bias_ratio"],
    )


def make_seed_inventory(specs, historical):
    templates = []
    calibration = []
    evaluation = []
    noiseless = []
    sensitivity = []
    benchmark = []
    choice_bootstrap = []
    root_ci_bootstrap = []
    t0 = CFG["seed_namespaces"]["template_start"]
    c0 = CFG["seed_namespaces"]["calibration_start"]
    e0 = CFG["seed_namespaces"]["evaluation_start"]
    n0 = CFG["seed_namespaces"]["noiseless_diagnostic_start"]
    s0 = CFG["seed_namespaces"]["noise_sensitivity_diagnostic_start"]
    b0 = CFG["seed_namespaces"]["benchmark_start"]
    boot0 = CFG["bootstrap_seed"]
    t_index = c_index = e_index = b_index = ci = 0
    for bi, spec in enumerate(specs):
        for candidate_index, candidate in enumerate(spec["candidates"]):
            templates.append({
                "bank": spec["key"], "candidate_index": candidate_index,
                "candidate": candidate, "seed": t0 + t_index,
            })
            t_index += 1
        noiseless.append({"bank": spec["key"], "seed": n0 + bi})
        sensitivity.append({"bank": spec["key"], "seed": s0 + bi})
        benchmark.append({"bank": spec["key"], "seed": b0 + bi})
        choice_bootstrap.append({"bank": spec["key"], "seed": boot0 + bi})
        for regime in spec["regimes"]:
            root_bootstrap_seed = 97991001 + ci
            root_ci_bootstrap.append({
                "bank": spec["key"], "regime": regime, "seed": root_bootstrap_seed,
            })
            ci += 1
            for root_index in range(CFG["calibration_roots_per_cell"]):
                calibration.append({
                    "bank": spec["key"], "regime": regime, "root_index": root_index,
                    "seed": c0 + c_index,
                })
                c_index += 1
            for root_index in range(CFG["evaluation_roots_per_cell"]):
                evaluation.append({
                    "bank": spec["key"], "regime": regime, "root_index": root_index,
                    "seed": e0 + e_index,
                })
                e_index += 1
    all_rows = templates + calibration + evaluation + noiseless + sensitivity + benchmark + choice_bootstrap + root_ci_bootstrap
    seeds = [int(r["seed"]) for r in all_rows]
    assert len(seeds) == len(set(seeds)), "duplicate proposed seed"
    collisions = sorted(set(seeds) & set(historical))
    if collisions:
        raise PilotStop(f"historical seed collision(s): {collisions[:20]}")
    return {
        "template": templates, "calibration": calibration, "evaluation": evaluation,
        "noiseless_diagnostic": noiseless, "sensitivity_diagnostic": sensitivity,
        "benchmark": benchmark, "choice_bootstrap": choice_bootstrap,
        "root_ci_bootstrap": root_ci_bootstrap,
        "unique_proposed_seed_count": len(seeds),
        "proposed_seed_count": len(all_rows),
        "historical_collisions": collisions,
        "historical_seed_values_recovered": len(historical),
        "historical_coverage_limit": "Recorded textual/config/filename values only; unrecorded streams are unknowable.",
    }


def prepare_banks(specs):
    banks = {}
    model_inventory = {"banks": [], "software": {
        "python": platform.python_version(), "stim": stim.__version__,
        "pymatching": pymatching.__version__, "numpy": np.__version__,
    }}
    started = time.perf_counter()
    for spec in specs:
        check_resources()
        models = []
        circuits = []
        dems = []
        correlated = []
        metadata = []
        for ci, candidate in enumerate(spec["candidates"]):
            c = candidate_circuit(spec, candidate)
            model, dem, is_correlated = build_decoder(c, spec["family"])
            if c.num_detectors != detector_count(spec["distance"]):
                raise PilotStop(
                    f"wrong detector count for {spec['key']}/{ci}: "
                    f"{c.num_detectors} != {detector_count(spec['distance'])}")
            if c.num_observables != 1:
                raise PilotStop(f"expected one logical observable for {spec['key']}/{ci}")
            model_path = ROOT / "models" / spec["key"]
            model_path.mkdir(parents=True, exist_ok=True)
            circuit_file = model_path / f"candidate_{ci}.stim"
            dem_file = model_path / f"candidate_{ci}.dem"
            circuit_file.write_text(str(c), encoding="utf-8")
            dem_file.write_text(str(dem), encoding="utf-8")
            rec = candidate_metadata(c, dem, model, spec["family"], candidate, is_correlated)
            rec["candidate_index"] = ci
            rec["circuit_file"] = str(circuit_file.relative_to(ROOT))
            rec["dem_file"] = str(dem_file.relative_to(ROOT))
            rec["circuit_file_sha256"] = sha256_file(circuit_file)
            rec["dem_file_sha256"] = sha256_file(dem_file)
            models.append(model)
            circuits.append(c)
            dems.append(dem)
            correlated.append(is_correlated)
            metadata.append(rec)
        banks[spec["key"]] = {
            "spec": spec, "models": models, "circuits": circuits, "dems": dems,
            "correlated": correlated, "metadata": metadata,
        }
        model_inventory["banks"].append({
            "key": spec["key"], "family": spec["family"], "distance": spec["distance"],
            "memory": spec["memory"], "regimes": spec["regimes"],
            "candidate_order": spec["candidates"], "candidates": metadata,
        })
    TIMINGS["model_build_seconds"] = time.perf_counter() - started
    atomic_json(ROOT / "MODEL_INVENTORY.json", model_inventory)
    return banks, model_inventory


def do_diagnostics_and_benchmark(banks, seeds):
    diagnostics = []
    benchmark_rows = []
    t = time.perf_counter()
    for bi, key in enumerate(banks):
        bank = banks[key]
        spec = bank["spec"]
        no_noise = bank["circuits"][0].without_noise()
        noiseless_seed = seeds["noiseless_diagnostic"][bi]["seed"]
        no_d, no_y = no_noise.compile_detector_sampler(seed=noiseless_seed).sample(
            shots=256, separate_observables=True)
        SHOT_COUNTS["noiseless_diagnostic"] += 256
        if no_d.shape != (256, detector_count(spec["distance"])) or no_y.shape != (256, 1):
            raise PilotStop(f"noiseless schema mismatch for {key}")
        if no_d.any() or no_y.any():
            raise PilotStop(f"noiseless circuit produced nonzero detector/observable for {key}")
        regime = spec["regimes"][0]
        c = generating_circuit(spec, regime)
        sens_seed = seeds["sensitivity_diagnostic"][bi]["seed"]
        t0 = time.perf_counter()
        sens_d, sens_y = c.compile_detector_sampler(seed=sens_seed).sample(
            shots=512, separate_observables=True)
        sens_seconds = time.perf_counter() - t0
        SHOT_COUNTS["sensitivity_diagnostic"] += 512
        if sens_d.shape != (512, detector_count(spec["distance"])) or sens_y.shape != (512, 1):
            raise PilotStop(f"noise sensitivity diagnostic shape mismatch for {key}")
        if not sens_d.any() and not sens_y.any():
            raise PilotStop(f"noise sensitivity diagnostic was all zero for {key}")
        diagnostics.append({
            "bank": key, "expected_detectors": detector_count(spec["distance"]),
            "actual_detectors": int(no_noise.num_detectors),
            "observables": int(no_noise.num_observables),
            "noiseless_shots": 256, "noiseless_all_zero": True,
            "sensitivity_shots": 512, "sensitivity_nonzero": True,
            "sensitivity_seconds": sens_seconds,
        })
        bseed = seeds["benchmark"][bi]["seed"]
        bt0 = time.perf_counter()
        bench_c = generating_circuit(spec, regime)
        bd, by = bench_c.compile_detector_sampler(seed=bseed).sample(
            shots=1000, separate_observables=True)
        sample_seconds = time.perf_counter() - bt0
        SHOT_COUNTS["benchmark"] += 1000
        decode_times = []
        for model, corr in zip(bank["models"], bank["correlated"]):
            dt = time.perf_counter()
            pred = decode(model, bd, corr)
            decode_times.append(time.perf_counter() - dt)
            if pred.shape != (1000,):
                raise PilotStop(f"benchmark prediction shape mismatch in {key}")
        benchmark_rows.append({
            "bank": key, "shots": 1000, "detectors": int(bd.shape[1]),
            "sampling_seconds": sample_seconds,
            "sampling_seconds_per_shot": sample_seconds / 1000,
            "decode_seconds_all_candidates": sum(decode_times),
            "decode_seconds_per_shot_per_candidate": float(np.mean(decode_times)) / 1000,
            "decode_seconds_each_candidate": decode_times,
            "raw_observable_errors": int(by.sum()),
        })
    planned_main_seconds = 0.0
    planned_redecode_seconds = 0.0
    for row in benchmark_rows:
        bank = banks[row["bank"]]
        candidate_count = len(bank["spec"]["candidates"])
        # 3 regimes × 5 roots × 5k shots in calibration and evaluation.
        main_shots = 3 * CFG["calibration_roots_per_cell"] * CFG["shots_per_root"] * 2
        template_shots = candidate_count * CFG["template_shots_per_candidate"]
        sampling_rate = row["sampling_seconds_per_shot"]
        decode_rate = row["decode_seconds_all_candidates"] / (1000 * candidate_count)
        planned_main_seconds += sampling_rate * (main_shots + template_shots)
        planned_redecode_seconds += decode_rate * main_shots * candidate_count * 2
    forecast_seconds = 1.25 * (planned_main_seconds + planned_redecode_seconds)
    return {
        "diagnostics": diagnostics,
        "benchmark": benchmark_rows,
        "benchmark_wall_seconds": time.perf_counter() - t,
        "forecast": {
            "sampling_and_template_seconds": planned_main_seconds,
            "calibration_and_evaluation_plus_redecode_seconds": planned_redecode_seconds,
            "with_25_percent_headroom_seconds": forecast_seconds,
            "available_wall_seconds_after_preflight": max(
                0.0, CFG["resource_caps"]["wall_seconds"] - (time.perf_counter() - START)),
        },
        "peak_rss_bytes": memory_rss(),
    }


def write_raw_shot(path: Path, detectors, observable, predictions, seed,
                   regime, family, distance, memory, stage):
    packed = np.packbits(np.asarray(detectors, dtype=np.uint8), axis=1, bitorder="little")
    arrays = {
        "detectors_packed_little": packed,
        "detector_count": np.asarray(detectors.shape[1], dtype=np.int32),
        "observable": np.asarray(observable, dtype=np.uint8),
        "predictions": np.asarray(predictions, dtype=np.uint8),
        "seed": np.asarray(seed, dtype=np.uint32),
        "regime": np.asarray(regime),
        "family": np.asarray(family),
        "distance": np.asarray(distance, dtype=np.int16),
        "memory": np.asarray(memory),
        "stage": np.asarray(stage),
    }
    atomic_npz(path, **arrays)


def unpack_raw(path: Path):
    with np.load(path, allow_pickle=False) as z:
        packed = z["detectors_packed_little"]
        count = int(z["detector_count"])
        detectors = np.unpackbits(packed, axis=1, bitorder="little")[:, :count]
        y = z["observable"].astype(np.uint8)
        predictions = z["predictions"].astype(np.uint8)
        seed = int(z["seed"])
        metadata = {
            "regime": str(z["regime"]), "family": str(z["family"]),
            "distance": int(z["distance"]), "memory": str(z["memory"]),
            "stage": str(z["stage"]),
        }
    if detectors.ndim != 2 or y.shape != (len(detectors),):
        raise ValueError(f"invalid detector or label shape in {path}")
    if predictions.ndim != 2 or predictions.shape[1] != len(y):
        raise ValueError(f"invalid prediction shape in {path}")
    if not np.isin(detectors, (0, 1)).all() or not np.isin(y, (0, 1)).all():
        raise ValueError(f"nonbinary detector/observable in {path}")
    if not np.isin(predictions, (0, 1)).all():
        raise ValueError(f"nonbinary prediction in {path}")
    return detectors.astype(np.uint8), y, predictions, seed, metadata


def sample_and_decode(bank, regime: str, seed: int, shots: int, stage: str,
                      write_path: Path):
    spec = bank["spec"]
    c = generating_circuit(spec, regime)
    t = time.perf_counter()
    detectors, observables = c.compile_detector_sampler(seed=int(seed)).sample(
        shots=shots, separate_observables=True)
    if stage not in ("calibration", "evaluation"):
        raise ValueError(f"unexpected saved-sample stage: {stage}")
    SHOT_COUNTS[stage] += len(detectors)
    sample_seconds = time.perf_counter() - t
    y = observables[:, 0].astype(np.uint8)
    if detectors.shape != (shots, detector_count(spec["distance"])):
        raise RuntimeError(f"detector dimensions changed for {spec['key']}/{regime}")
    preds = []
    decode_seconds = 0.0
    for model, corr in zip(bank["models"], bank["correlated"]):
        dt = time.perf_counter()
        preds.append(decode(model, detectors, corr))
        decode_seconds += time.perf_counter() - dt
    pred_matrix = np.stack(preds).astype(np.uint8)
    write_raw_shot(write_path, detectors, y, pred_matrix, seed, regime,
                   spec["family"], spec["distance"], spec["memory"], stage)
    residuals = residual_errors(y, pred_matrix)
    return {
        "detectors": detectors.astype(np.uint8), "labels": y,
        "predictions": pred_matrix, "residuals": residuals,
        "sample_seconds": sample_seconds, "decode_seconds": decode_seconds,
    }


def prepare_templates_and_calibration(banks, seed_inventory):
    all_selections = []
    cal_data_for_verification = []
    template_seed_map = {
        (r["bank"], r["candidate_index"]): r["seed"]
        for r in seed_inventory["template"]
    }
    cal_seed_map = {}
    for r in seed_inventory["calibration"]:
        cal_seed_map[(r["bank"], r["regime"], r["root_index"])] = r["seed"]
    bootstrap_map = {r["bank"]: r["seed"] for r in seed_inventory["choice_bootstrap"]}
    for bank_index, (key, bank) in enumerate(banks.items()):
        check_resources()
        spec = bank["spec"]
        profiles = []
        template_metadata = []
        t_start = time.perf_counter()
        for ci, (candidate_c, candidate, candidate_meta) in enumerate(
                zip(bank["circuits"], spec["candidates"], bank["metadata"])):
            seed = template_seed_map[(key, ci)]
            d = candidate_c.compile_detector_sampler(seed=seed).sample(
                shots=CFG["template_shots_per_candidate"])
            SHOT_COUNTS["template"] += len(d)
            profile = detector_profiles(d)
            profiles.append(profile)
            path = ROOT / "templates" / f"{key}_candidate_{ci}.npz"
            packed = np.packbits(d, axis=1, bitorder="little")
            atomic_npz(path, detectors_packed_little=packed,
                       detector_count=np.asarray(d.shape[1], dtype=np.int32),
                       seed=np.asarray(seed, dtype=np.uint32),
                       candidate_index=np.asarray(ci, dtype=np.int16),
                       detector_marginals=profile.astype(np.float64))
            template_metadata.append({
                "candidate_index": ci, "candidate": candidate, "seed": seed,
                "shots": len(d), "detector_count": int(d.shape[1]),
                "file": str(path.relative_to(ROOT)), "sha256": sha256_file(path),
                "candidate_dem_sha256": candidate_meta["dem_sha256"],
            })
        profiles = np.asarray(profiles, dtype=np.float64)
        TIMINGS["template_seconds"] += time.perf_counter() - t_start
        template_profile_file = ROOT / "templates" / f"{key}_profiles.npz"
        atomic_npz(template_profile_file, detector_marginals=profiles)

        cal_by_regime = {r: [] for r in spec["regimes"]}
        template_fit_indices = {}
        root_choice_counts = {r: [0] * len(spec["candidates"]) for r in spec["regimes"]}
        for regime in spec["regimes"]:
            for root_index in range(CFG["calibration_roots_per_cell"]):
                check_resources(CFG["shots_per_root"])
                seed = cal_seed_map[(key, regime, root_index)]
                path = ROOT / "raw" / (
                    f"cal_{key}_{regime}_root{root_index}_{seed}.npz")
                t0 = time.perf_counter()
                record = sample_and_decode(
                    bank, regime, seed, CFG["shots_per_root"], "calibration", path)
                TIMINGS["calibration_seconds"] += time.perf_counter() - t0
                cal_by_regime[regime].append(record)
                residual_counts = record["residuals"].sum(axis=1)
                root_choice = int(np.argmin(residual_counts))
                root_choice_counts[regime][root_choice] += 1
                template_fit_indices.setdefault(regime, []).append(
                    fit_detector_model(record["detectors"], profiles))
                cal_data_for_verification.append({
                    "path": str(path.relative_to(ROOT)), "seed": seed,
                    "bank": key, "regime": regime,
                })
                del record
            check_resources()
        selection = select_calibration(
            cal_by_regime, spec["regimes"], len(spec["candidates"]))
        choice_probs = bootstrap_choice_probabilities(
            cal_by_regime, spec["regimes"], len(spec["candidates"]),
            CFG["bootstrap_resamples"], bootstrap_map[key])
        detector_fit_indices = {}
        detector_fit_scores = {}
        for regime in spec["regimes"]:
            pooled_detectors = np.concatenate(
                [r["detectors"] for r in cal_by_regime[regime]], axis=0)
            scores = marginal_scores(pooled_detectors, profiles)
            detector_fit_indices[regime] = int(np.argmax(scores))
            detector_fit_scores[regime] = scores.tolist()
        selection.update({
            "bank": key, "family": spec["family"], "distance": spec["distance"],
            "memory": spec["memory"], "candidate_order": spec["candidates"],
            "detector_marginal_fit_indices": detector_fit_indices,
            "detector_marginal_scores": detector_fit_scores,
            "calibration_single_root_winner_counts": root_choice_counts,
            "calibration_single_root_detector_fit_indices": template_fit_indices,
            "choice_bootstrap": choice_probs,
            "template_bank": template_metadata,
            "pooled_nominal_candidate_index": (
                spec["candidates"].index((0.003, 0.003))
                if spec["family"] == "native" else spec["candidates"].index("balanced")
            ),
        })
        all_selections.append(selection)
        del cal_by_regime
        check_resources()
    atomic_json(ROOT / "CALIBRATION_SELECTIONS.json", {
        "selection_source": "calibration labels only for utility rankings; detectors only for marginal-fit selections",
        "evaluation_labels_accessed": False,
        "banks": all_selections,
    })
    atomic_json(ROOT / "CALIBRATION_EVIDENCE_INDEX.json", {
        "calibration_files": cal_data_for_verification,
        "count": len(cal_data_for_verification),
        "arrays_saved": ["packed detectors", "observable", "candidate predictions"],
    })
    return all_selections, cal_data_for_verification


def disagreement_matrix(rows, candidate_count):
    matrix = np.zeros((candidate_count, candidate_count), dtype=np.int64)
    total = 0
    for row in rows:
        pred = row["predictions"]
        total += pred.shape[1]
        for i in range(candidate_count):
            for j in range(i + 1, candidate_count):
                n = int(np.count_nonzero(pred[i] != pred[j]))
                matrix[i, j] += n
                matrix[j, i] += n
    return {
        "shots": total,
        "counts": matrix.tolist(),
        "rates": (matrix / total).tolist() if total else matrix.tolist(),
        "zero_disagreement_pairs": [
            [i, j] for i in range(candidate_count) for j in range(i + 1, candidate_count)
            if matrix[i, j] == 0
        ],
    }


def evaluate_banks(banks, selections, seed_inventory):
    selection_by_key = {x["bank"]: x for x in selections}
    eval_seed_map = {}
    for r in seed_inventory["evaluation"]:
        eval_seed_map[(r["bank"], r["regime"], r["root_index"])] = r["seed"]
    root_boot_map = {}
    for r in seed_inventory["root_ci_bootstrap"]:
        root_boot_map[(r["bank"], r["regime"])] = r["seed"]
    all_root_rows = []
    all_headroom_rows = []
    all_disagreement_rows = []
    utility_analysis = {}
    evaluation_evidence = []
    bank_results = []
    for key, bank in banks.items():
        check_resources()
        spec = bank["spec"]
        selected = selection_by_key[key]
        pooled_idx = int(selected["pooled_fixed_index"])
        eval_by_regime = {r: [] for r in spec["regimes"]}
        root_winners = {r: [0] * len(spec["candidates"]) for r in spec["regimes"]}
        for regime in spec["regimes"]:
            for root_index in range(CFG["evaluation_roots_per_cell"]):
                check_resources(CFG["shots_per_root"])
                seed = eval_seed_map[(key, regime, root_index)]
                path = ROOT / "raw" / (
                    f"eval_{key}_{regime}_root{root_index}_{seed}.npz")
                t0 = time.perf_counter()
                row = sample_and_decode(
                    bank, regime, seed, CFG["shots_per_root"], "evaluation", path)
                TIMINGS["evaluation_seconds"] += time.perf_counter() - t0
                eval_by_regime[regime].append(row)
                root_winners[regime][int(np.argmin(row["residuals"].sum(axis=1)))] += 1
                evaluation_evidence.append({
                    "path": str(path.relative_to(ROOT)), "seed": seed,
                    "bank": key, "regime": regime, "root_index": root_index,
                })
                root_output = {
                    "bank": key, "family": spec["family"],
                    "distance": spec["distance"], "memory": spec["memory"],
                    "regime": regime, "root_index": root_index, "seed": seed,
                    "shots": CFG["shots_per_root"],
                    "raw_observable_errors": int(row["labels"].sum()),
                    "candidate_errors": row["residuals"].sum(axis=1).astype(int).tolist(),
                    "candidate_ler": row["residuals"].mean(axis=1).astype(float).tolist(),
                    "pooled_fixed_index": pooled_idx,
                    "regime_specialist_index": selected["regime_specialist_indices"][regime],
                    "detector_fit_index": selected["detector_marginal_fit_indices"][regime],
                }
                all_root_rows.append(root_output)
                del row
        per_regime_effects = {}
        disagreement_by_regime = {}
        for ri, regime in enumerate(spec["regimes"]):
            specialist = int(selected["regime_specialist_indices"][regime])
            bootstrap_seed = root_boot_map[(key, regime)]
            # Re-open exact arrays so the summarized comparison derives from saved evidence.
            saved_rows = []
            for root_index in range(CFG["evaluation_roots_per_cell"]):
                seed = eval_seed_map[(key, regime, root_index)]
                path = ROOT / "raw" / (
                    f"eval_{key}_{regime}_root{root_index}_{seed}.npz")
                detectors, labels, predictions, got_seed, meta = unpack_raw(path)
                if got_seed != seed or meta != {
                    "regime": regime, "family": spec["family"],
                    "distance": spec["distance"], "memory": spec["memory"],
                    "stage": "evaluation",
                }:
                    raise RuntimeError(f"saved evidence metadata mismatch: {path}")
                red = residual_errors(labels, predictions)
                # Re-decode from the persisted detectors, not runner predictions.
                for ci, (model, corr) in enumerate(zip(bank["models"], bank["correlated"])):
                    check_resources()
                    t0 = time.perf_counter()
                    recreated = decode(model, detectors, corr).astype(np.uint8)
                    TIMINGS["independent_redecode_seconds"] += time.perf_counter() - t0
                    if not np.array_equal(recreated, predictions[ci]):
                        raise RuntimeError(f"prediction re-decode mismatch: {path}, model {ci}")
                saved_rows.append({
                    "residuals": red, "predictions": predictions,
                    "labels": labels, "detectors": detectors,
                })
            eval_by_regime[regime] = saved_rows
            effect = paired_root_effect(
                eval_by_regime, regime, specialist, pooled_idx,
                CFG["bootstrap_resamples"], bootstrap_seed)
            fit_idx = int(selected["detector_marginal_fit_indices"][regime])
            detector_effect = paired_root_effect(
                eval_by_regime, regime, fit_idx, pooled_idx,
                CFG["bootstrap_resamples"], bootstrap_seed + 1000)
            nominal_idx = int(selected["pooled_nominal_candidate_index"])
            nominal_effect = paired_root_effect(
                eval_by_regime, regime, nominal_idx, pooled_idx,
                CFG["bootstrap_resamples"], bootstrap_seed + 2000)
            effect.update({
                "detector_fit_index": fit_idx,
                "detector_fit_minus_pooled": detector_effect,
                "nominal_index": nominal_idx,
                "nominal_minus_pooled": nominal_effect,
                "specialist_calibration_selection_probability":
                    selected["choice_bootstrap"]["regime_choice_probability"][regime][specialist],
                "regime_specialist_root_winner_counts":
                    selected["calibration_single_root_winner_counts"][regime],
                "evaluation_root_best_candidate_counts": root_winners[regime],
            })
            per_regime_effects[regime] = effect
            disagreement_by_regime[regime] = disagreement_matrix(
                eval_by_regime[regime], len(spec["candidates"]))
            for i in range(len(spec["candidates"])):
                for j in range(i + 1, len(spec["candidates"])):
                    n = disagreement_by_regime[regime]["shots"]
                    k = disagreement_by_regime[regime]["counts"][i][j]
                    all_disagreement_rows.append({
                        "bank": key, "family": spec["family"],
                        "distance": spec["distance"], "memory": spec["memory"],
                        "regime": regime, "candidate_i": i, "candidate_j": j,
                        "disagreement_shots": k, "shots": n,
                        "disagreement_rate": k / n if n else 0.0,
                    })
            all_headroom_rows.append({
                "bank": key, "family": spec["family"], "distance": spec["distance"],
                "memory": spec["memory"], "regime": regime,
                "regime_candidate": specialist, "pooled_fixed_candidate": pooled_idx,
                "detector_fit_candidate": fit_idx,
                "candidate_labels": json.dumps(spec["candidates"]),
                "calibration_ler_regime": json.dumps(selected["calibration_ler"][regime]),
                "calibration_ler_pooled": json.dumps(selected["pooled_ler"]),
                "candidate_calibration_winner_probability":
                    effect["specialist_calibration_selection_probability"],
                "evaluation_shots": effect["shots"],
                "specialist_errors": effect["specialist_errors"],
                "pooled_errors": effect["pooled_errors"],
                "specialist_ler": effect["specialist_ler"],
                "pooled_ler": effect["pooled_ler"],
                "difference_ler": effect["difference_ler"],
                "relative_reduction": effect["relative_reduction"],
                "specialist_only_wrong": effect["specialist_only_wrong"],
                "pooled_only_wrong": effect["pooled_only_wrong"],
                "prediction_disagreement_rate": effect["prediction_disagreement_rate"],
                "roots_favoring_specialist": effect["roots_favoring_specialist"],
                "roots_favoring_pooled": effect["roots_favoring_pooled"],
                "root_bootstrap_ci95_low": effect["root_bootstrap_ci95"][0],
                "root_bootstrap_ci95_high": effect["root_bootstrap_ci95"][1],
            })
        bank_results.append({
            "bank": key, "family": spec["family"], "distance": spec["distance"],
            "memory": spec["memory"], "candidate_order": spec["candidates"],
            "pooled_fixed_index": pooled_idx,
            "regime_specialist_indices": selected["regime_specialist_indices"],
            "detector_marginal_fit_indices": selected["detector_marginal_fit_indices"],
            "regimes": per_regime_effects,
            "disagreement_matrices": disagreement_by_regime,
            "evaluation_root_winner_counts": root_winners,
        })
        utility_analysis[key] = per_regime_effects
        check_resources()
    return bank_results, all_root_rows, all_headroom_rows, all_disagreement_rows, utility_analysis, evaluation_evidence


def assess_headroom_gate(bank_results):
    gate = CFG["headroom_gate"]
    by_family_basis = {}
    bank_lookup = {(r["family"], r["memory"], r["distance"]): r for r in bank_results}
    for family in ("native", "pauli_biased"):
        for memory in CFG["memory_bases"]:
            qualifying_distances = []
            distance_details = []
            pair_distance_counts = {}
            for distance in CFG["distances"]:
                result = bank_lookup[(family, memory, distance)]
                regimes = list(result["regimes"])
                choices = result["regime_specialist_indices"]
                pooled = result["pooled_fixed_index"]
                eligible_regimes = []
                for regime in regimes:
                    effect = result["regimes"][regime]
                    stable = effect["specialist_calibration_selection_probability"] >= gate[
                        "minimum_calibration_bootstrap_selection_probability"]
                    practical = (
                        effect["relative_reduction"] >= gate["minimum_relative_ler_reduction"]
                        and -effect["difference_ler"] >= gate["minimum_absolute_ler_reduction"]
                    )
                    stable_eval = (
                        effect["roots_favoring_specialist"] >= gate[
                            "minimum_evaluation_roots_favoring_specialist"]
                        and effect["root_bootstrap_ci95"][1] < 0
                    )
                    if choices[regime] != pooled and stable and practical and stable_eval:
                        eligible_regimes.append(regime)
                qualifying_pairs = []
                for i, left in enumerate(eligible_regimes):
                    for right in eligible_regimes[i + 1:]:
                        if choices[left] != choices[right]:
                            pair = (left, right)
                            qualifying_pairs.append(pair)
                            pair_distance_counts.setdefault(pair, []).append(distance)
                has_distinct = bool(qualifying_pairs)
                if has_distinct:
                    qualifying_distances.append(distance)
                distance_details.append({
                    "distance": distance, "pooled_fixed_index": pooled,
                    "regime_specialist_indices": choices,
                    "eligible_regimes": eligible_regimes,
                    "qualifying_regime_pairs": [list(x) for x in qualifying_pairs],
                    "distinct_regime_winners_qualify": has_distinct,
                })
            replicated_pairs = {
                f"{left}|{right}": distances
                for (left, right), distances in pair_distance_counts.items()
                if len(distances) >= gate["minimum_replicated_distance_strata"]
            }
            passed = bool(replicated_pairs)
            by_family_basis[f"{family}_{memory}"] = {
                "passed": passed, "qualifying_distances": qualifying_distances,
                "replicated_regime_pairs": replicated_pairs,
                "required_distances": gate["minimum_replicated_distance_strata"],
                "distance_details": distance_details,
            }
    return {
        "passed": any(v["passed"] for v in by_family_basis.values()),
        "by_family_basis": by_family_basis,
        "criteria": gate,
        "interpretation": (
            "Development evidence met the prespecified headroom gate."
            if any(v["passed"] for v in by_family_basis.values())
            else "No useful regime-dependent utility headroom was established under the prespecified development gate."
        ),
    }


def historical_hashes():
    paths = [
        "outputs/phase4a_model_adequacy/PHASE4A_METHOD.md",
        "outputs/phase4a_model_adequacy/config.json",
        "outputs/phase4a_model_adequacy/run_phase4a.py",
        "outputs/phase4a_model_adequacy/RESULTS.json",
        "outputs/phase4a_model_adequacy/MANIFEST_FINAL.json",
        "outputs/phase4b_replication/PHASE4B_PROTOCOL.md",
        "outputs/phase4b_replication/config.json",
        "outputs/phase4b_replication/run_phase4b.py",
        "outputs/phase4b_replication/RESULTS.json",
        "outputs/phase4b_evidence_verification/PHASE4B_EVIDENCE_AUDIT.md",
        "outputs/phase4c_strong_baselines/PHASE4C_STAGE1_PROTOCOL.md",
        "outputs/phase4c_strong_baselines/PHASE4C_BASELINE_FREEZE.json",
        "outputs/phase4c_strong_baselines/stage2/PHASE4C_STAGE2_PROTOCOL_SUPERSEDING_AMENDMENT.md",
        "outputs/phase4c_strong_baselines/stage2/PHASE4C_STAGE2_PROTOCOL_SUPERSEDING_AMENDMENT.md",
        "outputs/phase4c_strong_baselines/stage2/STAGE2_RECOVERED_RESULTS.json",
        "outputs/phase4c_strong_baselines/stage2/STAGE2_RECOVERED_LIMITATIONS.md",
        "outputs/phase4c_strong_baselines/adaptive/PHASE5E_FINDINGS.md",
        "outputs/phase4c_strong_baselines/adaptive/PHASE5E_RESULTS.json",
        "outputs/phase4c_strong_baselines/adaptive/PHASE5E_DECODER_AUDIT.md",
        "outputs/phase4c_strong_baselines/adaptive/DEVELOPMENT_RESULTS_v3.json",
        "outputs/prototype_development/AUDITED_RESULTS.json",
    ]
    # OUTPUTS is <workspace>/outputs; resolve historical paths from workspace.
    workspace = OUTPUTS.parent
    present = {p: sha256_file(workspace / p) for p in paths if (workspace / p).is_file()}
    missing = [p for p in paths if not (workspace / p).is_file()]
    return {"present_sha256": present, "missing_paths": missing}


def main():
    if (ROOT / "FREEZE.json").exists():
        raise SystemExit("FREEZE.json exists; refusing to overwrite this pilot")
    specs = bank_specs()
    historical = scan_historical_seeds(OUTPUTS, exclude_dir=ROOT)
    seed_inventory = make_seed_inventory(specs, set(historical["recoverable_unique_seed_values"]))
    atomic_json(ROOT / "HISTORICAL_SEED_SCAN.json", historical)
    atomic_json(ROOT / "SEED_INVENTORY.json", seed_inventory)
    if seed_inventory["unique_proposed_seed_count"] != seed_inventory["proposed_seed_count"]:
        raise PilotStop("proposed seed uniqueness check failed")
    if seed_inventory["historical_collisions"]:
        raise PilotStop("historical seed collision detected")
    baseline_before = historical_hashes()
    banks, model_inventory = prepare_banks(specs)
    model_hash = sha256_file(ROOT / "MODEL_INVENTORY.json")
    source_files = [
        ROOT / "config.json", ROOT / "PHASE_PROTOCOL.md", ROOT / "headroom.py",
        ROOT / "run_pilot.py", ROOT / "test_headroom.py", ROOT / "test_headroom_unittest.py",
        ROOT / "SEED_INVENTORY.json", ROOT / "MODEL_INVENTORY.json",
        ROOT / "HISTORICAL_SEED_SCAN.json",
    ]
    freeze = {
        "study": CFG["study"], "frozen_before_development_sampling": True,
        "freeze_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_status": "development feasibility only; no final confirmatory samples",
        "protocol_hashes": {p.name: sha256_file(p) for p in source_files},
        "model_inventory_sha256": model_hash,
        "historical_phase_artifact_hashes_before": baseline_before,
        "seed_inventory_sha256": sha256_file(ROOT / "SEED_INVENTORY.json"),
        "seed_audit": {
            "historical_recoverable_values": len(historical["recoverable_unique_seed_values"]),
            "proposed_unique_values": seed_inventory["unique_proposed_seed_count"],
            "collisions": seed_inventory["historical_collisions"],
            "historical_coverage_limit": historical["coverage_limit"],
        },
    }
    atomic_json(ROOT / "FREEZE.json", freeze)
    validation_and_bench = do_diagnostics_and_benchmark(banks, seed_inventory)
    atomic_json(ROOT / "CIRCUIT_PREFLIGHT.json", {
        "status": "PASS", "diagnostics": validation_and_bench["diagnostics"],
        "model_build_seconds": TIMINGS["model_build_seconds"],
        "peak_rss_bytes_after_preflight": memory_rss(),
        "model_inventory_sha256": model_hash,
    })
    atomic_json(ROOT / "COMPUTE_BENCHMARK.json", {
        **validation_and_bench,
        "shot_counts_at_benchmark": dict(SHOT_COUNTS),
        "resource_caps": CFG["resource_caps"],
        "environment": model_inventory["software"],
    })
    if validation_and_bench["forecast"]["with_25_percent_headroom_seconds"] > validation_and_bench["forecast"]["available_wall_seconds_after_preflight"]:
        raise PilotStop(
            "measured pilot forecast exceeds remaining 30-minute wall budget; "
            "stopped before calibration/template/evaluation sampling."
        )
    selections, cal_evidence = prepare_templates_and_calibration(banks, seed_inventory)
    atomic_json(ROOT / "CALIBRATION_EVIDENCE_INDEX.json", {
        "calibration_files": cal_evidence, "count": len(cal_evidence),
        "arrays_saved": ["packed detectors", "observable", "candidate predictions"],
    })
    results, root_rows, headroom_rows, disagreement_rows, utility, eval_evidence = evaluate_banks(
        banks, selections, seed_inventory)
    gate = assess_headroom_gate(results)
    historical_after = historical_hashes()
    unchanged = baseline_before == historical_after
    if not unchanged:
        raise RuntimeError("a historical Phase 4/5 artifact hash changed during this run")
    payload = {
        "status": "completed_development_feasibility",
        "study": CFG["study"],
        "config": CFG,
        "software": model_inventory["software"],
        "seed_audit": {
            "historical_files_scanned": historical["files_scanned"],
            "recoverable_unique_historical_seed_values": len(historical["recoverable_unique_seed_values"]),
            "unique_proposed_seeds": seed_inventory["unique_proposed_seed_count"],
            "collisions": seed_inventory["historical_collisions"],
            "historical_coverage_limit": historical["coverage_limit"],
        },
        "preflight": validation_and_bench["diagnostics"],
        "banks": results,
        "headroom_gate": gate,
        "evaluation_evidence": eval_evidence,
        "historical_artifacts_unchanged": unchanged,
        "historical_hashes_before": baseline_before,
        "historical_hashes_after": historical_after,
        "shot_counts": SHOT_COUNTS,
        "timings": TIMINGS,
        "wall_seconds": time.perf_counter() - START,
        "peak_rss_bytes": memory_rss(),
        "calibration_array_count": len(cal_evidence),
        "evaluation_array_count": len(eval_evidence),
        "test_data_generated": False,
        "adaptive_controller_evaluated": False,
        "statistical_claim": "development-only root-bootstrap intervals; no confirmatory p-values",
    }
    atomic_json(ROOT / "HEADROOM_RESULTS.json", payload)
    save_csv(ROOT / "CALIBRATION_HEADROOM.csv", headroom_rows)
    save_csv(ROOT / "PER_ROOT_UTILITY.csv", root_rows)
    save_csv(ROOT / "DECODER_DISAGREEMENT.csv", disagreement_rows)
    save_csv(ROOT / "RANKING_STABILITY.csv", ranking_rows(results))
    atomic_json(ROOT / "PAIRED_UTILITY.json", utility)
    atomic_json(ROOT / "HEADROOM_GATE.json", gate)
    verify_calibration_evidence(banks, cal_evidence)
    atomic_json(ROOT / "CALIBRATION_EVIDENCE_AUDIT.json", {
        "status": "PASS", "arrays_independently_redecoded": len(cal_evidence),
        "selected_choices_recomputed_from_saved_arrays": True,
    })
    atomic_json(ROOT / "EVALUATION_EVIDENCE_AUDIT.json", {
        "status": "PASS", "arrays_independently_redecoded": len(eval_evidence),
        "residual_counts_recomputed_from_saved_arrays": True,
        "same_sample_pairing": "all candidate predictions in each bundle share its packed detector array and observable labels",
    })
    write_final_outputs(payload, results, selections, gate, validation_and_bench, historical)
    build_manifest()
    print(json.dumps({
        "status": payload["status"],
        "total_shots": sum(SHOT_COUNTS.values()),
        "headroom_gate_passed": gate["passed"],
        "wall_seconds": payload["wall_seconds"],
        "peak_rss_bytes": payload["peak_rss_bytes"],
        "output": str(ROOT),
    }, indent=2))


def ranking_rows(results):
    rows = []
    for bank in results:
        for regime, effect in bank["regimes"].items():
            counts = effect["regime_specialist_root_winner_counts"]
            eval_counts = effect["evaluation_root_best_candidate_counts"]
            for i, candidate in enumerate(bank["candidate_order"]):
                rows.append({
                    "bank": bank["bank"], "family": bank["family"],
                    "distance": bank["distance"], "memory": bank["memory"],
                    "regime": regime, "candidate_index": i,
                    "calibration_errors": bank.get("calibration_ler", {}).get(regime, []),
                    "calibration_single_root_best_count": counts[i],
                    "evaluation_single_root_best_count": eval_counts[i],
                    "bootstrap_selection_probability": effect[
                        "specialist_calibration_selection_probability"]
                        if i == bank["regime_specialist_indices"][regime] else 0.0,
                    "selected_regime_specialist": i == bank["regime_specialist_indices"][regime],
                    "selected_pooled_fixed": i == bank["pooled_fixed_index"],
                    "candidate": json.dumps(candidate),
                })
    return rows


def verify_calibration_evidence(banks, evidence):
    # Independently re-decode calibration predictions and recompute utility choices.
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in evidence:
        path = ROOT / item["path"]
        bank = banks[item["bank"]]
        det, y, predictions, seed, meta = unpack_raw(path)
        if seed != item["seed"] or meta["stage"] != "calibration":
            raise RuntimeError(f"calibration evidence metadata mismatch: {path}")
        for ci, (model, corr) in enumerate(zip(bank["models"], bank["correlated"])):
            pred = decode(model, det, corr).astype(np.uint8)
            if not np.array_equal(pred, predictions[ci]):
                raise RuntimeError(f"calibration prediction mismatch: {path} candidate {ci}")
        residuals = residual_errors(y, predictions)
        grouped.setdefault((item["bank"], item["regime"]), []).append({
            "residuals": residuals, "detectors": det,
        })
    for key, bank in banks.items():
        spec = bank["spec"]
        cal = {r: grouped[(key, r)] for r in spec["regimes"]}
        recomputed = select_calibration(cal, spec["regimes"], len(spec["candidates"]))
        saved_all = json.loads((ROOT / "CALIBRATION_SELECTIONS.json").read_text(encoding="utf-8"))["banks"]
        saved = next(v for v in saved_all if v["bank"] == key)
        for k in ("pooled_fixed_index", "regime_specialist_indices", "calibration_errors"):
            if recomputed[k] != saved[k]:
                raise RuntimeError(f"calibration selection recomputation mismatch for {key}/{k}")


def save_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp, path)


def write_final_outputs(payload, results, selections, gate, bench, historical):
    write_phase4_audit()
    write_preflight(payload, bench)
    write_ranking_report(results, selections)
    write_paired_report(results, gate)
    write_compute_report(payload, bench)
    write_power_report(gate, results, payload)
    write_stop_report(gate, results, payload)
    write_reproduce(payload)


def write_phase4_audit():
    text = """# Phase 4A–4C baseline and provenance audit

## Phase 4A: detector-fit specialist versus nominal

Phase 4A uses rotated Z-memory, d=3, r=5, 40 detectors and one logical observable. Native DEPOLARIZE1/2 gate noise and basis-appropriate premeasurement noise are injected at Stim-generated locations. Its nine candidates use gate and measurement p in {.001,.003,.006}. Separate 50,000-shot/candidate templates yield Jeffreys-smoothed detector marginals. Per-regime calibration detector counts are scored by a summed composite Bernoulli log likelihood; calibration labels do not choose the calibrated model. Fixed is nominal (.003,.003); informed reference uses true rates. Each decoder receives the same test detector outcomes; residual is observable XOR predicted logical frame.

In measurement-heavy noise (.001,.006), 940/600,000 calibrated errors versus 1,118 nominal, 80 candidate-only and 258 fixed-only, p=5.600789e-23, 19/20 seed wins. Data-heavy is slightly worse and nominal ties. Independent Stage 0 audit explained three Markdown hash differences as documentation-only and passed scientific artifact checks. Static, condition-specific result only.

## Phase 4B: independent static replication, with deviation

Same d=3/r=5 Z-memory and grid, 20 fresh roots and 600,000 measurement-heavy test shots. Fixed made 1,165 errors and calibrated 1,008; discordances 99/256, exact McNemar p=3.730723e-17, 20/20 roots favored calibration. Saved test predictions independently re-decoded. Audit decision is PASS WITH DEVIATION: the actual runner created a fresh template bank while protocol text specified reuse. The result is a static calibrated-versus-nominal replication, not adaptive evidence. Recorded freeze chronology is not cryptographic proof.

## Phase 4C: stronger fixed comparison and missing calibration evidence

Stage 1 used calibration logical labels over 1.2 million development shots to select pooled fixed (.001,.003), minimax fixed (.006,.003), and condition-specific candidates. This is not the Phase 4A detector-marginal fit. Stage 2 used that frozen pooled model as baseline and the nine-point Phase 4A-style detector-marginal calibrated choice. On 1.8 million paired held-out shots, the equal-regime calibrated-minus-pooled difference was +0.00001556, 95% root-stratified CI [-0.00004889,+0.00007667], p=.66658. No gain over pooled fixed was detected.

The Stage 2 raw test predictions for all 60 roots were independently re-decoded. Calibration detector arrays and fitting score traces were not saved, so the choices cannot be independently refit. The RNG allocation was resolved by prospective amendments after the original Stage 2 plan; it is not an unqualified original preregistration.

## Causal interpretation

Phase 4A/B’s positive result is relative to a deliberately nominal fixed model. Stage 1 demonstrates that a stronger pooled fixed candidate can be selected from calibration outcomes. Stage 2 finds no calibration gain over that pooled baseline. This is consistent with baseline weakness and calibration selection variability as explanations for the earlier apparent headroom; it does not establish that these are the only causes. Calibration arrays missing in Stage 2 prevent a full reconstruction. Every within-phase decoder contrast described above is paired on common detector/observable shots; phases must not be pooled because they use different baselines/selection estimands.
"""
    (ROOT / "PHASE4_BASELINE_AUDIT.md").write_text(text, encoding="utf-8")


def write_preflight(payload, bench):
    rows = payload["preflight"]
    lines = [
        "# Circuit and decoder preflight",
        "",
        "All cells use Stim rotated surface-code memory circuits with rounds equal to distance. Noiseless samples use the identical circuit with noise instructions removed. Native DEMs use decomposed graph errors without approximate-disjoint conversion; Pauli categorical channels use approximate-disjoint conversion and correlated PyMatching.",
        "",
        "| Bank | Detectors | Observables | Noiseless | Noise sensitivity |",
        "|---|---:|---:|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['bank']} | {r['actual_detectors']} | {r['observables']} | "
            f"{r['noiseless_shots']} all-zero | {r['sensitivity_shots']} nonzero |")
    lines += [
        "",
        "Detector dimension formula: (d²−1)r, giving 24, 120 and 336 detectors for d=r=3,5,7. Every model has one logical fault ID and the same generated detector/observable definition within each bank. Candidate DEM, circuit and edge-weight hashes are in MODEL_INVENTORY.json. Noiseless behavior was checked with 256 shots per bank; noisy sensitivity with 512 per bank.",
        "",
        "Noiseless and sensitivity preflights are diagnostics, not calibration or evaluation data. The circuit generator sets basis-appropriate measurement noise. The native and Pauli families are analyzed separately.",
    ]
    (ROOT / "CIRCUIT_PREFLIGHT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ranking_report(results, selections):
    lines = [
        "# Decoder ranking stability",
        "",
        "Candidate rankings are development-only. Calibration choices use five independent 5,000-shot roots per regime. Bootstrap probabilities resample calibration roots within each regime; they are selection-stability summaries, not posterior probabilities or confirmatory tests. Evaluation root-best counts are retrospective diagnostics and did not select models.",
        "",
        "| Bank | Regime | Pooled index | Utility specialist | Detector-fit index | Utility winner bootstrap probability | Single-root cal best counts | Eval-root best counts |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for bank in results:
        sel = next(x for x in selections if x["bank"] == bank["bank"])
        for regime, effect in bank["regimes"].items():
            idx = bank["regime_specialist_indices"][regime]
            lines.append(
                f"| {bank['bank']} | {regime} | {bank['pooled_fixed_index']} | {idx} | "
                f"{bank['detector_marginal_fit_indices'][regime]} | "
                f"{effect['specialist_calibration_selection_probability']:.3f} | "
                f"{effect['regime_specialist_root_winner_counts']} | "
                f"{effect['evaluation_root_best_candidate_counts']} |")
    lines += [
        "",
        "Interpretation must distinguish detector-profile fit from logical-error utility. A detector-fit model can be closer to the data-generating noise yet fail to improve logical decoding. Calibration root rankings and independent evaluation root rankings are both shown to expose instability; the evaluation ranking is not used for a selector.",
    ]
    (ROOT / "DECODER_RANKING_STABILITY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_paired_report(results, gate):
    lines = [
        "# Paired utility analysis",
        "",
        "Each evaluation root stores one packed detector matrix, one observable vector and all bank predictions. Residual indicators are recomputed as logical observable XOR prediction. Candidate and pooled outcomes are paired shot by shot. Root bootstrap resamples the five independent evaluation-root differences; these intervals are descriptive feasibility estimates, not confirmatory inference.",
        "",
        "| Bank | Regime | Specialist | Pooled | Specialist errors | Pooled errors | Candidate-only | Pooled-only | Delta LER | Relative reduction | Root 95% CI | Candidate disagreement |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for bank in results:
        for regime, effect in bank["regimes"].items():
            lines.append(
                f"| {bank['bank']} | {regime} | {effect['specialist_index']} | "
                f"{effect['pooled_index']} | {effect['specialist_errors']} | "
                f"{effect['pooled_errors']} | {effect['specialist_only_wrong']} | "
                f"{effect['pooled_only_wrong']} | {effect['difference_ler']:+.6g} | "
                f"{effect['relative_reduction']:+.2%} | "
                f"[{effect['root_bootstrap_ci95'][0]:+.6g}, {effect['root_bootstrap_ci95'][1]:+.6g}] | "
                f"{effect['prediction_disagreement_rate']:.4%} |")
    lines += [
        "",
        "Positive delta means the regime specialist is worse. Candidate-only is specialist wrong / pooled correct; pooled-only is the reverse. Decoder disagreement is not error improvement. Per-root paired observations are in PER_ROOT_UTILITY.csv; all candidate-pair disagreement counts are in DECODER_DISAGREEMENT.csv.",
        "",
        "## Prespecified gate result",
        "",
        f"Gate passed: **{gate['passed']}**. {gate['interpretation']}",
        "",
        "No evaluation-label winner or retrospective oracle contributes to this decision.",
    ]
    (ROOT / "PAIRED_UTILITY_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_compute_report(payload, bench):
    lines = [
        "# Compute and memory benchmark",
        "",
        f"Pilot shot totals: {json.dumps(payload['shot_counts'], sort_keys=True)}.",
        f"Wall time: {payload['wall_seconds']:.2f} s. Peak observed RSS: {payload['peak_rss_bytes']} bytes.",
        "",
        "| Bank | Detector count | 1k-shot simulator s/shot | Mean candidate decoder s/shot | Decode candidates total s |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in bench["benchmark"]:
        lines.append(
            f"| {row['bank']} | {row['detectors']} | "
            f"{row['sampling_seconds_per_shot']:.3g} | "
            f"{row['decode_seconds_per_shot_per_candidate']:.3g} | "
            f"{row['decode_seconds_all_candidates']:.4g} |")
    lines += [
        "",
        f"Model construction: {payload['timings']['model_build_seconds']:.3f} s; template generation: {payload['timings']['template_seconds']:.3f} s; calibration sampling/decoding: {payload['timings']['calibration_seconds']:.3f} s; evaluation sampling/decoding: {payload['timings']['evaluation_seconds']:.3f} s; independent prediction re-decode: {payload['timings']['independent_redecode_seconds']:.3f} s.",
        "",
        "The benchmark uses batched software sampling and decoding, not hardware latency. RSS is process-level and includes shared Python/native allocations; it is not a per-model memory estimate. Full model/circuit/DEM hashes and edge metadata are in MODEL_INVENTORY.json.",
    ]
    (ROOT / "COMPUTE_BENCHMARK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_power_report(gate, results, payload):
    if not gate["passed"]:
        text = f"""# Power and resource feasibility

**Status: not advanced to adaptive power calculation.** The prespecified headroom gate failed: {gate['interpretation']}

The requested conditional Stage 5 work is not scientifically justified without reproducible utility headroom. No adaptive-minus-pooled-fixed confirmatory effect or sample-size target is estimated from a retrospectively selected favorable cell. The pilot used {payload['shot_counts']['evaluation']} independent development-evaluation shots and {payload['shot_counts']['calibration']} calibration shots across 12 bank configurations; peak RSS was {payload['peak_rss_bytes']} bytes and total runtime was {payload['wall_seconds']:.2f} seconds.

The 24 CPU-hour and 20-million-test-shot limits remain untested for a confirmatory adaptive study. They are not a reason to proceed when the opportunity gate is absent. If future work changes the bank/noise model, it needs fresh development calibration and a new frozen gate before power analysis.
"""
    else:
        text = f"""# Power and resource feasibility

The development headroom gate passed for at least one family/basis. The next statistical step is still prospective planning, not test generation.

The pilot produced {payload['shot_counts']['evaluation']} independent development-evaluation shots. Use the root-cluster differences in HEADROOM_RESULTS.json to plan the equal-regime adaptive-minus-pooled endpoint. Determine the practical margin from measured controller and switching costs before final-test freeze, and simulate root-cluster power from development roots only. Do not count shots as independent roots. The planned 24 CPU-hour and 20-million-test-shot caps were not consumed by confirmatory testing; no final samples were generated.

No power result is claimed in this feasibility stage. A new frozen benchmark must calculate and approve that design before test sampling.
"""
    (ROOT / "POWER_FEASIBILITY.md").write_text(text, encoding="utf-8")


def write_stop_report(gate, results, payload):
    verdict = "GO" if gate["passed"] else "NO-GO"
    text = f"""# Stop/go decision

## Recommendation: {verdict}

Prespecified headroom gate passed: **{gate['passed']}**.

{gate['interpretation']}

This recommendation applies only to the tested calibration-selected banks, channels, distances and sample sizes. If NO-GO, stop before adaptive power planning or confirmatory samples. If GO, only proceed to a separately frozen adaptive benchmark after power/resource planning; this phase itself contains no adaptive controller test.

## Verified scope

- Development-only: {payload['shot_counts']['evaluation']} evaluation shots paired across all candidates.
- Calibration: {payload['shot_counts']['calibration']} shots; independent template bank: {payload['shot_counts']['template']} shots.
- No final confirmatory samples: {not payload['test_data_generated']}.
- Historical Phase 4/5 hashes unchanged: {payload['historical_artifacts_unchanged']}.
- Gate criteria and every family/basis/distance result are in HEADROOM_RESULTS.json.
"""
    (ROOT / "STOP_GO_DECISION.md").write_text(text, encoding="utf-8")


def write_reproduce(payload):
    text = f"""# Reproduce the headroom feasibility pilot

Run from the repository workspace:

    python -m unittest discover -s outputs/headroom_feasibility -p test_headroom_unittest.py -v
    python outputs/headroom_feasibility/run_pilot.py

The legacy pytest-form test file is retained, but pytest could not be installed in the restricted network environment used for this run; the standard-library unittest suite exercises the same core checks.

The runner refuses to overwrite FREEZE.json. It writes the prospective freeze and machine-readable seed inventory before diagnostics, templates, calibration or evaluation. Calibration and evaluation arrays are saved as atomic compressed NPZ bundles under raw/; templates are under templates/. Evaluation predictions are independently re-decoded from packed saved detectors before aggregate metrics are accepted.

Environment observed for this run: Python {payload['software']['python']}, Stim {payload['software']['stim']}, PyMatching {payload['software']['pymatching']}, NumPy {payload['software']['numpy']}. Optional psutil is used for process RSS; if unavailable, memory is reported as unavailable rather than fabricated.

All evidence is development-only. The code does not sample final confirmatory data or test adaptive switching.
"""
    (ROOT / "REPRODUCE.md").write_text(text, encoding="utf-8")


def build_manifest():
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.json" or "__pycache__" in path.parts:
            continue
        rows.append({
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    atomic_json(ROOT / "MANIFEST.json", {
        "study": CFG["study"], "files": rows,
        "historical_artifacts_modified": False,
    })


if __name__ == "__main__":
    try:
        main()
    except PilotStop as exc:
        atomic_json(ROOT / "RUN_FAILURE.json", {
            "status": "stopped", "reason": str(exc), "shot_counts": SHOT_COUNTS,
            "timings": TIMINGS, "wall_seconds": time.perf_counter() - START,
            "peak_rss_bytes": PEAK_RSS,
            "traceback": traceback.format_exc(),
        })
        raise
    except Exception as exc:
        atomic_json(ROOT / "RUN_FAILURE.json", {
            "status": "failed", "reason": str(exc), "shot_counts": SHOT_COUNTS,
            "timings": TIMINGS, "wall_seconds": time.perf_counter() - START,
            "peak_rss_bytes": PEAK_RSS,
            "traceback": traceback.format_exc(),
        })
        raise
