"""DB3 tiebreak run: W0 vs DB2_PLAN vs DB2 on fresh seeds (PLAN_DB3.md). Development only.

  python db3_run.py fidelity                # DB2 dev episode RB_e1 re-run: every DB2 arm must match DB2's record
  python db3_run.py dev [--workers 8]       # the tiebreak run (fresh DB3 seeds)
  python db3_run.py analyze <out_dir>       # ANALYSIS.json + TIMELINE.json (twice -> byte-identical)

Per block t (6-29) every arm decodes the same 1,000 evaluation rows; each arm's choice uses only blocks < t.
  W0        DB2's gate, worst-case next state, kappa 0
  DB2_PLAN  DB2's gate as first approved (worst case, kappa 0.0005)
  DB2       DB2's amended gate (hybrid, kappa 0)
  BANK      DB1's rule, unchanged; AD3, STATIC (key A), ORACLE, A_nominal as in DB1/DB2
The per-block loop is DB2's episode_job with the W0 arm added (fidelity-checked against DB2's stored record).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import db3_config as C  # noqa: I001  (puts DB2, DB1 and AD2/AD3 on sys.path first)
import db2_core as G  # noqa: E402
import db3_core as K  # noqa: E402

WORK = C.ROOT / "work"
FID = ("DB2", "RB", 1)


def _training():
    return json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))


def _setup(mode, s, e):
    """-> (truth(t), seed(t, part), n_eval, params, true_changes)."""
    if mode == "fidelity":
        C2 = C.C2
        sd = json.loads((C.DB2 / "DB2_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
        prm = C2.episode_params(s, e, int(sd[f"db2:params:{s}:e{e}"]))
        return (lambda t: C2.block_state(s, t, prm)), (lambda t, p: int(sd[C2.block_key(s, e, t, p)])),             C.EVAL_PER_BLOCK, prm, C2.changes(s, prm)
    sd = json.loads((C.ROOT / "DB3_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    prm = C.episode_params(s, e, int(sd[f"db3:params:{s}:e{e}"]))
    return (lambda t: C.block_state(s, t, prm)), (lambda t, p: int(sd[C.block_key(s, e, t, p)])),         C.EVAL_PER_BLOCK, prm, C.changes(s, prm)


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
            keys[arm], srcs[arm] = _bank_arm(kn, est, k_ad, prev[arm])
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


# ------------------------------------------------------------------ fidelity: DB2's record reproduced
FID_ARMS = ("DB2", "DB2_PLAN", "BANK", "AD3", "STATIC", "ORACLE", "A_nominal")


def cmd_fidelity():
    run = WORK / "fidelity"
    (run / "records").mkdir(parents=True, exist_ok=False)
    _, s, e = FID
    episode_job(("fidelity", s, e, str(run)))
    mine = json.loads((run / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
    ref = json.loads((C.DB2 / "results" / "dev" / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
    z0, z1 = np.load(C.DB2 / "work" / "dev" / ref["archive"]), np.load(run / mine["archive"])
    by = {b["block"]: b for b in ref["blocks"]}
    res = {"episode": f"DB2 dev {s}_e{e}", "changes_detected": mine["changes_detected"] == ref["changes_detected"],
           "seeds": mine["seeds"] == ref["seeds"], "params": mine["params"] == ref["params"], "blocks": {}}
    for b in mine["blocks"]:
        r = by[b["block"]]
        d = {f: b[f] == r[f] for f in ("plausible", "estimate", "estimate_ad3", "alarm", "tracker", "gfit")}
        for a in FID_ARMS:
            d[f"key_{a}"] = b["keys"].get(a, "nominal") == r["keys"].get(a, "nominal")
            d[f"errors_{a}"] = b["errors"][a] == r["errors"][a]
            d[f"bits_{a}"] = bool(np.array_equal(z0[f"b{b['block']:02d}_{a}"], z1[f"b{b['block']:02d}_{a}"]))
        res["blocks"][b["block"]] = d
    res["all_pass"] = bool(res["changes_detected"] and res["seeds"] and res["params"]
                           and all(all(v.values()) for v in res["blocks"].values()))
    import studykit as SK
    SK.write_once_json(C.ROOT / "FIDELITY.json", res)
    print(json.dumps({"all_pass": res["all_pass"], "changes": res["changes_detected"], "seeds": res["seeds"]}))


# ------------------------------------------------------------------ tiebreak run
def cmd_dev(workers):
    import studykit as SK
    if not SK.tree_clean():
        raise SystemExit("working tree not clean; commit the plan and code first")
    if not json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))["all_pass"]:
        raise SystemExit("fidelity did not pass")
    if not (C.ROOT / "W0_REPLAY.json").exists():
        raise SystemExit("W0_REPLAY.json (E3) must be committed before the run")
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


# ------------------------------------------------------------------ analysis and the pre-declared selection
CANDS = tuple(C.CANDIDATES)
PAIRS = (("DB2", "DB2_PLAN"), ("W0", "DB2_PLAN"), ("W0", "DB2"), ("W0", "STATIC"), ("DB2", "STATIC"),
         ("DB2_PLAN", "STATIC"), ("W0", "BANK"), ("DB2", "BANK"), ("DB2_PLAN", "BANK"))


def selection(S, e3):
    """PLAN_DB3.md: score = sum over panels of mean errors per episode; E1, E2, E3; simplicity tie-break."""
    mean = {s: {a: float(np.mean(S[s]["errors_per_episode"][a])) for a in C.ARMS} for s in S}
    score = {c: sum(mean[s][c] for s in S) for c in CANDS}
    e1 = {c: all(v <= 1 for s in C.NULL_SCHED for v in S[s]["key_switches_per_episode"][c]) for c in CANDS}
    e2 = {c: all(mean[s][c] <= mean[s]["STATIC"] + C.MARGIN for s in S) for c in CANDS}
    elig = {c: bool(e1[c] and e2[c] and e3[c]) for c in CANDS}
    regret = {c: {s: mean[s][c] - min(mean[s][x] for x in CANDS) for s in S} for c in CANDS}
    return {"score": score, "E1_null_le_1_switch": e1, "E2_within_12_of_STATIC_every_panel": e2,
            "E3_F1_F6_on_DB2_records": e3, "eligible": elig, "chosen": K.select(score, elig),
            "worst_panel_regret": {c: max(v.values()) for c, v in regret.items()}, "regret": regret,
            "mean_errors_per_episode": mean,
            "DB2_minus_DB2_PLAN_per_panel": {s: mean[s]["DB2"] - mean[s]["DB2_PLAN"] for s in S}}


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
    out = {"schema": "qshift-decoder-bank-db3-analysis-v1", "run_status": {k: st.get(k) for k in
           ("head", "started", "finished", "wall_seconds", "n_jobs")}, "schedules": {}}
    timeline = {"schema": "qshift-decoder-bank-db3-timeline-v1", "blocks": list(C.SCORED), "schedules": {}}
    for s in C.SCHEDULES:
        rr = sorted([r for r in recs if r["schedule"] == s], key=lambda r: r["episode"])
        tot = {a: [sum(b["errors"][a] for b in r["blocks"]) for r in rr] for a in C.ARMS}
        sw = {a: [sum(r["blocks"][i]["keys"][a] != r["blocks"][i - 1]["keys"][a] for i in range(1, len(r["blocks"])))
                  for r in rr] for a in C.BANK_ARMS + ("AD3",)}
        held = {a: {"blocks": sum(b["state"] == "OFF" and b["keys"][a] == "bank:A" for r in rr for b in r["blocks"]),
                    "extra_errors_vs_ORACLE": sum(b["errors"][a] - b["errors"]["ORACLE"] for r in rr for b in r["blocks"]
                                                  if b["state"] == "OFF" and b["keys"][a] == "bank:A")}
                for a in C.BANK_ARMS}
        src = {a: {} for a in C.BANK_ARMS}
        for r in rr:
            for b in r["blocks"]:
                for a in src:
                    src[a][b["source"][a]] = src[a].get(b["source"][a], 0) + 1
        res = {"episodes": len(rr), "params": [r["params"] for r in rr], "true_changes": [r["true_changes"] for r in rr],
               "changes_detected": [r["changes_detected"] for r in rr],
               "errors": {a: int(sum(v)) for a, v in tot.items()}, "errors_per_episode": tot,
               "ler": {a: float(sum(v) / (len(rr) * n_rows)) for a, v in tot.items()},
               "key_switches_per_episode": sw, "held_A_on_OFF": held, "sources": src}
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
    e3 = json.loads((C.ROOT / "W0_REPLAY.json").read_text(encoding="utf-8"))["E3"]
    out["selection"] = selection(out["schedules"], e3)
    return out, timeline


def cmd_analyze(out_dir):
    res, tl = analyze(WORK / "dev")
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    import studykit as SK
    SK.write_once_json(o / "ANALYSIS.json", res)
    SK.write_once_json(o / "TIMELINE.json", tl)
    sel = res["selection"]
    print(json.dumps({k: sel[k] for k in ("score", "eligible", "chosen", "worst_panel_regret",
                                          "DB2_minus_DB2_PLAN_per_panel")}, indent=1))


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
