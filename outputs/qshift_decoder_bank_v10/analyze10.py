"""Analysis over already verified (record, arrays) pairs. Nothing is re-read from disk (audit F5).

The criteria and decision are DB8's frozen functions (v9 db8_analyze.criteria, decide), unchanged."""
from __future__ import annotations

import db8_analyze as A
import db8_config as C


def rows(pairs):
    out = []
    for r, bits in pairs:
        def fires(arm):
            return [b for b in r["blocks"] if b["source"].get(arm) == "lookahead"]

        def wrong(arm):
            return sum(b["keys"][arm] != "bank:" + b["state"] for b in fires(arm))

        def shot(arm):
            return int(sum((x[arm] & ~x["W0F"]).sum() for x in bits.values()))
        rule = (A.PRIMARY, A.SECONDARY, A.R1)
        out.append({"schedule": r["schedule"], "episode": r["episode"],
                    "errors": {a: int(sum(x[a].sum() for x in bits.values())) for a in C.ARMS},
                    "block_harm": {a: max(int(x[a].sum()) - int(x["W0F"].sum()) for x in bits.values())
                                   for a in rule + ("CB",)},
                    "shot_harm": {a: shot(a) for a in rule + ("LA_W0F", "CB")},
                    "fires": {a: len(fires(a)) for a in rule + ("LA_W0F",)},
                    "wrong_actions": {a: wrong(a) for a in rule}, "wrong_ident_LA_W0F": wrong("LA_W0F")})
    return out


def analyze(pairs):
    rr = rows(pairs)
    pooled = {a: sum(x["errors"][a] for x in rr) for a in C.ARMS}
    p, s = A.criteria(rr, A.PRIMARY), A.criteria(rr, A.SECONDARY)
    return {"decision": A.decide(p, s, pooled), "primary": p, "secondary": s, "pooled_errors": pooled, "episodes": rr}
