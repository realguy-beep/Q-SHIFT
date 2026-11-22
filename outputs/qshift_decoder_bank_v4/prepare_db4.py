"""Write DB4_SEEDS.json (development episodes), screened against every prior inventory through DB3_SEEDS.json."""
from __future__ import annotations

import hashlib
import json

import db4_config as C
import prepare_db3 as P3
import studykit as SK

NS = "qshift-decoder-bank-v4:db4"


def screened():
    vals, rec, derive = P3.screened()
    raw = (C.DB3 / "DB3_SEEDS.json").read_bytes()
    v = set(json.loads(raw)["seeds"].values())
    vals |= v
    rec["outputs/qshift_decoder_bank_v3/DB3_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    so = C.ROOT / "DB4_SEEDS.json"
    if so.exists():
        raise SystemExit("DB4_SEEDS.json exists")
    vals, rec, derive = screened()
    used, out = set(vals), {}
    for k in C.all_keys():
        out[k] = derive(NS, k, used)
        used.add(out[k])
    SK.write_once_json(so, {"schema": "qshift-decoder-bank-db4-seeds-v1", "namespace": NS, "seeds": out,
                            "screened": rec, "union_screened": len(vals)})
    print(len(out), "seeds; screened", len(vals))


if __name__ == "__main__":
    main()
