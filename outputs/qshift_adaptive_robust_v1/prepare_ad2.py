"""Write AD2_SEEDS.json, screened against every prior inventory (through RE2_SEEDS.json)."""
from __future__ import annotations

import hashlib
import json

import ad2_config as C
import prepare_re2 as PR

NS, NS_REH = "qshift-adaptive-robust-v1:ad2", "qshift-adaptive-robust-v1:ad2:REHEARSAL"


def screened():
    vals, rec, derive = PR.screened()
    raw = (C.ROOT / "RE2_SEEDS.json").read_bytes()
    b = json.loads(raw)
    v = set(b["seeds"].values()) | set(b["rehearsal_seeds"].values())
    vals |= v
    rec["outputs/qshift_adaptive_robust_v1/RE2_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    so = C.ROOT / "AD2_SEEDS.json"
    if so.exists():
        raise SystemExit("AD2_SEEDS.json exists")
    vals, rec, derive = screened()
    used, seeds, reh = set(vals), {}, {}
    for k in C.all_keys():
        seeds[k] = derive(NS, k, used)
        used.add(seeds[k])
    for k in C.rehearsal_keys():
        reh[k] = derive(NS_REH, k, used)
        used.add(reh[k])
    import studykit as SK
    SK.write_once_json(so, {"schema": "qshift-adaptive-robust-ad2-seeds-v1", "namespace": NS, "seeds": seeds,
                            "rehearsal_seeds": reh, "screened": rec, "union_screened": len(vals)})
    print(len(seeds), "seeds,", len(reh), "rehearsal; screened", len(vals))


if __name__ == "__main__":
    main()
