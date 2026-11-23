"""DB8-dev analysis (PROTOCOL_DB8.md sections 4-5): advance criteria A1-A4 and reported values.

  python db8_analyze.py <out_dir>       # reads work/dev; writes ANALYSIS.json (run twice -> identical bytes)

Loading is v8 runkit.load_strict: exact episode set, record/archive/seed identity, 1,000 evaluation rows per block,
per-episode job status, archive key set, width, zero padding and counts. Descriptive contrasts carry no p value.
"""
from __future__ import annotations

import json
import sys
from math import comb
from pathlib import Path

import numpy as np

import db8_config as C  # noqa: I001
import runkit as RK  # noqa: E402

PRIMARY, SECONDARY, R1 = "LA_R2", "LA_R2_170", "LA_R1"


def sign_test_p(d):
    nz = [x for x in d if x != 0]
    n, k = len(nz), sum(x < 0 for x in nz)
    return 1.0 if n == 0 else float(sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def seeds_for(seeds):
    def f(s, e):
        return {f"b{t:02d}:{p}": int(seeds[C.block_key(s, e, t, p)]) for t in range(C.BLOCKS) for p in C.PARTS}
    return f


def episode_rows(recs, run):
    rows = []
    for r in recs:
        z = np.load(Path(run) / r["archive"])
        tot = {a: sum(b["errors"][a] for b in r["blocks"]) for a in C.ARMS}

        def shot_harm(arm):
            return int(sum((np.unpackbits(z[f"b{b['block']:02d}_{arm}"])[:C.EVAL_PER_BLOCK] &
                            ~np.unpackbits(z[f"b{b['block']:02d}_W0F"])[:C.EVAL_PER_BLOCK]).sum() for b in r["blocks"]))

        def fires(arm):
            return [b for b in r["blocks"] if b["source"].get(arm) == "lookahead"]

        def wrong(arm):
            return [b for b in fires(arm) if b["keys"][arm] != "bank:" + b["state"]]
        rows.append({"schedule": r["schedule"], "episode": r["episode"], "errors": tot,
                     "block_harm": {a: max(b["errors"][a] - b["errors"]["W0F"] for b in r["blocks"])
                                    for a in (PRIMARY, SECONDARY, R1, "CB")},
                     "shot_harm": {a: shot_harm(a) for a in (PRIMARY, SECONDARY, R1, "LA_W0F", "CB")},
                     "fires": {a: len(fires(a)) for a in (PRIMARY, SECONDARY, R1, "LA_W0F")},
                     "wrong_actions": {a: len(wrong(a)) for a in (PRIMARY, SECONDARY, R1)},
                     "wrong_ident_LA_W0F": len(wrong("LA_W0F"))})
    return rows


def criteria(rows, arm):
    inb = [x for x in rows if x["schedule"] in C.INBANK]
    unk = [x for x in rows if x["schedule"] in C.UNKNOWN_EP]
    pool = lambda xs, a: sum(x["errors"][a] for x in xs)          # noqa: E731
    den = pool(inb, "W0F") - pool(inb, "LA_W0F")
    ret = (pool(inb, "W0F") - pool(inb, arm)) / den if den > 0 else None
    d_inb = [x["errors"][arm] - x["errors"]["W0F"] for x in inb]
    a1 = {"retention": ret, "sign_p": sign_test_p(d_inb), "better": sum(v < 0 for v in d_inb),
          "worse": sum(v > 0 for v in d_inb), "tied": sum(v == 0 for v in d_inb)}
    a1["pass"] = bool(ret is not None and ret >= C.A1_RETENTION and a1["sign_p"] <= C.A1_ALPHA)
    a2s = [x for x in rows if x["schedule"] in C.A2_PANELS]
    w_arm = sum(x["wrong_actions"][arm] > 0 for x in a2s)
    w_r1 = sum(x["wrong_actions"][R1] > 0 for x in a2s)
    a2 = {"episodes": len(a2s), "wrong_action_episodes": w_arm, "LA_R1_wrong_action_episodes": w_r1,
          "pass": bool(w_arm <= C.A2_MAX_EPISODES and w_arm <= w_r1)}
    d_all = [x["errors"][arm] - x["errors"]["W0F"] for x in rows]
    per_panel = {}
    for p in C.UNKNOWN_EP:
        dd = [x["errors"][arm] - x["errors"]["W0F"] for x in unk if x["schedule"] == p]
        per_panel[p] = {"d": dd, "pooled": sum(dd)}
    a3 = {"max_episode": max(d_all), "max_block": max(x["block_harm"][arm] for x in rows), "unknown": per_panel}
    a3["pass"] = bool(a3["max_episode"] <= C.A3_EPISODE_CAP and a3["max_block"] <= C.A3_BLOCK_CAP and all(
        v["pooled"] <= 0 and all(t <= C.A3_UNKNOWN_EPISODE_CAP for t in v["d"]) for v in per_panel.values()))
    a4 = {"pooled": {a: pool(rows, a) for a in (arm,) + C.A4_BASELINES}}
    a4["pass"] = bool(all(a4["pooled"][arm] <= a4["pooled"][b] for b in C.A4_BASELINES))
    return {"A1": a1, "A2": a2, "A3": a3, "A4": a4, "ADVANCE": all(v["pass"] for v in (a1, a2, a3, a4))}


def decide(prim, sec, pooled):
    if prim["ADVANCE"]:
        out = PRIMARY
    elif sec["ADVANCE"] and not prim["A2"]["pass"] and all(prim[k]["pass"] for k in ("A1", "A3", "A4")):
        out = SECONDARY
    else:
        out = None
    cb_note = pooled["CB"] < pooled[PRIMARY]
    return {"ADVANCE": out is not None, "arm_for_CF3_plan": out, "CB_has_fewer_errors_than_LA_R2": bool(cb_note)}


def analyze(run):
    run = Path(run)
    seeds = json.loads((C.ROOT / "DB8_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    st, recs = RK.load_strict(run, C.EPISODES, C.ARMS, C.EVAL_PER_BLOCK, C.SCORED, seeds_for(seeds))
    recs = sorted(recs, key=lambda r: (list(C.EPISODES).index(r["schedule"]), r["episode"]))
    rows = episode_rows(recs, run)
    pooled = {a: sum(x["errors"][a] for x in rows) for a in C.ARMS}
    prim, sec = criteria(rows, PRIMARY), criteria(rows, SECONDARY)
    best_fixed = {}
    for s in C.EPISODES:
        rr = [x for x in rows if x["schedule"] == s]
        best_fixed[s] = min(C.FIX_ARMS, key=lambda a: (sum(x["errors"][a] for x in rr), a))
    out = {"schema": "qshift-decoder-bank-db8-analysis-v1",
           "run_status": {k: st.get(k) for k in ("started", "finished", "n_jobs", "reruns", "state")},
           "decision": decide(prim, sec, pooled), "primary": prim, "secondary": sec, "pooled_errors": pooled,
           "reported": {
               "per_panel": {s: {a: sum(x["errors"][a] for x in rows if x["schedule"] == s) for a in C.ARMS}
                             for s in C.EPISODES},
               "best_fixed_key_per_panel_descriptive": best_fixed,
               "vs_W0F_descriptive": {a: RK.describe([x["errors"][a] - x["errors"]["W0F"] for x in rows])
                                      for a in (PRIMARY, SECONDARY, R1, "LA_W0F", "CB", "LA_DB2")},
               "fires": {a: sum(x["fires"][a] for x in rows) for a in (PRIMARY, SECONDARY, R1, "LA_W0F")},
               "wrong_actions_by_panel": {s: {a: sum(x["wrong_actions"][a] for x in rows if x["schedule"] == s)
                                              for a in (PRIMARY, SECONDARY, R1)} for s in C.EPISODES},
               "LA_W0F_wrong_identifications": sum(x["wrong_ident_LA_W0F"] for x in rows),
               "shot_harm": {a: sum(x["shot_harm"][a] for x in rows) for a in (PRIMARY, SECONDARY, R1, "LA_W0F", "CB")}},
           "episodes": rows}
    return out


def main(out_dir):
    import studykit as SK
    res = analyze(C.ROOT / "work" / "dev")
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    SK.write_once_json(o / "ANALYSIS.json", res)
    print(json.dumps(res["decision"], indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
