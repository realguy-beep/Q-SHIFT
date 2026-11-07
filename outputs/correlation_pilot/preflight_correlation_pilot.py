"""Prospective preflight and deterministic smoke test for the Q-SHIFT pilot."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTS = ROOT / "outputs"
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
PHASE2B = (HERE / CFG["phase2b_source_dir"]).resolve()
sys.path.insert(0, str(PHASE2B))
noise_model = importlib.import_module("noise_model")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def candidate_seeds() -> dict:
    alloc = CFG["seed_allocation"]
    roots = []
    for si in range(len(CFG["stratum_order"])):
        for ri in range(CFG["roots_per_stratum"]):
            roots.append({"stratum_index": si, "root_index": ri,
                          "seed": alloc["root_seed_base"] + 100 * si + ri
                          if "root_seed_base" in alloc else 93000001 + 100 * si + ri})
    groups = {
        "circuit_roots": roots,
        "diagnostic": [int(alloc["diagnostic"])],
        "bootstrap_rng": [int(alloc["bootstrap_rng"])],
        "primary_signflip_rng": [int(alloc["primary_signflip_rng"])],
    }
    flat = [int(x["seed"]) if isinstance(x, dict) else int(x)
            for values in groups.values() for x in values]
    if len(flat) != len(set(flat)):
        raise RuntimeError("Proposed circuit/statistical RNG seeds are not internally unique")
    return groups


def scan_seed_collisions() -> dict:
    groups = candidate_seeds()
    proposed = sorted(int(x["seed"]) if isinstance(x, dict) else int(x)
                      for values in groups.values() for x in values)
    pattern = re.compile(r"(?<!\d)(?:" + "|".join(map(str, proposed)) + r")(?!\d)")
    text_ext = {".json", ".md", ".py", ".csv", ".txt", ".log", ".yaml", ".yml"}
    excluded = {HERE.resolve(), (OUTS / "research_direction_selection").resolve()}
    text_files, npz_files, hits, read_errors = [], [], [], []
    for path in sorted(OUTS.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        resolved = path.resolve()
        if any(ex == resolved or ex in resolved.parents for ex in excluded):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() in text_ext:
            text_files.append(rel)
            try:
                body = path.read_text(encoding="utf-8", errors="ignore")
                hits.extend({"file": rel, "seed": int(m.group(0)), "kind": "text_match"}
                            for m in pattern.finditer(body))
            except OSError as ex:
                read_errors.append({"file": rel, "error": str(ex)})
        elif path.suffix.lower() == ".npz":
            npz_files.append(rel)
            try:
                with np.load(path, allow_pickle=False) as z:
                    for key in z.files:
                        if not any(tok in key.lower() for tok in ("seed", "rng")):
                            continue
                        arr = np.asarray(z[key])
                        if arr.size > 100000 or arr.dtype.kind not in "iu":
                            continue
                        for value in np.unique(arr):
                            if int(value) in set(proposed):
                                hits.append({"file": rel, "key": key, "seed": int(value),
                                             "kind": "npz_seed_field"})
            except Exception as ex:
                read_errors.append({"file": rel, "error": repr(ex)})
    report = {
        "seed_groups": groups,
        "proposed_seed_count": len(proposed),
        "internal_unique": len(proposed) == 75,
        "historical_roots_examined": ["outputs/ excluding this new run directory and its originating selection-plan document"],
        "text_file_count": len(text_files), "text_files_examined": text_files,
        "npz_file_count": len(npz_files), "npz_files_examined": npz_files,
        "candidate_seed_collisions": hits,
        "collision_free_over_scanned_records": not hits,
        "read_errors": read_errors,
        "coverage_limit": "Exact proposed-seed matches were scanned in available Markdown, JSON, Python, CSV, text, log, YAML and numeric NPZ fields whose key contains seed or rng. Unrecorded RNG use and unavailable historical records cannot be ruled out. The source selection-plan directory was excluded because it necessarily records this proposed allocation; it is not historical experiment evidence."
    }
    return report


def graph_signature(matching: pymatching.Matching) -> list:
    edges = []
    for u, v, attrs in matching.edges():
        u = -1 if u is None else int(u)
        v = -1 if v is None else int(v)
        edges.append((u, v, float(attrs["weight"]).hex(),
                      tuple(sorted(int(x) for x in attrs.get("fault_ids", set())))))
    return sorted(edges)


def historical_weighted_graph_hash(matching: pymatching.Matching) -> str:
    weighted = []
    for u, v, attrs in matching.edges():
        u = -1 if u is None else int(u)
        v = -1 if v is None else int(v)
        weighted.append((u, v, round(float(attrs["weight"]), 12),
                         tuple(sorted(int(x) for x in attrs.get("fault_ids", set())))))
    return sha256_bytes(repr(sorted(weighted)).encode("utf-8"))


def atomic_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_preflight(smoke_shots: int = 4096) -> dict:
    start_all = time.perf_counter()
    if CFG["primary_comparison"]["minimum_practical_improvement_absolute_ler"] != 0.0002:
        raise RuntimeError("Practical improvement margin must equal exactly 0.0002 absolute LER")
    seed_report = scan_seed_collisions()
    if not seed_report["internal_unique"] or not seed_report["collision_free_over_scanned_records"] or seed_report["read_errors"]:
        raise RuntimeError("Seed screening failed; do not sample full pilot")

    strata = []
    phase2b_bank_audit = json.loads((PHASE2B / "DECODER_BANK_AUDIT.json").read_text(encoding="utf-8"))
    normalized_structure_hashes = {"x": set(), "z": set()}
    primary_difference_counts = []
    construction_seconds = 0.0
    inference_seconds = 0.0
    compressed_smoke_bytes = 0
    for si, label in enumerate(CFG["stratum_order"]):
        basis, regime = label.split("_", 1)
        t0 = time.perf_counter()
        circuit, noise = noise_model.circuit_noise_record(
            basis, regime, distance=CFG["distance"], rounds=CFG["rounds"],
            gate_p=CFG["gate_fault_probability_1q"],
            measurement_p=CFG["measurement_flip_probability"], bias_ratio=CFG["bias_ratio"])
        dem = circuit.detector_error_model(**CFG["dem_conversion"])
        dem_text = str(dem)
        dem_sha = sha256_bytes(dem_text.encode("utf-8"))
        saved_circuit = PHASE2B / "dems" / f"circuit_{basis}_{regime}.stim"
        saved_dem = PHASE2B / "dems" / f"dem_{basis}_{regime}.dem"
        if not saved_circuit.is_file() or saved_circuit.read_text(encoding="utf-8") != str(circuit):
            raise RuntimeError(f"Generated circuit differs from frozen Phase 2B file: {saved_circuit}")
        if not saved_dem.is_file() or saved_dem.read_text(encoding="utf-8") != dem_text:
            raise RuntimeError(f"Generated DEM differs from frozen Phase 2B file: {saved_dem}")
        normalized = str(circuit.without_noise())
        normalized_structure_hashes[basis].add(sha256_bytes(normalized.encode("utf-8")))
        if circuit.num_detectors != 40 or circuit.num_observables != 1:
            raise RuntimeError(f"Circuit shape mismatch in {label}")
        if dem.num_detectors != 40 or dem.num_observables != 1:
            raise RuntimeError(f"DEM shape mismatch in {label}")
        if noise["distance"] != 3 or noise["rounds"] != 5:
            raise RuntimeError(f"Phase 2B circuit geometry mismatch in {label}")
        if not np.isclose(noise["total_fault_probability_per_1q_instruction"], 0.003):
            raise RuntimeError(f"1Q fault probability mismatch in {label}")
        if not np.isclose(noise["total_fault_probability_per_2q_instruction"], 0.003):
            raise RuntimeError(f"2Q fault probability mismatch in {label}")
        if not np.isclose(noise["measurement_flip_probability"], 0.003):
            raise RuntimeError(f"Measurement probability mismatch in {label}")
        separators = dem_text.count(" ^ ")
        if separators <= 0:
            raise RuntimeError(f"No decomposed correlation metadata present in {label}")

        # Confirm noiseless determinism without modifying the generated layout.
        zero = noise_model.build_circuit(basis, regime, distance=3, rounds=5,
                                         gate_p=0.0, measurement_p=0.0, bias_ratio=10.0)
        dz, yz = zero.compile_detector_sampler(seed=CFG["seed_allocation"]["diagnostic"]).sample(
            32, separate_observables=True)
        if np.any(dz) or np.any(yz):
            raise RuntimeError(f"Noiseless circuit produced a detector/observable flip in {label}")

        t1 = time.perf_counter()
        fixed_index = CFG["pooled_fixed_model_index_by_basis"][basis]
        regime_index = CFG["regimes"].index(regime)
        models = {}
        for name, index in (("pooled", fixed_index), ("regime", regime_index)):
            # All candidate DEMs are regenerated from the Phase 2B generator so
            # the fixed and regime-informed arms use exactly the frozen inputs.
            model_regime = CFG["regimes"][index]
            model_circuit = noise_model.build_circuit(
                basis, model_regime, distance=3, rounds=5, gate_p=0.003,
                measurement_p=0.003, bias_ratio=10.0)
            model_dem = model_circuit.detector_error_model(**CFG["dem_conversion"])
            model_dem_sha = sha256_bytes(str(model_dem).encode("utf-8"))
            off = pymatching.Matching.from_detector_error_model(model_dem, enable_correlations=False)
            on = pymatching.Matching.from_detector_error_model(model_dem, enable_correlations=True)
            if off.num_detectors != 40 or on.num_detectors != 40:
                raise RuntimeError("Matcher detector count mismatch")
            if off.num_fault_ids != 1 or on.num_fault_ids != 1:
                raise RuntimeError("Matcher observable/fault-id mismatch")
            if graph_signature(off) != graph_signature(on):
                raise RuntimeError(f"On/off graph edges or weights differ for {basis}/{model_regime}")
            audit_record = next(m for m in phase2b_bank_audit["models"]
                                if m["decoder_index"] == index and
                                m["noise_model"]["memory_basis"] == basis)
            if audit_record["dem_sha256"] != model_dem_sha:
                raise RuntimeError(f"Frozen Phase 2B DEM hash mismatch for {basis}/{model_regime}")
            if audit_record["weighted_fault_graph_sha256"] != historical_weighted_graph_hash(off):
                raise RuntimeError(f"PyMatching graph/weight fingerprint differs from Phase 2B audit for {basis}/{model_regime}")
            models[name] = {"index": index, "regime": model_regime, "dem_sha256": model_dem_sha,
                            "off": off, "on": on}
        construction_seconds += time.perf_counter() - t1

        # An explicit negative control: asking an unconfigured matcher to use
        # correlations must fail in PyMatching 2.4.0.
        rejected_unconfigured_call = False
        try:
            models["pooled"]["off"].decode_batch(np.zeros((1, 40), dtype=np.uint8),
                                                  enable_correlations=True)
        except ValueError as ex:
            rejected_unconfigured_call = "not been configured" in str(ex)
        if not rejected_unconfigured_call:
            raise RuntimeError("PyMatching correlation-mode negative control did not reject unconfigured matcher")

        # Fresh deterministic smoke samples, shared by all arms.
        d, obs = circuit.compile_detector_sampler(seed=CFG["seed_allocation"]["diagnostic"]).sample(
            smoke_shots, separate_observables=True)
        d_repeat, obs_repeat = circuit.compile_detector_sampler(seed=CFG["seed_allocation"]["diagnostic"]).sample(
            smoke_shots, separate_observables=True)
        if not np.array_equal(d, d_repeat) or not np.array_equal(obs, obs_repeat):
            raise RuntimeError(f"Fixed diagnostic seed was not deterministic for {label}")
        if d.shape != (smoke_shots, 40) or obs.shape != (smoke_shots, 1):
            raise RuntimeError(f"Smoke sample shape mismatch for {label}")
        t2 = time.perf_counter()
        p = [models["pooled"]["off"].decode_batch(d, enable_correlations=False),
             models["pooled"]["on"].decode_batch(d, enable_correlations=True),
             models["regime"]["off"].decode_batch(d, enable_correlations=False),
             models["regime"]["on"].decode_batch(d, enable_correlations=True)]
        inference_seconds += time.perf_counter() - t2
        pred = np.stack([np.asarray(x, dtype=np.uint8).reshape(-1) for x in p])
        if pred.shape != (4, smoke_shots) or not np.isin(pred, [0, 1]).all():
            raise RuntimeError(f"Smoke predictions invalid for {label}")
        if not np.isin(obs, [0, 1]).all():
            raise RuntimeError("Smoke observables are not binary")
        primary_difference_counts.append(int(np.count_nonzero(pred[0] != pred[1])))
        packed = np.packbits(d, axis=1, bitorder="little")
        # Include realistic NPZ compression in projected evidence size.
        import io
        buf = io.BytesIO()
        np.savez_compressed(buf, detectors=packed, observable=obs[:, 0].astype(np.uint8),
                            predictions=pred, root_seed=np.int64(CFG["seed_allocation"]["root_seed_base"] + si * 100),
                            stratum_index=np.int16(si), root_index=np.int16(0))
        compressed_smoke_bytes += len(buf.getvalue())
        strata.append({
            "stratum_index": si, "label": label, "basis": basis, "regime": regime,
            "circuit_detectors": circuit.num_detectors, "circuit_observables": circuit.num_observables,
            "dem_detectors": dem.num_detectors, "dem_observables": dem.num_observables,
            "dem_sha256": dem_sha, "dem_separator_count": separators,
            "circuit_without_noise_sha256": sha256_bytes(normalized.encode("utf-8")),
            "noise_record": noise,
            "fixed_decoder_grid_index": fixed_index,
            "regime_decoder_grid_index": regime_index,
            "pooled_dem_sha256": models["pooled"]["dem_sha256"],
            "regime_dem_sha256": models["regime"]["dem_sha256"],
            "paired_graph_weight_identical_on_off": True,
            "matcher_num_fault_ids": 1,
            "smoke_shots": smoke_shots,
            "smoke_prediction_shape": list(pred.shape),
            "pooled_prediction_disagreements_on_vs_off": primary_difference_counts[-1],
            "unconfigured_correlation_call_rejected": rejected_unconfigured_call,
            "sampler_and_decode_seconds": round((time.perf_counter() - t0), 6)
        })

    if any(len(values) != 1 for values in normalized_structure_hashes.values()):
        raise RuntimeError("Circuit structure without noise differs across regimes within a basis")

    usage = shutil.disk_usage(HERE)
    planned_shots = len(CFG["stratum_order"]) * CFG["roots_per_stratum"] * CFG["shots_per_root"]
    ratio = planned_shots / (len(CFG["stratum_order"]) * smoke_shots)
    projected_npz = int(compressed_smoke_bytes * ratio * 1.5)  # 50% safety allowance
    elapsed = time.perf_counter() - start_all
    try:
        import psutil
        rss = int(psutil.Process().memory_info().rss)
    except Exception:
        rss = None
    sys.path.insert(0, str(HERE))
    analysis_module = importlib.import_module("analyze_correlation_pilot")
    statistics_check = analysis_module.run_statistical_self_checks()
    atomic_json(HERE / "STATISTICAL_SELF_CHECK.json", statistics_check)
    report = {
        "status": "PASS",
        "created_utc_local_clock_not_recorded": "timestamps supplied by filesystem only",
        "python": sys.version,
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "phase2b_source_dir": PHASE2B.relative_to(ROOT).as_posix(),
        "phase2b_noise_model_sha256": sha256_file(PHASE2B / "noise_model.py"),
        "phase2b_decoder_bank_sha256": sha256_file(PHASE2B / "decoder_bank.py"),
        "seed_audit": seed_report,
        "seed_collision_free": True,
        "practical_margin_absolute_ler": CFG["primary_comparison"]["minimum_practical_improvement_absolute_ler"],
        "statistical_self_check": statistics_check,
        "correlation_api": {
            "matching_ctor_disabled_then_decode_enabled_rejected": True,
            "enabled_constructor_and_enabled_decode_accepted": True,
            "all_dem_edges_and_weights_identical_between_modes": True,
            "all_observable_ids_preserved": True,
            "feature_evidence": "DEM decomposition separators present; constructor+decode enabled accepted; negative control rejected the enabled decode call when matcher was constructed without correlation support.",
            "source_documentation": "PyMatching 2.4.0 installed matching.py requires enable_correlations at both from_detector_error_model construction and decode_batch call."
        },
        "six_strata": strata,
        "normalized_circuit_structure_consistent_by_basis": True,
        "root_seed_count": 72,
        "all_75_rng_stream_ids_unique": True,
        "planned_total_shots": planned_shots,
        "smoke_total_shots": len(CFG["stratum_order"]) * smoke_shots,
        "measured_smoke_wall_seconds": round(elapsed, 4),
        "measured_decoder_construction_seconds": round(construction_seconds, 4),
        "measured_smoke_inference_seconds": round(inference_seconds, 4),
        "estimated_full_inference_seconds_scaled_from_smoke": round(inference_seconds * ratio, 2),
        "estimated_total_compute_seconds_with_2x_margin": round(elapsed * ratio * 2, 2),
        "smoke_compressed_npz_bytes_six_roots": compressed_smoke_bytes,
        "estimated_full_evidence_bytes_with_50pct_margin": projected_npz,
        "disk_free_bytes": usage.free,
        "estimated_storage_fits": usage.free > projected_npz * 2,
        "process_rss_bytes_after_preflight": rss,
        "preflight_script_sha256": sha256_file(HERE / "preflight_correlation_pilot.py"),
        "config_sha256": sha256_file(HERE / "config.json")
    }
    if not report["estimated_storage_fits"]:
        raise RuntimeError("Insufficient disk free space for projected evidence")
    atomic_json(HERE / "SMOKE_PREFLIGHT.json", report)
    return report


if __name__ == "__main__":
    result = run_preflight()
    print(json.dumps({k: result[k] for k in (
        "status", "stim_version", "pymatching_version", "seed_collision_free",
        "planned_total_shots", "measured_smoke_wall_seconds",
        "estimated_total_compute_seconds_with_2x_margin",
        "estimated_full_evidence_bytes_with_50pct_margin", "disk_free_bytes")}, indent=2))
