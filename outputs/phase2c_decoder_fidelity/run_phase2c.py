from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pymatching
import sklearn
import stim

HERE = Path(__file__).resolve().parent
OUTS = HERE.parent
P2B = OUTS / "phase2b_pauli_bias"
sys.path.insert(0, str(P2B))
from noise_model import MEMORY_BASES, REGIMES, build_circuit, circuit_noise_record  # noqa: E402
from decoder_bank import build_bank, decode_bank  # noqa: E402
from reference_decoder import SampledPosteriorDecoder  # noqa: E402

CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
CELL_LIST = [(b, r) for b in MEMORY_BASES for r in REGIMES]
CELL_INDEX = {cell: i for i, cell in enumerate(CELL_LIST)}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def atomic_npz(path: Path, **arrays):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.npz")
    np.savez_compressed(tmp, **arrays)
    tmp.replace(path)


def current_working_set_bytes() -> int | None:
    if os.name != "nt":
        return None
    from ctypes import wintypes
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    counters = PMC()
    counters.cb = ctypes.sizeof(PMC)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    get_info = psapi.GetProcessMemoryInfo
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    get_info.restype = wintypes.BOOL
    # GetCurrentProcess pseudo-handle is (HANDLE)-1; specifying the pointer
    # width avoids ctypes' default 32-bit integer return truncation.
    handle = wintypes.HANDLE(ctypes.c_void_p(-1).value)
    ok = get_info(handle, ctypes.byref(counters), counters.cb)
    return int(counters.WorkingSetSize) if ok else None


def all_stage_seeds() -> list[int]:
    seeds = []
    for key in ("diagnostic", "development", "calibration"):
        seeds.extend(int(x) for x in CONFIG["seeds"][key])
    seeds.extend(89200001 + 100 * cell_idx + root
                 for cell_idx in range(len(CELL_LIST)) for root in range(CONFIG["pilot_roots_per_cell"]))
    seeds.extend([int(CONFIG["seeds"]["bootstrap"]), int(CONFIG["seeds"]["signflip"])])
    return seeds


def historical_seed_scan():
    """Scan recoverable prior output text/JSON/CSV and NPZ seed fields."""
    found: dict[int, list[str]] = {}
    examined = []
    failures = []
    text_ext = {".json", ".csv", ".md", ".py", ".txt", ".log", ".yaml", ".yml"}
    key_pattern = re.compile(r"(?i)(?:random_)?(?:rng_)?seed(?:_root|_id)?[\"'\s:=,-]{0,24}(\d{6,})")

    def add(value, source):
        try:
            v = int(value)
        except (TypeError, ValueError):
            return
        if v >= 100000:
            found.setdefault(v, []).append(str(source.relative_to(OUTS)))

    def scan_obj(obj, path):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if "seed" in str(k).lower():
                    if isinstance(v, (int, float, str)):
                        add(v, path)
                    elif isinstance(v, list):
                        for item in v:
                            add(item, path)
                scan_obj(v, path)
        elif isinstance(obj, list):
            for v in obj:
                scan_obj(v, path)

    for path in OUTS.rglob("*"):
        if not path.is_file() or HERE in path.parents:
            continue
        try:
            if path.suffix.lower() in text_ext:
                text = path.read_text(encoding="utf-8", errors="ignore")
                examined.append(str(path.relative_to(OUTS)))
                if path.suffix.lower() == ".json":
                    try:
                        scan_obj(json.loads(text), path)
                    except json.JSONDecodeError:
                        pass
                for match in key_pattern.finditer(text):
                    add(match.group(1), path)
            elif path.suffix.lower() == ".npz":
                examined.append(str(path.relative_to(OUTS)))
                with np.load(path, allow_pickle=False) as archive:
                    for key in archive.files:
                        if "seed" not in key.lower() and "metadata" not in key.lower():
                            continue
                        arr = np.asarray(archive[key])
                        if arr.size == 1:
                            val = arr.reshape(-1)[0]
                            if isinstance(val, bytes):
                                val = val.decode("utf-8", errors="ignore")
                            if isinstance(val, str):
                                for match in key_pattern.finditer(f"seed: {val}"):
                                    add(match.group(1), path)
                            else:
                                add(val, path)
        except Exception as ex:  # preserve exact coverage and continue read-only
            failures.append({"file": str(path.relative_to(OUTS)), "error": repr(ex)})
    return {"seed_sources": found, "examined_files": sorted(set(examined)), "read_failures": failures}


def seed_audit():
    proposed = all_stage_seeds()
    if len(proposed) != len(set(proposed)):
        raise RuntimeError("Phase 2C seed plan contains internal collisions")
    hist = historical_seed_scan()
    historical = {int(k) for k in hist["seed_sources"]}
    collision = sorted(historical.intersection(proposed))
    result = {
        "scan_scope": "all recoverable files below outputs/ except this new Phase 2C directory; keyed seed fields and seed-labelled text plus NPZ seed/metadata fields",
        "files_examined": len(hist["examined_files"]),
        "examined_files": hist["examined_files"],
        "historical_seed_values": {str(k): sorted(set(v)) for k, v in sorted(hist["seed_sources"].items())},
        "distinct_historical_seed_count": len(historical),
        "proposed_seeds": proposed,
        "proposed_seed_count": len(proposed),
        "proposed_seeds_unique": len(proposed) == len(set(proposed)),
        "collisions": collision,
        "collisions_absent": not collision,
        "read_failures": hist["read_failures"],
        "coverage_limitation": "Historical seeds absent from saved text/manifests/NPZ seed fields cannot be independently screened. Any read failures are enumerated; no completeness claim is made beyond recoverable records."
    }
    write_json(HERE / "SEED_COLLISION_AUDIT.json", result)
    if collision:
        raise RuntimeError(f"Phase 2C seed collision: {collision}")
    if hist["read_failures"]:
        raise RuntimeError(f"seed scan encountered unreadable artifacts; inspect SEED_COLLISION_AUDIT.json")
    return result


def sample(circuit, count: int, seed: int):
    det, obs = circuit.compile_detector_sampler(seed=int(seed)).sample(
        shots=int(count), separate_observables=True)
    det = np.asarray(det, dtype=np.uint8)
    obs = np.asarray(obs, dtype=np.uint8)[:, 0]
    if det.shape != (count, 40) or obs.shape != (count,):
        raise RuntimeError(f"bad Stim sample shapes {det.shape} / {obs.shape}")
    return det, obs


def calibration_and_fitting():
    models = {}
    records = {"fit_metrics": {}, "calibration_matrix": {}, "model_files": {},
               "global_fixed_reference_index_by_basis": {},
               "regime_informed_reference_index_by_cell": {}}
    resource = {"working_set_before_training": current_working_set_bytes(), "after_each_fit": {}}
    start_all = time.perf_counter()
    for cell_idx, (basis, regime) in enumerate(CELL_LIST):
        circuit, _ = circuit_noise_record(basis, regime,
                                          distance=CONFIG["distance"], rounds=CONFIG["rounds"],
                                          gate_p=CONFIG["gate_probability"],
                                          measurement_p=CONFIG["measurement_probability"],
                                          bias_ratio=CONFIG["bias_ratio"])
        dev_seed = CONFIG["seeds"]["development"][cell_idx]
        d, y = sample(circuit, CONFIG["training_shots_per_cell"], dev_seed)
        train_path = HERE / "data" / f"development_{basis}_{regime}.npz"
        atomic_npz(train_path, detectors=d, observable=y, seed=np.int64(dev_seed))
        params = CONFIG["reference_model"]
        decoder = SampledPosteriorDecoder(
            seed=dev_seed + 1000,
            n_estimators=params["n_estimators"],
            min_samples_leaf=params["min_samples_leaf"],
            max_features=params["max_features"],
            max_depth=params["max_depth"],
        ).fit(d, y)
        model_path = HERE / "models" / f"reference_{basis}_{regime}.joblib"
        joblib.dump(decoder, model_path, compress=3)
        models[(basis, regime)] = decoder
        records["fit_metrics"][f"{basis}/{regime}"] = {
            "shots": len(y), "logical_ones": int(y.sum()), "training_ler": float(y.mean()),
            "fit_seconds": decoder.fit_seconds,
            "train_brier_score_in_sample": float(np.mean((decoder.predict_probability(d) - y) ** 2)),
            "model_file_bytes": model_path.stat().st_size,
            "model_sha256": sha256(model_path),
        }
        resource["after_each_fit"][f"{basis}/{regime}"] = current_working_set_bytes()
        records["model_files"][f"{basis}/{regime}"] = str(model_path.relative_to(HERE))
        del d, y

    # Independent calibration samples; compute the 3 x 3 candidate error matrix per basis.
    for basis in MEMORY_BASES:
        matrix = np.zeros((len(REGIMES), len(REGIMES)), dtype=np.int64)
        for gen_idx, regime in enumerate(REGIMES):
            circuit = build_circuit(basis, regime, distance=CONFIG["distance"], rounds=CONFIG["rounds"],
                                    gate_p=CONFIG["gate_probability"],
                                    measurement_p=CONFIG["measurement_probability"],
                                    bias_ratio=CONFIG["bias_ratio"])
            cell_idx = CELL_INDEX[(basis, regime)]
            seed = CONFIG["seeds"]["calibration"][cell_idx]
            d, y = sample(circuit, CONFIG["calibration_shots_per_cell"], seed)
            atomic_npz(HERE / "data" / f"calibration_{basis}_{regime}.npz",
                       detectors=d, observable=y, seed=np.int64(seed))
            for candidate_idx, assumed_regime in enumerate(REGIMES):
                pred = models[(basis, assumed_regime)].predict(d)
                matrix[gen_idx, candidate_idx] = int(np.count_nonzero(pred ^ y))
        global_scores = matrix.sum(axis=0) / (len(REGIMES) * CONFIG["calibration_shots_per_cell"])
        global_choice = int(np.flatnonzero(global_scores == global_scores.min())[0])
        per_regime_choice = [int(np.flatnonzero(row == row.min())[0]) for row in matrix]
        records["calibration_matrix"][basis] = {
            "rows_generating_regime_order": list(REGIMES),
            "columns_reference_training_regime_order": list(REGIMES),
            "errors": matrix.tolist(),
            "shots_per_cell": CONFIG["calibration_shots_per_cell"],
            "global_equal_regime_ler": global_scores.tolist(),
            "global_fixed_choice_index": global_choice,
            "per_regime_choice_index": per_regime_choice,
            "tie_break": "lowest candidate index"
        }
        records["global_fixed_reference_index_by_basis"][basis] = global_choice
        for gen_idx, regime in enumerate(REGIMES):
            records["regime_informed_reference_index_by_cell"][f"{basis}/{regime}"] = per_regime_choice[gen_idx]

    records["fit_total_seconds"] = time.perf_counter() - start_all
    records["resource"] = resource
    records["selection_source"] = "independent calibration labels only; heldout not yet generated"
    write_json(HERE / "CALIBRATION_SELECTION.json", records)
    return records


def prepare():
    pilot_dir = HERE / "data" / "pilot"
    if pilot_dir.exists() and any(pilot_dir.glob("*.npz")):
        raise RuntimeError("pilot bundles already exist; refusing to rewrite or reuse pilot data")
    seeds = seed_audit()
    validation = {"passed": [], "failed": [], "basis_records": {},
                  "seed_audit_pass": True, "software": {"stim": stim.__version__,
                  "pymatching": pymatching.__version__, "sklearn": sklearn.__version__,
                  "numpy": np.__version__}}
    for basis in MEMORY_BASES:
        bank, bank_records = build_bank(basis, distance=CONFIG["distance"], rounds=CONFIG["rounds"],
                                        gate_p=CONFIG["gate_probability"],
                                        measurement_p=CONFIG["measurement_probability"],
                                        bias_ratio=CONFIG["bias_ratio"], dem_dir=HERE / "dems")
        for rec in bank_records:
            key = f"{basis}/{rec['assumed_regime']}"
            circ, nrec = circuit_noise_record(basis, rec["assumed_regime"],
                                              distance=CONFIG["distance"], rounds=CONFIG["rounds"],
                                              gate_p=CONFIG["gate_probability"],
                                              measurement_p=CONFIG["measurement_probability"],
                                              bias_ratio=CONFIG["bias_ratio"])
            noiseless = build_circuit(basis, rec["assumed_regime"], distance=CONFIG["distance"],
                                      rounds=CONFIG["rounds"], gate_p=0, measurement_p=0,
                                      bias_ratio=CONFIG["bias_ratio"])
            zdet, zobs = sample(noiseless, 128, CONFIG["seeds"]["diagnostic"][CELL_INDEX[(basis, rec["assumed_regime"])]])
            if np.any(zdet) or np.any(zobs):
                raise RuntimeError(f"noiseless validation failed for {key}")
            det, _ = sample(circ, 3000, CONFIG["seeds"]["diagnostic"][CELL_INDEX[(basis, rec["assumed_regime"])]])
            if not np.any(det):
                raise RuntimeError(f"noisy sensitivity validation failed for {key}")
            if circ.num_detectors != 40 or circ.num_observables != 1:
                raise RuntimeError(f"circuit dimensions failed for {key}")
            if rec["detectors"] != 40 or bank[REGIMES.index(rec["assumed_regime"])].num_detectors != 40:
                raise RuntimeError(f"DEM/matching dimensions failed for {key}")
            p1 = nrec["1q_pauli_probabilities_X_Y_Z"]
            p2 = nrec["2q_pauli_pair_probabilities"]
            if not np.isclose(sum(p1), CONFIG["gate_probability"]) or not np.isclose(sum(p2), CONFIG["gate_probability"]):
                raise RuntimeError(f"gate channel mass failed for {key}")
            validation["passed"].extend([f"{key}: 40 detectors, 1 observable",
                                         f"{key}: noiseless samples all zero",
                                         f"{key}: noisy detectors nonzero",
                                         f"{key}: DEM and matching construction"])
            validation["basis_records"][key] = {"noise": nrec, "dem_sha256": rec["dem_sha256"],
                                                "circuit_sha256": rec["circuit_sha256"],
                                                "matching_nodes": rec["nodes"], "matching_edges": rec["edges"],
                                                "logical_fault_ids": rec["logical_fault_ids"],
                                                "conversion": rec["dem_approximation"]}
    write_json(HERE / "PREFLIGHT_VALIDATION.json", validation)

    selection = calibration_and_fitting()
    # Freeze all inputs needed to reproduce the pilot before sampling any pilot shot.
    freeze_paths = [HERE / n for n in ["PHASE2C_PROTOCOL.md", "PHASE2C_SOURCE_AUDIT.md", "REFERENCE_DECODER_DESIGN.md",
                                       "config.json", "run_phase2c.py", "reference_decoder.py",
                                       "exact_toy.py", "test_phase2c.py", "PREFLIGHT_VALIDATION.json",
                                       "CALIBRATION_SELECTION.json", "SEED_COLLISION_AUDIT.json"]]
    freeze_paths += [P2B / n for n in ["noise_model.py", "decoder_bank.py", "PHASE2B_PROTOCOL.md",
                                       "NOISE_MODEL_SPECIFICATION.md"]]
    freeze_paths += sorted((HERE / "data").glob("development_*.npz"))
    freeze_paths += sorted((HERE / "data").glob("calibration_*.npz"))
    freeze_paths += sorted((HERE / "models").glob("*.joblib"))
    freeze_paths += sorted((HERE / "dems").glob("*"))
    files = {str(p.resolve().relative_to(HERE.parent.parent)): sha256(p) for p in freeze_paths}
    freeze = {
        "freeze_status": "PRE-PILOT FROZEN",
        "frozen_before_heldout_sampling": True,
        "pilot_shots_generated_at_freeze": 0,
        "files_sha256": files,
        "selection": selection,
        "seed_screen_summary": {"proposed_count": seeds["proposed_seed_count"],
                                 "historical_distinct_count": seeds["distinct_historical_seed_count"],
                                 "collision_free": seeds["collisions_absent"]},
        "software": validation["software"],
        "freeze_note": "The frozen decoder is a sample-trained posterior surrogate. No pilot test data contributed to fit or selection."
    }
    write_json(HERE / "PILOT_FREEZE.json", freeze)
    print(f"PREPARE COMPLETE: calibration/model freeze; unique proposed seeds={len(seeds['proposed_seeds'])}; pilot shots=0")


def verify_freeze():
    freeze = json.loads((HERE / "PILOT_FREEZE.json").read_text(encoding="utf-8"))
    if not freeze.get("frozen_before_heldout_sampling") or freeze.get("pilot_shots_generated_at_freeze") != 0:
        raise RuntimeError("freeze does not attest to a pre-pilot state")
    for rel, expected in freeze["files_sha256"].items():
        path = HERE.parent.parent / Path(rel)
        if not path.exists() or sha256(path) != expected:
            raise RuntimeError(f"frozen file hash mismatch: {rel}")
    return freeze


def pilot():
    freeze = verify_freeze()
    models = {}
    for basis in MEMORY_BASES:
        for regime in REGIMES:
            path = HERE / "models" / f"reference_{basis}_{regime}.joblib"
            models[(basis, regime)] = joblib.load(path)
    run = {"freeze_sha256": sha256(HERE / "PILOT_FREEZE.json"), "roots": [],
           "total_test_shots": 0, "aggregate_runtime_seconds": {},
           "working_set_before_pilot": current_working_set_bytes()}
    match_times = np.zeros(3, dtype=np.float64)
    ref_times = np.zeros(3, dtype=np.float64)
    for basis in MEMORY_BASES:
        matching_models = []
        for regime in REGIMES:
            dem_path = HERE / "dems" / f"dem_{basis}_{regime}.dem"
            dem = stim.DetectorErrorModel.from_file(str(dem_path))
            matching_models.append(pymatching.Matching.from_detector_error_model(dem, enable_correlations=True))
        for regime in REGIMES:
            circuit = build_circuit(basis, regime, distance=CONFIG["distance"], rounds=CONFIG["rounds"],
                                    gate_p=CONFIG["gate_probability"],
                                    measurement_p=CONFIG["measurement_probability"],
                                    bias_ratio=CONFIG["bias_ratio"])
            cell_idx = CELL_INDEX[(basis, regime)]
            for root_idx in range(CONFIG["pilot_roots_per_cell"]):
                seed = 89200001 + 100 * cell_idx + root_idx
                d, y = sample(circuit, CONFIG["pilot_shots_per_root"], seed)
                pm_preds = []
                pm_seconds = []
                for model in matching_models:
                    t0 = time.perf_counter()
                    pred = np.asarray(model.decode_batch(d, enable_correlations=True), dtype=np.uint8)[:, 0]
                    elapsed = time.perf_counter() - t0
                    pm_preds.append(pred)
                    pm_seconds.append(elapsed)
                rf_preds, rf_probs, rf_seconds = [], [], []
                for assumed in REGIMES:
                    t0 = time.perf_counter()
                    probs = models[(basis, assumed)].predict_probability(d)
                    elapsed = time.perf_counter() - t0
                    rf_probs.append(probs)
                    rf_preds.append((probs > 0.5).astype(np.uint8))
                    rf_seconds.append(elapsed)
                preds = np.stack(pm_preds + rf_preds)
                probs = np.stack(rf_probs)
                path = HERE / "data" / "pilot" / f"pilot_{basis}_{regime}_root{root_idx:02}.npz"
                atomic_npz(path, detectors=d, observable=y, predictions=preds,
                           reference_probabilities=probs, seed=np.int64(seed),
                           memory_basis=np.asarray(basis), generating_regime=np.asarray(regime),
                           decoder_order=np.asarray(["pm_x", "pm_balanced", "pm_z", "ref_x", "ref_balanced", "ref_z"]))
                rec = {"basis": basis, "regime": regime, "root_index": root_idx,
                       "seed": seed, "shots": len(y), "logical_errors_raw": int(y.sum()),
                       "file": str(path.relative_to(HERE)), "sha256": sha256(path),
                       "py_matching_decode_seconds_by_candidate": pm_seconds,
                       "reference_probability_seconds_by_candidate": rf_seconds}
                run["roots"].append(rec)
                run["total_test_shots"] += len(y)
                match_times += np.asarray(pm_seconds)
                ref_times += np.asarray(rf_seconds)
                print(f"pilot {basis}/{regime} root {root_idx + 1}/{CONFIG['pilot_roots_per_cell']} saved")
    denom = run["total_test_shots"]
    run["aggregate_runtime_seconds"] = {
        "phase2b_matching_seconds_by_candidate": match_times.tolist(),
        "phase2b_matching_seconds_per_shot_by_candidate": (match_times / denom).tolist(),
        "reference_seconds_by_candidate": ref_times.tolist(),
        "reference_seconds_per_shot_by_candidate": (ref_times / denom).tolist(),
        "pilot_generation_and_decoding_wall_seconds": sum(sum(x["py_matching_decode_seconds_by_candidate"]) +
                                                            sum(x["reference_probability_seconds_by_candidate"])
                                                            for x in run["roots"]),
        "working_set_after_pilot": current_working_set_bytes()
    }
    write_json(HERE / "PILOT_RUN.json", run)
    print(f"PILOT COMPLETE: roots={len(run['roots'])}, shots={run['total_test_shots']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "pilot"])
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    else:
        pilot()

