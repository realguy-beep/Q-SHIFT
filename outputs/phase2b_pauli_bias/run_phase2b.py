"""Prepare/freeze Phase 2B, then produce fresh paired held-out samples.

Commands:
    python run_phase2b.py prepare
    python run_phase2b.py heldout
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pymatching
import stim

from decoder_bank import build_bank, decode_bank
from noise_model import MEMORY_BASES, REGIMES, build_circuit, circuit_noise_record

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
CFG = json.loads((P / "config.json").read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def atomic_npz(path: Path, **arrays):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(f, **arrays)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def cells():
    return [(basis, regime) for basis in MEMORY_BASES for regime in REGIMES]


def cell_index(basis: str, regime: str) -> int:
    return cells().index((basis, regime))


def allocated_seeds():
    seeds = {
        "diagnostic": [87990001 + i for i in range(6)],
        "development_validation": [88000001 + 100 * i for i in range(6)],
        "calibration": [88100001 + 100 * i for i in range(6)],
        "heldout": [88200001 + 1000 * i + root for i in range(6) for root in range(20)],
        "bootstrap": [88300001],
        "signflip": [88300002],
    }
    flat = [int(s) for group in seeds.values() for s in group]
    if len(flat) != len(set(flat)):
        raise RuntimeError("Phase 2B seed allocation has an internal collision")
    return seeds


def scan_historical_seeds(seed_inventory: dict) -> dict:
    """Screen available prior text plus numeric seed fields in historical NPZs."""
    proposed = sorted({int(x) for group in seed_inventory.values() for x in group})
    regex = re.compile(r"(?<!\d)(?:" + "|".join(map(str, proposed)) + r")(?!\d)")
    outputs = ROOT / "outputs"
    text_ext = {".json", ".md", ".py", ".csv", ".txt", ".log", ".yaml", ".yml"}
    text_files, text_hits, npz_files, npz_seeds, read_errors = [], [], [], [], []
    for path in sorted(outputs.rglob("*")):
        if not path.is_file() or P in path.parents or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() in text_ext:
            rel = path.relative_to(ROOT).as_posix()
            text_files.append(rel)
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                text_hits.extend({"file": rel, "seed": int(m.group(0))} for m in regex.finditer(content))
            except OSError as ex:
                read_errors.append({"file": rel, "error": str(ex)})
        elif path.suffix.lower() == ".npz":
            rel = path.relative_to(ROOT).as_posix()
            npz_files.append(rel)
            try:
                with np.load(path, allow_pickle=False) as z:
                    for key in z.files:
                        if "seed" not in key.lower():
                            continue
                        arr = np.asarray(z[key])
                        if arr.size > 10000 or arr.dtype.kind not in "iu":
                            continue
                        for val in np.unique(arr):
                            if int(val) in proposed:
                                npz_seeds.append({"file": rel, "key": key, "seed": int(val)})
            except Exception as ex:
                read_errors.append({"file": rel, "error": repr(ex)})
    collisions = text_hits + [{"file": x["file"], "seed": x["seed"], "source": x["key"]} for x in npz_seeds]
    report = {
        "historical_roots_examined": ["outputs/"],
        "text_file_count": len(text_files), "text_files_examined": text_files,
        "npz_file_count": len(npz_files), "npz_files_examined": npz_files,
        "historical_proposed_seed_matches": collisions,
        "proposed_seed_count": len(proposed), "proposed_seed_values": proposed,
        "internal_unique": len(proposed) == sum(len(x) for x in seed_inventory.values()),
        "collision_free_over_recoverable_records": not collisions,
        "read_errors": read_errors,
        "coverage_limit": "Scanned available files under outputs/: exact textual references in listed formats and numeric fields whose key contains 'seed' in NPZs. This does not prove absence of unrecorded RNG use or unavailable artifacts.",
    }
    if collisions:
        raise RuntimeError(f"Phase 2B seeds collide with recoverable historical seed records: {collisions[:5]}")
    if read_errors:
        raise RuntimeError(f"Historical seed scan had unreadable files: {read_errors[:5]}")
    write_json(P / "SEED_SCREENING.json", report)
    return report


def diagnostic_circuit_validation(banks):
    diagnostic = []
    for ci, (basis, regime) in enumerate(cells()):
        zero = build_circuit(basis, regime, gate_p=0.0, measurement_p=0.0)
        dz, yz = zero.compile_detector_sampler(seed=87990001 + ci).sample(16, separate_observables=True)
        if np.any(dz) or np.any(yz):
            raise RuntimeError(f"noiseless circuit failed for {basis}/{regime}")
        noisy = build_circuit(basis, regime)
        dn, yn = noisy.compile_detector_sampler(seed=87990001 + ci).sample(1500, separate_observables=True)
        if not np.any(dn):
            raise RuntimeError(f"noise sensitivity failed for {basis}/{regime}: no detectors fired")
        preds = decode_bank(banks[basis], dn[:64])
        if preds.shape != (3, 64):
            raise RuntimeError("paired preflight decode shape check failed")
        _, record = circuit_noise_record(basis, regime)
        diagnostic.append({"basis": basis, "regime": regime, "noiseless_detector_and_observable_bits_all_zero": True,
                           "noisy_diagnostic_shots": 1500, "noisy_detector_ones": int(np.count_nonzero(dn)),
                           "noisy_observable_ones": int(np.count_nonzero(yn)),
                           "paired_decode_shape": list(preds.shape), "noise_record": record})
    return diagnostic


def seed_manifest_rows(seeds):
    rows = []
    for ci, (basis, regime) in enumerate(cells()):
        rows.append({"partition": "diagnostic", "basis": basis, "regime_index": REGIMES.index(regime),
                     "regime": regime, "root_index": "", "seed": seeds["diagnostic"][ci],
                     "shots": 1500, "file": "diagnostic-only; not used for selection/evaluation"})
        rows.append({"partition": "development_validation", "basis": basis, "regime_index": REGIMES.index(regime),
                     "regime": regime, "root_index": "", "seed": seeds["development_validation"][ci],
                     "shots": CFG["partitions"]["development_validation_shots_per_memory_regime"],
                     "file": f"data/development_validation/devval_{basis}_{regime}.npz"})
        rows.append({"partition": "calibration", "basis": basis, "regime_index": REGIMES.index(regime),
                     "regime": regime, "root_index": "", "seed": seeds["calibration"][ci],
                     "shots": CFG["partitions"]["calibration_shots_per_memory_regime"],
                     "file": f"data/calibration/calibration_{basis}_{regime}.npz"})
        for root, seed in enumerate(seeds["heldout"][ci * 20:(ci + 1) * 20]):
            rows.append({"partition": "heldout", "basis": basis, "regime_index": REGIMES.index(regime),
                         "regime": regime, "root_index": root, "seed": seed,
                         "shots": CFG["partitions"]["heldout_shots_per_root"],
                         "file": f"data/heldout/test_{basis}_{regime}_root{root:02d}.npz"})
    for label in ("bootstrap", "signflip"):
        rows.append({"partition": label, "basis": "", "regime_index": "", "regime": "", "root_index": "",
                     "seed": seeds[label][0], "shots": 0, "file": "statistical RNG only"})
    return rows


def write_seed_manifest(rows):
    path = P / "SEED_MANIFEST.csv"
    fields = ["partition", "basis", "regime_index", "regime", "root_index", "seed", "shots", "file"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_sample(path: Path, circuit, models, *, seed: int, shots: int,
                basis: str, regime: str, root_index: int = -1):
    detectors, observables = circuit.compile_detector_sampler(seed=int(seed)).sample(
        shots=int(shots), separate_observables=True)
    detectors = np.asarray(detectors, dtype=np.uint8)
    observables = np.asarray(observables[:, 0], dtype=np.uint8)
    predictions = decode_bank(models, detectors).astype(np.uint8)
    atomic_npz(path, detectors=detectors, observable=observables, predictions=predictions,
               basis_id=np.asarray(MEMORY_BASES.index(basis), dtype=np.uint8),
               regime_id=np.asarray(REGIMES.index(regime), dtype=np.uint8),
               root_index=np.asarray(root_index, dtype=np.int16), seed=np.asarray(seed, dtype=np.uint32))
    return detectors, observables, predictions


def prepare():
    freeze_path = P / "PRETEST_FREEZE.json"
    if freeze_path.exists():
        raise RuntimeError("PRETEST_FREEZE.json already exists; refusing to rewrite the historical pretest freeze")
    heldout_dir = P / "data" / "heldout"
    if any(heldout_dir.glob("*.npz")):
        raise RuntimeError("held-out files already exist before prepare; refusing to overwrite evidence")
    seeds = allocated_seeds()
    screening = scan_historical_seeds(seeds)

    banks, all_records = {}, []
    dem_dir = P / "dems"
    for basis in MEMORY_BASES:
        bank, records = build_bank(basis, distance=3, rounds=5, dem_dir=dem_dir)
        banks[basis] = bank
        all_records.extend(records)
    bank_audit = {
        "bank_index_order": list(REGIMES), "memory_bases": list(MEMORY_BASES),
        "model_count": len(all_records), "unique_graphs_by_basis": {
            basis: len({r["weighted_fault_graph_sha256"] for r in all_records if r["noise_model"]["memory_basis"] == basis})
            for basis in MEMORY_BASES},
        "models": all_records,
        "interpretation": "The three model indices represent assumed Pauli composition, not decoder quality rankings. Each decoder uses its own assumed circuit-derived DEM and never receives the evaluation regime label.",
    }
    write_json(P / "DECODER_BANK_AUDIT.json", bank_audit)
    diagnostic = diagnostic_circuit_validation(banks)
    write_json(P / "CIRCUIT_VALIDATION.json", {"status": "PASS", "diagnostic_results": diagnostic,
        "all_six_noiseless_checks_passed": True, "all_six_noise_sensitivity_checks_passed": True,
        "detector_count": 40, "observable_count": 1})
    validation_md = ["# Phase 2B Circuit Validation", "",
        "## Deterministic preflight", "",
        "All six generated memory-basis/noise-regime circuits retained 40 detectors and one logical observable. Each zero-gate/zero-measurement-noise circuit produced zero detector and observable flips in 16 deterministic diagnostic shots. Each configured noisy circuit produced detector activity in a 1,500-shot sensitivity diagnostic. These diagnostic seeds are separate from development/validation, calibration, and held-out streams.", "",
        "## Noise locations and channel checks", "",
        "`DEPOLARIZE1`/`DEPOLARIZE2` were replaced at their generated post-Clifford targets by `PAULI_CHANNEL_1`/`PAULI_CHANNEL_2`. The generated measurement flip channels remained at 0.003. The gate channel probability sum is 0.003 for every one- and two-qubit channel in every regime. The measured flattened instruction/target counts below are computed from actual Stim circuits.", "",
        "| Memory | Regime | 1Q (pX,pY,pZ) | 1Q sum | 2Q sum | Measurement p | 1Q locations | 2Q pairs | Detector ones / diagnostic shots |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in diagnostic:
        nr = row["noise_record"]
        q = nr["1q_pauli_probabilities_X_Y_Z"]
        validation_md.append(f"| {row['basis']} | {row['regime']} | ({q[0]:.8g}, {q[1]:.8g}, {q[2]:.8g}) | {nr['1q_pauli_probability_sum']:.8g} | {nr['2q_pauli_probability_sum']:.8g} | {nr['measurement_flip_probability']:.8g} | {nr['flattened_noise_target_counts']['one_qubit_channel_targets']} | {nr['flattened_noise_target_counts']['two_qubit_channel_pairs']} | {row['noisy_detector_ones']} / {row['noisy_diagnostic_shots']} |")
    validation_md += ["", "## DEM and decoder preflight", "",
        "All six circuit/assumption DEMs built with `decompose_errors=True` and `approximate_disjoint_errors=True`; all six PyMatching graphs had 40 detector nodes and one logical fault ID. Correlated matching was enabled at construction and decoding. This conversion is an approximation of the sampled custom Pauli channels, as documented in `NOISE_MODEL_SPECIFICATION.md`.", "",
        "No held-out test shots are generated by the prepare step. The pretest freeze is saved only after seed screening, channel/graph checks, development/validation sampling, and calibration-only decoder selection pass."]
    (P / "CIRCUIT_VALIDATION.md").write_text("\n".join(validation_md) + "\n", encoding="utf-8")

    rows = seed_manifest_rows(seeds)
    write_seed_manifest(rows)
    calibration_rows = []
    devval_records = []
    cal_records = []
    devval_dir = P / "data" / "development_validation"
    cal_dir = P / "data" / "calibration"
    start = time.perf_counter()
    for ci, (basis, regime) in enumerate(cells()):
        circuit = build_circuit(basis, regime)
        dv_seed = seeds["development_validation"][ci]
        d, y, pred = save_sample(devval_dir / f"devval_{basis}_{regime}.npz", circuit, banks[basis],
                                 seed=dv_seed, shots=CFG["partitions"]["development_validation_shots_per_memory_regime"],
                                 basis=basis, regime=regime)
        devval_records.append({"basis": basis, "regime": regime, "seed": dv_seed,
                               "shots": len(y), "detector_ones": int(d.sum()),
                               "observable_ones": int(y.sum()),
                               "decoder_errors": [int(x) for x in (pred ^ y[None, :]).sum(axis=1)]})
        cal_seed = seeds["calibration"][ci]
        d, y, pred = save_sample(cal_dir / f"calibration_{basis}_{regime}.npz", circuit, banks[basis],
                                 seed=cal_seed, shots=CFG["partitions"]["calibration_shots_per_memory_regime"],
                                 basis=basis, regime=regime)
        errors = (pred ^ y[None, :]).sum(axis=1).astype(int)
        cal_records.append({"basis": basis, "regime": regime, "seed": cal_seed,
                            "shots": len(y), "errors": errors.tolist(),
                            "ler": [float(x / len(y)) for x in errors]})
        for i, err in enumerate(errors):
            calibration_rows.append({"basis": basis, "regime": regime, "regime_index": REGIMES.index(regime),
                                     "decoder_index": i, "assumed_noise": REGIMES[i], "shots": len(y),
                                     "errors": int(err), "ler": float(err / len(y))})

    # Selection is on calibration labels only. Validation summaries remain separate.
    selected = {}
    for basis in MEMORY_BASES:
        rows_b = [r for r in cal_records if r["basis"] == basis]
        matrix = np.asarray([r["ler"] for r in rows_b], dtype=float)  # regime x decoder
        selected[basis] = {
            "global_index": int(np.argmin(matrix.mean(axis=0))),
            "per_regime_indices": {r: int(np.argmin(matrix[REGIMES.index(r)])) for r in REGIMES},
            "tie_break": "lowest bank index",
            "calibration_only": True,
        }
    calibration_data = {"selected_models": selected, "rows": cal_records,
                        "selection_source": "saved calibration detector/observable samples only"}
    write_json(P / "CALIBRATION_SELECTION.json", calibration_data)
    with (P / "CALIBRATION_RESULTS.csv").open("w", newline="", encoding="utf-8") as f:
        fields = list(calibration_rows[0])
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(calibration_rows)
    write_json(P / "DEVELOPMENT_VALIDATION_RESULTS.json", {
        "partition": "development_validation; not used for decoder selection",
        "records": devval_records,
        "usage": "Check that simulated noise produces detector activity and summarize exploratory scores. No candidate or protocol selection was performed using these data.",
    })

    # The freeze contains complete source/config/protocol/stat-plan hashes plus all
    # pretest channel, calibration, and development-validation evidence hashes.
    frozen_paths = [P / name for name in ["config.json", "PHASE2B_PROTOCOL.md", "NOISE_MODEL_SPECIFICATION.md",
                    "STATISTICAL_PLAN.json", "run_phase2b.py", "analyze_phase2b.py", "noise_model.py",
                    "decoder_bank.py", "test_phase2b.py", "SEED_SCREENING.json", "DECODER_BANK_AUDIT.json",
                    "CIRCUIT_VALIDATION.json", "CIRCUIT_VALIDATION.md", "CALIBRATION_SELECTION.json", "CALIBRATION_RESULTS.csv",
                    "DEVELOPMENT_VALIDATION_RESULTS.json", "SEED_MANIFEST.csv"]]
    frozen_paths += sorted(dem_dir.glob("*.dem")) + sorted(dem_dir.glob("*.stim"))
    frozen_paths += sorted(devval_dir.glob("*.npz")) + sorted(cal_dir.glob("*.npz"))
    # Include the prior Phase 2A freeze/audit to make the baseline provenance explicit.
    p2a = ROOT / "outputs" / "phase2a_decoder_specialization"
    frozen_paths += [p2a / "PRETEST_FREEZE.json"] if (p2a / "PRETEST_FREEZE.json").exists() else []
    frozen_paths += [p2a / "FREEZE.json", p2a / "PHASE2A_MANIFEST.json", p2a / "PHASE2A_RESULTS.json"]
    freeze = {
        "status": "FROZEN_BEFORE_HELDOUT_SAMPLING",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "heldout_shots_generated_at_freeze": 0,
        "protocol_summary": "Three equal-gate-probability Pauli compositions, both Z and X memory; calibration-selected per-basis global and regime-informed decoders; 1.2M new paired test shots; primary and secondary tests in STATISTICAL_PLAN.json.",
        "selected_models": selected,
        "seed_inventory": seeds,
        "seed_screening_sha256": sha256(P / "SEED_SCREENING.json"),
        "files_sha256": {path.relative_to(ROOT).as_posix(): sha256(path) for path in frozen_paths},
        "software": {"python": platform.python_version(), "stim": stim.__version__,
                     "pymatching": pymatching.__version__, "numpy": np.__version__},
        "pretest_checks": {"seed_scan_pass": screening["collision_free_over_recoverable_records"],
                           "circuit_validation_pass": True, "bank_construction_pass": True,
                           "calibration_selection_pass": True, "devval_test_separate": True},
        "calibration_selection_source_hash": sha256(P / "CALIBRATION_SELECTION.json"),
        "pretest_runtime_seconds": time.perf_counter() - start,
    }
    write_json(freeze_path, freeze)
    print(f"PRETEST FREEZE saved; 0 held-out shots. Selection: {json.dumps(selected, sort_keys=True)}", flush=True)


def verify_frozen_files(freeze):
    mismatches = []
    for rel, expected in freeze["files_sha256"].items():
        path = ROOT / rel
        actual = sha256(path) if path.is_file() else None
        if actual != expected:
            mismatches.append({"file": rel, "expected": expected, "actual": actual})
    if mismatches:
        raise RuntimeError(f"pretest frozen files changed; held-out sampling refused: {mismatches[:5]}")


def load_or_validate_root(path: Path, basis: str, regime: str, root: int,
                          seed: int, models, expected_shots: int) -> dict:
    with np.load(path, allow_pickle=False) as z:
        d, y, pred = z["detectors"], z["observable"], z["predictions"]
        assert d.shape == (expected_shots, 40) and d.dtype == np.uint8
        assert y.shape == (expected_shots,) and y.dtype == np.uint8
        assert pred.shape == (3, expected_shots) and pred.dtype == np.uint8
        assert int(z["basis_id"]) == MEMORY_BASES.index(basis)
        assert int(z["regime_id"]) == REGIMES.index(regime)
        assert int(z["root_index"]) == root and int(z["seed"]) == seed
        assert np.array_equal(pred, decode_bank(models, d)), f"checkpoint prediction mismatch: {path.name}"
        return {"basis": basis, "regime": regime, "root_index": root, "seed": seed,
                "shots": len(y), "sha256": sha256(path), "status": "verified"}


def heldout():
    freeze_path = P / "PRETEST_FREEZE.json"
    if not freeze_path.exists():
        raise RuntimeError("run 'prepare' first; no pretest freeze exists")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    verify_frozen_files(freeze)
    if freeze["status"] != "FROZEN_BEFORE_HELDOUT_SAMPLING":
        raise RuntimeError("freeze status invalid")
    seeds = freeze["seed_inventory"]["heldout"]
    bank_by_basis = {basis: build_bank(basis, distance=3, rounds=5)[0] for basis in MEMORY_BASES}
    test_dir = P / "data" / "heldout"
    test_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    started = time.perf_counter()
    shots_per_root = CFG["partitions"]["heldout_shots_per_root"]
    fresh_roots = 0
    resumed_roots = 0
    for ci, (basis, regime) in enumerate(cells()):
        circuit = build_circuit(basis, regime)
        for root in range(CFG["partitions"]["heldout_roots_per_memory_regime"]):
            seed = int(seeds[ci * 20 + root])
            path = test_dir / f"test_{basis}_{regime}_root{root:02d}.npz"
            if path.exists():
                resumed_roots += 1
                record = load_or_validate_root(path, basis, regime, root, seed,
                                               bank_by_basis[basis], shots_per_root)
            else:
                fresh_roots += 1
                save_sample(path, circuit, bank_by_basis[basis], seed=seed, shots=shots_per_root,
                            basis=basis, regime=regime, root_index=root)
                record = load_or_validate_root(path, basis, regime, root, seed,
                                               bank_by_basis[basis], shots_per_root)
            manifest.append(record)
            # Atomic checkpoint metadata supports restart without changing any stream.
            write_json(P / "HELDOUT_CHECKPOINTS.json", {"verified_roots": len(manifest),
                "verified_shots": len(manifest) * shots_per_root, "records": manifest})
            if root % 5 == 0:
                print(f"{basis}-memory/{regime}: verified root {root + 1}/20; total roots {len(manifest)}/120", flush=True)
    total = len(manifest) * shots_per_root
    if len(manifest) != 120 or total != 1_200_000:
        raise RuntimeError(f"heldout coverage incomplete: {len(manifest)} roots, {total} shots")
    write_json(P / "RUN_METADATA.json", {"status": "HELDOUT_SAMPLING_COMPLETE", "roots": len(manifest),
        "shots_per_root": shots_per_root, "total_shots": total,
        "runtime_seconds": time.perf_counter() - started,
        "heldout_file_hashes": {r["basis"] + "/" + r["regime"] + "/" + str(r["root_index"]): r["sha256"] for r in manifest},
        "fresh_roots_generated_in_this_call": fresh_roots,
        "existing_roots_resumed_and_redecoded": resumed_roots,
        "resumed_root_validations": len(manifest),
        "paired_predictions_saved": True, "labels_used_for_selection": False,
        "freeze_sha256": sha256(freeze_path)})
    print(f"Held-out sampling complete: {len(manifest)} roots, {total:,} paired shots.", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "heldout"}:
        raise SystemExit("usage: python run_phase2b.py prepare|heldout")
    if sys.argv[1] == "prepare":
        prepare()
    else:
        heldout()
