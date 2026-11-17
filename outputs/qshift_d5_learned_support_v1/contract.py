"""Phase B development-gate contract (DEV_PROTOCOL.md). Pure constants and helpers; no sampling."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import learner_d5 as LD
from learner_d5 import L, m

ROOT = Path(__file__).resolve().parent
SPEC = m.CodeSpec(distance=5, gate_p=0.003, measurement_p=0.003)
QS = (0.0, 0.01, 0.02)

# True development bursts. SC/CR: the two pre-declared geometric families. M0/M1: the first mixed
# class (sorted signature order) holding a weight-3 support of flip 0 / flip 1; the smallest such
# support is the true burst. For both, the min-weight heuristic picks the wrong flip.
BURSTS = {"SC": (23, 31, 34), "CR": (25, 27, 29), "M0": (12, 34, 45), "M1": (1, 23, 45)}

POOLS = 24
DET_PER_Q = 4_000          # detector-only rows per q per pool (labels discarded unread)
LAB_PER_Q = 500            # labeled rows per q per pool (flip stage only)
Q0_POOL_SHOTS = 12_000     # burst-free pools for G2
CURVE_PER_Q = (1_000, 2_000, 4_000)   # 3k / 6k / 12k prefixes (descriptive)
REHEARSAL_POOLS = 1

G1_MIN = 23                # of 24 pools, per burst: class correct
G2_MIN = 22                # of 24 q=0 pools: "no burst"
G3_MIN_FRACTION = 0.95     # flip correct among class-correct pools, per burst


def burst_key(b, k, qi):
    return f"d5ls:dev:{b}:pool{k:02d}:q{QS[qi]:.2f}"


def q0_key(k):
    return f"d5ls:dev:Q0:pool{k:02d}"


def all_keys(pools=POOLS):
    return [burst_key(b, k, qi) for b in BURSTS for k in range(pools) for qi in range(len(QS))] + \
           [q0_key(k) for k in range(pools)]


def load_classes():
    rec = json.loads((ROOT / "CLASSES_D5.json").read_text(encoding="utf-8"))
    body = rec["classes"]
    if hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != rec["classes_sha256"]:
        raise SystemExit("CLASSES_D5.json hash mismatch")
    return [L.SignatureClass(tuple(tuple(e) for e in c["events"]), tuple(tuple(s) for s in c["flip0"]),
                             tuple(tuple(s) for s in c["flip1"])) for c in body]


def truth(classes, support):
    for i, c in enumerate(classes):
        if support in c.supports_flip0:
            return i, 0
        if support in c.supports_flip1:
            return i, 1
    raise KeyError(support)


def threshold(classes):
    return LD.threshold(len(classes))
