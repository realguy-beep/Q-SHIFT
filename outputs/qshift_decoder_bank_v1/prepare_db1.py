"""Write DB1_SEEDS.json (training, validation and fidelity-free seeds), screened against every prior inventory
(through AD3_SEEDS.json)."""
from __future__ import annotations

import hashlib
import json

import db_config as C
import prepare_ad3 as P3
import studykit as SK

NS = "qshift-decoder-bank-v1:db1"


def screened():
    vals, rec, derive = P3.screened()
    raw = (C.ADR / "AD3_SEEDS.json").read_bytes()
    b = json.loads(raw)
    v = set(b["seeds"].values()) | set(b["rehearsal_seeds"].values()) | set(b["screen_seeds"].values())
    vals |= v
    rec["outputs/qshift_adaptive_robust_v1/AD3_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    so = C.ROOT / "DB1_SEEDS.json"
    if so.exists():
        raise SystemExit("DB1_SEEDS.json exists")
    vals, rec, derive = screened()
    used, out = set(vals), {}
    for name, ns, keys in (("train_seeds", NS + ":TRAIN", C.train_keys()), ("seeds", NS, C.all_keys())):
        out[name] = {}
        for k in keys:
            out[name][k] = derive(ns, k, used)
            used.add(out[name][k])
    SK.write_once_json(so, {"schema": "qshift-decoder-bank-db1-seeds-v1", "namespace": NS, **out,
                            "screened": rec, "union_screened": len(vals)})
    print({k: len(v) for k, v in out.items()}, "screened", len(vals))


if __name__ == "__main__":
    main()
