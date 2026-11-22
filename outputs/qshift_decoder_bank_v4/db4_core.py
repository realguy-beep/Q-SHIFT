"""DB4 pure functions: the static fallback on the unknown path, and its exact replay on stored records.

Unknown path (plausible set P empty):
  DB1-DB3:  AD's key if AD's estimate is accepted (not flagged), else hold the previous key.
  W0F:      AD's key only if the estimate is accepted AND names a burst class; otherwise the static key."""
from __future__ import annotations

import db2_core as G
import db3_core as K3
import db4_config as C

REF_ARMS = ("BANK", "DB2", "DB2_PLAN", "W0", "AD3", "STATIC", "ORACLE")


def fallback_uses_ad(est):
    """True if W0F takes AD's key on the unknown path; False -> static key."""
    return (not est["flagged"]) and est["class_index"] is not None


def fallback_key(kname, est, k_ad, prev, static):
    """W0F's version of DB1's _bank_arm: -> (key, source)."""
    if kname is not None:
        return "bank:" + kname, "bank"
    return (k_ad, "learn") if fallback_uses_ad(est) else ("bank:" + static, "static_fallback")


def replay(rec, risk, mode, kappa, fallback, static="A"):
    """-> [(key, errors or None, triggered)] per stored block. Without `fallback` this is db3_core.replay.
    With it, the AD key on the unknown path is the key every bank arm took (recorded as BANK's, source 'learn')."""
    prev, out = "bank:" + static, []
    name = lambda k: k.split(":", 1)[1] if k.startswith("bank:") else None   # noqa: E731
    for b in rec["blocks"]:
        P, est, trig = b["plausible"], b["estimate"], False
        if P:
            key = "bank:" + G.gate(P, risk, K3._tracker(b["tracker"]), name(prev), mode, kappa)
        elif fallback and not fallback_uses_ad(est):
            key, trig = "bank:" + static, True
        elif not est["flagged"]:
            if b["source"]["BANK"] != "learn":
                raise ValueError("unknown path: BANK did not take AD's key")
            key = b["keys"]["BANK"]
        else:
            key = prev
        hit = next((a for a in REF_ARMS if b["keys"].get(a) == key), None)
        out.append((key, b["errors"][hit] if hit else None, trig))
        prev = key
    return out
