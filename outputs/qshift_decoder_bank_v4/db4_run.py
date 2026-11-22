"""DB4 development run: W0 + static fallback on the unknown path (W0F) against W0 and the DB3 arms (PLAN_DB4.md).

  python db4_run.py fidelity                # DB3 dev episode AA_e1 re-run: DB3 arms match DB3's record; W0F = replay
  python db4_run.py dev [--workers 8]       # the development run (fresh DB4 seeds)
  python db4_run.py analyze <out_dir>       # ANALYSIS.json + TIMELINE.json (twice -> byte-identical)

Per block t (6-29) every arm decodes the same 1,000 evaluation rows; each arm's choice uses only blocks < t.
The per-block loop is DB3's episode_job; the one change is W0F's unknown-path rule (db4_core.fallback_key).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import db4_config as C  # noqa: I001  (puts DB3, DB2, DB1 and AD2/AD3 on sys.path first)
import db2_core as G  # noqa: E402
import db4_core as F  # noqa: E402

WORK = C.ROOT / "work"
FID = ("DB3", "AA", 1)
FID_W0F = {"errors": 35, "triggers": [8, 9, 12, 17]}      # PLAN_DB4.md: the seen-data replay of AA_e1


def _training():
    return json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))


def _setup(mode, s, e):
    """-> (truth(t), seed(t, part), n_eval, params, true_changes)."""
    if mode == "fidelity":
        C3 = C.C3
        sd = json.loads((C.DB3 / "DB3_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
        prm = C3.episode_params(s, e, int(sd[f"db3:params:{s}:e{e}"]))
        return (lambda t: C3.block_state(s, t, prm)), (lambda t, p: int(sd[C3.block_key(s, e, t, p)])), \
            C.EVAL_PER_BLOCK, prm, C3.changes(s, prm)
    sd = json.loads((C.ROOT / "DB4_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    prm = C.episode_params(s, e, int(sd[f"db4:params:{s}:e{e}"]))
    return (lambda t: C.block_state(s, t, prm)), (lambda t, p: int(sd[C.block_key(s, e, t, p)])), \
        C.EVAL_PER_BLOCK, prm, C.changes(s, prm)


def _bank_arm(kname, est, k_ad, prev):
    """Unknown path shared with DB1: AD's accepted estimate, else hold."""
    if kname is not None:
        return "bank:" + kname, "bank"
    return (k_ad, "learn") if not est["flagged"] else (prev, "hold")


def episode_job(args):
    mode, s, e, run = args
    import ad2
    import ad3
    import db_core as D
    import mm_contract as K
    import re1
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    run = Path(run)
    out = run / "records" / f"{s}_e{e}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    truth, seed, n_eval, prm, true_ch = _setup(mode, s, e)
    tr = _training()
    tpl = {k: np.array(v) for k, v in tr["templates"].items()}
    tau_fit, risk, static = tr["tau_fit"], tr["risk"], tr["static_key"]
    t0 = time.perf_counter()
    classes = K.B.load_classes()
    p0 = C.spec(gate_p=C.P0, measurement_p=C.P0)
    a_nom = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(C.spec(**C.NOMINAL))))
    models = {ad2.NOMKEY: (C.spec(**C.NOMINAL), None)}
    for st in C.STATES + ("E",):
        models["bank:" + st] = (p0, C.support(st))
    decs, seeds_used = {}, {}
    dets, labx, laby, cnt = [], [], [], []
    seg0, changes, gs, library = 0, [], {}, {}
    prev = {a: "bank:" + static for a in C.BANK_ARMS}
    trk = G.Tracker()
    n_alarms_seen = 0
    blocks, bits = [], {}
    dec_s = est_s = 0.0
    for t in range(C.BLOCKS):
        if t >= 2:                                       # change test for block u = t-1 (AD3's, shared)
            u = t - 1
            k0, n0 = ad3.pool(cnt[ad3.segment_lo(seg0, u):u])
            gs[u] = ad3.g_stat(*cnt[u], k0, n0)
            if gs[u] > C.AD3_TAU:
                seg0 = u
                changes.append(u)
        for part, nrow in (("det", C.DET_PER_BLOCK), ("lab", C.LAB_PER_BLOCK)):
            sd = seed(t, part)
            seeds_used[f"b{t:02d}:{part}"] = sd
            x, y = D.sample(truth(t), nrow, sd)
            if part == "det":
                dets.append(x)
                cnt.append(ad3.counts(x))
            else:
                labx.append(x)
                laby.append(y)
        if t < C.WINDOW:
            continue
        te = time.perf_counter()
        truth_sup = C.support(truth(t - 1))
        t_idx, t_flip = ad3._truth(classes, truth_sup)
        w0 = t - C.WINDOW
        model, sup, est = ad2.estimate(dets[w0:t], labx[w0:t], laby[w0:t], classes, truth_sup)
        k_ad = ad2.model_key(est, sup)
        models.setdefault(k_ad, (model, sup))
        # ---- AD3 (verbatim from DB1's episode_job, M = 6)
        seg_len = t - seg0
        src, k3, e3, store = None, None, None, None
        if seg_len >= C.WINDOW:
            src, k3, e3 = "window", k_ad, dict(est)
            if not est["flagged"]:
                store = (k_ad, model, sup, est, ad3.pool(cnt[w0:t]))
        else:
            kk, nn = ad3.pool(cnt[seg0:t])
            hit = ad3.recall(library, kk, nn, C.AD3_TAU)
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
            library[ad3._ident(ex)] = {"key": kx, "model": mx, "sup": sx, "est": ex, "k": kc, "n": nc}
        e3.update({"source": src, "seg0": seg0, "seg_len": seg_len})
        # ---- bank arms (segment = AD3's segment, at most the last 6 blocks)
        lo = ad3.segment_lo(seg0, t)
        L = t - lo
        kseg, nseg = ad3.pool(cnt[lo:t])
        gf = {st: D.g_fit(kseg, nseg, tpl[st]) for st in C.STATES}
        name = lambda k: k.split(":", 1)[1] if k.startswith("bank:") else None   # noqa: E731
        kb, P = D.bank_decide(gf, L, tau_fit, risk, name(prev["BANK"]))
        alarm = len(changes) > n_alarms_seen
        n_alarms_seen = len(changes)
        trk.observe(P, alarm)
        snap = trk.snapshot()
        kn_arm = {"BANK": kb}
        for arm, (gm, kap) in C.CANDIDATES.items():
            kn_arm[arm] = G.gate(P, risk, trk, name(prev[arm]), gm, kap)
        trk.commit(P)
        keys, srcs = {}, {}
        for arm, kn in kn_arm.items():
            keys[arm], srcs[arm] = F.fallback_key(kn, est, k_ad, prev[arm], static) if arm in C.FALLBACK_ARMS \
                else _bank_arm(kn, est, k_ad, prev[arm])
        prev.update(keys)
        est_s += time.perf_counter() - te
        st_t = truth(t)
        arm_key = {**keys, "AD3": k3, "STATIC": "bank:" + static, "ORACLE": "bank:" + st_t}
        x, y = D.sample(st_t, n_eval, seed(t, "eval"))
        seeds_used[f"b{t:02d}:eval"] = seed(t, "eval")
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
        acc = {a: D.acceptable(models[k][1], st_t, classes) for a, k in arm_key.items()}
        blocks.append({"block": t, "state": st_t, "estimate": est, "estimate_ad3": ad2._jsonable(e3),
                       "g_prev": gs.get(t - 1), "seg0": seg0, "L": L, "gfit": {k: round(v, 3) for k, v in gf.items()},
                       "plausible": P, "alarm": alarm, "tracker": snap, "keys": arm_key,
                       "source": {**srcs, "AD3": src}, "acceptable": acc,
                       "burst_action": {a: models[k][1] is not None for a, k in arm_key.items()}, "errors": errs})
        keep = {k for k in models if k.startswith("bank:")} | {ad2.NOMKEY, k_ad, k3} | set(keys.values()) | \
            {v["key"] for v in library.values()}
        decs = {k: v for k, v in decs.items() if k in keep}
        models = {k: v for k, v in models.items() if k in keep}
    (run / "archives").mkdir(parents=True, exist_ok=True)
    arc = run / "archives" / f"{s}_e{e}.npz"
    np.savez_compressed(arc, **bits)
    rec = {"schedule": s, "episode": e, "mode": mode, "params": prm, "states": [truth(t) for t in range(C.BLOCKS)],
           "true_changes": true_ch, "arms": list(C.ARMS), "eval_per_block": n_eval, "seeds": seeds_used,
           "static_key": static, "changes_detected": changes, "g": {str(k): v for k, v in sorted(gs.items())},
           "blocks": blocks, "archive": f"archives/{arc.name}",
           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest(),
           "timing": {"decode_s": round(dec_s, 1), "control_s": round(est_s, 1)},
           "seconds": round(time.perf_counter() - t0, 1)}
    import studykit as SK
    SK.write_once_json(out, ad2._jsonable(rec))
    return out.name


# ------------------------------------------------------------------ fidelity: DB3's record reproduced; W0F = replay
FID_ARMS = ("W0", "DB2", "DB2_PLAN", "BANK", "AD3", "STATIC", "ORACLE", "A_nominal")


def cmd_fidelity():
    run = WORK / "fidelity"
    (run / "records").mkdir(parents=True, exist_ok=False)
    _, s, e = FID
    episode_job(("fidelity", s, e, str(run)))
    mine = json.loads((run / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
    ref = json.loads((C.DB3 / "results" / "dev" / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
    z0, z1 = np.load(C.DB3 / "work" / "dev" / ref["archive"]), np.load(run / mine["archive"])
    by = {b["block"]: b for b in ref["blocks"]}
    res = {"episode": f"DB3 dev {s}_e{e}", "changes_detected": mine["changes_detected"] == ref["changes_detected"],
           "seeds": mine["seeds"] == ref["seeds"], "params": mine["params"] == ref["params"], "blocks": {}}
    for b in mine["blocks"]:
        r = by[b["block"]]
        d = {f: b[f] == r[f] for f in ("plausible", "estimate", "estimate_ad3", "alarm", "tracker", "gfit")}
        for a in FID_ARMS:
            d[f"key_{a}"] = b["keys"].get(a, "nominal") == r["keys"].get(a, "nominal")
            d[f"errors_{a}"] = b["errors"][a] == r["errors"][a]
            d[f"bits_{a}"] = bool(np.array_equal(z0[f"b{b['block']:02d}_{a}"], z1[f"b{b['block']:02d}_{a}"]))
        res["blocks"][b["block"]] = d
    trig = [b["block"] for b in mine["blocks"] if b["source"]["W0F"] == "static_fallback"]
    w0f = sum(b["errors"]["W0F"] for b in mine["blocks"])
    risk = _training()["risk"]
    rp = F.replay(ref, risk, *C.CANDIDATES["W0F"], fallback=True)
    res["W0F"] = {"errors": w0f, "triggers": trig, "expected": FID_W0F,
                  "keys_equal_replay": [b["keys"]["W0F"] for b in mine["blocks"]] == [k for k, _, _ in rp],
                  "errors_equal_replay": [b["errors"]["W0F"] for b in mine["blocks"]] == [x for _, x, _ in rp]}
    w_ok = (w0f == FID_W0F["errors"] and trig == FID_W0F["triggers"] and res["W0F"]["keys_equal_replay"]
            and res["W0F"]["errors_equal_replay"])
    res["all_pass"] = bool(res["changes_detected"] and res["seeds"] and res["params"] and w_ok
                           and all(all(v.values()) for v in res["blocks"].values()))
    import studykit as SK
    SK.write_once_json(C.ROOT / "FIDELITY.json", res)
    print(json.dumps({"all_pass": res["all_pass"], "W0F": res["W0F"]}))


# ------------------------------------------------------------------ development run
def cmd_dev(workers):
    import studykit as SK
    if not SK.tree_clean():
        raise SystemExit("working tree not clean; commit the plan and code first")
    if not json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))["all_pass"]:
        raise SystemExit("fidelity did not pass")
    run = WORK / "dev"
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    (run / "records").mkdir(parents=True, exist_ok=True)
    js = [("dev", s, e, str(run)) for s in C.SCHEDULES for e in range(C.EPISODES[s])]
    js.sort(key=lambda j: j[1] in C.NULL_SCHED)          # dynamic panels first
    status = {"head": SK.git_head(), "workers": workers, "state": "running",
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": {}}
    SK.dump_json(st, status)
    t0 = time.perf_counter()
    try:
        with get_context("spawn").Pool(workers) as pool:
            hs = [(f"{j[1]}_e{j[2]}", pool.apply_async(episode_job, (j,))) for j in js]
            for i, (nm, h) in enumerate(hs, 1):
                h.get(timeout=20_000)
                status["jobs"][nm] = {"returncode": 0}
                print(nm, f"{i}/{len(js)}", f"{time.perf_counter() - t0:.0f}s", flush=True)
        status["state"] = "ready_for_analysis"
    except BaseException as ex:      # noqa: BLE001  (recorded; never retried)
        status["state"], status["error"] = "failed", repr(ex)
        raise
    finally:
        status.update(finished=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      wall_seconds=round(time.perf_counter() - t0, 1), n_jobs=len(js))
        SK.dump_json(st, status)


# ------------------------------------------------------------------ analysis and the pre-declared criteria
PAIRS = (("W0F", "W0"), ("W0F", "STATIC"), ("W0F", "AD3"), ("W0F", "BANK"), ("W0F", "DB2_PLAN"), ("W0F", "DB2"),
         ("W0", "STATIC"), ("BANK", "STATIC"))


def criteria(S):
    """PLAN_DB4.md G1-G6 (errors per episode; 24 = 0.001 LER)."""
    m = lambda s, a: float(np.mean(S[s]["errors_per_episode"][a]))   # noqa: E731
    g4 = {s: m(s, "W0F") - m(s, "STATIC") for s in C.G4_PANELS}
    v = {"G1_W0F_minus_W0": {s: m(s, "W0F") - m(s, "W0") for s in S},
         "G2_W0F_minus_STATIC": {s: m(s, "W0F") - m(s, "STATIC") for s in S},
         "G3_U_W0F_minus_AD3": m("U", "W0F") - m("U", "AD3"),
         "G4_W0F_minus_STATIC": g4, "G4_pooled": float(np.mean(list(g4.values()))),
         "G5_null_switches": {s: S[s]["key_switches_per_episode"]["W0F"] for s in C.NULL_SCHED},
         "G6_AA_W0F_minus_BANK": m("AA", "W0F") - m("AA", "BANK"),
         "G6_AA_episodes_W0F_le_BANK": S["AA"]["W0F_minus_BANK"]["episodes_le_0"]}
    c = {"G1_no_harm_vs_W0_every_panel_le_+2": all(x <= 2 for x in v["G1_W0F_minus_W0"].values()),
         "G2_every_panel_le_STATIC_+12": all(x <= 12 for x in v["G2_W0F_minus_STATIC"].values()),
         "G3_U_minus_AD3_le_+24": v["G3_U_W0F_minus_AD3"] <= 24,
         "G4_each_le_-12_and_pooled_le_-24": all(x <= -12 for x in g4.values()) and v["G4_pooled"] <= -24,
         "G5_null_le_1_switch": all(x <= 1 for xs in v["G5_null_switches"].values() for x in xs),
         "G6_AA_minus_BANK_le_-24_all_episodes": v["G6_AA_W0F_minus_BANK"] <= -24
         and v["G6_AA_episodes_W0F_le_BANK"] == S["AA"]["episodes"]}
    c = {k: bool(x) for k, x in c.items()}
    c["values"] = v
    c["ADVANCE"] = all(x for k, x in c.items() if k.startswith("G"))
    return c


def analyze(run):
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    if len(recs) != st["n_jobs"] or len(recs) != sum(C.EPISODES.values()):
        raise SystemExit("record count does not match jobs")
    for r in recs:
        if hashlib.sha256((run / r["archive"]).read_bytes()).hexdigest() != r["archive_sha256"]:
            raise ValueError("archive hash")
        z = np.load(run / r["archive"])
        for b in r["blocks"]:
            for a in r["arms"]:
                if int(np.unpackbits(z[f"b{b['block']:02d}_{a}"])[: r["eval_per_block"]].sum()) != b["errors"][a]:
                    raise ValueError("count mismatch")
    n_rows = len(C.SCORED) * C.EVAL_PER_BLOCK
    out = {"schema": "qshift-decoder-bank-db4-analysis-v1", "run_status": {k: st.get(k) for k in
           ("head", "started", "finished", "wall_seconds", "n_jobs")}, "schedules": {}, "triggers": []}
    timeline = {"schema": "qshift-decoder-bank-db4-timeline-v1", "blocks": list(C.SCORED), "schedules": {}}
    for s in C.SCHEDULES:
        rr = sorted([r for r in recs if r["schedule"] == s], key=lambda r: r["episode"])
        tot = {a: [sum(b["errors"][a] for b in r["blocks"]) for r in rr] for a in C.ARMS}
        sw = {a: [sum(r["blocks"][i]["keys"][a] != r["blocks"][i - 1]["keys"][a] for i in range(1, len(r["blocks"])))
                  for r in rr] for a in C.BANK_ARMS + ("AD3",)}
        src = {a: {} for a in C.BANK_ARMS}
        for r in rr:
            for b in r["blocks"]:
                for a in src:
                    src[a][b["source"][a]] = src[a].get(b["source"][a], 0) + 1
                if b["source"]["W0F"] == "static_fallback":
                    out["triggers"].append({"episode": f"{s}_e{r['episode']}", "block": b["block"], "state": b["state"],
                                            "flagged": b["estimate"]["flagged"],
                                            "class_index": b["estimate"]["class_index"],
                                            "W0F_key": b["keys"]["W0F"], "W0_key": b["keys"]["W0"],
                                            "errors": {a: b["errors"][a] for a in ("W0F", "W0", "STATIC", "ORACLE")}})
        res = {"episodes": len(rr), "params": [r["params"] for r in rr], "true_changes": [r["true_changes"] for r in rr],
               "changes_detected": [r["changes_detected"] for r in rr],
               "errors": {a: int(sum(v)) for a, v in tot.items()}, "errors_per_episode": tot,
               "ler": {a: float(sum(v) / (len(rr) * n_rows)) for a, v in tot.items()},
               "key_switches_per_episode": sw, "sources": src,
               "empty_P_blocks": sum(not b["plausible"] for r in rr for b in r["blocks"])}
        for a, b in PAIRS:
            d = [x - y for x, y in zip(tot[a], tot[b])]
            res[f"{a}_minus_{b}"] = {"errors_per_episode": d, "mean": float(np.mean(d)),
                                     "ler": float(np.mean(d) / n_rows), "episodes_le_0": int(sum(v <= 0 for v in d))}
        out["schedules"][s] = res
        timeline["schedules"][s] = {
            "state": [[b["state"] for b in r["blocks"]] for r in rr],
            "plausible": [[b["plausible"] for b in r["blocks"]] for r in rr],
            "keys": {a: [[b["keys"][a] for b in r["blocks"]] for r in rr] for a in C.BANK_ARMS},
            "errors": {a: [[b["errors"][a] for b in r["blocks"]] for r in rr] for a in C.ARMS}}
    n_blocks = sum(len(r["blocks"]) for r in recs)
    out["trigger_rate"] = {"triggers": len(out["triggers"]), "blocks": n_blocks}
    out["criteria"] = criteria(out["schedules"])
    return out, timeline


def cmd_analyze(out_dir):
    res, tl = analyze(WORK / "dev")
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    import studykit as SK
    SK.write_once_json(o / "ANALYSIS.json", res)
    SK.write_once_json(o / "TIMELINE.json", tl)
    print(json.dumps({**{k: v for k, v in res["criteria"].items() if k != "values"},
                      "trigger_rate": res["trigger_rate"]}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fidelity", "dev", "analyze"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--workers", type=int, default=8)
    x = ap.parse_args()
    if x.cmd == "fidelity":
        cmd_fidelity()
    elif x.cmd == "dev":
        cmd_dev(x.workers)
    else:
        cmd_analyze(x.path)
