"""Read-only mechanism audit of saved Q-SHIFT correlation-pilot NPZs.

No Stim shots are generated. The script reads the completed pilot checkpoints,
Phase 2B's saved circuit/DEM files, and existing analysis only for comparison.
It does not import pilot runner or reporting functions.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import stim

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "outputs" / "correlation_pilot"
PHASE2B = ROOT / "outputs" / "phase2b_pauli_bias"
OUT = Path(__file__).resolve().parent
CFG = json.loads((PILOT / "config.json").read_text(encoding="utf-8"))
RESULTS = json.loads((PILOT / "RESULTS.json").read_text(encoding="utf-8"))
ARMS = CFG["decoder_arms"]
STRATA = CFG["stratum_order"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def dem_summary(basis: str, regime: str) -> dict:
    path = PHASE2B / "dems" / f"dem_{basis}_{regime}.dem"
    text = path.read_text(encoding="utf-8")
    errors = [line.strip() for line in text.splitlines()
              if line.lstrip().startswith("error(")]
    sep_lines = [line for line in errors if "^" in line]
    sep_count = sum(line.count("^") for line in sep_lines)
    sep_with_logical = sum(("L0" in line and "^" in line) for line in sep_lines)
    detector_components = []
    for line in sep_lines:
        parts = line.split("^")
        detector_components.append(len(parts))
    return {"dem_file": str(path.relative_to(ROOT)), "sha256": sha256(path),
            "error_records": len(errors), "records_with_separator": len(sep_lines),
            "separator_count": sep_count, "separator_records_with_L0": sep_with_logical,
            "mean_components_in_separator_records": float(np.mean(detector_components)) if detector_components else None}


def main() -> None:
    roots = int(CFG["roots_per_stratum"])
    nshots = int(CFG["shots_per_root"])
    per_stratum = []
    per_root = []
    feature_acc = defaultdict(lambda: {"shots": 0, "hamming": [], "round_counts": [], "label": []})
    syndromes = {i: defaultdict(lambda: [0, 0, 0, 0, 0]) for i in range(6)}
    # Per signature counts: total, standard-only, correlation-only, label-0, label-1.
    all_stratum_predictions = np.zeros((6, 4), dtype=np.int64)
    all_raw_obs = np.zeros(6, dtype=np.int64)
    primary_pairs = np.zeros((6, 2), dtype=np.int64)  # standard-only, correlation-only
    all_disagreements = np.zeros(6, dtype=np.int64)
    all_detector_samples = [0] * 6
    coordinate_times = {}
    detector_time_groups = {}
    circuit_hashes = {}

    for basis in ("x", "z"):
        circuit_path = PHASE2B / "dems" / f"circuit_{basis}_balanced.stim"
        circuit = stim.Circuit.from_file(str(circuit_path))
        coords = circuit.get_detector_coordinates()
        if len(coords) != 40:
            raise AssertionError(f"Expected 40 detector coordinates in {circuit_path}")
        times = [int(round(coords[d][2])) for d in range(40)]
        # Stim places boundary detectors at t=0 and t=5 for a five-round circuit.
        if sorted(set(times)) != [0, 1, 2, 3, 4, 5]:
            raise AssertionError(f"Unexpected detector time coordinates for {basis}: {sorted(set(times))}")
        coordinate_times[basis] = times
        detector_time_groups[basis] = {str(t): [d for d, q in enumerate(times) if q == t] for t in range(6)}
        circuit_hashes[basis] = sha256(circuit_path)

    for si, label in enumerate(STRATA):
        basis, regime = label.split("_", 1)
        times = coordinate_times[basis]
        round_ids = np.asarray(times)
        round_masks = np.stack([round_ids == t for t in range(6)])
        root_arm_errors = np.zeros((4, roots), dtype=np.int64)
        root_deltas = np.zeros(roots, dtype=np.float64)
        root_std_only = np.zeros(roots, dtype=np.int64)
        root_corr_only = np.zeros(roots, dtype=np.int64)
        raw_errors = 0
        stratum_pred_disagreements = 0
        for ri in range(roots):
            path = PILOT / "checkpoints" / f"stratum_{si:02d}_root_{ri:02d}.npz"
            if not path.is_file():
                raise FileNotFoundError(path)
            with np.load(path, allow_pickle=False) as z:
                packed = z["detectors"]
                detectors = np.unpackbits(packed, axis=1, count=40, bitorder="little")
                obs = z["observable"]
                preds = z["predictions"]
                if detectors.shape != (nshots, 40) or obs.shape != (nshots,) or preds.shape != (4, nshots):
                    raise AssertionError(f"Checkpoint shape mismatch: {path}")
                if int(z["stratum_index"]) != si or int(z["root_index"]) != ri:
                    raise AssertionError(f"Root metadata mismatch: {path}")
                expected_seed = int(CFG["seed_allocation"]["root_seed_base"] + 100 * si + ri)
                expected_regime_index = CFG["regimes"].index(regime)
                expected_fixed_index = int(CFG["pooled_fixed_model_index_by_basis"][basis])
                if (int(z["root_seed"]) != expected_seed or str(z["basis"].item()) != basis or
                        str(z["regime"].item()) != regime or
                        int(z["regime_decoder_index"]) != expected_regime_index or
                        int(z["fixed_decoder_index"]) != expected_fixed_index):
                    raise AssertionError(f"Seed/condition/decoder mapping mismatch: {path}")

            residual = preds ^ obs[None, :]
            same_name_model = basis == regime[0]
            if same_name_model and (not np.array_equal(preds[0], preds[2]) or
                                    not np.array_equal(preds[1], preds[3])):
                raise AssertionError(f"Pooled/regime-informed arms should be identical for same-name model in {path}")
            errs = residual.sum(axis=1).astype(np.int64)
            root_arm_errors[:, ri] = errs
            root_deltas[ri] = (errs[1] - errs[0]) / nshots
            raw_errors += int(obs.sum())
            all_raw_obs[si] += int(obs.sum())
            all_stratum_predictions[si] += errs

            off, on = preds[0], preds[1]
            changed = off != on
            standard_only = changed & (off != obs) & (on == obs)
            correlation_only = changed & (off == obs) & (on != obs)
            if np.any(changed != (standard_only | correlation_only)):
                raise AssertionError("Every binary prediction disagreement must assign one arm correct and one wrong")
            std_n = int(standard_only.sum())
            corr_n = int(correlation_only.sum())
            root_std_only[ri] = std_n
            root_corr_only[ri] = corr_n
            primary_pairs[si] += (std_n, corr_n)
            all_disagreements[si] += int(changed.sum())
            stratum_pred_disagreements += int(changed.sum())
            all_detector_samples[si] += nshots

            counts_by_round = np.stack([detectors[:, mask].sum(axis=1) for mask in round_masks], axis=1)
            hamming = detectors.sum(axis=1)
            for cls, mask in (("standard_only_failure", standard_only),
                              ("correlation_only_failure", correlation_only),
                              ("all_prediction_disagreements", changed),
                              ("all_shots", np.ones(nshots, dtype=bool))):
                if mask.any():
                    feat = feature_acc[(si, cls)]
                    feat["shots"] += int(mask.sum())
                    feat["hamming"].extend(hamming[mask].astype(int).tolist())
                    feat["round_counts"].append(counts_by_round[mask].astype(np.float64))
                    feat["label"].extend(obs[mask].astype(int).tolist())

            # Group identical 40-bit syndromes; record whether outcomes support
            # both disagreement directions for the same syndrome signature.
            packed_signatures = np.packbits(detectors, axis=1, bitorder="little")
            for j in np.flatnonzero(changed):
                key = packed_signatures[j].tobytes()
                entry = syndromes[si][key]
                entry[0] += 1
                entry[1] += int(standard_only[j])
                entry[2] += int(correlation_only[j])
                entry[3 + int(obs[j])] += 1

            per_root.append({
                "stratum_index": si, "stratum": label, "root_index": ri,
                "seed": int(CFG["seed_allocation"]["root_seed_base"] + 100 * si + ri),
                "pooled_off_errors": int(errs[0]), "pooled_on_errors": int(errs[1]),
                "pooled_delta_ler": float(root_deltas[ri]),
                "standard_only_failures": std_n, "correlation_only_failures": corr_n,
                "prediction_disagreements": int(changed.sum())})

        res = RESULTS["per_stratum"][si]
        delta = float(root_deltas.mean())
        off_ler = float(root_arm_errors[0].sum() / (roots * nshots))
        on_ler = float(root_arm_errors[1].sum() / (roots * nshots))
        if [int(x) for x in root_arm_errors.sum(axis=1)] != [res[f"{a}_errors"] for a in ARMS]:
            raise AssertionError(f"Raw checkpoints disagree with saved per-stratum results for {label}")
        if (int(primary_pairs[si, 0]) != res["primary_standard_only_failures"] or
                int(primary_pairs[si, 1]) != res["primary_correlation_only_failures"]):
            raise AssertionError(f"Paired discordances disagree with saved results for {label}")
        per_stratum.append({
            "stratum_index": si, "stratum": label, "basis": basis, "bias_regime": regime,
            "same_name_basis_bias_pair": (basis == regime[0]),
            "shots": roots * nshots, "roots": roots, "observable_errors": raw_errors,
            "pooled_uncorrelated_errors": int(root_arm_errors[0].sum()),
            "pooled_correlated_errors": int(root_arm_errors[1].sum()),
            "pooled_uncorrelated_ler": off_ler, "pooled_correlated_ler": on_ler,
            "paired_delta_correlated_minus_uncorrelated": delta,
            "root_delta_sd": float(root_deltas.std(ddof=1)),
            "root_wins_correlated": int(np.count_nonzero(root_deltas < 0)),
            "root_losses_correlated": int(np.count_nonzero(root_deltas > 0)),
            "root_ties": int(np.count_nonzero(root_deltas == 0)),
            "standard_only_failures": int(primary_pairs[si, 0]),
            "correlation_only_failures": int(primary_pairs[si, 1]),
            "paired_prediction_disagreements": int(all_disagreements[si]),
            "disagreement_rate": float(all_disagreements[si] / (roots * nshots)),
            "regime_informed_uncorrelated_errors": int(root_arm_errors[2].sum()),
            "regime_informed_correlated_errors": int(root_arm_errors[3].sum()),
            "regime_informed_vs_pooled_correlated_delta_errors": int(root_arm_errors[3].sum() - root_arm_errors[1].sum()),
            "prediction_signature_count": len(syndromes[si]),
            "signatures_with_both_failure_directions": int(sum(1 for v in syndromes[si].values() if v[1] and v[2])),
        })

    # Summarize root-level direction by the six fixed conditions, and aggregate
    # detector-syndrome features. All statistics are descriptive/post-hoc.
    feature_rows = []
    for (si, cls), values in sorted(feature_acc.items()):
        h = np.asarray(values["hamming"], dtype=np.float64)
        rc = np.concatenate(values["round_counts"], axis=0) if values["round_counts"] else np.empty((0, 5))
        row = {"stratum_index": si, "stratum": STRATA[si], "group": cls,
               "shots": values["shots"], "mean_syndrome_weight": float(h.mean()) if h.size else None,
               "median_syndrome_weight": float(np.median(h)) if h.size else None,
               "mean_detector_time_0_triggers": float(rc[:, 0].mean()) if rc.size else None}
        row.update({f"mean_detector_time_{t}_triggers": float(rc[:, t].mean()) if rc.size else None for t in range(6)})
        feature_rows.append(row)

    dem_rows = []
    for basis in ("x", "z"):
        for regime in CFG["regimes"]:
            d = dem_summary(basis, regime)
            d["basis"] = basis
            d["regime"] = regime
            d["is_pooled_fixed_model"] = int(CFG["pooled_fixed_model_index_by_basis"][basis]) == CFG["regimes"].index(regime)
            dem_rows.append(d)

    # Same-name cells use exactly the same DEM/model for pooled-fixed and
    # regime-informed arms; this is a structural mapping fact, not an inference.
    same_name = [r for r in per_stratum if r["same_name_basis_bias_pair"]]
    other = [r for r in per_stratum if not r["same_name_basis_bias_pair"]]
    data = {
        "status": "PASS_READ_ONLY_SAVED_DATA_AUDIT",
        "source_scope": "Existing correlation-aware pilot raw NPZ checkpoints and saved Phase 2B circuits/DEMs only; no new shots generated",
        "pilot_checkpoints": 72, "paired_shots": 720000,
        "saved_result_reproduction": True,
        "aggregate": {
            "arm_errors": all_stratum_predictions.sum(axis=0).astype(int).tolist(),
            "primary_standard_only_failures": int(primary_pairs[:, 0].sum()),
            "primary_correlation_only_failures": int(primary_pairs[:, 1].sum()),
            "primary_prediction_disagreements": int(all_disagreements.sum()),
        },
        "same_name_pair_descriptive_mean_delta": float(np.mean([r["paired_delta_correlated_minus_uncorrelated"] for r in same_name])),
        "other_four_cells_descriptive_mean_delta": float(np.mean([r["paired_delta_correlated_minus_uncorrelated"] for r in other])),
        "per_stratum": per_stratum,
        "syndrome_features": feature_rows,
        "dem_metadata": dem_rows,
        "saved_circuit_hashes": circuit_hashes,
        "scope_limitations": [
            "Per-condition mechanism comparisons were identified after viewing the pilot and are exploratory.",
            "Saved predictions do not include matching paths, activated correlation-group IDs, or likelihood decompositions; specific DEM separator records cannot be causally attributed to individual corrections.",
            "Detector-pattern features are descriptive and not multiplicity-adjusted hypothesis tests.",
            "The saved labels and predictions permit residual recomputation but not reconstruction of the latent physical Pauli fault history for each shot."
        ]
    }
    (OUT / "AUDIT_METRICS.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for name, rows in (("STRATUM_METRICS.csv", per_stratum), ("ROOT_METRICS.csv", per_root),
                       ("DISAGREEMENT_FEATURES.csv", feature_rows), ("DEM_METADATA.csv", dem_rows)):
        with (OUT / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({"status": data["status"], "aggregate": data["aggregate"],
                      "same_name_mean_delta": data["same_name_pair_descriptive_mean_delta"],
                      "other_four_mean_delta": data["other_four_cells_descriptive_mean_delta"],
                      "dem_metadata": [{k: r[k] for k in ("basis", "regime", "error_records", "records_with_separator", "separator_count", "is_pooled_fixed_model")} for r in dem_rows]}, indent=2))


if __name__ == "__main__":
    main()
