"""Read-only recomputation for the Q-SHIFT final evidence decision."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pymatching
import stim


WORKSPACE = Path(__file__).resolve().parents[2]
HF = WORKSPACE / "outputs" / "headroom_feasibility"
OUT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def readj(name):
    return json.loads((HF / name).read_text(encoding="utf-8"))


def raw_bundle(path: Path):
    with np.load(path, allow_pickle=False) as z:
        packed = z["detectors_packed_little"]
        n_det = int(z["detector_count"])
        detectors = np.unpackbits(packed, axis=1, bitorder="little")[:, :n_det]
        labels = z["observable"].astype(np.uint8)
        predictions = z["predictions"].astype(np.uint8)
        metadata = {
            "seed": int(z["seed"]), "regime": str(z["regime"]),
            "family": str(z["family"]), "distance": int(z["distance"]),
            "memory": str(z["memory"]), "stage": str(z["stage"]),
            "detector_count": n_det,
        }
    assert detectors.ndim == 2 and labels.shape == (len(detectors),)
    assert predictions.ndim == 2 and predictions.shape[1] == len(labels)
    assert np.isin(detectors, (0, 1)).all()
    assert np.isin(labels, (0, 1)).all() and np.isin(predictions, (0, 1)).all()
    residual = np.bitwise_xor(predictions, labels[None, :])
    return detectors, labels, predictions, residual, metadata


def main():
    config = readj("config.json")
    freeze = readj("FREEZE.json")
    evidence_audit = readj("EVIDENCE_AUDIT.json")
    seed_inventory = readj("SEED_INVENTORY.json")
    model_inventory = readj("MODEL_INVENTORY.json")
    selections = {r["bank"]: r for r in readj("CALIBRATION_SELECTIONS.json")["banks"]}
    reported = {r["bank"]: r for r in readj("HEADROOM_RESULTS.json")["banks"]}
    original_gate = readj("HEADROOM_GATE.json")
    if evidence_audit["status"] != "PASS":
        raise RuntimeError("the preceding headroom evidence audit is not PASS")

    # Check new-run manifest hashes, pre-test freeze hashes, and stored array hashes.
    manifest = readj("MANIFEST.json")
    manifest_mismatches = []
    for rec in manifest["files"]:
        path = HF / rec["path"]
        if not path.is_file() or path.stat().st_size != rec["bytes"] or sha(path) != rec["sha256"]:
            manifest_mismatches.append(rec["path"])
    freeze_mismatches = []
    for name, digest in freeze["protocol_hashes"].items():
        path = HF / name
        if not path.is_file() or sha(path) != digest:
            freeze_mismatches.append(name)
    seed_groups = ["template", "calibration", "evaluation", "noiseless_diagnostic",
                   "sensitivity_diagnostic", "benchmark", "choice_bootstrap", "root_ci_bootstrap"]
    all_seeds = [int(row["seed"]) for group in seed_groups for row in seed_inventory[group]]
    historical = set(readj("HISTORICAL_SEED_SCAN.json")["recoverable_unique_seed_values"])
    seed_collisions = sorted(set(all_seeds) & historical)
    if manifest_mismatches or freeze_mismatches or seed_collisions or len(all_seeds) != len(set(all_seeds)):
        raise RuntimeError("manifest/freeze/seed integrity failure")

    # Ingest only stored calibration/evaluation bundles; no sampling occurs here.
    expected = {}
    for stage, prefix in (("calibration", "cal"), ("evaluation", "eval")):
        for r in seed_inventory[stage]:
            name = f"{prefix}_{r['bank']}_{r['regime']}_root{r['root_index']}_{r['seed']}.npz"
            expected[name] = (stage, r["bank"], r["regime"], int(r["root_index"]), int(r["seed"]))
    actual = {p.name: p for p in (HF / "raw").glob("*.npz")}
    if set(expected) != set(actual):
        raise RuntimeError(f"raw checkpoint inventory mismatch {len(actual)} vs {len(expected)}")
    evidence_hashes = evidence_audit["raw_bundle_sha256"]
    cal = defaultdict(lambda: defaultdict(list))
    ev = defaultdict(lambda: defaultdict(list))
    per_bundle = []
    for name, spec in expected.items():
        stage, bank, regime, root_idx, seed = spec
        path = actual[name]
        rel = str(path.relative_to(HF))
        if evidence_hashes.get(rel) != sha(path):
            raise RuntimeError(f"raw array hash mismatch: {rel}")
        det, y, pred, residual, meta = raw_bundle(path)
        if meta["seed"] != seed or meta["stage"] != stage or meta["regime"] != regime:
            raise RuntimeError(f"raw bundle metadata mismatch: {rel}")
        model_meta = next(b for b in model_inventory["banks"] if b["key"] == bank)
        if (meta["family"], meta["distance"], meta["memory"]) != (
                model_meta["family"], model_meta["distance"], model_meta["memory"]):
            raise RuntimeError(f"raw bundle bank metadata mismatch: {rel}")
        row = {"root_index": root_idx, "seed": seed, "detectors": det,
               "labels": y, "predictions": pred, "residuals": residual,
               "candidate_errors": residual.sum(axis=1, dtype=np.int64)}
        (cal if stage == "calibration" else ev)[bank][regime].append(row)
        per_bundle.append({"file": rel, "stage": stage, "bank": bank, "regime": regime,
                           "root_index": root_idx, "shots": len(y), "sha256": sha(path)})

    # Rebuild complete candidate graph fingerprints from saved DEM files.
    candidate_models = {}
    pair_structure = {}
    for bank in model_inventory["banks"]:
        key = bank["key"]
        entries = []
        for cand in bank["candidates"]:
            dem_path = HF / cand["dem_file"]
            dem = stim.DetectorErrorModel(dem_path.read_text(encoding="utf-8"))
            dem_hash = hashlib.sha256(str(dem).encode()).hexdigest()
            # Use the original stored DEM byte hash independently as a separate exact check.
            byte_hash = sha(dem_path)
            model = pymatching.Matching.from_detector_error_model(
                dem, enable_correlations=bool(cand["correlated_matching"]))
            edge_rows = []
            for u, v, attrs in model.edges():
                a = -1 if u is None else int(u)
                b = -1 if v is None else int(v)
                if a > b:
                    a, b = b, a
                edge_rows.append([a, b, float(attrs["weight"]),
                                  sorted(int(x) for x in attrs.get("fault_ids", set()))])
            graph_bytes = json.dumps({
                "detectors": model.num_detectors,
                "fault_ids": model.num_fault_ids,
                "correlated": bool(cand["correlated_matching"]),
                "edges": sorted(edge_rows),
            }, separators=(",", ":"), sort_keys=True).encode()
            graph_hash = hashlib.sha256(graph_bytes).hexdigest()
            if byte_hash != cand["dem_file_sha256"]:
                raise RuntimeError(f"saved DEM hash mismatch: {dem_path}")
            entries.append({"dem_hash_bytes": byte_hash, "dem_hash_canonical": dem_hash,
                            "graph_hash": graph_hash,
                            "candidate_index": int(cand["candidate_index"]),
                            "correlated": bool(cand["correlated_matching"])})
        candidate_models[key] = entries

    # Recompute calibration selection and root-bootstrap selection frequencies.
    cal_selections = {}
    selection_frequency_checks = {}
    choice_seed_map = {r["bank"]: int(r["seed"]) for r in seed_inventory["choice_bootstrap"]}
    ci_seed_map = {(r["bank"], r["regime"]): int(r["seed"])
                   for r in seed_inventory["root_ci_bootstrap"]}
    outcomes = {}
    detailed = []
    selection_rows = []
    for bank in model_inventory["banks"]:
        key, regimes = bank["key"], list(bank["regimes"])
        n_candidates = len(bank["candidates"])
        cal_rates = {}
        cal_errors = {}
        roots_cal = {}
        for regime in regimes:
            rows = sorted(cal[key][regime], key=lambda x: x["root_index"])
            if len(rows) != config["calibration_roots_per_cell"]:
                raise RuntimeError(f"missing calibration root {key}/{regime}")
            counts = sum((r["candidate_errors"] for r in rows), np.zeros(n_candidates, dtype=np.int64))
            n = sum(len(r["labels"]) for r in rows)
            cal_errors[regime] = counts
            cal_rates[regime] = counts / n
            roots_cal[regime] = np.stack([r["candidate_errors"] / len(r["labels"]) for r in rows])
        pooled_ler = np.mean(np.stack([cal_rates[r] for r in regimes]), axis=0)
        pooled_idx = int(np.argmin(pooled_ler))
        specialist_idx = {r: int(np.argmin(cal_rates[r])) for r in regimes}
        saved = selections[key]
        if pooled_idx != int(saved["pooled_fixed_index"]) or specialist_idx != saved["regime_specialist_indices"]:
            raise RuntimeError(f"calibration choices do not recompute for {key}")
        cal_selections[key] = {"pooled": pooled_idx, "specialist": specialist_idx,
                               "rates": cal_rates, "errors": cal_errors}

        # Replicate the frozen 20k root-bootstrap selection distribution.
        rng = np.random.default_rng(choice_seed_map[key])
        frequencies = {r: np.zeros(n_candidates, dtype=np.int64) for r in regimes}
        pooled_freq = np.zeros(n_candidates, dtype=np.int64)
        for _ in range(int(config["bootstrap_resamples"])):
            rates = {}
            for regime in regimes:
                arr = roots_cal[regime]
                idx = rng.integers(0, len(arr), size=len(arr))
                rates[regime] = arr[idx].mean(axis=0)
                frequencies[regime][int(np.argmin(rates[regime]))] += 1
            pooled_freq[int(np.argmin(np.mean(np.stack([rates[r] for r in regimes]), axis=0)))] += 1
        saved_boot = saved["choice_bootstrap"]
        for regime in regimes:
            recomputed = (frequencies[regime] / config["bootstrap_resamples"]).tolist()
            if not np.allclose(recomputed, saved_boot["regime_choice_probability"][regime], atol=0, rtol=0):
                raise RuntimeError(f"calibration bootstrap mismatch {key}/{regime}")
        recomputed_pool = (pooled_freq / config["bootstrap_resamples"]).tolist()
        if not np.allclose(recomputed_pool, saved_boot["pooled_choice_probability"], atol=0, rtol=0):
            raise RuntimeError(f"pooled bootstrap mismatch {key}")
        selection_frequency_checks[key] = {r: (frequencies[r] / config["bootstrap_resamples"]).tolist()
                                           for r in regimes}

        outbank = reported[key]
        for regime in regimes:
            rows = sorted(ev[key][regime], key=lambda x: x["root_index"])
            if len(rows) != config["evaluation_roots_per_cell"]:
                raise RuntimeError(f"missing evaluation root {key}/{regime}")
            idx, base = specialist_idx[regime], pooled_idx
            diff_roots = []
            counts_by_candidate = np.zeros(n_candidates, dtype=np.int64)
            fixed_errors = cand_errors = cand_only = fixed_only = pred_diff = nshots = 0
            for row in rows:
                residual = row["residuals"].astype(bool)
                y = row["labels"]
                pred = row["predictions"]
                c, f = residual[idx], residual[base]
                diff_roots.append(float(c.mean() - f.mean()))
                cand_errors += int(c.sum())
                fixed_errors += int(f.sum())
                cand_only += int(np.count_nonzero(c & ~f))
                fixed_only += int(np.count_nonzero(~c & f))
                pred_diff += int(np.count_nonzero(pred[idx] != pred[base]))
                counts_by_candidate += residual.sum(axis=1, dtype=np.int64)
                nshots += len(y)
            diff_roots = np.asarray(diff_roots)
            ci_rng = np.random.default_rng(ci_seed_map[(key, regime)])
            boot_idx = ci_rng.integers(0, len(diff_roots), size=(int(config["bootstrap_resamples"]), len(diff_roots)))
            ci = np.quantile(diff_roots[boot_idx].mean(axis=1), [0.025, 0.975]).tolist()
            root_wins = int(np.count_nonzero(diff_roots < 0))
            root_losses = int(np.count_nonzero(diff_roots > 0))
            base_error_rate = fixed_errors / nshots if nshots else 0
            cand_error_rate = cand_errors / nshots if nshots else 0
            delta = float(diff_roots.mean())
            relative_reduction = (fixed_errors - cand_errors) / fixed_errors if fixed_errors else 0.0
            model_choice_prob = selection_frequency_checks[key][regime][idx]
            recompute = {
                "shots": nshots, "specialist_errors": cand_errors,
                "pooled_errors": fixed_errors, "specialist_only_wrong": cand_only,
                "pooled_only_wrong": fixed_only, "prediction_disagreements": pred_diff,
                "specialist_ler": cand_error_rate, "pooled_ler": base_error_rate,
                "difference_ler": delta, "relative_reduction": relative_reduction,
                "root_ci95": ci, "root_wins": root_wins, "root_losses": root_losses,
                "root_ties": len(diff_roots) - root_wins - root_losses,
                "root_differences": diff_roots.tolist(),
                "per_candidate_errors": counts_by_candidate.tolist(),
                "specialist_index": idx, "pooled_index": base,
                "calibration_selection_frequency": model_choice_prob,
            }
            saved_eff = outbank["regimes"][regime]
            for fld, saved_fld in (("specialist_errors", "specialist_errors"),
                                   ("pooled_errors", "pooled_errors"),
                                   ("specialist_only_wrong", "specialist_only_wrong"),
                                   ("pooled_only_wrong", "pooled_only_wrong"),
                                   ("prediction_disagreements", "prediction_disagreements")):
                if recompute[fld] != int(saved_eff[saved_fld]):
                    raise RuntimeError(f"saved metric mismatch {key}/{regime}/{fld}")
            if not np.allclose(ci, saved_eff["root_bootstrap_ci95"], atol=1e-14, rtol=0):
                raise RuntimeError(f"root bootstrap CI mismatch {key}/{regime}")
            outcome_key = f"{key}/{regime}"
            outcomes[outcome_key] = recompute
            selection_rows.append({
                "bank": key, "family": bank["family"], "distance": bank["distance"],
                "memory": bank["memory"], "regime": regime,
                "candidate_index": idx, "pooled_index": base,
                "candidate_parameters": json.dumps(bank["candidate_order"][idx]),
                "pooled_parameters": json.dumps(bank["candidate_order"][base]),
                "calibration_choice_frequency": model_choice_prob,
                "calibration_choice_differs": idx != base,
                "evaluation_candidate_errors": cand_errors,
                "evaluation_pooled_errors": fixed_errors,
                "specialist_only_wrong": cand_only, "pooled_only_wrong": fixed_only,
                "prediction_disagreement_shots": pred_diff,
                "difference_ler": delta, "relative_reduction": relative_reduction,
                "root_wins": root_wins, "root_losses": root_losses,
                "root_ties": len(diff_roots) - root_wins - root_losses,
                "root_ci95_low": ci[0], "root_ci95_high": ci[1],
                "bootstrap_selection_frequency": model_choice_prob,
            })

    # Independently apply every per-regime threshold and the same-regime-pair two-distance gate.
    gate_cfg = config["headroom_gate"]
    eligibility = {}
    family_basis = {}
    for bank in model_inventory["banks"]:
        key = bank["key"]
        for regime in bank["regimes"]:
            e = outcomes[f"{key}/{regime}"]
            eligible = (
                e["specialist_index"] != e["pooled_index"]
                and e["calibration_selection_frequency"] >= gate_cfg["minimum_calibration_bootstrap_selection_probability"]
                and e["relative_reduction"] >= gate_cfg["minimum_relative_ler_reduction"]
                and e["pooled_ler"] - e["specialist_ler"] >= gate_cfg["minimum_absolute_ler_reduction"]
                and e["root_wins"] >= gate_cfg["minimum_evaluation_roots_favoring_specialist"]
                and e["root_ci95"][1] < 0
            )
            eligibility[f"{key}/{regime}"] = eligible
    for family in ("native", "pauli_biased"):
        for memory in config["memory_bases"]:
            pair_distances = defaultdict(list)
            distance_rows = []
            for distance in config["distances"]:
                bank_key = f"{family}_d{distance}_{memory}"
                selected = cal_selections[bank_key]
                eligible_regimes = [
                    regime for regime in selected["specialist"]
                    if eligibility[f"{bank_key}/{regime}"]
                ]
                pairs = []
                for i, left in enumerate(eligible_regimes):
                    for right in eligible_regimes[i + 1:]:
                        if selected["specialist"][left] != selected["specialist"][right]:
                            pair = (left, right)
                            pairs.append(pair)
                            pair_distances[pair].append(distance)
                distance_rows.append({
                    "distance": distance,
                    "pooled_index": selected["pooled"],
                    "specialist_indices": selected["specialist"],
                    "eligible_regimes": eligible_regimes,
                    "qualifying_pairs": [list(x) for x in pairs],
                })
            replicated = {f"{a}|{b}": ds for (a, b), ds in pair_distances.items()
                          if len(ds) >= gate_cfg["minimum_replicated_distance_strata"]}
            passed = bool(replicated)
            family_basis[f"{family}_{memory}"] = {
                "passed": passed, "replicated_regime_pairs": replicated,
                "distances": distance_rows,
            }

    # Count the 702 paired candidate contrasts and structurally compare the 95 zero-disagreement pairs.
    with (HF / "DECODER_DISAGREEMENT.csv").open(newline="", encoding="utf-8") as f:
        disagreements = list(csv.DictReader(f))
    if len(disagreements) != 702:
        raise RuntimeError(f"expected 702 candidate-pair rows, got {len(disagreements)}")
    zero_rows = [r for r in disagreements if int(r["disagreement_shots"]) == 0]
    if len(zero_rows) != 95:
        raise RuntimeError(f"expected 95 sample-identical pairs, got {len(zero_rows)}")
    structural_rows = []
    model_map = {b["key"]: b for b in model_inventory["banks"]}
    for r in zero_rows:
        bank = model_map[r["bank"]]
        i, j = int(r["candidate_i"]), int(r["candidate_j"])
        ci, cj = bank["candidates"][i], bank["candidates"][j]
        # Rebuild canonical graph signatures with candidate (distinct DEM files) and edge records.
        def graph_signature(c):
            dem_path = HF / c["dem_file"]
            dem = stim.DetectorErrorModel(dem_path.read_text(encoding="utf-8"))
            matching = pymatching.Matching.from_detector_error_model(
                dem, enable_correlations=bool(c["correlated_matching"]))
            edges = []
            for u, v, attrs in matching.edges():
                a = -1 if u is None else int(u); b0 = -1 if v is None else int(v)
                if a > b0: a, b0 = b0, a
                edges.append([a, b0, float(attrs["weight"]),
                              sorted(int(x) for x in attrs.get("fault_ids", set()))])
            payload = {"detectors": matching.num_detectors,
                       "fault_ids": matching.num_fault_ids,
                       "correlated": bool(c["correlated_matching"]),
                       "edges": sorted(edges)}
            return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        same_dem = ci["dem_file_sha256"] == cj["dem_file_sha256"]
        sig_i, sig_j = graph_signature(ci), graph_signature(cj)
        same_graph = sig_i == sig_j
        structural_rows.append({
            "bank": r["bank"], "regime": r["regime"],
            "candidate_i": i, "candidate_j": j,
            "disagreement_shots": 0, "shots": int(r["shots"]),
            "candidate_i_dem_sha256": ci["dem_file_sha256"],
            "candidate_j_dem_sha256": cj["dem_file_sha256"],
            "same_dem_bytes": same_dem, "same_canonical_matching_graph": same_graph,
            "candidate_i_graph_sha256": sig_i, "candidate_j_graph_sha256": sig_j,
            "interpretation": "finite-sample equality; graphs differ" if not same_graph else "same canonical graph",
        })
    with (OUT / "DECODER_EQUIVALENCE_PAIRS.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(structural_rows[0]))
        writer.writeheader(); writer.writerows(structural_rows)

    changed = [r for r in selection_rows if r["calibration_choice_differs"]]
    better = [r for r in changed if r["difference_ler"] < 0]
    worse = [r for r in changed if r["difference_ler"] > 0]
    tie = [r for r in changed if r["difference_ler"] == 0]
    if (len(changed), len(better), len(worse), len(tie)) != (14, 7, 6, 1):
        raise RuntimeError("14 specialist selection breakdown did not recompute")
    with (OUT / "SPECIALIST_SELECTIONS_RECOMPUTED.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(selection_rows[0]))
        writer.writeheader(); writer.writerows(changed)

    # Leave-one-calibration-root-out stability, computed only from saved calibration bundles.
    loo_rows = []
    for bank in model_inventory["banks"]:
        key, regimes = bank["key"], list(bank["regimes"])
        full = cal_selections[key]
        pooled_loo = []
        for omit in range(int(config["calibration_roots_per_cell"])):
            loo_rates = []
            for regime in regimes:
                rows = sorted(cal[key][regime], key=lambda x: x["root_index"])
                kept = [r for j, r in enumerate(rows) if j != omit]
                errors = sum((r["candidate_errors"] for r in kept),
                             np.zeros(len(bank["candidates"]), dtype=np.int64))
                loo_rates.append(errors / sum(len(r["labels"]) for r in kept))
            pooled_loo.append(int(np.argmin(np.mean(np.stack(loo_rates), axis=0))))
        for regime in regimes:
            rows = sorted(cal[key][regime], key=lambda x: x["root_index"])
            specialist_loo = []
            for omit in range(int(config["calibration_roots_per_cell"])):
                kept = [r for j, r in enumerate(rows) if j != omit]
                errors = sum((r["candidate_errors"] for r in kept),
                             np.zeros(len(bank["candidates"]), dtype=np.int64))
                specialist_loo.append(int(np.argmin(errors)))
            selected = full["specialist"][regime]
            loo_rows.append({
                "bank": key, "family": bank["family"], "distance": bank["distance"],
                "memory": bank["memory"], "regime": regime,
                "full_calibration_specialist": selected,
                "specialist_leave_one_root_out_choices": json.dumps(specialist_loo),
                "specialist_loo_retained_full_choice": sum(x == selected for x in specialist_loo),
                "full_calibration_pooled": full["pooled"],
                "pooled_leave_one_root_out_choices": json.dumps(pooled_loo),
                "pooled_loo_retained_full_choice": sum(x == full["pooled"] for x in pooled_loo),
            })
    with (OUT / "CALIBRATION_LOO_STABILITY.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(loo_rows[0]))
        writer.writeheader(); writer.writerows(loo_rows)
    with (OUT / "CROSS_DISTANCE_ELIGIBILITY.csv").open("w", newline="", encoding="utf-8") as f:
        rows = []
        for key, fb in family_basis.items():
            family, memory = key.rsplit("_", 1)
            for dr in fb["distances"]:
                rows.append({"family": family, "memory": memory,
                             "distance": dr["distance"], "pooled_index": dr["pooled_index"],
                             "specialist_indices": json.dumps(dr["specialist_indices"], sort_keys=True),
                             "eligible_regimes": json.dumps(dr["eligible_regimes"]),
                             "qualifying_pairs": json.dumps(dr["qualifying_pairs"]),
                             "replicated_pair_gate": fb["passed"]})
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

    summary = {
        "status": "PASS" if all(not family_basis[k]["passed"] for k in family_basis)
                         and original_gate["passed"] is False else "FAIL",
        "source_evidence_audit_status": evidence_audit["status"],
        "manifest_entries": len(manifest["files"]),
        "manifest_mismatches": manifest_mismatches,
        "freeze_hash_mismatches": freeze_mismatches,
        "historical_recoverable_seed_count": len(historical),
        "historical_exclusion_aware_file_count": evidence_audit["seed_audit"]["historical_files_independently_counted_excluding_pilot"],
        "proposed_seed_count": len(all_seeds), "unique_proposed_seeds": len(set(all_seeds)),
        "historical_seed_collisions": seed_collisions,
        "raw_calibration_bundles": sum(len(cal[b][r]) for b in cal for r in cal[b]),
        "raw_evaluation_bundles": sum(len(ev[b][r]) for b in ev for r in ev[b]),
        "regime_cells": len(selection_rows), "candidate_pair_rows": len(disagreements),
        "sample_identical_pairs": len(zero_rows),
        "identical_pairs_same_dem": sum(x["same_dem_bytes"] for x in structural_rows),
        "identical_pairs_same_canonical_graph": sum(x["same_canonical_matching_graph"] for x in structural_rows),
        "identical_pairs_different_canonical_graph": sum(not x["same_canonical_matching_graph"] for x in structural_rows),
        "specialist_selections_different_from_pooled": len(changed),
        "specialists_better": len(better), "specialists_worse": len(worse), "specialists_tied": len(tie),
        "per_regime_cells_meeting_all_numeric_gate_conditions": sum(eligibility.values()),
        "family_basis_gate": family_basis,
        "outcomes": outcomes,
        "test_samples_generated": False,
    }
    (OUT / "INDEPENDENT_RECOMPUTATION.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in (
        "status", "regime_cells", "candidate_pair_rows", "sample_identical_pairs",
        "identical_pairs_same_canonical_graph", "specialist_selections_different_from_pooled",
        "specialists_better", "specialists_worse", "specialists_tied",
        "per_regime_cells_meeting_all_numeric_gate_conditions")}, indent=2))


if __name__ == "__main__":
    main()
