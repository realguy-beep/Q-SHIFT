"""Independent V1.6b analysis from saved arrays. Imports no runner code.

Validates all metadata and archive hashes before writing; outputs may go to a separate
directory. Usage: analyze_saved.py <run_dir> [--output-dir DIR]
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

from outputs.qshift_correlated_decoder_v1_6b import contract as K  # noqa: E402

INVENTORY_PATH = ROOT / "seed_inventory.json"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decide(*, known_co_primary_upper: list[float], known_gap_upper: float, known_static_errors: int,
           known_q0_bounds: list[float], hidden_gap_upper: float, hidden_not_worse_upper: float,
           known_vs_oracle_lower: float) -> str:
    if (all(u < 0 for u in known_co_primary_upper) and known_gap_upper < K.NONINFERIORITY_MARGIN
            and known_static_errors >= K.MIN_ASTAR_ORACLE_NONZERO_ERRORS
            and known_q0_bounds[1] < K.Q0_HARM_TOLERANCE
            and hidden_gap_upper < K.NONINFERIORITY_MARGIN and hidden_not_worse_upper <= 0):
        return "GO_DEVELOPMENT_ONLY"
    if known_vs_oracle_lower >= 0 or known_q0_bounds[0] > K.Q0_HARM_TOLERANCE:
        return "NO_GO"
    return "INCONCLUSIVE"


def target(relative_ci: list[float]) -> str:
    return "TARGET_MET" if relative_ci[0] >= K.TARGET_RELATIVE_REDUCTION_LOWER_BOUND else "TARGET_NOT_MET"


def analyze(run_dir: Path, output_dir: Path | None = None, *, allocation: K.Allocation = K.FROZEN_ALLOCATION,
            inventory_path: Path = INVENTORY_PATH) -> dict:
    run_dir = Path(run_dir)
    output_dir = run_dir if output_dir is None else Path(output_dir)
    status = json.loads((run_dir / K.FILE_STATUS).read_text(encoding="utf-8"))
    identity = json.loads((run_dir / K.FILE_IDENTITY).read_text(encoding="utf-8"))
    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    if status.get("state") not in (K.STATE_READY_FOR_ANALYSIS, K.STATE_COMPLETED):
        raise ValueError("runner status is not analysis-ready")
    if status.get("allocation") != allocation.as_dict():
        raise ValueError("run allocation does not match the analysis allocation")
    if identity.get(K.KEY_LABELS_EXPOSED) is not False:
        raise ValueError("identity record does not certify the detector-only decoder boundary")
    n, shots = allocation.roots_per_q, allocation.eval_shots_per_root
    calls = {c["key"]: c for c in status.get("sampler_calls_started", [])}
    if len(calls) != allocation.sampler_calls or any(c.get("state") != "committed" for c in calls.values()):
        raise ValueError("sampler-call inventory is incomplete or not fully committed")
    for key, c in calls.items():
        if int(c["seed"]) != int(inventory["seeds"][key]):
            raise ValueError(f"seed mismatch for {key}")
        if _digest(run_dir / c["archive"]) != c["archive_sha256"]:
            raise ValueError(f"archive hash mismatch for {c['archive']}")
    models, devices = {}, {}
    for cond in K.CONDITIONS:
        models[cond] = json.loads((run_dir / cond / K.FILE_MODELS).read_text(encoding="utf-8"))
        devices[cond] = json.loads((run_dir / cond / K.FILE_DEVICE).read_text(encoding="utf-8"))
        missing = [k for k in K.MODEL_REQUIRED_KEYS if k not in models[cond]]
        if missing:
            raise ValueError(f"{cond}/{K.FILE_MODELS} lacks required keys {missing}")

    rows, per = [], {}
    for cond in K.CONDITIONS:
        for qi, q in enumerate(K.QS):
            for r in range(n):
                path = run_dir / cond / K.DIR_EVALUATION / K.eval_archive_name(qi, r)
                with np.load(path, allow_pickle=False) as z:
                    if set(z.files) != {"detectors", "observables", *(K.pred_member(a) for a in K.ARMS)}:
                        raise ValueError(f"unexpected arrays in {path}")
                    y = z["observables"][:, 0]
                    if len(y) != shots:
                        raise ValueError(f"shot count mismatch in {path}")
                    err = {a: z[K.pred_member(a)][:, 0] != y for a in K.ARMS}
                row = {"condition": cond, "q": q, "root": r, "shots": shots}
                for a in K.ARMS:
                    row[f"{a}_errors"] = int(err[a].sum())
                for x, b in K.CONTRASTS:
                    row[f"{x}_minus_{b}"] = (row[f"{x}_errors"] - row[f"{b}_errors"]) / shots
                rows.append(row)
                per[(cond, qi, r)] = row

    out = {}
    for ci, cond in enumerate(K.CONDITIONS):
        rng = np.random.default_rng(int(inventory["seeds"][K.stats_key(cond, "primary")]))
        idx = {qi: rng.integers(0, n, size=(K.BOOTSTRAPS, n)) for qi in range(3)}
        diff = lambda x, b, qi: np.asarray([per[(cond, qi, r)][f"{x}_minus_{b}"] for r in range(n)])  # noqa: E731
        ler = lambda a, qi: np.asarray([per[(cond, qi, r)][f"{a}_errors"] / shots for r in range(n)])  # noqa: E731
        contrasts = {}
        for x, b in K.CONTRASTS:
            boot = np.mean([diff(x, b, qi)[idx[qi]].mean(axis=1) for qi in (1, 2)], axis=0)
            contrasts[f"{x}_minus_{b}"] = {
                "nonzero_estimate": float(np.mean([diff(x, b, qi).mean() for qi in (1, 2)])),
                "nonzero_95ci": np.quantile(boot, [0.025, 0.975], method=K.QUANTILE_METHOD).tolist(),
                "q0_estimate": float(diff(x, b, 0).mean())}
        zrng = np.random.default_rng(int(inventory["seeds"][K.stats_key(cond, "zero")]))
        q0 = diff(*K.SAFETY, 0)[zrng.integers(0, n, size=(K.BOOTSTRAPS, n))].mean(axis=1)
        tx, tb = K.TARGET
        bx = np.mean([ler(tx, qi)[idx[qi]].mean(axis=1) for qi in (1, 2)], axis=0)
        bb = np.mean([ler(tb, qi)[idx[qi]].mean(axis=1) for qi in (1, 2)], axis=0)
        nz = {a: float(np.mean([ler(a, qi).mean() for qi in (1, 2)])) for a in K.ARMS}
        defined = bb > 0  # a replicate with zero comparator errors has an undefined ratio
        rel_boot = 1 - bx[defined] / bb[defined]
        rel_ci = (np.quantile(rel_boot, [0.025, 0.975], method=K.QUANTILE_METHOD).tolist()
                  if defined.all() else [float("-inf"), float("inf")])
        out[cond] = {
            "contrasts": contrasts,
            "q0_safety_5th_95th": np.quantile(q0, [0.05, 0.95], method=K.QUANTILE_METHOD).tolist(),
            "relative_reduction_Blearn_vs_Astar_oracle": {
                "estimate": 1 - nz[tx] / nz[tb] if nz[tb] else None,
                "95ci": rel_ci, "undefined_replicates": int((~defined).sum()),
                "rule": "if any replicate has zero comparator errors the interval is reported as unbounded (target not met)"},
            "arm_errors_q0_q001_q002": {a: [sum(per[(cond, qi, r)][f"{a}_errors"] for r in range(n)) for qi in range(3)]
                                        for a in K.ARMS},
            "nonzero_ler": nz,
            "learned": {"class_index": models[cond][K.KEY_LEARNED_CLASS], "flip": models[cond][K.KEY_LEARNED_FLIP],
                        "true_class_index": models[cond].get("true_class_index"), "true_flip": models[cond].get("true_flip"),
                        "class_correct": models[cond][K.KEY_LEARNED_CLASS] == models[cond].get("true_class_index"),
                        "flip_correct": models[cond][K.KEY_LEARNED_FLIP] == models[cond].get("true_flip"),
                        "device_q_hat": devices[cond]["device_q_hat"], "delta": devices[cond]["delta"]},
        }
    k, h = out["known"], out["hidden"]
    name = lambda pair: f"{pair[0]}_minus_{pair[1]}"  # noqa: E731
    decision = decide(
        known_co_primary_upper=[k["contrasts"][name(p)]["nonzero_95ci"][1] for p in K.KNOWN_CO_PRIMARY],
        known_gap_upper=k["contrasts"][name(K.ORACLE_GAP)]["nonzero_95ci"][1],
        known_static_errors=sum(k["arm_errors_q0_q001_q002"]["Astar_oracle"][1:]),
        known_q0_bounds=k["q0_safety_5th_95th"],
        hidden_gap_upper=h["contrasts"][name(K.ORACLE_GAP)]["nonzero_95ci"][1],
        hidden_not_worse_upper=h["contrasts"][name(K.HIDDEN_NOT_WORSE)]["nonzero_95ci"][1],
        known_vs_oracle_lower=k["contrasts"][name(K.KNOWN_CO_PRIMARY[0])]["nonzero_95ci"][0])
    target_status = target(k["relative_reduction_Blearn_vs_Astar_oracle"]["95ci"])

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / K.FILE_PAIRED_CSV
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    result = {"schema": "qshift-correlated-decoder-v1.6b-independent-analysis-v1", "allocation": allocation.as_dict(),
              "bootstrap_replicates": K.BOOTSTRAPS, "conditions": out, "decision": decision,
              "target_endpoint": {"definition": "known burst: 95% lower bound of 1 - LER(Blearn)/LER(Astar_oracle) >= 0.40",
                                  "status": target_status},
              "paired_results_csv_sha256": _digest(csv_path),
              "interpretation": "development evidence for one synthetic d=3 mechanism plus one hidden synthetic burst; Blearn learns support from device calibration (detector-only) and the logical bit from a labeled device partition; exact only for the DEM"}
    (output_dir / K.FILE_ANALYSIS).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                              encoding="utf-8", newline="\n")
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    r = analyze(args.run_dir.resolve(), None if args.output_dir is None else args.output_dir.resolve())
    print(json.dumps({"decision": r["decision"], "target": r["target_endpoint"]["status"]}, indent=2))


if __name__ == "__main__":
    main()
