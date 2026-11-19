"""Write RE1_SEEDS.json, screened against every prior inventory plus DEV2_SEEDS.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import prepare_dev2 as P2
import re1_config as R

ROOT = Path(__file__).resolve().parent
NS, NS_REH = "qshift-adaptive-robust-v1:re1", "qshift-adaptive-robust-v1:re1:REHEARSAL"


def screened():
    vals, rec, derive = P2.screened()
    raw = (ROOT / "DEV2_SEEDS.json").read_bytes()
    d2 = json.loads(raw)
    v = set(d2["seeds"].values()) | set(d2["rehearsal_seeds"].values())
    vals |= v
    rec["outputs/qshift_adaptive_robust_v1/DEV2_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    out = ROOT / "RE1_SEEDS.json"
    if out.exists():
        raise SystemExit("RE1_SEEDS.json exists")
    vals, rec, derive = screened()
    used, seeds, reh = set(vals), {}, {}
    for k in R.all_keys():
        seeds[k] = derive(NS, k, used)
        used.add(seeds[k])
    for k in R.rehearsal_keys():
        reh[k] = derive(NS_REH, k, used)
        used.add(reh[k])
    out.write_text(json.dumps({"schema": "qshift-adaptive-robust-re1-seeds-v1", "namespace": NS, "seeds": seeds,
                               "rehearsal_seeds": reh, "screened": rec, "union_screened": len(vals)},
                              indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(seeds), "seeds,", len(reh), "rehearsal; screened", len(vals))


if __name__ == "__main__":
    main()
