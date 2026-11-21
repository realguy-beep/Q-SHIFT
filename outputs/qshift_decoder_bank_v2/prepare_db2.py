"""Write DB2_SEEDS.json (development episodes), screened against every prior inventory through DB1_SEEDS.json."""
from __future__ import annotations

import hashlib
import json

import db2_config as C
import prepare_db1 as P1
import studykit as SK

NS = "qshift-decoder-bank-v2:db2"


def screened():
    vals, rec, derive = P1.screened()
    raw = (C.DB1 / "DB1_SEEDS.json").read_bytes()
    b = json.loads(raw)
    v = set(b["seeds"].values()) | set(b["train_seeds"].values())
    vals |= v
    rec["outputs/qshift_decoder_bank_v1/DB1_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    so = C.ROOT / "DB2_SEEDS.json"
    if so.exists():
        raise SystemExit("DB2_SEEDS.json exists")
    vals, rec, derive = screened()
    used, out = set(vals), {}
    for k in C.all_keys():
        out[k] = derive(NS, k, used)
        used.add(out[k])
    SK.write_once_json(so, {"schema": "qshift-decoder-bank-db2-seeds-v1", "namespace": NS, "seeds": out,
                            "screened": rec, "union_screened": len(vals)})
    print(len(out), "seeds; screened", len(vals))


if __name__ == "__main__":
    main()
