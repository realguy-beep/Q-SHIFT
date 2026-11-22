"""DB6 feasibility numbers from development records only (DB2, DB3, DB4). Never reads CF1 or sealed data.

  python feasibility.py          # writes FEASIBILITY.json (deterministic)
"""
from __future__ import annotations

import collections
import json

import devdata as D
import la_replay as L


def category(r, b):
    st, t = r["states"], b["block"]
    if st[t] != st[t - 1]:
        return "onset"
    return "identified" if b["plausible"] == [st[t]] else "lag_or_ambiguous"


def main():
    recs = list(D.records())
    assert {r["study"] for r in recs} == {"DB2", "DB3", "DB4"}
    gap = collections.defaultdict(collections.Counter)
    prem = collections.Counter()
    onset = collections.defaultdict(lambda: {"onsets": 0, "same_block_alarm": 0})
    single = collections.defaultdict(collections.Counter)
    for r in recs:
        st, ch = r["states"], set(r["changes_detected"])
        for b in r["blocks"]:
            c, t = category(r, b), b["block"]
            for a in ("ORACLE", "BANK", "DB2"):
                gap[f"{r['schedule']}|W0F-{a}"][c] += b["errors"]["W0F"] - b["errors"][a]
                gap[f"ALL|W0F-{a}"][c] += b["errors"]["W0F"] - b["errors"][a]
            gap["ALL|blocks"][c] += 1
            if c == "identified" and b["keys"]["W0F"] != "bank:" + st[t]:
                prem[f"{st[t]}|{b['keys']['W0F']}"] += b["errors"]["W0F"] - b["errors"]["ORACLE"]
            if b["L"] == 1:
                P, s = b["plausible"], st[t - 1]
                single[s]["right" if P == [s] else "empty" if not P else "wrong" if len(P) == 1 else "multi"] += 1
        for t in range(6, 29):
            if st[t] != st[t - 1]:
                k = f"{st[t - 1]}->{st[t]}"
                onset[k]["onsets"] += 1
                onset[k]["same_block_alarm"] += t in ch
    out, eps, cov = L.run()
    tot = collections.Counter()
    for v in out.values():
        tot.update(v)
    la = {a: {"base": tot[a], "with_LA": tot["LA_" + a],
              "episodes_better": sum(e[3][a] < 0 for e in eps), "episodes_worse": sum(e[3][a] > 0 for e in eps),
              "max_episode_harm": max(e[3][a] for e in eps)} for a in ("W0F", "BANK", "DB2", "STATIC")}
    res = {"schema": "qshift-decoder-bank-db6-feasibility-v1", "records": {s: sum(r["study"] == s for r in recs)
           for s in ("DB2", "DB3", "DB4")}, "episodes": len(recs),
           "gap_decomposition": {k: dict(v) for k, v in sorted(gap.items())},
           "identified_block_premium": dict(sorted(prem.items())),
           "onset_same_block_alarm": dict(sorted(onset.items())),
           "single_block_plausible_set_quality": {k: dict(v) for k, v in sorted(single.items())},
           "lookahead_overlay": {"coverage": dict(cov), "totals": la,
                                 "per_panel": {s: dict(v) for s, v in sorted(out.items())}}}
    with open(D.ROOT / "FEASIBILITY.json", "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps(res["lookahead_overlay"]["totals"], indent=1))


if __name__ == "__main__":
    main()
