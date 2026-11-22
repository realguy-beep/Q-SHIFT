"""Write CF1_SEEDS.json (confirmatory episodes), screened against every prior inventory through DB4_SEEDS.json."""
from __future__ import annotations

import hashlib
import json

import cf1_config as C
import prepare_db4 as P4
import studykit as SK

NS = "qshift-decoder-bank-v5:cf1"


def screened():
    vals, rec, derive = P4.screened()
    raw = (C.DB4 / "DB4_SEEDS.json").read_bytes()
    v = set(json.loads(raw)["seeds"].values())
    vals |= v
    rec["outputs/qshift_decoder_bank_v4/DB4_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    so = C.ROOT / "CF1_SEEDS.json"
    if so.exists():
        raise SystemExit("CF1_SEEDS.json exists")
    vals, rec, derive = screened()
    used, out = set(vals), {}
    for k in C.all_keys():
        out[k] = derive(NS, k, used)
        used.add(out[k])
    SK.write_once_json(so, {"schema": "qshift-decoder-bank-cf1-seeds-v1", "namespace": NS, "seeds": out,
                            "screened": rec, "union_screened": len(vals)})
    print(len(out), "seeds; screened", len(vals))


if __name__ == "__main__":
    main()
