"""CF2 analysis (PLAN_CF2.md section 3): C1-C3 exact sign tests with Holm, safety gates G1-G6, the onset table.

  python cf2_analyze.py <out_dir>          # reads work/cf2; writes ANALYSIS.json + TIMELINE.json (run twice -> identical)

Strict archive validation (hash, arm list, exact key set, 125-byte width, zero padding, counts) is DB6's load_checked.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

import cf2_config as C  # noqa: I001
import db6_run as R6  # noqa: E402

sign_test_p, cp_upper = R6.sign_test_p, R6.cp_upper


def holm(ps, alpha):
    """-> {name: rejected} under Holm's step-down at family-wise alpha."""
    order = sorted(ps, key=lambda k: (ps[k], k))
    out, go = {}, True
    for i, k in enumerate(order):
        go = go and ps[k] <= alpha / (len(order) - i)
        out[k] = bool(go)
    return out


def boot_ci(d, n, seed):
    rng = np.random.default_rng(seed)
    a = np.asarray(d, float)
    m = a[rng.integers(0, len(a), size=(n, len(a)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def describe(d):
    return {"n": len(d), "mean": float(np.mean(d)), "median": float(np.median(d)), "better": sum(x < 0 for x in d),
            "worse": sum(x > 0 for x in d), "tied": sum(x == 0 for x in d), "sign_p": sign_test_p(d),
            "boot95_mean": boot_ci(d, C.BOOT_RESAMPLES, C.BOOT_SEED), "d": list(d)}


def onset_table(recs):
    """Opportunities: scored blocks whose true state differs from block t-1's (truth used for scoring only)."""
    dest, other = {}, {"triggers": 0, "correct": 0, "saved_vs_W0F": 0}
    for r in recs:
        for b in r["blocks"]:
            t = b["block"]
            fired = b["source"]["LA_W0F"] == "lookahead"
            ok = fired and b["keys"]["LA_W0F"] == "bank:" + b["state"]
            saved = b["errors"]["W0F"] - b["errors"]["LA_W0F"]
            if r["states"][t] != r["states"][t - 1]:
                x = dest.setdefault(b["state"], {"opportunities": 0, "triggers": 0, "correct": 0, "saved_vs_W0F": 0})
                x["opportunities"] += 1
            elif fired:
                x = other
            else:
                continue
            x["triggers"] += fired
            x["correct"] += ok
            x["saved_vs_W0F"] += saved
    return {"by_destination": dict(sorted(dest.items())), "non_opportunity_triggers": other}


def analyze(run, episodes=None, arms=None, hypotheses=None):
    episodes, arms, hypotheses = episodes or C.EPISODES, arms or C.ARMS, hypotheses or C.HYPOTHESES
    st, recs = R6.load_checked(Path(run), episodes, arms)
    recs = sorted(recs, key=lambda r: (list(episodes).index(r["schedule"]), r["episode"]))
    tot = [(r["schedule"], {a: sum(b["errors"][a] for b in r["blocks"]) for a in arms}) for r in recs]
    dW = [e["LA_W0F"] - e["W0F"] for _, e in tot]
    out = {"schema": "qshift-decoder-bank-cf2-analysis-v1",
           "run_status": {k: st.get(k) for k in ("head", "started", "finished", "wall_seconds", "n_jobs", "reruns")},
           "pooled_errors": {a: sum(e[a] for _, e in tot) for a in arms}, "hypotheses": {}, "schedules": {}}
    for name, comp, panels in hypotheses:
        out["hypotheses"][name] = {"comparator": comp, "panels": list(panels),
                                   **describe([e["LA_W0F"] - e[comp] for s, e in tot if s in panels])}
    rej = holm({k: v["sign_p"] for k, v in out["hypotheses"].items()}, C.ALPHA)
    for k, v in out["hypotheses"].items():
        v["holm_rejected"] = rej[k]
    h = out["hypotheses"]
    uses = sum(b["source"]["LA_W0F"] == "lookahead" for r in recs for b in r["blocks"])
    wrong = sum(b["source"]["LA_W0F"] == "lookahead" and (r["schedule"] in C.OOB_SCHED
                                                         or b["keys"]["LA_W0F"] != "bank:" + b["state"])
                for r in recs for b in r["blocks"])
    block_harm = max(b["errors"]["LA_W0F"] - b["errors"]["W0F"] for r in recs for b in r["blocks"])
    harm = sum(x > 0 for x in dW)
    rx = [e["LA_W0F"] - e["W0F"] for s, e in tot if s == "RX"]
    uu = [e["LA_W0F"] - e["W0F"] for s, e in tot if s == "U"]
    g = {"G1_max_episode_harm": max(dW), "G2_max_block_harm": block_harm, "G3_harm_episodes": harm,
         "G3_harm_cp_upper": cp_upper(harm, len(dW)), "G4_uses": uses, "G4_wrong": wrong,
         "G4_wrong_cp_upper": cp_upper(wrong, uses), "G5_RX_d": rx, "G6_U_d": uu}
    dec = {"C1": h["C1"]["holm_rejected"] and h["C1"]["mean"] <= C.C1_MEAN,
           "G1": g["G1_max_episode_harm"] <= C.G1_EPISODE_CAP, "G2": block_harm <= C.G2_BLOCK_CAP,
           "G3": harm <= C.G3_HARM_MAX, "G4": uses > 0 and g["G4_wrong_cp_upper"] <= C.G4_WRONG_CP_MAX,
           "G5": bool(rx) and sum(rx) <= 0 and all(x <= C.G5_RX_EPISODE_CAP for x in rx),
           "G6": bool(uu) and sum(uu) <= 0 and all(x <= C.G6_U_EPISODE_CAP for x in uu)}
    dec = {k: bool(v) for k, v in dec.items()}
    dec["CONFIRMED"] = all(dec.values())
    dec["C2"] = bool(dec["CONFIRMED"] and h["C2"]["holm_rejected"])
    dec["C3"] = bool(dec["CONFIRMED"] and h["C3"]["holm_rejected"])
    out["gates"], out["decision"] = g, dec
    po = out["pooled_errors"]
    out["reported"] = {"gap_closed_vs_ORACLE": (po["W0F"] - po["LA_W0F"]) / (po["W0F"] - po["ORACLE"])
                       if po["W0F"] != po["ORACLE"] else None,
                       "vs": {c: describe([e["LA_W0F"] - e[c] for _, e in tot])
                              for c in ("LA_DB2", "W0", "BANK", "DB2", "STATIC", "AD3", "ORACLE", "LA2_W0F")},
                       "onsets": onset_table(recs)}
    tl = {"schema": "qshift-decoder-bank-cf2-timeline-v1", "blocks": list(C.SCORED), "schedules": {}}
    for s in episodes:
        rr = [r for r in recs if r["schedule"] == s]
        e = [x for ss, x in tot if ss == s]
        out["schedules"][s] = {"episodes": len(rr), "params": [r["params"] for r in rr],
                               "errors": {a: sum(x[a] for x in e) for a in arms},
                               "errors_per_episode": {a: [x[a] for x in e] for a in arms},
                               "LA_W0F_uses": [sum(b["source"]["LA_W0F"] == "lookahead" for b in r["blocks"]) for r in rr]}
        tl["schedules"][s] = {"state": [[b["state"] for b in r["blocks"]] for r in rr],
                              "lookahead": [[b["lookahead"] for b in r["blocks"]] for r in rr],
                              "keys": {a: [[b["keys"][a] for b in r["blocks"]] for r in rr]
                                       for a in C.BANK_ARMS + tuple(C.LA_ARMS) + tuple(C.LA2_ARMS)},
                              "errors": {a: [[b["errors"][a] for b in r["blocks"]] for r in rr] for a in arms}}
    return out, tl


def main(out_dir):
    import studykit as SK
    res, tl = analyze(C.ROOT / "work" / "cf2")
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    SK.write_once_json(o / "ANALYSIS.json", res)
    SK.write_once_json(o / "TIMELINE.json", tl)
    print(json.dumps(res["decision"], indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
