"""Exact replay of the alarm-gated lookahead overlay (LA) on development records (DB2-DB4 only).

LA(base) at block t: if AD3's change test fires on block t's own detection counts (the record of block t+1 has
L == 1, i.e. seg0 == t) and DB1's plausible set fitted on block t alone is a singleton {s}, decode block t with
bank:s; otherwise use the base arm's key. Inputs: detection-only rows of blocks <= t; no labels, no eval rows.
The base arm's own state is untouched (overlay), so its later keys are as recorded/replayed: the replay is exact
whenever bank:s was decoded by some recorded arm at block t (coverage reported)."""
from __future__ import annotations

import collections

import devdata as D


def la_key(bl, i):
    if i + 1 < len(bl):
        nb = bl[i + 1]
        if nb["L"] == 1 and nb["seg0"] == bl[i]["block"] and len(nb["plausible"]) == 1:
            return "bank:" + nb["plausible"][0]
    return None


def run(bases=("W0F", "BANK", "DB2", "STATIC")):
    out = collections.defaultdict(lambda: collections.Counter())
    eps, cov = [], collections.Counter()
    for r in D.records():
        st, bl, s = r["states"], r["blocks"], r["schedule"]
        d = collections.Counter()
        for i, b in enumerate(bl):
            k = la_key(bl, i)
            y = D.err_of(b, k) if k else None
            if k:
                cov["la_blocks"] += 1
                cov["covered"] += y is not None
                cov["wrong_state"] += k != "bank:" + st[b["block"]]
            for a in bases:
                x = b["errors"][a]
                la = y if y is not None else x
                out[s][a] += x
                out[s]["LA_" + a] += la
                d[a] += la - x
            out[s]["ORACLE"] += b["errors"]["ORACLE"]
        eps.append((r["study"], s, r["episode"], dict(d)))
    return out, eps, cov


if __name__ == "__main__":
    out, eps, cov = run()
    T = collections.Counter()
    for s, v in sorted(out.items()):
        T.update(v)
    print(dict(cov))
    print("ALL", dict(T))
    for a in ("W0F", "BANK", "DB2", "STATIC"):
        ds = [e[3][a] for e in eps]
        print(a, "LA gain", T["LA_" + a] - T[a], "episodes better/worse", sum(x < 0 for x in ds), sum(x > 0 for x in ds),
              "max harm", max(ds))
