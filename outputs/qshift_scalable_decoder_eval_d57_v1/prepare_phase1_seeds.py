"""Phase 1 seed identities (and separate rehearsal seeds); screened against all prior inventories."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT / "PHASE1_SEEDS.json"
NAMESPACE = "qshift-d57-phase1-2026-11-16"
REHEARSAL_NAMESPACE = "qshift-d57-phase1-REHEARSAL-2026-11-16"
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
JOBS = [(d, q) for d in (5, 7) for q in (0.0, 0.01, 0.02)]


def label(d: int, q: float) -> str:
    return f"phase1:d{d}:q{q:.2f}"


def derive(namespace: str, lab: str, used: set[int]) -> int:
    counter = 0
    while True:
        v = int.from_bytes(hashlib.sha256(f"{namespace}:{lab}:{counter}".encode()).digest()[:8], "big") % (2**31 - 1) + 1
        if v not in used:
            return v
        counter += 1


def build() -> dict:
    screened, record = set(), {}
    for rel in SCREENED:
        raw = (REPO / rel).read_bytes()
        vals = set(json.loads(raw)["seeds"].values())
        screened |= vals
        record[rel] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(vals)}
    used = set(screened)
    seeds, rehearsal = {}, {}
    for d, q in JOBS:
        seeds[label(d, q)] = derive(NAMESPACE, label(d, q), used)
        used.add(seeds[label(d, q)])
    for d, q in JOBS:
        rehearsal[label(d, q)] = derive(REHEARSAL_NAMESPACE, label(d, q), used)
        used.add(rehearsal[label(d, q)])
    if (set(seeds.values()) | set(rehearsal.values())) & screened:
        raise RuntimeError("seed collision with prior inventories")
    return {"schema": "qshift-d57-phase1-seeds-v1", "namespace": NAMESPACE, "seeds": seeds,
            "rehearsal_namespace": REHEARSAL_NAMESPACE, "rehearsal_seeds": rehearsal,
            "screened": record, "union_screened": len(screened),
            "purpose": "Phase 1 development selection/sizing only; never reused for evaluation"}


if __name__ == "__main__":
    if OUT.exists():
        raise SystemExit("PHASE1_SEEDS.json exists")
    inv = build()
    OUT.write_text(json.dumps(inv, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(inv["seeds"]), "seeds +", len(inv["rehearsal_seeds"]), "rehearsal; screened", inv["union_screened"])
