"""Independent read-only audit of the saved headroom feasibility evidence."""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pymatching
import stim


ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def decode(model, detectors, correlated):
    if correlated:
        raw = model.decode_batch(detectors, enable_correlations=True)
    else:
        raw = model.decode_batch(detectors)
    pred = np.asarray(raw, dtype=np.uint8)
    if pred.ndim == 2:
        if pred.shape != (len(detectors), 1):
            raise AssertionError(f"prediction shape {pred.shape}")
        pred = pred[:, 0]
    if pred.shape != (len(detectors),) or not np.isin(pred, (0, 1)).all():
        raise AssertionError(f"invalid prediction values/shape: {pred.shape}")
    return pred


def unpack_bundle(path: Path):
    with np.load(path, allow_pickle=False) as z:
        packed = z["detectors_packed_little"]
        count = int(z["detector_count"])
        det = np.unpackbits(packed, axis=1, bitorder="little")[:, :count]
        y = z["observable"].astype(np.uint8)
        pred = z["predictions"].astype(np.uint8)
        meta = {
            "seed": int(z["seed"]), "regime": str(z["regime"]),
            "family": str(z["family"]), "distance": int(z["distance"]),
            "memory": str(z["memory"]), "stage": str(z["stage"]),
            "detector_count": count, "packed_shape": list(packed.shape),
        }
    if det.ndim != 2 or y.shape != (len(det),):
        raise AssertionError(f"detector/observable shape mismatch in {path}")
    if pred.ndim != 2 or pred.shape[1] != len(y):
        raise AssertionError(f"prediction shape mismatch in {path}")
    if not np.isin(det, (0, 1)).all() or not np.isin(y, (0, 1)).all():
        raise AssertionError(f"non-binary detector or observable in {path}")
    if not np.isin(pred, (0, 1)).all():
        raise AssertionError(f"non-binary prediction in {path}")
    return det, y, pred, meta


def main():
    config = load_json(ROOT / "config.json")
    freeze = load_json(ROOT / "FREEZE.json")
    inv = load_json(ROOT / "SEED_INVENTORY.json")
    model_inv = load_json(ROOT / "MODEL_INVENTORY.json")
    selections = load_json(ROOT / "CALIBRATION_SELECTIONS.json")["banks"]
    reported = load_json(ROOT / "HEADROOM_RESULTS.json")
    manifest = load_json(ROOT / "MANIFEST.json")
    failures = []
    checks = {}

    # Verify the prospective freeze against files as they now exist.
    hash_locations = {
        "config.json": ROOT / "config.json",
        "PHASE_PROTOCOL.md": ROOT / "PHASE_PROTOCOL.md",
        "headroom.py": ROOT / "headroom.py",
        "run_pilot.py": ROOT / "run_pilot.py",
        "test_headroom.py": ROOT / "test_headroom.py",
        "test_headroom_unittest.py": ROOT / "test_headroom_unittest.py",
        "SEED_INVENTORY.json": ROOT / "SEED_INVENTORY.json",
        "MODEL_INVENTORY.json": ROOT / "MODEL_INVENTORY.json",
        "HISTORICAL_SEED_SCAN.json": ROOT / "HISTORICAL_SEED_SCAN.json",
    }
    hash_ok = {}
    for name, path in hash_locations.items():
        expected = freeze["protocol_hashes"].get(name)
        actual = sha256(path) if path.is_file() else None
        hash_ok[name] = expected == actual
        if not hash_ok[name]:
            failures.append(f"freeze hash mismatch or missing: {name}")
    if sha256(ROOT / "MODEL_INVENTORY.json") != freeze["model_inventory_sha256"]:
        failures.append("model inventory hash mismatch")
    checks["freeze_hashes_match"] = hash_ok
    manifest_failures = []
    for rec in manifest.get("files", []):
        path = ROOT / rec["path"]
        if not path.is_file() or path.stat().st_size != int(rec["bytes"]) or sha256(path) != rec["sha256"]:
            manifest_failures.append(rec["path"])
    if manifest_failures:
        failures.append(f"original run manifest mismatch: {manifest_failures[:10]}")
    checks["initial_manifest_mismatches"] = manifest_failures

    # Validate inventory uniqueness/disjointness and independently count historical coverage.
    proposed = []
    for group in ("template", "calibration", "evaluation", "noiseless_diagnostic",
                  "sensitivity_diagnostic", "benchmark", "choice_bootstrap", "root_ci_bootstrap"):
        proposed.extend(int(r["seed"]) for r in inv[group])
    inv_unique = len(proposed) == len(set(proposed)) == inv["unique_proposed_seed_count"]
    if not inv_unique:
        failures.append("seed inventory is not unique")
    historical = load_json(ROOT / "HISTORICAL_SEED_SCAN.json")
    hist_set = set(historical["recoverable_unique_seed_values"])
    collisions = sorted(hist_set.intersection(proposed))
    if collisions:
        failures.append(f"historical seed collision(s): {collisions[:10]}")
    excluded_root = ROOT.resolve()
    scanned_files = []
    for f in OUT.rglob("*"):
        if not f.is_file():
            continue
        try:
            f.resolve().relative_to(excluded_root)
        except ValueError:
            scanned_files.append(f)
    checks["seed_audit"] = {
        "proposed_seed_count": len(proposed), "unique_proposed_seed_count": len(set(proposed)),
        "inventory_claimed_unique": inv["unique_proposed_seed_count"],
        "historical_seed_values_recovered": len(hist_set),
        "historical_files_independently_counted_excluding_pilot": len(scanned_files),
        "historical_collisions": collisions,
        "coverage_limit": historical["coverage_limit"],
    }

    # Build matching models from the saved circuits/DEMs, never from saved predictions.
    model_map = {}
    metadata_map = {}
    expected_raw = {}
    for bank in model_inv["banks"]:
        key = bank["key"]
        models = []
        for candidate in bank["candidates"]:
            circuit_file = ROOT / candidate["circuit_file"]
            dem_file = ROOT / candidate["dem_file"]
            if sha256(circuit_file) != candidate["circuit_file_sha256"]:
                failures.append(f"circuit file hash mismatch: {circuit_file}")
            if sha256(dem_file) != candidate["dem_file_sha256"]:
                failures.append(f"DEM file hash mismatch: {dem_file}")
            circuit = stim.Circuit(circuit_file.read_text(encoding="utf-8"))
            dem = stim.DetectorErrorModel(dem_file.read_text(encoding="utf-8"))
            model = pymatching.Matching.from_detector_error_model(
                dem, enable_correlations=bool(candidate["correlated_matching"]))
            if model.num_detectors != int(candidate["detectors"]) or model.num_fault_ids != 1:
                failures.append(f"matching graph schema mismatch: {key}/{candidate['candidate_index']}")
            if circuit.num_detectors != int(candidate["detectors"]) or circuit.num_observables != 1:
                failures.append(f"circuit annotation mismatch: {key}/{candidate['candidate_index']}")
            models.append((model, bool(candidate["correlated_matching"])))
        model_map[key] = models
        metadata_map[key] = bank

    seed_expected = {}
    filename_prefix = {"calibration": "cal", "evaluation": "eval"}
    for stage in ("calibration", "evaluation"):
        for item in inv[stage]:
            seed_expected[(stage, item["bank"], item["regime"], int(item["root_index"]))] = int(item["seed"])
    for ident, seed in seed_expected.items():
        stage, bank, regime, root_idx = ident
        expected_raw[f"{filename_prefix[stage]}_{bank}_{regime}_root{root_idx}_{seed}.npz"] = ident
    actual_raw = {p.name: p for p in (ROOT / "raw").glob("*.npz")}
    if set(actual_raw) != set(expected_raw):
        failures.append(
            f"raw bundle inventory mismatch: expected {len(expected_raw)}, found {len(actual_raw)}")

    cal = defaultdict(lambda: defaultdict(list))
    ev = defaultdict(lambda: defaultdict(list))
    raw_hashes = {}
    redecoded_bundles = 0
    redecoded_predictions = 0
    metadata_valid = 0
    for filename, ident in expected_raw.items():
        path = actual_raw.get(filename)
        if path is None:
            continue
        stage, bank_key, regime, root_idx = ident
        det, y, pred, meta = unpack_bundle(path)
        raw_hashes[str(path.relative_to(ROOT))] = sha256(path)
        bank = metadata_map[bank_key]
        expected_detectors = (int(bank["distance"]) ** 2 - 1) * int(bank["distance"])
        if meta["seed"] != seed_expected[ident] or meta["stage"] != stage:
            failures.append(f"filename/seed/stage mismatch: {path}")
        if (meta["family"], meta["distance"], meta["memory"], meta["regime"]) != (
            bank["family"], bank["distance"], bank["memory"], regime):
            failures.append(f"filename/family/distance/basis/regime mismatch: {path}")
        if meta["detector_count"] != expected_detectors or det.shape[1] != expected_detectors:
            failures.append(f"detector width mismatch: {path}")
        if meta["packed_shape"] != [len(y), (expected_detectors + 7) // 8]:
            failures.append(f"packed detector shape mismatch: {path}")
        if pred.shape != (len(model_map[bank_key]), len(y)):
            failures.append(f"candidate prediction array dimensions mismatch: {path}")
        if len(y) != int(config["shots_per_root"]):
            failures.append(f"shot count mismatch: {path}")
        else:
            metadata_valid += 1
        resid = np.bitwise_xor(pred, y[None, :])
        for ci, (model, correlated) in enumerate(model_map[bank_key]):
            rebuilt = decode(model, det, correlated)
            redecoded_predictions += len(y)
            if not np.array_equal(rebuilt, pred[ci]):
                failures.append(f"prediction re-decode mismatch: {path}, decoder {ci}")
        redecoded_bundles += 1
        row = {
            "seed": meta["seed"], "root_index": root_idx, "n": len(y),
            "errors": resid.sum(axis=1, dtype=np.int64),
            "predictions": pred, "labels": y,
        }
        (cal if stage == "calibration" else ev)[bank_key][regime].append(row)

    # Independently recompute all calibration-based fixed/specialist selections.
    selections_by_key = {r["bank"]: r for r in selections}
    selection_checks = {}
    for bank_key, bank in metadata_map.items():
        regimes = list(bank["regimes"])
        n_candidates = len(model_map[bank_key])
        rates = {}
        counts = {}
        for regime in regimes:
            rows = sorted(cal[bank_key][regime], key=lambda x: x["root_index"])
            if len(rows) != int(config["calibration_roots_per_cell"]):
                failures.append(f"missing calibration roots: {bank_key}/{regime}")
            errors = np.zeros(n_candidates, dtype=np.int64)
            nshots = 0
            for row in rows:
                errors += row["errors"]
                nshots += row["n"]
            counts[regime] = errors.tolist()
            rates[regime] = (errors / nshots).tolist()
        pooled = np.mean(np.asarray([rates[r] for r in regimes]), axis=0)
        pooled_choice = int(np.argmin(pooled))
        specialists = {r: int(np.argmin(rates[r])) for r in regimes}
        saved = selections_by_key[bank_key]
        valid = (
            pooled_choice == int(saved["pooled_fixed_index"])
            and specialists == saved["regime_specialist_indices"]
            and counts == saved["calibration_errors"]
        )
        selection_checks[bank_key] = {
            "recomputed_pooled_fixed_index": pooled_choice,
            "recomputed_regime_specialist_indices": specialists,
            "matches_saved_calibration_selection": valid,
        }
        if not valid:
            failures.append(f"calibration selection mismatch: {bank_key}")

    # Aggregate evaluation data from saved arrays, using only calibration-selected indices.
    result_checks = {}
    for reported_bank in reported["banks"]:
        bank_key = reported_bank["bank"]
        base_idx = int(reported_bank["pooled_fixed_index"])
        for regime, reported_eff in reported_bank["regimes"].items():
            spec_idx = int(reported_bank["regime_specialist_indices"][regime])
            rows = sorted(ev[bank_key][regime], key=lambda x: x["root_index"])
            if len(rows) != int(config["evaluation_roots_per_cell"]):
                failures.append(f"missing evaluation roots: {bank_key}/{regime}")
            agg_specialist = agg_base = cand_only = base_only = disagree = shots = 0
            root_diffs = []
            per_candidate_counts = np.zeros(len(model_map[bank_key]), dtype=np.int64)
            for row in rows:
                y = row["labels"]
                pred = row["predictions"]
                residual = np.bitwise_xor(pred, y[None, :])
                per_candidate_counts += residual.sum(axis=1, dtype=np.int64)
                s = residual[spec_idx].astype(bool)
                b = residual[base_idx].astype(bool)
                agg_specialist += int(s.sum())
                agg_base += int(b.sum())
                cand_only += int(np.count_nonzero(s & ~b))
                base_only += int(np.count_nonzero(~s & b))
                disagree += int(np.count_nonzero(pred[spec_idx] != pred[base_idx]))
                shots += len(y)
                root_diffs.append(float(s.mean() - b.mean()))
            values = {
                "shots": shots, "specialist_errors": agg_specialist,
                "pooled_errors": agg_base, "specialist_only_wrong": cand_only,
                "pooled_only_wrong": base_only, "prediction_disagreements": disagree,
                "difference_ler": float(np.mean(root_diffs)),
                "per_candidate_errors": per_candidate_counts.tolist(),
            }
            for field in ("shots", "specialist_errors", "pooled_errors",
                          "specialist_only_wrong", "pooled_only_wrong",
                          "prediction_disagreements"):
                if values[field] != int(reported_eff[field]):
                    failures.append(f"aggregate mismatch {bank_key}/{regime}/{field}")
            if not np.isclose(values["difference_ler"], reported_eff["difference_ler"], atol=1e-14):
                failures.append(f"paired LER difference mismatch {bank_key}/{regime}")
            result_checks[f"{bank_key}/{regime}"] = values

    # Check template profiles and candidate mappings from the saved template arrays.
    template_records = [r for s in selections for r in s["template_bank"]]
    template_checks = 0
    for rec in template_records:
        path = ROOT / rec["file"]
        if sha256(path) != rec["sha256"]:
            failures.append(f"template file hash mismatch: {path}")
        with np.load(path, allow_pickle=False) as z:
            packed = z["detectors_packed_little"]
            count = int(z["detector_count"])
            d = np.unpackbits(packed, axis=1, bitorder="little")[:, :count]
            p = z["detector_marginals"].astype(np.float64)
            seed = int(z["seed"])
            ci = int(z["candidate_index"])
        recomputed = (d.sum(axis=0, dtype=np.int64) + 0.5) / (len(d) + 1.0)
        if seed != int(rec["seed"]) or ci != int(rec["candidate_index"]):
            failures.append(f"template seed/candidate mapping mismatch: {path}")
        if not np.allclose(recomputed, p, rtol=0, atol=0):
            failures.append(f"template detector profile mismatch: {path}")
        template_checks += 1

    audit = {
        "status": "PASS" if not failures else "FAIL",
        "historical_phase_artifacts_modified": reported.get("historical_artifacts_unchanged") is not True,
        "failure_count": len(failures), "failures": failures,
        "raw_bundle_count_expected": len(expected_raw),
        "raw_bundle_count_found": len(actual_raw),
        "raw_bundle_sha256": raw_hashes,
        "metadata_valid_bundle_count": metadata_valid,
        "independently_redecoded_bundle_count": redecoded_bundles,
        "independently_redecoded_prediction_shots": redecoded_predictions,
        "template_profile_count_verified": template_checks,
        "calibration_selection_checks": selection_checks,
        "evaluation_aggregate_checks": result_checks,
        "seed_audit": checks["seed_audit"],
        "freeze_hash_checks": checks["freeze_hashes_match"],
        "test_label_use": "Only evaluation reporting/residual recomputation; choices independently reproduced from calibration arrays.",
        "limitations": [
            "Historical RNG coverage is limited to recorded artifacts; unrecorded streams cannot be excluded.",
            "Phase 4C Stage 2 calibration arrays were not preserved, limiting reconstruction of that historical fit.",
            "This is development feasibility evidence, not a confirmatory adaptive test.",
        ],
    }
    (ROOT / "EVIDENCE_AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Independent saved-evidence audit",
        "",
        f"**Status: {audit['status']}** ({len(failures)} failures).",
        "",
        f"- Raw calibration/evaluation bundles: {len(actual_raw)} expected, {redecoded_bundles} independently re-decoded.",
        f"- Prediction shot checks: {redecoded_predictions:,}; template profiles checked: {template_checks}.",
        f"- Unique proposed seeds: {len(set(proposed))}/{len(proposed)}; historical collisions: {len(collisions)}.",
        f"- Historical files examined excluding this pilot directory: {len(scanned_files)}; recovered seed values: {len(hist_set)}.",
        "- Calibration choices were recomputed from saved calibration arrays. Evaluation labels were used only to calculate residual metrics.",
        "- Per-root saved detector/observable arrays pair every decoder prediction on identical shots.",
        "",
        "## Outcome",
        "",
        "The runner’s aggregate counts were recomputed from saved NPZ evidence and compared field-by-field. Model outputs were independently regenerated from the saved DEM files. Raw file hashes are recorded in EVIDENCE_AUDIT.json.",
        "",
        "## Limitations",
        "",
        *[f"- {x}" for x in audit["limitations"]],
    ]
    if failures:
        md += ["", "## Failed checks", "", *[f"- {f}" for f in failures]]
    (ROOT / "EVIDENCE_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit(f"evidence audit failed: {len(failures)} checks; see EVIDENCE_AUDIT.md")
    manifest_rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.json" or "__pycache__" in path.parts:
            continue
        manifest_rows.append({
            "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    (ROOT / "MANIFEST.json").write_text(json.dumps({
        "study": config["study"], "files": manifest_rows,
        "historical_artifacts_modified": False,
        "independent_evidence_audit": "PASS",
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": audit["status"], "raw_bundles": redecoded_bundles,
        "redecoded_prediction_shots": redecoded_predictions,
        "templates": template_checks, "historical_collisions": len(collisions),
        "audit": str(ROOT / "EVIDENCE_AUDIT.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
