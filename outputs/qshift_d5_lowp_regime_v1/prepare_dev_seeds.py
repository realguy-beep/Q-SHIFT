"""Stage S seeds, screened against every prior inventory, including the robustness, learned-support and
mismatch seed files. Written once."""
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
NAMESPACE = "qshift-d5-lowp-regime-dev-2026-11-18"
REHEARSAL_NAMESPACE = "qshift-d5-lowp-regime-dev-REHEARSAL-2026-11-18"
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
    "outputs/qshift_d5_learned_support_v1/DEV_SEEDS.json",
    "outputs/qshift_d5_learned_support_v1/B2_SEEDS.json",
    "outputs/qshift_d5_learned_support_v1/C_SEEDS.json",
)
EXTRA_SCREENED = (1,)               # learned-support Phase B timing probe (stim seed 1)


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
    mm = "outputs/qshift_d5_model_mismatch_v1/SEEDS.json"
    raw = (REPO / mm).read_bytes()
    js = json.loads(raw)
    v = set().union(*(set(js[n].values()) for n in ("diag_seeds", "seeds", "rehearsal_seeds")))
    vals |= v
    rec[mm] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec


def main() -> None:
    if OUT.exists():
        raise SystemExit("DEV_SEEDS.json exists")
    screened, rec = screened_values()
    used = set(screened)
    seeds, reh = {}, {}
    for c in K.CONDITIONS:
        for qi in range(len(K.QS)):
            seeds[K.dev_key(c, qi)] = derive(NAMESPACE, K.dev_key(c, qi), used)
            used.add(seeds[K.dev_key(c, qi)])
            reh[K.dev_key(c, qi)] = derive(REHEARSAL_NAMESPACE, K.dev_key(c, qi), used)
            used.add(reh[K.dev_key(c, qi)])
    OUT.write_text(json.dumps({"schema": "qshift-d5-lowp-regime-dev-seeds-v1", "namespace": NAMESPACE, "seeds": seeds,
                               "rehearsal_seeds": reh, "screened": rec, "union_screened": len(screened)},
                              indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(seeds), "dev seeds,", len(reh), "rehearsal; screened", len(screened))


if __name__ == "__main__":
    main()
