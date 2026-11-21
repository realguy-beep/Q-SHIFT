"""AD3 faster reaction to a change (PLAN_AD3.md, AD3_PROTOCOL.md).

  python ad3.py run <eval|rehearsal> --expected-head <sha> [--workers 8]
  python ad3.py analyze <eval|rehearsal> <out_dir>          # writes ANALYSIS.json and TIMELINE.json
  python ad3.py recount <eval|rehearsal> <analysis.json>

AD2's stream, schedules and pipeline (ad1.estimate_window via ad2.estimate), unchanged. New: the AD3 arm.
  Change test   after block u is decoded, its 2,000 unlabelled detector rows are compared with the pooled rows of
                the current segment (blocks since the last detected change, at most the last 6) by a two-sample
                binomial log-likelihood ratio over the 120 detectors. G > tau -> a change at u; the segment
                restarts at u. Block t's decoding uses only blocks < t (causal).
  AD3 window    segment length >= 6: AD's 6-block window (identical to AD).
                M <= length < 6: E1T on the segment; used if unflagged.
                otherwise (shorter, or the segment estimate flagged): recall a model learned earlier in the
                episode whose window rows are not rejected against the segment (G <= tau, smallest G);
                otherwise AD's own estimate (AD2's behaviour).
  Library       every unflagged AD3 estimate whose window lies inside one segment (latest per learned class).
tau and M come from AD3_SCREEN.json (Phase 1, fixed rules, frozen). Arms: AD3, AD, PERIODIC, ONCE, ORACLE, A_nominal,
all on the same evaluation shots; identical (model, support) pairs share one decoder and one prediction (exact).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import ad2
import ad3_config as C
import studykit as SK

ROOT = C.ROOT
WORK = ROOT / "work" / "ad3"
NOMKEY = ad2.NOMKEY


# ------------------------------------------------------------------ change statistic (unlabelled rows only)
def counts(rows):
    rows = np.asarray(rows, np.uint8)
    return rows.sum(axis=0).astype(np.int64), int(len(rows))


def pool(cs):
    return sum(c[0] for c in cs), sum(c[1] for c in cs)


def _ll(k, n, p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return k * np.log(p) + (n - k) * np.log1p(-p)


def g_stat(k1, n1, k0, n0):
    """Two-sample binomial LLR summed over detectors: 2 [ll(own rates) - ll(pooled rate)]."""
    k1, k0 = np.asarray(k1, float), np.asarray(k0, float)
    p = (k1 + k0) / (n1 + n0)
    g = _ll(k1, n1, k1 / n1) + _ll(k0, n0, k0 / n0) - _ll(k1, n1, p) - _ll(k0, n0, p)
    return float(2 * g.sum())


def segment_lo(seg0, u):
    """Comparison blocks for block u: the segment's blocks before u, at most the last 6."""
    return max(seg0, u - C.WINDOW)


# ------------------------------------------------------------------ sampling and seeds
def seed(mode, key):
    s = json.loads((ROOT / "AD3_SEEDS.json").read_text(encoding="utf-8"))
    pool_ = {"rehearsal": s["rehearsal_seeds"], "screen": s["screen_seeds"]}.get(mode, s["seeds"])
    return int(pool_[key])


def sample_state(name, n, sd, p=C.A2.P0):
    """Rows from the background at p with burst `name` (or none) at q = 0.01."""
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    sp = C.spec(**C.A2._bg(p))
    sup = C.BURSTS[name]["support"] if name else None
    c = m.build_candidate_circuit(sp, C.A2.BURST_Q, tuple(sup)) if sup else m.build_base_circuit(sp)
    d, o = c.compile_detector_sampler(seed=sd).sample(shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def fallback_level():
    p = ROOT / "AD3_PREFLIGHT.json"
    return int(json.loads(p.read_text(encoding="utf-8"))["fallback_level"]) if p.exists() else 0


def run_episodes(level):
    return C.EPISODES if level < 1 else C.EPISODES_FALLBACK


def _truth(classes, sup):
    import mm_contract as K
    return K.B.truth(classes, tuple(sup)) if sup else (None, None)


def recall(library, k, n, tau):
    """The library entry whose window rows are closest to the segment (G <= tau), or None."""
    best = None
    for ident, ent in library.items():
        g = g_stat(k, n, ent["k"], ent["n"])
        if g <= tau and (best is None or g < best[0]):
            best = (g, ident)
    return best


def _ident(est):
    return json.dumps([est.get("class_index"), est.get("flip")])


# ------------------------------------------------------------------ one episode
def episode_job(args):
    mode, s, e, head, run, n_eval = args
    if mode in ("eval", "replay"):                       # replay reads the eval seeds (seed())
        SK.require_frozen_head(ROOT / "AD3_FREEZE.json", head)
    tau, M = C.screen_params()
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
    decs = {}
    used, dets, labx, laby, cnt = {}, [], [], [], []
    sel = ad2.new_selector()
    seg0, changes, gs = 0, [], {}
    library = {}
    blocks, bits = [], {}
    dec_s = est_s = 0.0
    for t in range(C.BLOCKS):
        if t >= 2:                                       # change test for block u = t-1 (already decoded)
            u = t - 1
            k0, n0 = pool(cnt[segment_lo(seg0, u):u])
            gs[u] = g_stat(*cnt[u], k0, n0)
            if gs[u] > tau:
                seg0 = u
                changes.append(u)
        for part, nrow in (("det", C.DET_PER_BLOCK), ("lab", C.LAB_PER_BLOCK)):
            key = C.block_key(s, e, t, part)
            used[key] = seed(mode, key)
            x, y = ad2.sample_block(s, t, nrow, used[key])
            if part == "det":
                dets.append(x)
                cnt.append(counts(x))
            else:
                labx.append(x)
                laby.append(y)
        if t < C.WINDOW:
            continue
        truth_sup = C.block_truth(s, t - 1)[2]           # window truth = the most recent window block's burst
        t_idx, t_flip = _truth(classes, truth_sup)
        w0 = t - C.WINDOW                                # AD: causal window blocks w0 .. t-1
        te = time.perf_counter()
        model, sup, est = ad2.estimate(dets[w0:t], labx[w0:t], laby[w0:t], classes, truth_sup)
        k_ad = ad2.model_key(est, sup)
        models.setdefault(k_ad, (model, sup))
        ad2.advance(sel, t, k_ad, est["flagged"])
        once, periodic = sel["once"], sel["periodic"]
        # ---- AD3
        seg_len = t - seg0
        src, k3, e3, store = None, None, None, None
        if seg_len >= C.WINDOW:
            src, k3, e3 = "window", k_ad, dict(est)
            if not est["flagged"]:
                store = (k_ad, model, sup, est, pool(cnt[w0:t]))
        else:
            if seg_len >= M:
                ms, ss, es = ad2.estimate(dets[seg0:t], labx[seg0:t], laby[seg0:t], classes, truth_sup)
                if not es["flagged"]:
                    ks = ad2.model_key(es, ss)
                    models.setdefault(ks, (ms, ss))
                    src, k3, e3 = "segment", ks, dict(es)
                    store = (ks, ms, ss, es, pool(cnt[seg0:t]))
            if src is None:
                kk, nn = pool(cnt[seg0:t])
                hit = recall(library, kk, nn, tau)
                if hit is not None:
                    ent = library[hit[1]]
                    ci, fl = ent["est"]["class_index"], ent["est"]["flip"]
                    src, k3 = "recall", ent["key"]
                    models.setdefault(k3, (ent["model"], ent["sup"]))
                    e3 = {"flagged": False, "class_index": ci, "flip": fl, "true_class": t_idx,
                          "learned_correct": bool(t_idx is not None and ci == t_idx and fl == t_flip),
                          "p_hat": ent["est"]["p_hat"], "b_hat": ent["est"]["b_hat"], "recall_g": hit[0]}
            if src is None:
                src, k3, e3 = "ad_fallback", k_ad, dict(est)
        if store is not None:
            kx, mx, sx, ex, (kc, nc) = store
            library[_ident(ex)] = {"key": kx, "model": mx, "sup": sx, "est": ex, "k": kc, "n": nc}
        e3.update({"source": src, "seg0": seg0, "seg_len": seg_len})
        est_s += time.perf_counter() - te
        kw, bname, tsup = C.block_truth(s, t)
        k_or = "oracle:" + C.state(s, t)
        models.setdefault(k_or, (C.spec(**kw), tsup))
        arm_key = {"AD3": k3, "AD": k_ad, "PERIODIC": periodic, "ONCE": once, "ORACLE": k_or}
        key = C.block_key(s, e, t, "eval")
        used[key] = seed(mode, key)
        x, y = ad2.sample_block(s, t, n_eval, used[key])
        td = time.perf_counter()
        preds = {}
        for k in dict.fromkeys(arm_key.values()):
            if k not in decs:
                decs[k] = re1.decoders(*models[k])
            preds[k] = re1.predict(decs[k][0], x, "l2") != y
        err = {a: preds[k] for a, k in arm_key.items()}
        err["A_nominal"] = re1.predict(a_nom, x, "plain") != y
        dec_s += time.perf_counter() - td
        errs = {}
        for a in C.ARMS:
            errs[a] = int(err[a].sum())
            bits[f"b{t:02d}_{a}"] = np.packbits(err[a])
        blocks.append({"block": t, "true": kw, "burst": bname, "estimate": est, "estimate_ad3": ad2._jsonable(e3),
                       "g_prev": gs.get(t - 1), "same_as_AD": {a: arm_key[a] == k_ad for a in arm_key if a != "AD"},
                       "errors": errs})
        keep = {once, periodic, k_or, NOMKEY, k_ad, k3} | {v["key"] for v in library.values()}
        decs = {k: v for k, v in decs.items() if k in keep}
        models = {k: v for k, v in models.items() if k in keep}
    arc = run / "archives" / f"{name}.npz"
    np.savez_compressed(arc, **bits)
    rec = {"schedule": s, "episode": e, "arms": list(C.ARMS), "seeds": used, "eval_per_block": n_eval,
           "tau": tau, "M": M, "changes_detected": changes, "g": {str(k): v for k, v in sorted(gs.items())},
           "bursts": {k: {"label": v["label"], "footprint": v["footprint"]} for k, v in C.BURSTS.items()},
           "blocks": blocks, "archive": f"archives/{arc.name}",
           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest(),
           "timing": {"decode_s": round(dec_s, 1), "estimate_s": round(est_s, 1)},
           "seconds": round(time.perf_counter() - t0, 1)}
    SK.write_once_json(out, ad2._jsonable(rec))
    return out.name


def plan_jobs(mode, head, run, level):
    if mode == "rehearsal":
        return [(mode, s, e, head, run, C.REHEARSAL_EVAL_PER_BLOCK) for s, e in C.REHEARSAL]
    return [(mode, s, e, head, run, C.EVAL_PER_BLOCK) for s in C.SCHEDULES for e in range(run_episodes(level))]


def cmd_run(mode, head, workers):
    level = 0
    if mode == "eval":
        SK.require_frozen_head(ROOT / "AD3_FREEZE.json", head)
        if not (ROOT / "AD3_PREFLIGHT.json").exists():
            raise SystemExit("AD3_PREFLIGHT.json missing")
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
        with get_context("spawn").Pool(workers) as pool_:
            hs = [(f"{j[1]}_e{j[2]}", pool_.apply_async(episode_job, (j,))) for j in js]
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


def detection_delays(r, s):
    """Per true change c: blocks from c to the first detected change >= c (None if never)."""
    out = []
    for c in C.CHANGES.get(s, ()):
        nxt = [u for u in r["changes_detected"] if u >= c]
        out.append(nxt[0] - c if nxt else None)
    return out


def analyze(mode, run):
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs = _load(run)
    seeds = json.loads((ROOT / "AD3_SEEDS.json").read_text(encoding="utf-8"))
    pool_ = seeds["rehearsal_seeds"] if mode == "rehearsal" else seeds["seeds"]
    for r in recs:
        for k, v in r["seeds"].items():
            if pool_[k] != v:
                raise ValueError("seed mismatch")
    if mode == "eval" and len(recs) != st["n_jobs"]:
        raise SystemExit("record count != jobs")
    bseed = int.from_bytes(hashlib.sha256(C.BOOT_SEED_LABEL.encode()).digest()[:8], "big")
    bursts = {k: {"label": v["label"], "footprint": v["footprint"]} for k, v in C.BURSTS.items()}
    out = {"schema": "qshift-adaptive-robust-ad3-analysis-v1", "mode": mode, "bursts": bursts,
           "tau": recs[0]["tau"] if recs else None, "M": recs[0]["M"] if recs else None,
           "schedules": {}, "endpoints": {}}
    timeline = {"schema": "qshift-adaptive-robust-ad3-timeline-v1", "mode": mode, "blocks": list(C.SCORED),
                "bursts": bursts, "schedules": {}}
    for si, s in enumerate(C.SCHEDULES):
        rr = sorted([r for r in recs if r["schedule"] == s], key=lambda r: r["episode"])
        if not rr:
            continue
        arms, n = rr[0]["arms"], rr[0]["eval_per_block"]
        T = list(C.SCORED)
        Tset = [t for t in T if ad2.settled_block(s, t)]
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

        def red(a, b, ts):
            lb = ler(b, ts)
            return (1 - ler(a, ts) / lb) if lb else None

        def excess(a, ts):
            o, x = per_ep("ORACLE", ts).sum(), per_ep(a, ts).sum()
            return float(x / o - 1) if o else (0.0 if x == 0 else None)

        lat3, lat_ad, delays = [], [], []
        for r in rr:
            a3, r3 = ad2.latencies(r, s, "estimate_ad3")
            aa, ra = ad2.latencies(r, s, "estimate")
            lat3 += a3 + r3
            lat_ad += aa + ra
            delays += detection_delays(r, s)
        sources = {}
        for bb in by:
            for t in T:
                sources[bb[t]["estimate_ad3"]["source"]] = sources.get(bb[t]["estimate_ad3"]["source"], 0) + 1
        row = {"episodes": len(rr), "arms": arms, "eval_per_block": n, "scored_blocks": len(T), "settled_blocks": Tset,
               "errors": {a: int(per_ep(a, T).sum()) for a in arms},
               "errors_settled": {a: int(per_ep(a, Tset).sum()) for a in arms},
               "errors_transition": {a: int(per_ep(a, Ttr).sum()) for a in arms},
               "ler": {a: ler(a, T) for a in arms},
               "AD3_minus_AD": boot_diff("AD3", "AD", T),
               "AD3_minus_AD_transition": boot_diff("AD3", "AD", Ttr),
               "AD3_excess_over_ORACLE": {"all": excess("AD3", T), "settled": excess("AD3", Tset) if Tset else None},
               "AD_excess_over_ORACLE": {"all": excess("AD", T), "settled": excess("AD", Tset) if Tset else None},
               "R_AD3_vs": {b: red("AD3", b, T) for b in ("AD", "ONCE", "PERIODIC", "A_nominal")},
               "R_AD_vs_A_nominal": red("AD", "A_nominal", T),
               "latency_AD3": lat3, "latency_AD3_median": ad2._med(lat3),
               "latency_AD": lat_ad, "latency_AD_median": ad2._med(lat_ad),
               "detection_delays": delays,
               "detections_per_episode": [len(r["changes_detected"]) for r in rr],
               "mislearned_settled_windows_AD3": sum(ad2.mislearned(bb[t]["estimate_ad3"]) for bb in by for t in T
                                                     if ad2.settled_window(s, t)),
               "mislearned_settled_windows_AD": sum(ad2.mislearned(bb[t]["estimate"]) for bb in by for t in T
                                                    if ad2.settled_window(s, t)),
               "ad3_sources": dict(sorted(sources.items())),
               "true_p": [C.block_truth(s, t)[0]["gate_p"] for t in T]}
        out["schedules"][s] = row
        timeline["schedules"][s] = {
            "true_burst": [C.block_truth(s, t)[1] for t in T], "true_p": row["true_p"],
            "settled": [t in Tset for t in T],
            "arms": {a: {"ler_mean": [float(np.mean([bb[t]["errors"][a] / n for bb in by])) for t in T],
                         "ler_min": [float(min(bb[t]["errors"][a] / n for bb in by)) for t in T],
                         "ler_max": [float(max(bb[t]["errors"][a] / n for bb in by)) for t in T]} for a in arms},
            "ad3_learned_fraction": [float(np.mean([bool(bb[t]["estimate_ad3"]["learned_correct"]) for bb in by]))
                                     for t in T],
            "ad_learned_fraction": [float(np.mean([bool(bb[t]["estimate"]["learned_correct"]) for bb in by])) for t in T],
            "ad3_change_detected_fraction": [float(np.mean([(t - 1) in r["changes_detected"] for r in rr])) for t in T]}
    S, E = out["schedules"], {}
    if "S2" in S:
        E["F1_S2"] = bool(S["S2"]["AD3_minus_AD"]["upper_97_5"] < 0)
    for s in ("S1", "S3", "S4"):
        if s in S:
            E[f"F2_{s}"] = bool(S[s]["AD3_minus_AD"]["estimate"] <= 0)
    if "C0" in S:
        E["F3_C0"] = bool(S["C0"]["errors"]["AD3"] <= C.NO_HARM_FACTOR * S["C0"]["errors"]["AD"] + C.NO_HARM_SLACK)
    E["F4"] = bool(all(S[s]["mislearned_settled_windows_AD3"] == 0 for s in S))
    for s in C.CHANGING:
        if s in S:
            v = S[s]["latency_AD3_median"]
            E[f"F5_{s}"] = bool(v is not None and v <= C.LATENCY_MAX)
    out["endpoints"] = E
    full = all(s in S for s in C.SCHEDULES)
    f1, f3, f4 = E.get("F1_S2", False), E.get("F3_C0", False), E["F4"]
    f2 = all(E.get(f"F2_{s}", False) for s in ("S1", "S3", "S4"))
    f5 = all(E.get(f"F5_{s}", False) for s in C.CHANGING)
    out["verdict"] = ("AD3_STRONG" if full and f1 and f2 and f3 and f4 and f5 else
                      "AD3_SUPPORTED" if full and f1 and f2 and f3 and f4 else
                      "AD3_PARTIAL" if full and f1 and f3 and f4 else "AD3_NOT_SUPPORTED")
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
    picks = []
    for s, e in ([(s, 0) for s in C.SCHEDULES] if mode == "eval" else C.REHEARSAL):
        r0 = json.loads((run / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        picks.append(("replay" if mode == "eval" else "rehearsal", s, e, st["head"], tmp, r0["eval_per_block"]))
    with get_context("spawn").Pool(min(8, len(picks))) as pool_:
        names = pool_.map(episode_job, picks)
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
