"""Mismatch-study seeds (diagnostic, eval, rehearsal), screened against every prior inventory, including all
of the learned-support package's seed files. Written once."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import mm_contract as K  # noqa: E402
import prepare_dev_seeds as PB  # noqa: E402  (Phase B helper: derive + prior inventories)

OUT = ROOT / "SEEDS.json"
NAMESPACES = {"diag_seeds": "qshift-d5-model-mismatch-A-diag-2026-11-17",
              "seeds": "qshift-d5-model-mismatch-B-eval-2026-11-17",
              "rehearsal_seeds": "qshift-d5-model-mismatch-B-REHEARSAL-2026-11-17"}
LOCAL = ("DEV_SEEDS.json", "B2_SEEDS.json", "C_SEEDS.json")


def screened_values():
    vals, rec = PB.screened_values()
    for name in LOCAL:
        raw = (K.PHASE_C / name).read_bytes()
        js = json.loads(raw)
        v = set(js["seeds"].values()) | set(js["rehearsal_seeds"].values())
        vals |= v
        rec[f"outputs/qshift_d5_learned_support_v1/{name}"] = {"sha256": hashlib.sha256(raw).hexdigest(),
                                                                "values": len(v)}
    return vals, rec


def keys_for(name):
    if name == "diag_seeds":
        return K.diag_keys()
    keys = K.eval_keys(K.FROZEN if name == "seeds" else K.REHEARSAL)
    return keys + (["d5mm:B:fake"] if name == "rehearsal_seeds" else [])


def main() -> None:
    if OUT.exists():
        raise SystemExit("SEEDS.json exists")
    screened, rec = screened_values()
    used = set(screened)
    out = {}
    for name, ns in NAMESPACES.items():
        out[name] = {}
        for key in keys_for(name):
            out[name][key] = PB.derive(ns, key, used)
            used.add(out[name][key])
    OUT.write_text(json.dumps({"schema": "qshift-d5-model-mismatch-seeds-v1", "namespaces": NAMESPACES, **out,
                               "screened": rec, "union_screened": len(screened)}, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print({k: len(v) for k, v in out.items()}, "screened", len(screened))


if __name__ == "__main__":
    main()
