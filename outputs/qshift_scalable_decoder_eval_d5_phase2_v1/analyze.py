"""Pre-registered Phase 2 (d=5) analysis. Deterministic; re-running on the same run gives identical output.

Usage: analyze.py <mode> <run_dir> <output_dir>
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import contract as K  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safety_passes(q0_95th: float, q0_margin: float) -> bool:
    """Not worse at q=0: 95th percentile <= 0, or below the relative margin."""
    return q0_95th <= 0 or q0_95th < q0_margin


def decide(co_ci: list[float], q0_95th: float, q0_margin: float) -> str:
    safety_ok = safety_passes(q0_95th, q0_margin)
    if co_ci[0] > 0 or not safety_ok:
        return "NO-GO_d5"
    if co_ci[1] < 0:
        return "GO_d5"
    return "INCONCLUSIVE"


def load_rows(mode: str, run_dir: Path) -> list[dict]:
    alloc = K.MODES[mode]
    status = json.loads((run_dir / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if status["state"] != "ready_for_analysis" or status["mode"] != mode or status["allocation"] != alloc.as_dict():
        raise ValueError("run is not analysis-ready for this mode/allocation")
    seeds = json.loads((ROOT / "SEEDS.json").read_text(encoding="utf-8"))
    rows = []
    for qi in range(len(K.QS)):
        for r in range(alloc.roots_per_q):
            rec = json.loads((run_dir / "roots" / f"{K.stem(qi, r)}.json").read_text(encoding="utf-8"))
            if mode == "eval" and rec["seed"] != seeds["seeds"][K.root_key(qi, r)]:
                raise ValueError(f"seed mismatch {K.root_key(qi, r)}")
            if mode == "rehearsal" and rec["seed"] != seeds["rehearsal_seeds"][K.root_key(qi, r)]:
                raise ValueError(f"rehearsal seed mismatch {K.root_key(qi, r)}")
            path = run_dir / rec["archive"]
            if sha(path) != rec["archive_sha256"]:
                raise ValueError(f"archive hash mismatch {path}")
            with np.load(path) as z:
                y, n = z["observables"], alloc.shots_per_root
                if len(y) != n or rec["shots"] != n:
                    raise ValueError(f"shot count mismatch {path}")
                err = {a: np.unpackbits(z[f"pred_{a}"])[:n] != y for a in K.ARMS}
            row = {"q": K.QS[qi], "root": r, "shots": n}
            for a in K.ARMS:
                row[f"{a}_errors"] = int(err[a].sum())
                if row[f"{a}_errors"] != rec["errors"][a]:
                    raise ValueError(f"recorded error count mismatch {K.stem(qi, r)} {a}")
            rows.append(row)
    return rows


def analyze(mode: str, run_dir: Path, output_dir: Path) -> dict:
    alloc = K.MODES[mode]
    rows = load_rows(mode, Path(run_dir))
    seeds = json.loads((ROOT / "SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    n, shots = alloc.roots_per_q, alloc.shots_per_root
    ler = {(a, qi): np.asarray([rows[qi * n + r][f"{a}_errors"] / shots for r in range(n)])
           for a in K.ARMS for qi in range(len(K.QS))}
    rng = np.random.default_rng(int(seeds[K.STATS_KEYS[0]]))
    idx = {qi: rng.integers(0, n, size=(K.BOOTSTRAPS, n)) for qi in (1, 2)}
    zidx = np.random.default_rng(int(seeds[K.STATS_KEYS[1]])).integers(0, n, size=(K.BOOTSTRAPS, n))
    boot_nz = {a: np.mean([ler[(a, qi)][idx[qi]].mean(axis=1) for qi in (1, 2)], axis=0) for a in K.ARMS}
    nz = {a: float(np.mean([ler[(a, qi)].mean() for qi in (1, 2)])) for a in K.ARMS}
    q0 = {a: float(ler[(a, 0)].mean()) for a in K.ARMS}
    contrasts = {}
    for x, b in K.CONTRASTS:
        bz = ler[(x, 0)][zidx].mean(axis=1) - ler[(b, 0)][zidx].mean(axis=1)
        contrasts[f"{x}_minus_{b}"] = {
            "nonzero_estimate": nz[x] - nz[b],
            "nonzero_95ci": np.quantile(boot_nz[x] - boot_nz[b], [0.025, 0.975], method=K.QUANTILE_METHOD).tolist(),
            "q0_estimate": q0[x] - q0[b],
            "q0_95ci": np.quantile(bz, [0.025, 0.975], method=K.QUANTILE_METHOD).tolist()}
    x, b = K.CANDIDATE, K.COMPARATOR
    q0_boot = ler[(x, 0)][zidx].mean(axis=1) - ler[(b, 0)][zidx].mean(axis=1)
    q0_95th = float(np.quantile(q0_boot, 0.95, method=K.QUANTILE_METHOD))
    q0_margin = K.SAFETY_RELATIVE_MARGIN * q0[b]
    defined = boot_nz[b] > 0
    rel_ci = (np.quantile(1 - boot_nz[x][defined] / boot_nz[b][defined], [0.025, 0.975],
                          method=K.QUANTILE_METHOD).tolist() if defined.all() else [float("-inf"), float("inf")])
    co_ci = contrasts[f"{x}_minus_{b}"]["nonzero_95ci"]
    totals = {a: [int(sum(rows[qi * n + r][f"{a}_errors"] for r in range(n))) for qi in range(len(K.QS))] for a in K.ARMS}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "paired_roots.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    result = {
        "schema": "qshift-d5-phase2-analysis-v1", "mode": mode, "allocation": alloc.as_dict(),
        "bootstrap_replicates": K.BOOTSTRAPS, "arm_errors_q0_q001_q002": totals,
        "nonzero_ler_equal_weight": nz, "q0_ler": q0, "contrasts": contrasts,
        "co_primary": {"contrast": f"{x}_minus_{b}", "nonzero_95ci": co_ci, "passes": co_ci[1] < 0},
        "safety_q0": {"95th_percentile": q0_95th, "margin": q0_margin, "passes": safety_passes(q0_95th, q0_margin)},
        "relative_reduction_L2s_vs_Astar": {"estimate": 1 - nz[x] / nz[b] if nz[b] else None, "95ci": rel_ci,
                                            "undefined_replicates": int((~defined).sum())},
        "decision": decide(co_ci, q0_95th, q0_margin),
        "paired_roots_csv_sha256": sha(csv_path),
        "label": ("FAKE PIPELINE TEST: not data" if mode == "fake" else
                  "REHEARSAL: not evidence" if mode == "rehearsal" else
                  "Phase 2 d=5 frozen evaluation; one synthetic burst mechanism; simulation only"),
    }
    (output_dir / "ANALYSIS.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                              encoding="utf-8", newline="\n")
    return result


if __name__ == "__main__":
    res = analyze(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]))
    print("DECISION", res["decision"], "| co-primary CI", res["co_primary"]["nonzero_95ci"],
          "| R", res["relative_reduction_L2s_vs_Astar"], "| errors", res["arm_errors_q0_q001_q002"])
