"""Phase C seeds, screened against every prior inventory plus Phase B and B2 seeds."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import c_contract as C  # noqa: E402
import prepare_dev_seeds as PB  # noqa: E402

OUT = ROOT / "C_SEEDS.json"
NAMESPACE = "qshift-d5-learned-support-C-eval-2026-11-17"
REHEARSAL_NAMESPACE = "qshift-d5-learned-support-C-REHEARSAL-2026-11-17"
LOCAL = ("DEV_SEEDS.json", "B2_SEEDS.json")


def screened_values():
    vals, rec = PB.screened_values()
    for name in LOCAL:
        raw = (ROOT / name).read_bytes()
        js = json.loads(raw)
        v = set(js["seeds"].values()) | set(js["rehearsal_seeds"].values())
        vals |= v
        rec[f"outputs/qshift_d5_learned_support_v1/{name}"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec


def main() -> None:
    if OUT.exists():
        raise SystemExit("C_SEEDS.json exists")
    screened, rec = screened_values()
    used = set(screened)
    out = {}
    for name, ns, alloc in (("seeds", NAMESPACE, C.FROZEN), ("rehearsal_seeds", REHEARSAL_NAMESPACE, C.REHEARSAL)):
        out[name] = {}
        for key in C.all_seed_keys(alloc):
            out[name][key] = PB.derive(ns, key, used)
            used.add(out[name][key])
    out["rehearsal_seeds"]["d5ls:C:fake"] = PB.derive(REHEARSAL_NAMESPACE, "d5ls:C:fake", used)
    OUT.write_text(json.dumps({"schema": "qshift-d5-learned-support-C-seeds-v1", "namespace": NAMESPACE, **out,
                               "screened": rec, "union_screened": len(screened)}, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(len(out["seeds"]), "seeds,", len(out["rehearsal_seeds"]), "rehearsal; screened", len(screened))


if __name__ == "__main__":
    main()
