"""BRT-0: E1T (cap OR S1 OR S2; no statistic) on EXISTING BRE and BRS data (PLAN_BRT.md). No sampling. Design check
only: both studies informed E1T, so nothing here is evidence or a verdict.

BRS records already hold E1's fit and the subset-rule structural flags. BRE records do not hold the excluded set, so
E1 is recomputed from BRE's saved arrays (reproducing BRE's fit, checked) and the structural flags are evaluated.

  python brt0.py [--workers 8]     -> results/brt/BRT0.json (aggregates)
"""
from __future__ import annotations

import argparse
import glob
import json
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import brt_config as C  # noqa: F401  (sys.path)

ROOT = Path(__file__).resolve().parent
BRE = ROOT / "work" / "bre" / "eval"
OUT = ROOT / "results" / "brt" / "BRT0.json"


def bre_job(name):
    import estimate3 as E3
    import estimate4 as E4
    import estimate5 as E5
    rec = json.loads((BRE / "records" / name).read_text(encoding="utf-8"))
    z = np.load(BRE / "arrays" / name.replace(".json", ".npz"))
    obs, n = E3.rates_from_rows(np.unpackbits(z["det"], axis=1)[:, :120])
    f = E4.e1_with_set(obs, n)
    same = all(f[k] == rec["fit"]["E1"][k] for k in ("p_hat", "b_hat", "stat", "excluded"))
    st = E4.structural_flags(f["excluded_set"], rec["learn"]["E1"]["class_index"])
    return {"study": "BRE", "cond": rec["cond"], "kind": rec["kind"], "in_family": rec["in_family"], "reproduces": same,
            "e1t": E5.e1t_flag(f, st), "e1s": E4.e1_flag(f) or st["S1_shape"] or st["S2_consistency"],
            "accepted": rec["learn"]["E1"]["class_index"], "ok": rec["learn"]["E1"]["learned_correct"]}


def brs_rows():
    import estimate4 as E4
    import estimate5 as E5
    out = []
    for p in sorted(glob.glob(str(ROOT / "results" / "brs" / "records" / "*.json"))):
        r = json.loads(Path(p).read_text(encoding="utf-8"))
        st, f = r["structural"], r["fit"]["E1"]
        out.append({"study": "BRS", "cond": r["cond"], "kind": r["kind"], "in_family": r["role"] == "in",
                    "reproduces": True, "e1t": E5.e1t_flag(f, st),
                    "e1s": E4.e1_flag(f) or st["S1_shape"] or st["S2_consistency"],
                    "accepted": r["learn"]["E1"]["class_index"], "ok": r["learn"]["E1"]["learned_correct"]})
    return out


def main(workers):
    if OUT.exists():
        raise SystemExit("BRT0.json exists; BRT-0 runs once")
    names = sorted(p.name for p in (BRE / "records").glob("*.json"))
    with get_context("spawn").Pool(workers) as pool:
        rows = pool.map(bre_job, names)
    rows += brs_rows()
    res = {"schema": "qshift-adaptive-robust-brt0-v1", "status": "design check on BRE and BRS data; not evidence",
           "bre_fits_reproduced": all(r["reproduces"] for r in rows if r["study"] == "BRE"), "studies": {}}
    for study in ("BRE", "BRS"):
        d = {}
        for c in sorted({r["cond"] for r in rows if r["study"] == study}):
            cell = {}
            for arm in ("e1t", "e1s"):
                b = [r for r in rows if r["study"] == study and r["cond"] == c and r["kind"] == "burst"]
                z = [r for r in rows if r["study"] == study and r["cond"] == c and r["kind"] == "q0"]
                cell[arm] = {"burst_pools": len(b), "burst_flagged": sum(r[arm] for r in b),
                             "burst_learned": sum((not r[arm]) and r["ok"] for r in b),
                             "q0_pools": len(z), "q0_flagged": sum(r[arm] for r in z),
                             "q0_false_accepts": sum((not r[arm]) and r["accepted"] is not None for r in z)}
            d[c] = cell
        res["studies"][study] = d
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    for study, d in res["studies"].items():
        for c, cell in d.items():
            print(study, c, {a: [v["burst_flagged"], v["burst_learned"], v["q0_flagged"], v["q0_false_accepts"]]
                             for a, v in cell.items()})
    print("BRE fits reproduced:", res["bre_fits_reproduced"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    main(ap.parse_args().workers)
