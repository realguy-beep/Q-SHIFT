"""Independent V1.3 paired analysis from saved arrays. Imports no runner code.

Shared names come only from contract.py. All metadata is validated before any
output file is written, and outputs may be directed outside the run directory.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_v1_3 import contract as K  # noqa: E402

INVENTORY_PATH = ROOT / "seed_inventory.json"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binary_column(a, name: str, rows: int) -> np.ndarray:
    x = np.asarray(a)
    if x.shape != (rows, 1) or not np.isin(x, [0, 1]).all():
        raise ValueError(f"{name} is not a binary [{rows},1] matrix")
    return x[:, 0].astype(np.uint8, copy=False)


def decide(*, star_ci, a2_ci, astar_nonzero_errors, b_better_both, q0_bounds) -> str:
    """star_ci: candidate - static comparator; a2_ci: candidate - adaptive comparator;
    q0_bounds: 5th/95th percentiles of candidate - adaptive comparator at q=0."""
    if (star_ci[1] < 0 and a2_ci[1] < 0 and astar_nonzero_errors >= K.MIN_STATIC_NONZERO_ERRORS
            and b_better_both and q0_bounds[1] < K.Q0_HARM_TOLERANCE):
        return "GO_DEVELOPMENT_ONLY"
    if star_ci[0] >= 0 or q0_bounds[0] > K.Q0_HARM_TOLERANCE:
        return "NO_GO"
    return "INCONCLUSIVE"


def analyze(run_dir: Path, output_dir: Path | None = None, *,
            allocation: K.Allocation = K.FROZEN_ALLOCATION,
            inventory_path: Path = INVENTORY_PATH) -> dict:
    run_dir = Path(run_dir)
    output_dir = run_dir if output_dir is None else Path(output_dir)
    status = json.loads((run_dir / K.FILE_STATUS).read_text(encoding="utf-8"))
    identity = json.loads((run_dir / K.FILE_IDENTITY).read_text(encoding="utf-8"))
    models = json.loads((run_dir / K.FILE_MODELS).read_text(encoding="utf-8"))
    calibration = json.loads((run_dir / K.FILE_CALIBRATION).read_text(encoding="utf-8"))
    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))

    # ---- metadata validation (nothing is written before this block passes) ----
    # READY: first finalization by the runner. COMPLETED: independent re-analysis
    # (use output_dir so the finalized run directory is not rewritten).
    if status.get("state") not in (K.STATE_READY_FOR_ANALYSIS, K.STATE_COMPLETED):
        raise ValueError("runner status is not analysis-ready")
    if status.get(K.KEY_ALLOCATION) != allocation.as_dict():
        raise ValueError("run allocation does not match the analysis allocation")
    if identity.get(K.KEY_LABELS_EXPOSED) is not False:
        raise ValueError("identity record does not certify the detector-only decoder boundary")
    missing = [key for key in K.MODEL_REQUIRED_KEYS if key not in models]
    if missing:
        raise ValueError(f"{K.FILE_MODELS} lacks required keys {missing}")
    if K.KEY_ESTIMATION_SUMMARY not in calibration:
        raise ValueError(f"{K.FILE_CALIBRATION} lacks {K.KEY_ESTIMATION_SUMMARY}")
    n, shots = allocation.roots_per_q, allocation.eval_shots_per_root
    eval_calls = [c for c in status.get("sampler_calls_started", []) if c.get("phase") == "evaluation"]
    expected_keys = {K.eval_key(q, r) for q in K.QS for r in range(n)}
    by_key = {c.get("key"): c for c in eval_calls}
    if len(eval_calls) != allocation.roots or set(by_key) != expected_keys:
        raise ValueError("evaluation call/root inventory is incomplete or duplicated")
    if any(c.get("state") != "committed" or c.get("shots") != shots for c in eval_calls):
        raise ValueError("an evaluation call is not committed at the allocated size")
    if status.get("eval_shots_committed") != allocation.eval_shots:
        raise ValueError("committed evaluation shot count mismatch")
    for key, call in by_key.items():
        if int(call["seed"]) != int(inventory["seeds"][key]):
            raise ValueError(f"evaluation seed mismatch for {key}")
    if len({c.get("sample_id") for c in eval_calls}) != allocation.roots:
        raise ValueError("evaluation sample IDs are missing or duplicated")

    # ---- per-root scoring from saved arrays ----
    eval_dir = run_dir / K.DIR_EVALUATION
    rows, archive_hashes = [], {}
    errors = {}  # (qi, r) -> {arm: bool array}
    for qi, q in enumerate(K.QS):
        for r in range(n):
            call = by_key[K.eval_key(q, r)]
            path = eval_dir / K.eval_archive_name(qi, r)
            if call.get("archive") != f"{K.DIR_EVALUATION}/{path.name}":
                raise ValueError(f"archive path mismatch for {path.name}")
            file_hash = _digest(path)
            if call.get("archive_sha256") != file_hash or call.get("archive_bytes") != path.stat().st_size:
                raise ValueError(f"archive identity mismatch for {path.name}")
            archive_hashes[path.name] = file_hash
            with np.load(path, allow_pickle=False) as archive:
                expected = {"detectors", "observables", *(K.pred_member(a) for a in K.ARMS)}
                if set(archive.files) != expected:
                    raise ValueError(f"unexpected arrays in {path.name}")
                det = np.asarray(archive["detectors"])
                y = _binary_column(archive["observables"], "observables", shots)
                preds = {a: _binary_column(archive[K.pred_member(a)], a, shots) for a in K.ARMS}
            if det.shape != (shots, K.DETECTORS) or det.dtype != np.uint8 or not np.isin(det, [0, 1]).all():
                raise ValueError(f"detector array contract failed for {path.name}")
            err = {a: preds[a] != y for a in K.ARMS}
            errors[(qi, r)] = err
            row = {"q": q, "root": r, "shots": shots,
                   "detector_sha256": hashlib.sha256(det.tobytes()).hexdigest()}
            for a in K.ARMS:
                row[f"{a}_errors"] = int(err[a].sum())
            for x, base in K.CO_PRIMARY + K.SECONDARY:
                row[f"{x}_minus_{base}"] = (row[f"{x}_errors"] - row[f"{base}_errors"]) / shots
                row[f"{x}_{base}_disagreements"] = int(np.count_nonzero(preds[x] != preds[base]))
            rows.append(row)
    unexpected = [p.name for p in eval_dir.iterdir() if p.suffix == ".npz" and p.name not in archive_hashes]
    if unexpected:
        raise ValueError(f"unregistered evaluation archives: {unexpected}")

    # ---- root-stratified paired bootstrap ----
    contrasts = K.CO_PRIMARY + K.SECONDARY
    diff = {c: {q: np.asarray([row[f"{c[0]}_minus_{c[1]}"] for row in rows if row["q"] == q])
                for q in K.QS} for c in contrasts}
    rng = np.random.default_rng(int(inventory["seeds"][K.SEED_STATS_PRIMARY]))
    idx = {q: rng.integers(0, n, size=(K.BOOTSTRAPS, n)) for q in K.QS}
    summary = {}
    for c in contrasts:
        cond_boot = {q: diff[c][q][idx[q]].mean(axis=1) for q in K.QS}
        nonzero_boot = np.mean([cond_boot[q] for q in K.NONZERO_QS], axis=0)
        summary[f"{c[0]}_minus_{c[1]}"] = {
            "nonzero_equal_weight_estimate": float(np.mean([diff[c][q].mean() for q in K.NONZERO_QS])),
            "nonzero_two_sided_95_ci": np.quantile(nonzero_boot, [0.025, 0.975], method=K.QUANTILE_METHOD).tolist(),
            "by_condition": {str(q): {"estimate": float(diff[c][q].mean()),
                                      "two_sided_95_ci": np.quantile(cond_boot[q], [0.025, 0.975],
                                                                     method=K.QUANTILE_METHOD).tolist()}
                             for q in K.QS},
        }
    zrng = np.random.default_rng(int(inventory["seeds"][K.SEED_STATS_ZERO]))
    zero_diff = diff[K.SAFETY][0.0]
    zero_boot = zero_diff[zrng.integers(0, n, size=(K.BOOTSTRAPS, n))].mean(axis=1)
    q0_bounds = np.quantile(zero_boot, [0.05, 0.95], method=K.QUANTILE_METHOD).tolist()

    totals = {a: {str(q): sum(r[f"{a}_errors"] for r in rows if r["q"] == q) for q in K.QS} for a in K.ARMS}
    per_cond_shots = n * shots
    nonzero_ler = {a: float(np.mean([totals[a][str(q)] / per_cond_shots for q in K.NONZERO_QS])) for a in K.ARMS}
    cand, stat, adap = K.CANDIDATE, K.STATIC_COMPARATOR, K.ADAPTIVE_COMPARATOR
    name_static, name_adaptive = f"{cand}_minus_{stat}", f"{cand}_minus_{adap}"
    static_nonzero = sum(totals[stat][str(q)] for q in K.NONZERO_QS)
    cand_better_both = all(totals[cand][str(q)] < totals[stat][str(q)] for q in K.NONZERO_QS)
    decision = decide(star_ci=summary[name_static]["nonzero_two_sided_95_ci"],
                      a2_ci=summary[name_adaptive]["nonzero_two_sided_95_ci"],
                      astar_nonzero_errors=static_nonzero, b_better_both=cand_better_both,
                      q0_bounds=q0_bounds)

    # ---- outputs ----
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / K.FILE_PAIRED_CSV
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "schema": "qshift-correlated-decoder-v1.3-independent-analysis-v1",
        "allocation": allocation.as_dict(),
        "evaluation_roots": allocation.roots,
        "evaluation_shots": allocation.eval_shots,
        "bootstrap_replicates": K.BOOTSTRAPS,
        "bootstrap_quantile_method": K.QUANTILE_METHOD,
        "co_primary": {name: summary[name] for name in (name_static, name_adaptive)},
        "secondary_descriptive": {f"{x}_minus_{b}": summary[f"{x}_minus_{b}"] for x, b in K.SECONDARY},
        f"q0_{K.SAFETY[0]}_minus_{K.SAFETY[1]}_bootstrap_5th_95th_percentiles": q0_bounds,
        "q0_harm_tolerance": K.Q0_HARM_TOLERANCE,
        "arm_errors_by_condition": totals,
        "equal_weight_nonzero_condition_ler": nonzero_ler,
        f"{stat}_nonzero_error_count": static_nonzero,
        f"{cand}_point_ler_lower_than_{stat}_at_both_nonzero_q": cand_better_both,
        "frozen_model_settings": {k: models[k] for k in (K.KEY_ASTAR, K.KEY_ASTAR_ALT, K.KEY_TAU,
                                                         K.KEY_BSTATIC_Q, K.KEY_BOFFSTATIC_Q)},
        "calibration_estimation_diagnostics": calibration[K.KEY_ESTIMATION_SUMMARY],
        "paired_archive_sha256": archive_hashes,
        "paired_results_csv_sha256": _digest(csv_path),
        "decision": decision,
        "interpretation": "development evidence for one synthetic three-qubit mechanism at d=3; five-factor arms know the burst support; not hardware, scaling or independent-test evidence",
    }
    (output_dir / K.FILE_ANALYSIS).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                              encoding="utf-8", newline="\n")
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    result = analyze(args.run_dir.resolve(), None if args.output_dir is None else args.output_dir.resolve())
    print(json.dumps({"decision": result["decision"], "co_primary": result["co_primary"]}, indent=2))


if __name__ == "__main__":
    main()
