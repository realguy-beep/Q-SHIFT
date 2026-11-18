"""Pre-registered Stage E analysis (PROTOCOL.md). Deterministic; re-running gives identical output.

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
import eval_contract as K  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safety_passes(q0_95th: float, margin: float) -> bool:
    return q0_95th <= 0 or q0_95th < margin


def decide(co_ci: list[float], q0_95th: float, margin: float) -> str:
    if co_ci[0] > 0 or not safety_passes(q0_95th, margin):
        return "NO-GO"
    return "GO" if co_ci[1] < 0 else "INCONCLUSIVE"


def overall(per: dict) -> str:
    """Bonferroni verdict over the two conditions."""
    if any(v["decision"] == "NO-GO" for v in per.values()):
        return "NOT_CONFIRMED"
    passes = [v["co_primary"]["passes_bonferroni"] and v["safety_q0"]["passes"] for v in per.values()]
    if all(passes):
        return "CONFIRMED"
    return "PARTIAL" if any(passes) else "INCONCLUSIVE"


def target(rel: dict) -> str:
    """Pre-registered 95% target statement for one condition's R = 1 - LER(L2s)/LER(Astar)."""
    if rel["estimate"] is None:
        return "TARGET_UNDEFINED"
    if rel["95ci"][0] >= K.TARGET_R:
        return "TARGET_MET_WITH_MARGIN"
    return "TARGET_MET" if rel["estimate"] >= K.TARGET_R else "TARGET_NOT_MET"


def load_rows(mode: str, run_dir: Path) -> list[dict]:
    alloc = K.MODES[mode]
    status = json.loads((run_dir / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if status["state"] != "ready_for_analysis" or status["mode"] != mode or status["allocation"] != alloc.as_dict():
        raise ValueError("run is not analysis-ready for this mode/allocation")
    seeds = json.loads((ROOT / "EVAL_SEEDS.json").read_text(encoding="utf-8"))
    rows = []
    for c, qi, r in K.jobs(alloc):
        rec = json.loads((run_dir / "roots" / f"{K.stem(c, qi, r)}.json").read_text(encoding="utf-8"))
        if mode == "eval" and rec["seed"] != seeds["seeds"][K.root_key(c, qi, r)]:
            raise ValueError(f"seed mismatch {K.root_key(c, qi, r)}")
        if mode == "rehearsal" and rec["seed"] != seeds["rehearsal_seeds"][K.root_key(c, qi, r)]:
            raise ValueError(f"rehearsal seed mismatch {K.root_key(c, qi, r)}")
        path = run_dir / rec["archive"]
        if sha(path) != rec["archive_sha256"]:
            raise ValueError(f"archive hash mismatch {path}")
        with np.load(path) as z:
            y, n = z["observables"], alloc.shots(c)
            if len(y) != n or rec["shots"] != n:
                raise ValueError(f"shot count mismatch {path}")
            err = {a: np.unpackbits(z[f"pred_{a}"])[:n] != y for a in K.ARMS}
        row = {"cond": c, "q": K.QS[qi], "root": r, "shots": n}
        for a in K.ARMS:
            row[f"{a}_errors"] = int(err[a].sum())
            if row[f"{a}_errors"] != rec["errors"][a]:
                raise ValueError(f"recorded error count mismatch {K.stem(c, qi, r)} {a}")
        rows.append(row)
    return rows


def analyze_condition(cond: str, rows: list[dict], alloc, seeds: dict) -> dict:
    n, shots = alloc.roots_per_q, alloc.shots(cond)
    by = {(r["q"], r["root"]): r for r in rows if r["cond"] == cond}
    ler = {(a, qi): np.asarray([by[(K.QS[qi], r)][f"{a}_errors"] / shots for r in range(n)])
           for a in K.ARMS for qi in range(len(K.QS))}
    k_nz, k_z = K.stats_keys(cond)
    rng = np.random.default_rng(int(seeds[k_nz]))
    idx = {qi: rng.integers(0, n, size=(K.BOOTSTRAPS, n)) for qi in (1, 2)}
    zidx = np.random.default_rng(int(seeds[k_z])).integers(0, n, size=(K.BOOTSTRAPS, n))
    boot = {a: np.mean([ler[(a, qi)][idx[qi]].mean(axis=1) for qi in (1, 2)], axis=0) for a in K.ARMS}
    nz = {a: float(np.mean([ler[(a, qi)].mean() for qi in (1, 2)])) for a in K.ARMS}
    q0 = {a: float(ler[(a, 0)].mean()) for a in K.ARMS}
    lo, hi = K.ALPHA_BONFERRONI / 2, 1 - K.ALPHA_BONFERRONI / 2
    contrasts = {}
    for x, b in K.CONTRASTS:
        d = boot[x] - boot[b]
        bz = ler[(x, 0)][zidx].mean(axis=1) - ler[(b, 0)][zidx].mean(axis=1)
        contrasts[f"{x}_minus_{b}"] = {
            "nonzero_estimate": nz[x] - nz[b],
            "nonzero_95ci": np.quantile(d, [0.025, 0.975], method=K.QUANTILE_METHOD).tolist(),
            "nonzero_bonferroni_ci": np.quantile(d, [lo, hi], method=K.QUANTILE_METHOD).tolist(),
            "q0_estimate": q0[x] - q0[b],
            "q0_95ci": np.quantile(bz, [0.025, 0.975], method=K.QUANTILE_METHOD).tolist()}
    x, b = K.CANDIDATE, K.COMPARATOR
    q0_boot = ler[(x, 0)][zidx].mean(axis=1) - ler[(b, 0)][zidx].mean(axis=1)
    q0_95th = float(np.quantile(q0_boot, 0.95, method=K.QUANTILE_METHOD))
    margin = K.SAFETY_RELATIVE_MARGIN * q0[b]
    defined = boot[b] > 0
    rel = 1 - boot[x][defined] / boot[b][defined]
    rel_ci = np.quantile(rel, [0.025, 0.975], method=K.QUANTILE_METHOD).tolist() if defined.all() else [float("-inf"), float("inf")]
    co = contrasts[f"{x}_minus_{b}"]
    totals = {a: [int(sum(by[(K.QS[qi], r)][f"{a}_errors"] for r in range(n))) for qi in range(len(K.QS))] for a in K.ARMS}
    out = {"selection": K.SELECTION[cond], "arm_errors_q0_q001_q002": totals, "nonzero_ler_equal_weight": nz,
            "q0_ler": q0, "contrasts": contrasts,
            "co_primary": {"contrast": f"{x}_minus_{b}", "nonzero_95ci": co["nonzero_95ci"],
                           "nonzero_bonferroni_ci": co["nonzero_bonferroni_ci"], "passes_95": co["nonzero_95ci"][1] < 0,
                           "passes_bonferroni": co["nonzero_bonferroni_ci"][1] < 0},
            "safety_q0": {"95th_percentile": q0_95th, "margin": margin, "passes": safety_passes(q0_95th, margin)},
            "relative_reduction_L2s_vs_Astar": {"estimate": 1 - nz[x] / nz[b] if nz[b] else None, "95ci": rel_ci,
                                                "undefined_replicates": int((~defined).sum())},
            "decision": decide(co["nonzero_95ci"], q0_95th, margin)}
    out["target_statement"] = target(out["relative_reduction_L2s_vs_Astar"])
    return out


def analyze(mode: str, run_dir: Path, output_dir: Path) -> dict:
    alloc = K.MODES[mode]
    rows = load_rows(mode, Path(run_dir))
    seeds = json.loads((ROOT / "EVAL_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    per = {c: analyze_condition(c, rows, alloc, seeds) for c in K.CONDITIONS}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "paired_roots.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    result = {"schema": "qshift-d5-lowp-regime-analysis-v1", "mode": mode, "allocation": alloc.as_dict(),
              "bootstrap_replicates": K.BOOTSTRAPS, "alpha_bonferroni": K.ALPHA_BONFERRONI, "conditions": per,
              "overall_verdict": overall(per), "target_condition": K.TARGET_CONDITION, "target_r": K.TARGET_R,
              "target_verdict": per[K.TARGET_CONDITION]["target_statement"], "paired_roots_csv_sha256": sha(csv_path),
              "label": ("FAKE PIPELINE TEST: not data" if mode == "fake" else "REHEARSAL: not evidence" if mode == "rehearsal"
                        else "d=5 low-p burst-dominated regime frozen evaluation (p=0.001, 0.0015); oracle support; simulation only")}
    (output_dir / "ANALYSIS.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                              encoding="utf-8", newline="\n")
    return result


if __name__ == "__main__":
    res = analyze(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]))
    print("OVERALL", res["overall_verdict"], "TARGET", res["target_verdict"])
    for c, v in res["conditions"].items():
        print(c, v["decision"], "bonf", v["co_primary"]["passes_bonferroni"], "R", v["relative_reduction_L2s_vs_Astar"], v["target_statement"],
              v["arm_errors_q0_q001_q002"])
