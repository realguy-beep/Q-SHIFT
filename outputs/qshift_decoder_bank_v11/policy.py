"""Every saved DB8-format controller field, recomputed from the fields it depends on (v10 review, blocker 3).

check_record = v10's schedule, key and LA/CB checks + a replay of segments, change points, plausible sets, the hazard
tracker, every bank-family arm, the estimator's own rules, AD3's window/recall/fallback and the action flags.

What cannot be recomputed from a record (raw detector rows are not saved): the estimator's numbers, the g and fit
values themselves, the choice among several AD3 library entries, and whether AD3 found no match.
These are checked for type, range and consistency only."""
from __future__ import annotations

import json

import db8_config as C  # noqa: I001
import ad2
import ad3
import brt_config
import db2_core as G
import db4_core as F
import db_core as D
import mm_contract as K
import validate as V10
from strict import SeedPlan, is_int, is_num, need, read_archive, same

EST = {"S1", "S2", "b_hat", "class_index", "excluded", "flagged", "flip", "learned_correct", "p_hat", "true_class"}
EST3 = EST | {"seg0", "seg_len", "source"}
RECALL = (EST3 - {"S1", "S2", "excluded"}) | {"recall_g"}
PLAN = SeedPlan(C.BLOCKS, C.SCORED, C.block_key)
N_DET = 120
_CLASSES = None


def classes():
    global _CLASSES
    if _CLASSES is None:
        _CLASSES = K.B.load_classes()
    return _CLASSES


def _support(est):
    if est["class_index"] is None:
        return None
    return tuple(int(v) for v in classes()[est["class_index"]].representative(est["flip"]))


def _learned_key(est):
    return ad2.model_key(est, _support(est))


def _truth(state):
    return ad3._truth(classes(), C.support(state))


def _key_support(k):
    if k.startswith("bank:"):
        return C.support(k[5:])
    return None if k == "nominal" else json.loads(k)[3]


def _estimate(e, truth_state, w, fields=EST):
    need(isinstance(e, dict) and set(e) == fields, w + "estimator fields")
    need(is_num(e["p_hat"]) and type(e["p_hat"]) is float and 0 < e["p_hat"] < 0.5, w + "p_hat")
    need(type(e["b_hat"]) is float and is_num(e["b_hat"]) and e["b_hat"] > 0, w + "b_hat")
    need(type(e["flagged"]) is bool and type(e["learned_correct"]) is bool, w + "estimator flags")
    ci, fl = e["class_index"], e["flip"]
    need((ci is None and fl is None) or (is_int(ci, 0, len(classes()) - 1) and is_int(fl, 0, 1)), w + "class or flip")
    t_idx, t_flip = _truth(truth_state)
    need(same(e["true_class"], t_idx), w + "true class")
    need(e["learned_correct"] is bool(t_idx is not None and ci == t_idx and fl == t_flip and not e["flagged"]),
         w + "learned_correct")
    if "excluded" in fields:
        need(is_int(e["excluded"], 0, N_DET) and type(e["S1"]) is bool and type(e["S2"]) is bool, w + "structural fields")
        if e["excluded"] == 0:
            need(not e["S1"] and e["S2"] is (ci is not None), w + "structural flags")
        else:
            need(ci is not None or e["S2"], w + "structural flags")
        need(e["flagged"] is (e["excluded"] > brt_config.E1_MAX_EXCLUDED or e["S1"] or e["S2"]), w + "flagged")


def check_record(r, seeds, tr, ident, extra=()):
    s, e = ident
    nm = f"{s}_e{e}"
    need(isinstance(r, dict) and same(r.get("seeds"), PLAN.expected(seeds, s, e)), f"{nm}: seeds")
    need(type(r.get("episode")) is int and type(r.get("eval_per_block")) is int, f"{nm}: integer fields")
    try:
        V10.validate_record(r, seeds, tr, ident, extra)
    except (KeyError, TypeError, AttributeError, IndexError) as ex:
        need(False, f"{nm}: malformed ({ex!r})")
    except ValueError as ex:
        need(False, str(ex))
    try:
        _replay(r, tr, nm)
    except (KeyError, TypeError, AttributeError, IndexError) as ex:
        need(False, f"{nm}: malformed ({ex!r})")


def _replay(r, tr, nm):
    tau, risk, static, B = tr["tau_fit"], tr["risk"], tr["static_key"], C.STATES
    need(isinstance(r["timing"], dict) and set(r["timing"]) == {"control_s", "decode_s"} and
         all(is_num(v) and v >= 0 for v in (*r["timing"].values(), r["seconds"])), f"{nm}: timing")
    need(all(type(t) is int for t in r["true_changes"] + r["changes_detected"]), f"{nm}: change points")
    g = r["g"]
    need(set(g) == {str(u) for u in range(1, C.BLOCKS - 1)} and all(is_num(v) and v >= -1e-6 for v in g.values()), f"{nm}: g")
    changes = [u for u in range(1, C.BLOCKS - 1) if g[str(u)] > C.AD3_TAU]
    need(r["changes_detected"] == changes, f"{nm}: change points do not follow from g")
    trk, seen, library = G.Tracker(), 0, {}
    prev = {a: "bank:" + static for a in C.BANK_ARMS}
    name = lambda k: k.split(":", 1)[1] if k.startswith("bank:") else None   # noqa: E731
    before = None
    for b in r["blocks"]:
        t, w = b["block"], f"{nm} b{b['block']:02d}: "
        need(type(t) is int, w + "block number")
        past = [u for u in changes if u < t]
        seg0 = past[-1] if past else 0
        L = t - ad3.segment_lo(seg0, t)
        need(is_int(b["seg0"]) and b["seg0"] == seg0, w + "segment start")
        need(is_int(b["L"]) and b["L"] == L, w + "segment length")
        need(b["g_prev"] == g[str(t - 1)], w + "g_prev")
        need(b["alarm"] is (len(past) > seen), w + "alarm")
        seen = len(past)
        if str(t) in g:
            need(b["lookahead"]["g"] == g[str(t)], w + "lookahead g")
        need(set(b["lookahead"]) == {"P1", "alarm", "g"} and set(b["db8"]) == {"gf1"}, w + "lookahead fields")
        gf, P = b["gfit"], b["plausible"]
        need(set(gf) == set(B) and all(is_num(v) for v in gf.values()), w + "gfit")
        need(P == [x for x in B if x in P], w + "plausible states")
        for x in B:                                           # gfit is saved rounded to 3 decimals
            if abs(gf[x] - tau[str(L)]) > 6e-4:
                need((x in P) is (gf[x] <= tau[str(L)]), w + "plausible set does not follow from gfit")
        if L == 1 and before is not None:
            need(all(abs(gf[x] - before["db8"]["gf1"][x]) < 6e-4 for x in B), w + "one-block gfit")
        est = b["estimate"]
        _estimate(est, r["states"][t - 1], w)
        k_ad = _learned_key(est)
        # ---- bank family
        trk.observe(P, b["alarm"])
        need(same(b["tracker"], json.loads(json.dumps(trk.snapshot()))), w + "tracker")
        kn = {"BANK": D.bank_decide({x: 0.0 if x in P else float("inf") for x in B}, L, tau, risk, name(prev["BANK"]))[0]}
        for arm, (mode, kap) in C.CANDIDATES.items():
            kn[arm] = G.gate(P, risk, trk, name(prev[arm]), mode, kap)
        trk.commit(P)
        for arm, k in kn.items():
            if arm in C.FALLBACK_ARMS:
                want = F.fallback_key(k, est, k_ad, prev[arm], static)
            elif k is not None:
                want = ("bank:" + k, "bank")
            else:
                want = (k_ad, "learn") if not est["flagged"] else (prev[arm], "hold")
            need((b["keys"][arm], b["source"][arm]) == want, w + f"{arm} does not follow the policy")
            prev[arm] = want[0]
        # ---- AD3
        e3, src, seg_len = b["estimate_ad3"], b["source"]["AD3"], t - seg0
        need(is_int(e3.get("seg0")) and e3["seg0"] == seg0 and is_int(e3.get("seg_len")) and e3["seg_len"] == seg_len and
             e3.get("source") == src, w + "AD3 segment")
        need((src == "window") is (seg_len >= C.WINDOW), w + "AD3 source")
        if src == "recall":
            _estimate(e3, r["states"][t - 1], w + "AD3 ", RECALL)
            ent = library.get(ad3._ident(e3))
            need(ent is not None and not e3["flagged"] and all(same(e3[f], ent[f]) for f in ("p_hat", "b_hat")), w + "AD3 recall")
            need(is_num(e3["recall_g"]) and -1e-6 <= e3["recall_g"] <= C.AD3_TAU, w + "AD3 recall g")
            need(b["keys"]["AD3"] == _learned_key(ent), w + "AD3 key")
        else:
            need(set(e3) == EST3 and all(same(e3[f], est[f]) for f in EST), w + "AD3 estimate")
            need(b["keys"]["AD3"] == k_ad, w + "AD3 key")
        if src == "window" and not est["flagged"]:
            library[ad3._ident(est)] = est
        # ---- action flags
        for a, k in b["keys"].items():
            sup = _key_support(k)
            need(b["burst_action"][a] is (sup is not None), w + f"{a} burst_action")
            need(b["acceptable"][a] is bool(D.acceptable(sup, b["state"], classes())), w + f"{a} acceptable")
        before = b


def check_arrays(r, raw):
    """-> {block: {arm: bool[rows]}}; counts match, and arms with one key have one result."""
    bits = read_archive(raw, [f"b{t:02d}_{a}" for t in C.SCORED for a in C.ARMS], C.EVAL_PER_BLOCK)
    out = {}
    for b in r["blocks"]:
        t, by = b["block"], {}
        out[t] = {a: bits[f"b{t:02d}_{a}"] for a in C.ARMS}
        for a, v in out[t].items():
            need(int(v.sum()) == b["errors"][a], f"b{t:02d} {a}: bit count")
            if a in b["keys"]:
                need((by.setdefault(b["keys"][a], v) == v).all(), f"b{t:02d}: one key, two results")
    return out
