"""Write DB8_SEEDS.json (development episodes), screened against every prior inventory through CF2_SEEDS.json.

The screening chain imports a different module named `contract` (qshift_d5_lowp_regime_v1) from the learner
catalog's, which db8_config loads. So screening and derivation run in a spawned child that never imports db8_config.
"""
from __future__ import annotations

import hashlib
import json
import sys
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V7 = ROOT.parent / "qshift_decoder_bank_v7"
NS = "qshift-decoder-bank-v9:db8"


def screened():
    """-> (values, record, derive). Child-process only (see module docstring)."""
    sys.path.insert(0, str(V7))
    import prepare_cf2 as P7
    vals, rec, derive = P7.screened()
    raw = (V7 / "CF2_SEEDS.json").read_bytes()
    v = set(json.loads(raw)["seeds"].values())
    vals |= v
    rec["outputs/qshift_decoder_bank_v7/CF2_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def screened_values():
    return screened()[0]


def _derive_all(keys):
    vals, rec, derive = screened()
    used, out = set(vals), {}
    for k in keys:
        out[k] = derive(NS, k, used)
        used.add(out[k])
    return out, rec, len(vals)


def main():
    so = ROOT / "DB8_SEEDS.json"
    if so.exists():
        raise SystemExit("DB8_SEEDS.json exists")
    import db8_config as C
    keys = C.all_keys()
    with get_context("spawn").Pool(1) as pool:
        out, rec, n = pool.apply(_derive_all, (keys,))
    import studykit as SK
    SK.write_once_json(so, {"schema": "qshift-decoder-bank-db8-seeds-v1", "namespace": NS, "seeds": out,
                            "screened": rec, "union_screened": n})
    print(len(out), "seeds; screened", n)


if __name__ == "__main__":
    main()
