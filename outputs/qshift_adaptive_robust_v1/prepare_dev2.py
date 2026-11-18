"""Write DEV2_SEEDS.json (screened against every prior inventory) and FLAG_THRESHOLD.json (from H-E1b records)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import dev2_config as D

ROOT = Path(__file__).resolve().parent
NS, NS_REH = "qshift-adaptive-robust-v1:dev2", "qshift-adaptive-robust-v1:dev2:REHEARSAL"


def screened():
    import importlib.util
    lowp = D.OUTS / "qshift_d5_lowp_regime_v1"
    spec = importlib.util.spec_from_file_location("lowp_pes", lowp / "prepare_eval_seeds.py")
    import sys
    sys.path.insert(0, str(lowp))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    vals, rec = mod.screened_values()
    raw = (lowp / "EVAL_SEEDS.json").read_bytes()
    ev = json.loads(raw)
    v = set(ev["seeds"].values()) | set(ev["rehearsal_seeds"].values())
    vals |= v
    rec["outputs/qshift_d5_lowp_regime_v1/EVAL_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, mod.P.derive


def main():
    out = ROOT / "DEV2_SEEDS.json"
    if out.exists():
        raise SystemExit("DEV2_SEEDS.json exists")
    vals, rec, derive = screened()
    used = set(vals)
    seeds, reh = {}, {}
    for k in D.all_keys():
        seeds[k] = derive(NS, k, used)
        used.add(seeds[k])
    for k in D.rehearsal_keys():
        reh[k] = derive(NS_REH, k, used)
        used.add(reh[k])
    out.write_text(json.dumps({"schema": "qshift-adaptive-robust-dev2-seeds-v1", "namespace": NS, "seeds": seeds,
                               "rehearsal_seeds": reh, "screened": rec, "union_screened": len(vals)},
                              indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    objs = [json.loads(p.read_text(encoding="utf-8"))["fit_objective"] for p in sorted((ROOT / "results/he1b/pools").glob("*.json"))]
    if len(objs) != 192:
        raise SystemExit("need the 192 H-E1b records")
    (ROOT / "FLAG_THRESHOLD.json").write_text(json.dumps(
        {"rule": "max H-E1b grid-fit objective over the 192 in-family development pools",
         "threshold": max(objs), "n_pools": len(objs), "median": sorted(objs)[96]}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    print(len(seeds), "seeds,", len(reh), "rehearsal; screened", len(vals), "; flag threshold", max(objs))


if __name__ == "__main__":
    main()
