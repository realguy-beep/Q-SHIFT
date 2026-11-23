"""Write CF2_SEEDS.json (confirmatory episodes), screened against every prior inventory through DB6_SEEDS.json."""
from __future__ import annotations

import hashlib
import json

import cf2_config as C
import prepare_db6 as P6
import studykit as SK

NS = "qshift-decoder-bank-v7:cf2"


def screened():
    vals, rec, derive = P6.screened()
    raw = (C.DB6 / "DB6_SEEDS.json").read_bytes()
    v = set(json.loads(raw)["seeds"].values())
    vals |= v
    rec["outputs/qshift_decoder_bank_v6/DB6_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    so = C.ROOT / "CF2_SEEDS.json"
    if so.exists():
        raise SystemExit("CF2_SEEDS.json exists")
    vals, rec, derive = screened()
    used, out = set(vals), {}
    for k in C.all_keys():
        out[k] = derive(NS, k, used)
        used.add(out[k])
    SK.write_once_json(so, {"schema": "qshift-decoder-bank-cf2-seeds-v1", "namespace": NS, "seeds": out,
                            "screened": rec, "union_screened": len(vals)})
    print(len(out), "seeds; screened", len(vals))


if __name__ == "__main__":
    main()
