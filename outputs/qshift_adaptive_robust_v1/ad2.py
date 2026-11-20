"""AD2 adaptive decoding when the burst itself changes (PLAN_AD2.md, AD2_PROTOCOL.md).

  python ad2.py run <eval|rehearsal> --expected-head <sha> [--workers 8]
  python ad2.py analyze <eval|rehearsal> <out_dir>          # writes ANALYSIS.json and TIMELINE.json
  python ad2.py recount <eval|rehearsal> <analysis.json>

One job = one episode of 30 blocks. For each scored block t (6-29):
  AD        E1T on blocks t-6..t-1 -> Phase C learner + flip -> BP+OSD (AD1's estimate_window, unchanged);
            flagged -> nominal, no burst
  AD_LG     AD's estimate; on a flag, the last accepted (unflagged) AD model and support (nominal if none yet)
  PERIODIC  AD's estimate taken only at blocks 6, 12, 18, 24 and held for 6 blocks
  ONCE      AD's block-6 estimate, frozen
  ORACLE    BP+OSD on block t's true model and true support
  AD_M      correlated matching on AD's model and support;  A_nominal  burst-free matching, nominal model
  AD_W3     as AD on blocks t-3..t-1 (descriptive)
All arms decode the same evaluation shots. Arms that resolve to the same (model, support) share one decoder and
one prediction (exact). Write-once records under work/ad2/<mode>/ (git-ignored); RUN_STATUS.json refuses a relaunch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import ad2_config as C
import studykit as SK

ROOT = C.ROOT
WORK = ROOT / "work" / "ad2"
NOMKEY = "nominal"


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    return o


def seed(mode, key):
    s = json.loads((ROOT / "AD2_SEEDS.json").read_text(encoding="utf-8"))
    return int((s["rehearsal_seeds"] if mode == "rehearsal" else s["seeds"])[key])


def fallback_level():
    p = ROOT / "AD2_PREFLIGHT.json"
    return int(json.loads(p.read_text(encoding="utf-8"))["fallback_level"]) if p.exists() else 0


def run_arms(level):
    return C.ARMS if level == 0 else C.ARMS_NO_W3


def run_episodes(level):
    return C.EPISODES if level < 2 else C.EPISODES_FALLBACK


def sample_block(schedule, t, n, sd):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    kw, _, sup = C.block_truth(schedule, t)
    spec = C.spec(**kw)
    c = m.build_candidate_circuit(spec, C.BURST_Q, tuple(sup)) if sup else m.build_base_circuit(spec)
    d, o = c.compile_detector_sampler(seed=sd).sample(shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def model_key(est, sup):
    if est["flagged"]:
        return NOMKEY
    return json.dumps(["est", float(est["p_hat"]), float(est["b_hat"]),
                       sorted(int(q) for q in sup) if sup is not None else None])


def new_selector():
    return {"once": None, "periodic": None, "lg": None, "lg_from": None, "periodic_from": None}


def advance(sel, t, k_ad, flagged):
    """Update ONCE / PERIODIC / last-good state with AD's block-t estimate; return AD_LG's model key."""
    if not flagged:
        sel["lg"], sel["lg_from"] = k_ad, t
    if sel["once"] is None:
        sel["once"] = k_ad
    if t in C.PERIODIC_AT:
        sel["periodic"], sel["periodic_from"] = k_ad, t
    return k_ad if not flagged else (sel["lg"] or NOMKEY)


def estimate(dets, labx, laby, classes, truth_sup):
    """AD1's frozen estimate_window (E1T -> learner -> flip; flagged -> nominal), unchanged."""
    import ad1
    model, sup, rec = ad1.estimate_window(dets, labx, laby, classes, truth_sup)
    return model, (tuple(int(q) for q in sup) if sup is not None else None), _jsonable(rec)


def episode_job(args):
    mode, s, e, head, run, n_eval, arms = args
    if mode == "eval":
        SK.require_frozen_head(ROOT / "AD2_FREEZE.json", head)
    import mm_contract as K
    import re1
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    name = f"{s}_e{e}"
    out = run / "records" / f"{name}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    t0 = time.perf_counter()
    classes = K.B.load_classes()
    a_nom = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(C.spec(**C.NOMINAL))))
    models = {NOMKEY: (C.spec(**C.NOMINAL), None)}
    decs = {}                                            # key -> (BP+OSD, correlated matching)
    used, dets, labx, laby = {}, [], [], []
    sel = new_selector()
    blocks, bits = [], {}
    dec_s = w3_s = 0.0
    for t in range(C.BLOCKS):
        for part, nrow in (("det", C.DET_PER_BLOCK), ("lab", C.LAB_PER_BLOCK)):
            key = C.block_key(s, e, t, part)
            used[key] = seed(mode, key)
            x, y = sample_block(s, t, nrow, used[key])
            (dets if part == "det" else labx).append(x)
            if part == "lab":
                laby.append(y)
        if t < C.WINDOW:
            continue
        truth_sup = C.block_truth(s, t - 1)[2]           # window truth = the most recent window block's burst
        w0 = t - C.WINDOW                                # causal window: blocks w0 .. t-1
        model, sup, est = estimate(dets[w0:t], labx[w0:t], laby[w0:t], classes, truth_sup)
        k_ad = model_key(est, sup)
        models.setdefault(k_ad, (model, sup))
        k_lg = advance(sel, t, k_ad, est["flagged"])
        once, periodic, lg = sel["once"], sel["periodic"], sel["lg"]
        lg_from, periodic_from = sel["lg_from"], sel["periodic_from"]
        est_w3, k_w3 = None, None
        if "AD_W3" in arms:
            tw = time.perf_counter()
            w3 = t - C.WINDOW_W3
            m3, s3, est_w3 = estimate(dets[w3:t], labx[w3:t], laby[w3:t], classes, truth_sup)
            k_w3 = model_key(est_w3, s3)
            models.setdefault(k_w3, (m3, s3))
            w3_s += time.perf_counter() - tw
        kw, bname, tsup = C.block_truth(s, t)
        k_or = "oracle:" + C.state(s, t)
        models.setdefault(k_or, (C.spec(**kw), tsup))
        arm_key = {"AD": k_ad, "AD_LG": k_lg, "PERIODIC": periodic, "ONCE": once, "ORACLE": k_or}
        if k_w3 is not None:
            arm_key["AD_W3"] = k_w3
        key = C.block_key(s, e, t, "eval")
        used[key] = seed(mode, key)
        x, y = sample_block(s, t, n_eval, used[key])
        preds = {}
        for k in dict.fromkeys(arm_key.values()):
            td = time.perf_counter()
            if k not in decs:
                decs[k] = re1.decoders(*models[k])
            preds[k] = re1.predict(decs[k][0], x, "l2") != y
            dt = time.perf_counter() - td
            dec_s += dt
            if k == k_w3 and sum(v == k for v in arm_key.values()) == 1:
                w3_s += dt
        td = time.perf_counter()
        err = {a: preds[k] for a, k in arm_key.items()}
        err["AD_M"] = re1.predict(decs[k_ad][1], x, "corr") != y
        err["A_nominal"] = re1.predict(a_nom, x, "plain") != y
        dec_s += time.perf_counter() - td
        errs = {}
        for a in arms:
            errs[a] = int(err[a].sum())
            bits[f"b{t:02d}_{a}"] = np.packbits(err[a])
        blocks.append({"block": t, "true": kw, "burst": bname, "estimate": est, "estimate_w3": est_w3,
                       "same_as_AD": {a: arm_key[a] == k_ad for a in arm_key if a != "AD"},
                       "lg_from": lg_from, "periodic_from": periodic_from, "errors": errs})
        keep = {once, periodic, lg, k_or, NOMKEY}
        decs = {k: v for k, v in decs.items() if k in keep}
        models = {k: v for k, v in models.items() if k in keep}
    arc = run / "archives" / f"{name}.npz"
    np.savez_compressed(arc, **bits)
    rec = {"schedule": s, "episode": e, "arms": list(arms), "seeds": used, "eval_per_block": n_eval,
           "bursts": {k: {"label": v["label"], "footprint": v["footprint"]} for k, v in C.BURSTS.items()},
           "blocks": blocks, "archive": f"archives/{arc.name}",
           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest(),
           "timing": {"decode_s": round(dec_s, 1), "w3_s": round(w3_s, 1)}, "seconds": round(time.perf_counter() - t0, 1)}
    SK.write_once_json(out, _jsonable(rec))
    return out.name


def plan_jobs(mode, head, run, level):
    arms = run_arms(level)
    if mode == "rehearsal":
        return [(mode, s, e, head, run, C.REHEARSAL_EVAL_PER_BLOCK, C.ARMS) for s, e in C.REHEARSAL]
    return [(mode, s, e, head, run, C.EVAL_PER_BLOCK, arms) for s in C.SCHEDULES for e in range(run_episodes(level))]


def cmd_run(mode, head, workers):
    level = 0
    if mode == "eval":
        SK.require_frozen_head(ROOT / "AD2_FREEZE.json", head)
        if not (ROOT / "AD2_PREFLIGHT.json").exists():
            raise SystemExit("AD2_PREFLIGHT.json missing")
        level = fallback_level()
    run = WORK / mode
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    for d in ("records", "archives"):
        (run / d).mkdir(parents=True, exist_ok=True)
    js = plan_jobs(mode, head, run, level)
    status = {"mode": mode, "head": SK.git_head(), "expected_head": head, "workers": workers, "fallback_level": level,
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "state": "running", "jobs": {}}
    SK.dump_json(st, status)
    t0 = time.perf_counter()
    try:
        with get_context("spawn").Pool(workers) as pool:
            hs = [(f"{j[1]}_e{j[2]}", pool.apply_async(episode_job, (j,))) for j in js]
            for i, (nm, h) in enumerate(hs, 1):
                h.get(timeout=C.JOB_TIMEOUT_S + 600)
                status["jobs"][nm] = {"returncode": 0}
                print(nm, f"{i}/{len(js)}", f"{time.perf_counter() - t0:.0f}s", flush=True)
        status["state"] = "ready_for_analysis"
    except BaseException as ex:      # noqa: BLE001  (recorded; never retried)
        status["state"], status["error"] = "failed", repr(ex)
        raise
    finally:
        status["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status["wall_seconds"] = round(time.perf_counter() - t0, 1)
        status["n_jobs"] = len(js)
        SK.dump_json(st, status)


# ------------------------------------------------------------------ analysis
def _load(run):
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    for r in recs:
        p = run / r["archive"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != r["archive_sha256"]:
            raise ValueError(f"archive hash mismatch {p.name}")
        z = np.load(p)
        for b in r["blocks"]:
            for a in r["arms"]:
                if int(np.unpackbits(z[f"b{b['block']:02d}_{a}"])[: r["eval_per_block"]].sum()) != b["errors"][a]:
                    raise ValueError("recorded count mismatch")
    return recs


def settled_block(s, t, w=C.WINDOW):
    """Block t and its whole window (t-w .. t) are in one state (burst and background)."""
    return len({C.state(s, u) for u in range(t - w, t + 1)}) == 1


def settled_window(s, t, w=C.WINDOW):
    return len({C.state(s, u) for u in range(t - w, t)}) == 1


def mislearned(est):
    """An accepted wrong class (AD1's rule): unflagged, a class learned, and not the window's true class."""
    return (not est["flagged"]) and est["class_index"] is not None and est["class_index"] != est["true_class"]


def latencies(r, s, key="estimate"):
    acq, rel = [], []
    by = {b["block"]: b for b in r["blocks"]}
    for c in C.CHANGES.get(s, ()):
        new = C.block_truth(s, c)[1]
        lat = None
        for t in range(max(c + 1, C.WINDOW), C.BLOCKS):
            est = by[t][key]
            ok = est["learned_correct"] if new else (est["flagged"] or est["class_index"] is None)
            if ok:
                lat = t - c
                break
        (acq if new else rel).append(lat)
    return acq, rel


def _med(v):
    return float(np.median([x if x is not None else 99 for x in v])) if v else None


def analyze(mode, run):
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs = _load(run)
    seeds = json.loads((ROOT / "AD2_SEEDS.json").read_text(encoding="utf-8"))
    pool = seeds["rehearsal_seeds"] if mode == "rehearsal" else seeds["seeds"]
    for r in recs:
        for k, v in r["seeds"].items():
            if pool[k] != v:
                raise ValueError("seed mismatch")
    if mode == "eval" and len(recs) != st["n_jobs"]:
        raise SystemExit("record count != jobs")
    bseed = int.from_bytes(hashlib.sha256(C.BOOT_SEED_LABEL.encode()).digest()[:8], "big")
    out = {"schema": "qshift-adaptive-robust-ad2-analysis-v1", "mode": mode,
           "bursts": {k: {"label": v["label"], "footprint": v["footprint"]} for k, v in C.BURSTS.items()},
           "schedules": {}, "endpoints": {}, "ad_lg": {}}
    timeline = {"schema": "qshift-adaptive-robust-ad2-timeline-v1", "mode": mode, "blocks": list(C.SCORED),
                "bursts": out["bursts"], "schedules": {}}
    for si, s in enumerate(C.SCHEDULES):
        rr = sorted([r for r in recs if r["schedule"] == s], key=lambda r: r["episode"])
        if not rr:
            continue
        arms = rr[0]["arms"]
        n = rr[0]["eval_per_block"]
        T = [t for t in C.SCORED]
        Tset = [t for t in T if settled_block(s, t)]
        Ttr = [t for t in T if t not in Tset]
        by = [{b["block"]: b for b in r["blocks"]} for r in rr]

        def per_ep(a, ts):
            return np.array([sum(bb[t]["errors"][a] for t in ts) for bb in by], float)

        rng = np.random.default_rng(bseed + si)
        idx = rng.integers(0, len(rr), size=(C.BOOT_REPS, len(rr)))

        def boot_diff(a, b, ts):
            if not ts:
                return None
            d = (per_ep(a, ts)[idx].sum(axis=1) - per_ep(b, ts)[idx].sum(axis=1)) / (len(rr) * len(ts) * n)
            est = float((per_ep(a, ts).sum() - per_ep(b, ts).sum()) / (len(rr) * len(ts) * n))
            return {"estimate": est, "upper_97_5": float(np.quantile(d, 0.975)),
                    "95ci": [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))]}

        def ler(a, ts):
            return float(per_ep(a, ts).sum() / (len(rr) * len(ts) * n)) if ts else None

        def excess(a, ts):
            o, x = per_ep("ORACLE", ts).sum(), per_ep(a, ts).sum()
            return float(x / o - 1) if o else (0.0 if x == 0 else None)

        def red(a, b, ts):
            lb = ler(b, ts)
            return (1 - ler(a, ts) / lb) if lb else None

        acq, rel = [], []
        acq3, rel3 = [], []
        for r in rr:
            a_, r_ = latencies(r, s)
            acq += a_
            rel += r_
            if "AD_W3" in arms:
                a3, r3 = latencies(r, s, "estimate_w3")
                acq3 += a3
                rel3 += r3
        mis = sum(mislearned(bb[t]["estimate"]) for bb in by for t in T if settled_window(s, t))
        flags_set = [sum(bb[t]["estimate"]["flagged"] for t in T if settled_window(s, t)) for bb in by]
        flags_tr = [sum(bb[t]["estimate"]["flagged"] for t in T if not settled_window(s, t)) for bb in by]
        row = {"episodes": len(rr), "arms": arms, "eval_per_block": n, "scored_blocks": len(T),
               "settled_blocks": Tset, "errors": {a: int(per_ep(a, T).sum()) for a in arms},
               "errors_settled": {a: int(per_ep(a, Tset).sum()) for a in arms},
               "errors_transition": {a: int(per_ep(a, Ttr).sum()) for a in arms},
               "ler": {a: ler(a, T) for a in arms}, "ler_settled": {a: ler(a, Tset) for a in arms},
               "AD_minus_ONCE": boot_diff("AD", "ONCE", T), "AD_minus_PERIODIC": boot_diff("AD", "PERIODIC", T),
               "AD_LG_minus_ONCE": boot_diff("AD_LG", "ONCE", T),
               "AD_LG_minus_AD_transition": boot_diff("AD_LG", "AD", Ttr),
               "AD_excess_over_ORACLE_settled": excess("AD", Tset) if Tset else None,
               "AD_LG_excess_over_ORACLE_settled": excess("AD_LG", Tset) if Tset else None,
               "R_vs_A_nominal": {"all": red("AD", "A_nominal", T), "settled": red("AD", "A_nominal", Tset)},
               "R_vs_AD_M": {"all": red("AD", "AD_M", T), "settled": red("AD", "AD_M", Tset)},
               "latency_acquire": acq, "latency_release": rel, "latency_median": _med(acq + rel),
               "mislearned_settled_windows": mis,
               "flagged_settled_windows_per_episode": flags_set, "flagged_transition_windows_per_episode": flags_tr,
               "learned_exactly_windows": sum(bool(bb[t]["estimate"]["learned_correct"]) for bb in by for t in T),
               "windows": len(rr) * len(T),
               "per_block_p_hat": [float(np.mean([bb[t]["estimate"]["p_hat"] for bb in by])) for t in T],
               "per_block_b_hat": [float(np.mean([bb[t]["estimate"]["b_hat"] for bb in by])) for t in T],
               "true_p": [C.block_truth(s, t)[0]["gate_p"] for t in T]}
        if "AD_W3" in arms:
            row["AD_W3"] = {"latency_acquire": acq3, "latency_release": rel3, "latency_median": _med(acq3 + rel3),
                            "mislearned_settled_windows": sum(mislearned(bb[t]["estimate_w3"]) for bb in by for t in T
                                                              if settled_window(s, t, C.WINDOW_W3)),
                            "AD_W3_minus_AD": boot_diff("AD_W3", "AD", T)}
        out["schedules"][s] = row
        timeline["schedules"][s] = {
            "true_burst": [C.block_truth(s, t)[1] for t in T], "true_p": row["true_p"],
            "settled": [t in Tset for t in T],
            "arms": {a: {"ler_mean": [float(np.mean([bb[t]["errors"][a] / n for bb in by])) for t in T],
                         "ler_min": [float(min(bb[t]["errors"][a] / n for bb in by)) for t in T],
                         "ler_max": [float(max(bb[t]["errors"][a] / n for bb in by)) for t in T]} for a in arms},
            "ad_learned_fraction": [float(np.mean([bool(bb[t]["estimate"]["learned_correct"]) for bb in by])) for t in T],
            "ad_flagged_fraction": [float(np.mean([bool(bb[t]["estimate"]["flagged"]) for bb in by])) for t in T]}
    S, E = out["schedules"], {}
    for s in C.CHANGING:
        if s not in S:
            continue
        E[f"E1_{s}"] = bool(S[s]["AD_minus_ONCE"]["upper_97_5"] < 0)
        E[f"E2_{s}"] = bool(S[s]["AD_minus_PERIODIC"]["upper_97_5"] < 0)
        if s in C.E3_SCHEDULES:
            x = S[s]["AD_excess_over_ORACLE_settled"]
            E[f"E3_{s}"] = bool(x is not None and x <= C.ORACLE_EXCESS_MAX)
        E[f"E4_{s}"] = bool(S[s]["latency_median"] is not None and S[s]["latency_median"] <= C.LATENCY_MAX)
    if "C0" in S:
        E["E5_C0"] = bool(S["C0"]["errors"]["AD"] <= C.NO_HARM_FACTOR * S["C0"]["errors"]["ONCE"] + C.NO_HARM_SLACK)
    E["E6"] = bool(all(S[s]["mislearned_settled_windows"] == 0 for s in S))
    out["endpoints"] = E
    full = all(s in S for s in C.SCHEDULES)
    e1 = [E.get(f"E1_{s}", False) for s in C.CHANGING]
    core = full and all(e1) and all(E.get(f"E3_{s}", False) for s in C.E3_SCHEDULES) and \
        all(E.get(f"E4_{s}", False) for s in C.CHANGING) and E.get("E5_C0", False) and E["E6"]
    n_e2 = sum(E.get(f"E2_{s}", False) for s in C.CHANGING)
    out["verdict"] = ("AD2_STRONG" if core and n_e2 >= C.STRONG_MIN_PERIODIC else "AD2_SUPPORTED" if core else
                      "AD2_PARTIAL" if full and sum(e1) >= C.PARTIAL_MIN_E1 and E.get("E5_C0", False) and E["E6"]
                      else "AD2_NOT_SUPPORTED")
    lg = {}
    for s in C.CHANGING:
        if s in S:
            x = S[s]["AD_LG_excess_over_ORACLE_settled"]
            lg[f"E1_{s}"] = bool(S[s]["AD_LG_minus_ONCE"]["upper_97_5"] < 0)
            if s in C.E3_SCHEDULES:
                lg[f"E3_{s}"] = bool(x is not None and x <= C.ORACLE_EXCESS_MAX)
            tr = S[s]["AD_LG_minus_AD_transition"]
            lg[f"better_than_AD_transition_{s}"] = bool(tr is not None and tr["upper_97_5"] < 0)
    if "C0" in S:
        lg["E5_C0"] = bool(S["C0"]["errors"]["AD_LG"] <= C.NO_HARM_FACTOR * S["C0"]["errors"]["ONCE"] + C.NO_HARM_SLACK)
    out["ad_lg"] = lg
    out["run_status"] = {k: st.get(k) for k in ("head", "started", "finished", "wall_seconds", "n_jobs", "fallback_level")}
    return out, timeline


def cmd_analyze(mode, out_dir):
    res, tl = analyze(mode, WORK / mode)
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    SK.write_once_json(o / "ANALYSIS.json", res)
    SK.write_once_json(o / "TIMELINE.json", tl)
    print(json.dumps({"verdict": res["verdict"], **res["endpoints"]}))


def cmd_recount(mode, analysis_path):
    """Re-derive the analysis; re-run episode 0 of every schedule into a replay dir (records and bits identical)."""
    run = WORK / mode
    a = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    same = json.dumps(analyze(mode, run)[0], sort_keys=True) == json.dumps(a, sort_keys=True)
    tmp = WORK / f"{mode}_replay"
    if tmp.exists():
        raise SystemExit(f"{tmp.name} exists; replay runs once")
    for d in ("records", "archives"):
        (tmp / d).mkdir(parents=True)
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    rm = "rehearsal" if mode == "rehearsal" else "replay"
    picks = []
    for s, e in ([(s, 0) for s in C.SCHEDULES] if mode == "eval" else C.REHEARSAL):
        r0 = json.loads((run / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        picks.append((rm, s, e, st["head"], tmp, r0["eval_per_block"], tuple(r0["arms"])))
    with get_context("spawn").Pool(min(8, len(picks))) as pool:
        names = pool.map(episode_job, picks)
    ident = {}
    for nm in names:
        r0 = json.loads((run / "records" / nm).read_text(encoding="utf-8"))
        r1 = json.loads((tmp / "records" / nm).read_text(encoding="utf-8"))
        for r_ in (r0, r1):
            r_.pop("seconds"), r_.pop("timing")
        z0, z1 = np.load(run / r0["archive"]), np.load(tmp / r1["archive"])
        ident[nm] = r0 == r1 and sorted(z0.files) == sorted(z1.files) and all(np.array_equal(z0[f], z1[f]) for f in z0.files)
    res = {"reanalysis_identical": same, "replay_identical": ident, "all_pass": bool(same and all(ident.values()))}
    print(json.dumps(res))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze", "recount"])
    ap.add_argument("mode", choices=["eval", "rehearsal"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--expected-head", default="")
    ap.add_argument("--workers", type=int, default=8)
    x = ap.parse_args()
    if x.cmd == "run":
        cmd_run(x.mode, x.expected_head, x.workers)
    elif x.cmd == "analyze":
        cmd_analyze(x.mode, x.path)
    else:
        cmd_recount(x.mode, x.path)
