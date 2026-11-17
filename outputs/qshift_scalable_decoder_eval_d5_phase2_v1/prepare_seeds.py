"""Phase 2 (d=5) seeds, screened against every prior inventory (including d57 Phase 1 and the screen)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import contract as K

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT / "SEEDS.json"
NAMESPACE = "qshift-d5-phase2-eval-2026-11-17"
REHEARSAL_NAMESPACE = "qshift-d5-phase2-REHEARSAL-2026-11-17"
SCREENED = (
    "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_2/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_3/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_4/GATE_SEEDS.json",
    "outputs/qshift_correlated_decoder_v1_5/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_6b/seed_inventory.json",
    "outputs/qshift_performance_sprint_v1/seed_inventory.json",
)
WITH_REHEARSAL = (
    "outputs/qshift_scalable_decoder_eval_d57_v1/PHASE1_SEEDS.json",
    "outputs/qshift_scalable_decoder_eval_d57_v1/SCREEN_SEEDS.json",
)


def derive(ns: str, lab: str, used: set[int]) -> int:
    k = 0
    while True:
        v = int.from_bytes(hashlib.sha256(f"{ns}:{lab}:{k}".encode()).digest()[:8], "big") % (2**31 - 1) + 1
        if v not in used:
            return v
        k += 1


def screened_values() -> tuple[set[int], dict]:
    vals, record = set(), {}
    for rel in SCREENED + WITH_REHEARSAL:
        raw = (REPO / rel).read_bytes()
        js = json.loads(raw)
        v = set(js["seeds"].values()) | set(js.get("rehearsal_seeds", {}).values())
        vals |= v
        record[rel] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, record


def main() -> None:
    if OUT.exists():
        raise SystemExit("SEEDS.json exists")
    screened, record = screened_values()
    used = set(screened)
    seeds, rehearsal = {}, {}
    for lab in [K.root_key(qi, r) for qi in range(len(K.QS)) for r in range(K.FROZEN.roots_per_q)] + list(K.STATS_KEYS):
        seeds[lab] = derive(NAMESPACE, lab, used)
        used.add(seeds[lab])
    for lab in [K.root_key(qi, 0) for qi in range(len(K.QS))] + ["p2d5:fake"]:
        rehearsal[lab] = derive(REHEARSAL_NAMESPACE, lab, used)
        used.add(rehearsal[lab])
    OUT.write_text(json.dumps({"schema": "qshift-d5-phase2-seeds-v1", "namespace": NAMESPACE, "seeds": seeds,
                               "rehearsal_seeds": rehearsal, "screened": record, "union_screened": len(screened)},
                              indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(seeds), "seeds,", len(rehearsal), "rehearsal; screened", len(screened))


if __name__ == "__main__":
    main()
