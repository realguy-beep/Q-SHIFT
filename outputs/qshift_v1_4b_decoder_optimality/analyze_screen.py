"""Pre-registered V1.4B screen statistics and residual-error taxonomy (development only).

Usage: analyze_screen.py <set_name>   reads work/<set>/root_*.npz, writes work/<set>_summary.json
Thresholds and data roles: PREREGISTRATION.md. Bootstrap: 20,000 root-stratified paired
replicates, seed 20261116, equal-weight over q in {0.01, 0.02}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
QS = (0.0, 0.01, 0.02)
BOOT, SEED = 20000, 20261116


def load(set_name: str):
    data = {}
    for qi in range(3):
        for r in range(24):
            with np.load(ROOT / "work" / set_name / f"root_q{qi}_r{r:02d}.npz") as z:
                data[(qi, r)] = {k: z[k] for k in z.files}
            c_path = ROOT / "work" / f"{set_name}_C" / f"root_q{qi}_r{r:02d}.npz"
            if c_path.exists():
                with np.load(c_path) as z:
                    data[(qi, r)]["C"] = z["C"]
                    data[(qi, r)]["seconds_C"] = z["seconds"]
    return data


def arm_errors(data, arm):
    return {(qi, r): (d[arm] != d["y"]) for (qi, r), d in data.items()}


def ler_table(data, arms):
    out = {}
    for a in arms:
        err = arm_errors(data, a)
        by_q = [int(sum(err[(qi, r)].sum() for r in range(24))) for qi in range(3)]
        shots = [sum(len(data[(qi, r)]["y"]) for r in range(24)) for qi in range(3)]
        out[a] = {"errors_q0_q001_q002": by_q,
                  "ler_q0": by_q[0] / shots[0],
                  "nonzero_equal_weight_ler": float(np.mean([by_q[1] / shots[1], by_q[2] / shots[2]]))}
    return out


def paired(data, x, base):
    ex, eb = arm_errors(data, x), arm_errors(data, base)
    diff = {qi: np.asarray([ex[(qi, r)].mean() - eb[(qi, r)].mean() for r in range(24)]) for qi in range(3)}
    rng = np.random.default_rng(SEED)
    idx = {qi: rng.integers(0, 24, size=(BOOT, 24)) for qi in range(3)}
    boot = np.mean([diff[qi][idx[qi]].mean(axis=1) for qi in (1, 2)], axis=0)
    q0 = diff[0][idx[0]].mean(axis=1)
    return {"nonzero_estimate": float(np.mean([diff[1].mean(), diff[2].mean()])),
            "nonzero_95ci": np.quantile(boot, [0.025, 0.975]).tolist(),
            "q0_estimate": float(diff[0].mean()), "q0_95ci": np.quantile(q0, [0.025, 0.975]).tolist()}


def taxonomy(data, decoder, reference="R_true"):
    rows = {"q0": {}, "nonzero": {}}
    for (qi, r), d in data.items():
        y = d["y"]
        dec_fail, ref_fail = d[decoder] != y, d[reference] != y
        burst_blind_differs = d["R_zero"] != d[reference]
        boff_burst = d["boff_mask_count"] > 0
        conf = np.abs(d[f"post_{reference}"] - 0.5) * 2  # reference confidence in [0,1]
        key = "q0" if qi == 0 else "nonzero"
        for name, sel in {
            "decoder_fail_ref_ok (recoverable)": dec_fail & ~ref_fail,
            "decoder_fail_ref_fail (inherent under DEM)": dec_fail & ref_fail,
            "decoder_ok_ref_fail": ~dec_fail & ref_fail,
        }.items():
            cell = rows[key].setdefault(name, {"count": 0, "burst_blind_exact_disagrees": 0,
                                               "boff_explained_a_burst": 0, "ref_confidence_sum": 0.0})
            cell["count"] += int(sel.sum())
            cell["burst_blind_exact_disagrees"] += int((sel & burst_blind_differs).sum())
            cell["boff_explained_a_burst"] += int((sel & boff_burst).sum())
            cell["ref_confidence_sum"] += float(conf[sel].sum())
    for key in rows:
        for cell in rows[key].values():
            total = cell.pop("ref_confidence_sum")
            cell["mean_ref_confidence"] = total / cell["count"] if cell["count"] else None
    return rows


def main() -> None:
    set_name = sys.argv[1]
    data = load(set_name)
    has_c = all("C" in d for d in data.values())
    cands = ("R_true", "Bmld", "Asoft") + (("C",) if has_c else ())
    arms = [k for k in next(iter(data.values())) if k.startswith("pred_")] + ["R_true", "R_zero", "Bmld", "Asoft"] + (["C"] if has_c else [])
    table = ler_table(data, arms)
    v13 = [a for a in ("pred_Boff", "pred_BoffStatic") if a in table]
    best = min(v13, key=lambda a: table[a]["nonzero_equal_weight_ler"])
    contrasts = {f"{x}_minus_{best}": paired(data, x, best) for x in cands}
    contrasts.update({f"{x}_minus_pred_Boff": paired(data, x, "pred_Boff") for x in cands})
    contrasts["Bmld_minus_R_true"] = paired(data, "Bmld", "R_true")
    rel = {x: 1 - table[x]["nonzero_equal_weight_ler"] / table[best]["nonzero_equal_weight_ler"] for x in cands}
    if has_c:
        c_secs = [float(d["seconds_C"]) / len(d["y"]) for d in data.values()]
    secs = [float(d["seconds_exact_three"]) / 3 / len(d["y"]) for d in data.values()]
    out = {"set": set_name, "best_v1_3": best, "ler": table, "contrasts": contrasts,
           "relative_nonzero_reduction_vs_best_v1_3": rel,
           "taxonomy_vs_R_true": {dec: taxonomy(data, dec) for dec in ("pred_Boff", "pred_BoffStatic", "Bmld")
                                  if dec in arms},
           "exact_decoder_ms_per_shot_mean": 1000 * float(np.mean(secs)),
           "candidate_C_ms_per_shot_mean": 1000 * float(np.mean(c_secs)) if has_c else None,
           "label": "DEVELOPMENT ONLY on already-exposed data; not independent confirmation"}
    (ROOT / "work" / f"{set_name}_summary.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("best_v1_3", "relative_nonzero_reduction_vs_best_v1_3")}, indent=1))
    for a in ("pred_Astar", "pred_A2sw", "pred_Boff", "pred_BoffStatic", "pred_Coff", "R_true", "Bmld", "Asoft", "C", "R_zero"):
        if a in table:
            print(a, table[a]["errors_q0_q001_q002"], "nonzero %.4f%%" % (100 * table[a]["nonzero_equal_weight_ler"]))
    for k, v in contrasts.items():
        print(k, "%+.5f" % v["nonzero_estimate"], [round(c, 5) for c in v["nonzero_95ci"]], "q0 %+.5f" % v["q0_estimate"])


if __name__ == "__main__":
    main()
