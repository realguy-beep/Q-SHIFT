"""Write DB3_SEEDS.json (tiebreak episodes), screened against every prior inventory through DB2_SEEDS.json."""
from __future__ import annotations

import hashlib
import json

import db3_config as C
import prepare_db2 as P2
import studykit as SK

NS = "qshift-decoder-bank-v3:db3"


def screened():
    vals, rec, derive = P2.screened()
    raw = (C.DB2 / "DB2_SEEDS.json").read_bytes()
    v = set(json.loads(raw)["seeds"].values())
    vals |= v
    rec["outputs/qshift_decoder_bank_v2/DB2_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    so = C.ROOT / "DB3_SEEDS.json"
    if so.exists():
        raise SystemExit("DB3_SEEDS.json exists")
    vals, rec, derive = screened()
    used, out = set(vals), {}
    for k in C.all_keys():
        out[k] = derive(NS, k, used)
        used.add(out[k])
    SK.write_once_json(so, {"schema": "qshift-decoder-bank-db3-seeds-v1", "namespace": NS, "seeds": out,
                            "screened": rec, "union_screened": len(vals)})
    print(len(out), "seeds; screened", len(vals))


if __name__ == "__main__":
    main()
