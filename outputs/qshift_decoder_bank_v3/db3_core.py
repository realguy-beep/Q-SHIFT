"""DB3 pure functions: the pre-declared selection rule, and the replay of a bank gate on stored DB2 records.

Replay: the gate is a pure function of the plausible set P, the hazard tracker and the previous key. DB2's records
store P and the tracker snapshot (taken after observe, before commit: exactly what the gate saw) for every block,
and neither depends on the arm. The unknown path (P empty) is DB1's: AD's estimate if not flagged (the key every
bank arm then took, recorded as BANK's), else hold."""
from __future__ import annotations

import db2_core as G
import db3_config as C

REF_ARMS = ("BANK", "DB2", "DB2_PLAN", "AD3", "STATIC", "ORACLE")


def select(scores, eligible, simplicity=C.SIMPLICITY, margin=C.MARGIN):
    """-> chosen candidate or None. Lowest score among eligible; a simpler eligible candidate within `margin`
    of that lowest score is chosen instead (the simplest such)."""
    el = [c for c in simplicity if eligible.get(c)]
    if not el:
        return None
    best = min(scores[c] for c in el)
    return next(c for c in el if scores[c] <= best + margin)


def _tracker(snap):
    t = G.Tracker()
    t.cur = snap["cur"]
    t.occ = dict(snap["occ"])
    t.outs = {s: list(snap["outs"].get(s, [])) for s in C.STATES}
    return t


def replay(rec, risk, mode, kappa, static="A"):
    """-> list of (key, errors or None) per stored block, for gate (mode, kappa)."""
    prev, out = "bank:" + static, []
    name = lambda k: k.split(":", 1)[1] if k.startswith("bank:") else None   # noqa: E731
    for b in rec["blocks"]:
        P = b["plausible"]
        if P:
            key = "bank:" + G.gate(P, risk, _tracker(b["tracker"]), name(prev), mode, kappa)
        elif not b["estimate"]["flagged"]:
            if b["source"]["BANK"] != "learn":
                raise ValueError("unknown path: BANK did not take AD's key")
            key = b["keys"]["BANK"]
        else:
            key = prev
        hit = next((a for a in REF_ARMS if b["keys"].get(a) == key), None)
        out.append((key, b["errors"][hit] if hit else None))
        prev = key
    return out
