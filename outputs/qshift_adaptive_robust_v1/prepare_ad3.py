"""Write AD3_SEEDS.json (study, rehearsal and Phase 1 screen seeds), screened against every prior inventory
(through AD2_SEEDS.json)."""
from __future__ import annotations

import hashlib
import json

import ad3_config as C
import prepare_ad2 as P2

NS = "qshift-adaptive-robust-v1:ad3"
NS_REH, NS_SCR = NS + ":REHEARSAL", NS + ":SCREEN"


def screened():
    vals, rec, derive = P2.screened()
    raw = (C.ROOT / "AD2_SEEDS.json").read_bytes()
    b = json.loads(raw)
    v = set(b["seeds"].values()) | set(b["rehearsal_seeds"].values())
    vals |= v
    rec["outputs/qshift_adaptive_robust_v1/AD2_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    so = C.ROOT / "AD3_SEEDS.json"
    if so.exists():
        raise SystemExit("AD3_SEEDS.json exists")
    vals, rec, derive = screened()
    used, out = set(vals), {}
    for name, ns, keys in (("seeds", NS, C.all_keys()), ("rehearsal_seeds", NS_REH, C.rehearsal_keys()),
                           ("screen_seeds", NS_SCR, C.screen_keys())):
        out[name] = {}
        for k in keys:
            out[name][k] = derive(ns, k, used)
            used.add(out[name][k])
    import studykit as SK
    SK.write_once_json(so, {"schema": "qshift-adaptive-robust-ad3-seeds-v1", "namespace": NS, **out,
                            "screened": rec, "union_screened": len(vals)})
    print({k: len(v) for k, v in out.items()}, "screened", len(vals))


if __name__ == "__main__":
    main()
