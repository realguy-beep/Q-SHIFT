"""Write AD1_SEEDS.json, screened against every prior inventory (through BRT_SEEDS.json)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import ad1_config as C
import prepare_brt as PT

ROOT = Path(__file__).resolve().parent
NS, NS_REH = "qshift-adaptive-robust-v1:ad1", "qshift-adaptive-robust-v1:ad1:REHEARSAL"


def screened():
    vals, rec, derive = PT.screened()
    raw = (ROOT / "BRT_SEEDS.json").read_bytes()
    b = json.loads(raw)
    v = set(b["seeds"].values()) | set(b["rehearsal_seeds"].values())
    vals |= v
    rec["outputs/qshift_adaptive_robust_v1/BRT_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    so = ROOT / "AD1_SEEDS.json"
    if so.exists():
        raise SystemExit("AD1_SEEDS.json exists")
    vals, rec, derive = screened()
    used, seeds, reh = set(vals), {}, {}
    for k in C.all_keys():
        seeds[k] = derive(NS, k, used)
        used.add(seeds[k])
    for k in C.rehearsal_keys():
        reh[k] = derive(NS_REH, k, used)
        used.add(reh[k])
    so.write_text(json.dumps({"schema": "qshift-adaptive-robust-ad1-seeds-v1", "namespace": NS, "seeds": seeds,
                              "rehearsal_seeds": reh, "screened": rec, "union_screened": len(vals)},
                             indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(seeds), "seeds,", len(reh), "rehearsal; screened", len(vals))


if __name__ == "__main__":
    main()
