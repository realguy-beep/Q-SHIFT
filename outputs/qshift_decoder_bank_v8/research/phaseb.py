"""Phase B (development evidence only): why E reads as A, whether detector-only unknown rejection can work, why LA's
gain sits at B onsets, and whether a causal controller keeps the gain with fewer inappropriate triggers.

  python research/phaseb.py            # writes research/PHASEB.json (deterministic)

Inputs: DB1 TRAINING.json; dev records of DB2 (v2), DB4 (v4) and DB6 (v6); DB6 dev archives (errors only).
Never reads CF2 (v7 work/ or results/), CF1 or any seal. Detection rows are re-generated from each dev record's own
recorded seeds (detector-only, 2,000 rows per block; no labels, evaluation rows or decoding) and validated against
the DB6 records' stored lookahead statistic, alarm and single-block plausible set before any use.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

V8 = Path(__file__).resolve().parents[1]
OUT = V8.parent
sys.path.insert(0, str(OUT / "qshift_decoder_bank_v6"))
import db6_config as C  # noqa: E402  (puts DB5-DB1 and AD2/AD3 on sys.path)
import ad3  # noqa: E402
import db_core as D  # noqa: E402
import db6_core as L6  # noqa: E402

TR = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))
TPL = {k: np.array(v) for k, v in TR["templates"].items()}
TAU, RISK = TR["tau_fit"], TR["risk"]
DEV = {"DB2": OUT / "qshift_decoder_bank_v2", "DB4": OUT / "qshift_decoder_bank_v4", "DB6": OUT / "qshift_decoder_bank_v6"}
FORBIDDEN = ("qshift_decoder_bank_v7", "qshift_decoder_bank_v5/results", "R" "6_")


def records(study):
    ps = sorted((DEV[study] / "results" / "dev" / "records").glob("*.json"))
    assert not any(f in str(p) for p in ps for f in FORBIDDEN)
    return [json.loads(p.read_text(encoding="utf-8")) for p in ps]


def det_counts(rec):
    return [ad3.counts(D.sample(rec["states"][t], C.DET_PER_BLOCK, int(rec["seeds"][f"b{t:02d}:det"]))[0])
            for t in range(len(rec["states"]))]


def chain(cnt):
    """DB6's causal chain on detector counts only: AD3 segment, then per block t the lookahead (g, alarm, P1) and
    all single-block fits. Mirrors db6_run.episode_job lines 90-97 and db6_core.lookahead."""
    seg0, out = 0, {}
    for t in range(len(cnt)):
        if t >= 2:
            u = t - 1
            k0, n0 = ad3.pool(cnt[ad3.segment_lo(seg0, u):u])
            if ad3.g_stat(*cnt[u], k0, n0) > C.AD3_TAU:
                seg0 = u
        if t < C.WINDOW:
            continue
        la = L6.lookahead(cnt, seg0, t, TPL, TAU)
        k1, n1 = cnt[t]
        gf = {s: D.g_fit(k1, n1, TPL[s]) for s in C.STATES}
        out[t] = {**la, "gf": gf}
    return out


# ------------------------------------------------------------------ 1. analytic detector rates (no sampling)
def analytic_rates():
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    DC = D.C                                          # the sampler's own config (db_core.sample)
    sp = DC.spec(gate_p=DC.P0, measurement_p=DC.P0)
    out = {}
    for st in C.STATES + ("E",):
        sup = DC.support(st)
        c = m.build_candidate_circuit(sp, DC.BURST_Q, tuple(sup)) if sup else m.build_base_circuit(sp)
        dem = c.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
        prod = np.ones(c.num_detectors)
        for inst in dem.flattened():
            if inst.type != "error":
                continue
            p = inst.args_copy()[0]
            for tg in inst.targets_copy():
                if tg.is_relative_detector_id():
                    prod[tg.val] *= 1 - 2 * p
        out[st] = (1 - prod) / 2
    return out


def kl_noncentrality(r, p, n):
    r, p = np.clip(r, 1e-12, 1 - 1e-12), np.clip(p, 1e-12, 1 - 1e-12)
    return float(2 * n * (r * np.log(r / p) + (1 - r) * np.log((1 - r) / (1 - p))).sum())


def main():
    res = {"schema": "qshift-v8-phaseb-v1", "inputs": {k: str(v.relative_to(OUT)) for k, v in DEV.items()},
           "cf2_read": False}
    # 1. analytic
    rates = analytic_rates()
    n = C.DET_PER_BLOCK
    res["analytic"] = {
        "template_vs_analytic_noncentrality": {s: kl_noncentrality(rates[s], TPL[s], n) for s in C.STATES},
        "expected_g_E_vs_template": {s: TPL[s].size + kl_noncentrality(rates["E"], TPL[s], n) for s in C.STATES},
        "expected_g_own_state": {s: TPL[s].size + kl_noncentrality(rates[s], TPL[s], n) for s in C.STATES},
        "tau_fit_L1": TAU["1"], "detectors": int(TPL["A"].size),
        "rows_needed_to_reject_E_as_A": None,
        "support": {s: list(map(int, C.support(s) or ())) for s in C.STATES + ("E",)},
        "mean_rate": {s: float(rates[s].mean()) for s in rates}}
    lamEA = kl_noncentrality(rates["E"], TPL["A"], 1)
    res["analytic"]["rows_needed_to_reject_E_as_A"] = float((TAU["1"] - TPL["A"].size) / lamEA) if lamEA > 0 else None
    # 2. regenerate and validate (DB6 dev), then features
    val = Counter()
    feats = []        # one row per scored block of every dev episode
    for study in ("DB6", "DB4", "DB2"):
        for r in records(study):
            if study != "DB6" and "E" not in r["states"]:
                continue
            cnt = det_counts(r)
            ch = chain(cnt)
            by_t = {b["block"]: b for b in r["blocks"]}
            for t, la in ch.items():
                b = by_t.get(t)
                row = {"study": study, "ep": f"{r['schedule']}_e{r['episode']}", "t": t, "state": r["states"][t],
                       "prev": r["states"][t - 1], "alarm": la["alarm"], "P1": la["P1"], "g": la["g"], "gf": la["gf"]}
                if study == "DB6" and b is not None:
                    ok = (b["lookahead"]["g"] == la["g"], b["lookahead"]["alarm"] == la["alarm"],
                          b["lookahead"]["P1"] == la["P1"])
                    val["blocks"] += 1
                    val["exact"] += all(ok)
                    row.update(src=b["source"]["LA_W0F"], k_la=b["keys"]["LA_W0F"], k_w0f=b["keys"]["W0F"],
                               e_la=b["errors"]["LA_W0F"], e_w0f=b["errors"]["W0F"])
                feats.append(row)
    res["validation_DB6"] = dict(val)
    assert val["blocks"] == val["exact"] == 27 * len(C.SCORED), val
    # 2a. E blocks: what fits them
    E = [f for f in feats if f["state"] == "E"]
    best = Counter(min(C.STATES, key=lambda s: f["gf"][s]) for f in E)
    res["E_blocks"] = {
        "n": len(E), "episodes": len({(f["study"], f["ep"]) for f in E}),
        "best_fit": dict(best),
        "P1": dict(Counter("+".join(f["P1"]) or "empty" for f in E)),
        "gfA_quantiles": np.quantile([f["gf"]["A"] for f in E], [0, .1, .5, .9, 1]).tolist(),
        "onsets": len([f for f in E if f["prev"] != "E"]),
        "onset_alarm": sum(f["alarm"] for f in E if f["prev"] != "E"),
        "onset_alarm_singleton_A": sum(f["alarm"] and f["P1"] == ["A"] for f in E if f["prev"] != "E"),
        "any_alarm_singleton": dict(Counter(f["P1"][0] for f in E if f["alarm"] and len(f["P1"]) == 1))}
    # 2b. unknown rejection by novelty (best single-block fit) vs in-bank own-state fits
    inb = [f for f in feats if f["state"] in C.STATES]
    own = np.array([f["gf"][f["state"]] for f in inb])
    nov_E = np.array([min(f["gf"].values()) for f in E])
    roc = []
    for c in (120, 130, 140, 150, 160, 170, 180, 190, 202.42):
        roc.append({"cap": c, "E_rejected": float((nov_E > c).mean()), "inbank_own_fit_rejected": float((own > c).mean())})
    res["novelty_rejection"] = {"E_best_fit_quantiles": np.quantile(nov_E, [0, .1, .5, .9, 1]).tolist(),
                                "inbank_own_fit_quantiles": np.quantile(own, [0, .1, .5, .9, 1]).tolist(), "roc": roc}
    # 2c. the misreads specifically: E blocks whose single-block plausible set is the singleton {A}
    misread = [min(f["gf"].values()) for f in E if f["P1"] == ["A"]]
    la_uses = [min(f["gf"].values()) for f in feats if f["study"] == "DB6" and f.get("src") == "lookahead"]
    res["misread_vs_genuine_fit"] = {
        "E_singleton_A_blocks": len(misread),
        "E_singleton_A_best_fit_quantiles": np.quantile(misread, [0, .25, .5, .75, 1]).tolist(),
        "DB6_LA_use_best_fit_quantiles": np.quantile(la_uses, [0, .25, .5, .75, 1]).tolist(),
        "by_cap": [{"cap": c, "E_singleton_A_kept": int(sum(x <= c for x in misread)),
                    "DB6_LA_uses_kept": int(sum(x <= c for x in la_uses)), "DB6_LA_uses": len(la_uses)}
                   for c in (140, 160, 170, 180, 190, 202.42)]}
    # 3. B-onset economics: risk-table prediction vs DB6 dev observation
    d6 = [f for f in feats if f["study"] == "DB6"]
    econ = defaultdict(lambda: {"opportunities": 0, "triggers": 0, "pred_saved": 0.0, "obs_saved": 0})
    for f in d6:
        if f["state"] == f["prev"] or f["state"] not in C.STATES:
            continue
        x = econ[f["state"]]
        x["opportunities"] += 1
        if f["src"] == "lookahead":
            x["triggers"] += 1
            base = f["k_w0f"].split(":", 1)[1] if f["k_w0f"].startswith("bank:") else None
            la = f["k_la"].split(":", 1)[1]
            if base in RISK[f["state"]]:
                x["pred_saved"] += 1000 * (RISK[f["state"]][base] - RISK[f["state"]][la])
            x["obs_saved"] += f["e_w0f"] - f["e_la"]
    res["onset_economics_DB6"] = {k: {**v, "pred_saved": round(v["pred_saved"], 1)} for k, v in sorted(econ.items())}
    res["risk_excess_of_minimax_key_A"] = {s: round(1000 * (RISK[s]["A"] - RISK[s][s]), 2) for s in C.STATES}
    # 4. controllers on DB6 dev: subsets of LA's own firings -> errors exactly known from the records
    uses = [f for f in d6 if f["src"] == "lookahead"]

    def evaluate(rule):
        fired = [f for f in uses if rule(f)]
        return {"uses": len(fired), "key_changing": sum(f["k_la"] != f["k_w0f"] for f in fired),
                "wrong": sum(f["k_la"] != "bank:" + f["state"] for f in fired),
                "errors_saved_vs_W0F": sum(f["e_w0f"] - f["e_la"] for f in fired),
                "errors_saved_total_LA": sum(f["e_w0f"] - f["e_la"] for f in uses)}
    ctl = {"R0_LA": evaluate(lambda f: True),
           "R1_key_change_only": evaluate(lambda f: f["k_la"] != f["k_w0f"])}
    for c in (140, 160, 180):
        ctl[f"R2_change_and_fit<={c}"] = evaluate(lambda f, c=c: f["k_la"] != f["k_w0f"] and min(f["gf"].values()) <= c)
    for mu in (20, 50, 100):
        ctl[f"R3_change_and_margin>={mu}"] = evaluate(
            lambda f, mu=mu: f["k_la"] != f["k_w0f"] and sorted(f["gf"].values())[1] - min(f["gf"].values()) >= mu)
    res["controllers_DB6"] = ctl
    # 4b. the same rules on E blocks (would they trigger?), using W0F's minimax key A as the base on E
    ctlE = {}
    for name, rule in (("R0_LA", lambda f: True),
                       ("R1_key_change_only(base A)", lambda f: f["P1"] != ["A"]),
                       ("R2_change_and_fit<=160(base A)", lambda f: f["P1"] != ["A"] and min(f["gf"].values()) <= 160)):
        trig = [f for f in E if f["alarm"] and len(f["P1"]) == 1 and rule(f)]
        ctlE[name] = {"triggers": len(trig), "keys": dict(Counter(f["P1"][0] for f in trig))}
    res["controllers_on_E_blocks"] = ctlE
    # 5. same-latency baselines (DB6 dev, pooled errors)
    pooled = Counter()
    for r in records("DB6"):
        for b in r["blocks"]:
            for a in ("W0F", "LA_W0F", "LA_DB2", "LA_BANK", "LA_STATIC", "LA2_W0F", "ORACLE"):
                pooled[a] += b["errors"][a]
    res["same_latency_DB6"] = dict(pooled)
    (V8 / "research" / "PHASEB.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                                                 newline="\n")
    print(json.dumps({k: res[k] for k in ("validation_DB6", "E_blocks", "analytic")}, indent=1)[:3000])


if __name__ == "__main__":
    main()
