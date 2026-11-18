"""Stage E seeds, screened against every prior inventory plus DEV_SEEDS.json (seeds and rehearsal seeds)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import eval_contract as K  # noqa: E402
import prepare_dev_seeds as P  # noqa: E402

OUT = ROOT / "EVAL_SEEDS.json"
NAMESPACE = "qshift-d5-lowp-regime-eval-2026-11-18"
REHEARSAL_NAMESPACE = "qshift-d5-lowp-regime-eval-REHEARSAL-2026-11-18"


def screened_values():
    vals, rec = P.screened_values()
    dev = json.loads((ROOT / "DEV_SEEDS.json").read_text(encoding="utf-8"))
    vals |= set(dev["seeds"].values()) | set(dev["rehearsal_seeds"].values())
    rec["outputs/qshift_d5_lowp_regime_v1/DEV_SEEDS.json"] = {"values": len(dev["seeds"]) + len(dev["rehearsal_seeds"])}
    return vals, rec


def main() -> None:
    if OUT.exists():
        raise SystemExit("EVAL_SEEDS.json exists")
    screened, rec = screened_values()
    used = set(screened)
    seeds, reh = {}, {}
    for lab in [K.root_key(*j) for j in K.jobs(K.FROZEN)] + [k for c in K.CONDITIONS for k in K.stats_keys(c)]:
        seeds[lab] = P.derive(NAMESPACE, lab, used)
        used.add(seeds[lab])
    for lab in [K.root_key(c, qi, 0) for c in K.CONDITIONS for qi in range(3)] + ["d5lowp:fake"]:
        reh[lab] = P.derive(REHEARSAL_NAMESPACE, lab, used)
        used.add(reh[lab])
    OUT.write_text(json.dumps({"schema": "qshift-d5-lowp-regime-eval-seeds-v1", "namespace": NAMESPACE, "seeds": seeds,
                               "rehearsal_seeds": reh, "screened": rec, "union_screened": len(screened)},
                              indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(seeds), "seeds,", len(reh), "rehearsal; screened", len(screened))


if __name__ == "__main__":
    main()
