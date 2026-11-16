"""Screen seeds (and rehearsal seeds); screened against all prior inventories including Phase 1."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT / "SCREEN_SEEDS.json"
NAMESPACE = "qshift-d57-screen-2026-11-16"
REHEARSAL_NAMESPACE = "qshift-d57-screen-REHEARSAL-2026-11-16"
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
CHUNKS = {7: 6, 5: 2}
QS = (0.0, 0.01, 0.02)


def label(d: int, q: float, c: int) -> str:
    return f"screen:d{d}:q{q:.2f}:chunk{c}"


def derive(ns, lab, used):
    k = 0
    while True:
        v = int.from_bytes(hashlib.sha256(f"{ns}:{lab}:{k}".encode()).digest()[:8], "big") % (2**31 - 1) + 1
        if v not in used:
            return v
        k += 1


def main() -> None:
    if OUT.exists():
        raise SystemExit("SCREEN_SEEDS.json exists")
    screened, record = set(), {}
    for rel in SCREENED:
        raw = (REPO / rel).read_bytes()
        vals = set(json.loads(raw)["seeds"].values())
        screened |= vals
        record[rel] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(vals)}
    p1 = json.loads((ROOT / "PHASE1_SEEDS.json").read_text(encoding="utf-8"))
    screened |= set(p1["seeds"].values()) | set(p1["rehearsal_seeds"].values())
    used = set(screened)
    seeds, rehearsal = {}, {}
    for d, n in CHUNKS.items():
        for q in QS:
            for c in range(n):
                seeds[label(d, q, c)] = derive(NAMESPACE, label(d, q, c), used)
                used.add(seeds[label(d, q, c)])
    rehearsal[label(7, 0.02, 0)] = derive(REHEARSAL_NAMESPACE, label(7, 0.02, 0), used)
    OUT.write_text(json.dumps({"schema": "qshift-d57-screen-seeds-v1", "namespace": NAMESPACE, "seeds": seeds,
                               "rehearsal_seeds": rehearsal, "screened": record,
                               "also_screened": "PHASE1_SEEDS.json seeds and rehearsal seeds",
                               "union_screened": len(screened)}, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(len(seeds), "seeds; screened", len(screened))


if __name__ == "__main__":
    main()
