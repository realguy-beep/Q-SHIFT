"""Phase B development seeds, screened against every prior inventory."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
import contract as K  # noqa: E402

OUT = ROOT / "DEV_SEEDS.json"
NAMESPACE = "qshift-d5-learned-support-dev-2026-11-17"
REHEARSAL_NAMESPACE = "qshift-d5-learned-support-dev-REHEARSAL-2026-11-17"
INVENTORIES = (
    "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_2/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_3/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_4/GATE_SEEDS.json",
    "outputs/qshift_correlated_decoder_v1_5/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_6b/seed_inventory.json",
    "outputs/qshift_performance_sprint_v1/seed_inventory.json",
    "outputs/qshift_scalable_decoder_eval_d57_v1/PHASE1_SEEDS.json",
    "outputs/qshift_scalable_decoder_eval_d57_v1/SCREEN_SEEDS.json",
    "outputs/qshift_scalable_decoder_eval_d5_phase2_v1/SEEDS.json",
    "outputs/qshift_d5_robustness_v1/DEV_SEEDS.json",
    "outputs/qshift_d5_robustness_v1/EVAL_SEEDS.json",
)
EXTRA_SCREENED = (1,)  # the pre-registration timing probe used stim seed 1 (DEV_PROTOCOL.md)


def derive(ns, lab, used):
    k = 0
    while True:
        v = int.from_bytes(hashlib.sha256(f"{ns}:{lab}:{k}".encode()).digest()[:8], "big") % (2**31 - 1) + 1
        if v not in used:
            return v
        k += 1


def screened_values():
    vals, rec = set(EXTRA_SCREENED), {}
    for rel in INVENTORIES:
        raw = (REPO / rel).read_bytes()
        js = json.loads(raw)
        v = set(js["seeds"].values()) | set(js.get("rehearsal_seeds", {}).values())
        vals |= v
        rec[rel] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec


def main() -> None:
    if OUT.exists():
        raise SystemExit("DEV_SEEDS.json exists")
    screened, rec = screened_values()
    used = set(screened)
    seeds, reh = {}, {}
    for key in K.all_keys():
        seeds[key] = derive(NAMESPACE, key, used)
        used.add(seeds[key])
    for key in K.all_keys(K.REHEARSAL_POOLS):
        reh[key] = derive(REHEARSAL_NAMESPACE, key, used)
        used.add(reh[key])
    OUT.write_text(json.dumps({"schema": "qshift-d5-learned-support-dev-seeds-v1", "namespace": NAMESPACE,
                               "seeds": seeds, "rehearsal_seeds": reh, "screened": rec,
                               "union_screened": len(screened)}, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(len(seeds), "dev seeds,", len(reh), "rehearsal; screened", len(screened))


if __name__ == "__main__":
    main()
