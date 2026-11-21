"""DB1 development validation: causal decoder bank vs AD3, AD and a strong static decoder (PLAN_DB1.md).

  python db_run.py fidelity                 # AD/AD3 re-implementation vs the committed AD3 rehearsal episode S2_e0
  python db_run.py dev [--workers 8]        # the development validation run (fresh DB1 seeds)
  python db_run.py analyze <out_dir>        # ANALYSIS.json + TIMELINE.json (twice -> byte-identical)

Per block t (6-29), every arm decodes the same 1,000 evaluation rows; each arm's model uses only blocks < t.
  AD        AD2's method (ad2.estimate on blocks t-6..t-1; flagged -> nominal)
  AD3       AD3's frozen rule (tau 163.13, M 6, episode library, recall, AD fallback) via ad3's own functions
  BANK      change detection (AD3's G, shared) -> template identification on the segment -> worst-case-risk key
            with hysteresis; unknown -> AD's accepted estimate, else hold
  BANK_ID   ablation: best-fitting plausible template, no risk gate; unknown as BANK
  STATIC    the development-selected single bank key (TRAINING.json)
  ORACLE    the same BP+OSD with block t's true model;  A_nominal  burst-free matching, nominal model
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import db_config as C
import db_core as D

WORK = C.ROOT / "work"


def _seeds():
    return json.loads((C.ROOT / "DB1_SEEDS.json").read_text(encoding="utf-8"))["seeds"]


def _training():
    return json.loads((C.ROOT / "TRAINING.json").read_text(encoding="utf-8"))


def _setup(mode, s, e):
    """-> (truth(t) -> state name, seed(t, part) -> int, n_eval, params)."""
    if mode == "fidelity":
        import ad3_config as A3
        rs = json.loads((C.ADR / "AD3_SEEDS.json").read_text(encoding="utf-8"))["rehearsal_seeds"]
        return (lambda t: A3.block_truth(s, t)[1] or "OFF"), (lambda t, p: int(rs[A3.block_key(s, e, t, p)])), \
            A3.REHEARSAL_EVAL_PER_BLOCK, {}
    sd = _seeds()
    prm = C.episode_params(s, e, int(sd[f"db1:params:{s}:e{e}"]))
    return (lambda t: C.block_state(s, t, prm)), (lambda t, p: int(sd[C.block_key(s, e, t, p)])), C.EVAL_PER_BLOCK, prm


def episode_job(args):
    mode, s, e, run = args
    import ad2
    import ad3
    import mm_contract as K
    import re1
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    run = Path(run)
    out = run / "records" / f"{s}_e{e}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    truth, seed, n_eval, prm = _setup(mode, s, e)
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
    decs, used, seeds_used = {}, set(), {}
    dets, labx, laby, cnt = [], [], [], []
    seg0, changes, gs, library = 0, [], {}, {}
    prev_b = prev_i = "bank:" + static
    blocks, bits = [], {}
    dec_s = est_s = 0.0
    for t in range(C.BLOCKS):
        if t >= 2:                                       # change test for block u = t-1 (AD3's, shared by BANK)
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
        # ---- AD3 (ad3.py's episode_job logic with M = 6: the segment branch never runs)
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
        # ---- BANK and BANK_ID (segment = AD3's segment, at most the last 6 blocks)
        lo = ad3.segment_lo(seg0, t)
        L = t - lo
        kseg, nseg = ad3.pool(cnt[lo:t])
        gf = {st: D.g_fit(kseg, nseg, tpl[st]) for st in C.STATES}
        kb, P = D.bank_decide(gf, L, tau_fit, risk, prev_b.split(":", 1)[1] if prev_b.startswith("bank:") else None)
        src_b = "bank" if kb is not None else ("learn" if not est["flagged"] else "hold")
        kb = "bank:" + kb if kb is not None else (k_ad if not est["flagged"] else prev_b)
        ki, _ = D.id_decide(gf, L, tau_fit)
        src_i = "bank" if ki is not None else ("learn" if not est["flagged"] else "hold")
        ki = "bank:" + ki if ki is not None else (k_ad if not est["flagged"] else prev_i)
        prev_b, prev_i = kb, ki
        est_s += time.perf_counter() - te
        st_t = truth(t)
        k_or = "bank:" + st_t
        arm_key = {"BANK": kb, "BANK_ID": ki, "AD3": k3, "AD": k_ad, "STATIC": "bank:" + static, "ORACLE": k_or}
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
                       "plausible": P, "keys": arm_key, "source": {"BANK": src_b, "BANK_ID": src_i, "AD3": src},
                       "acceptable": acc, "burst_action": {a: models[k][1] is not None for a, k in arm_key.items()},
                       "errors": errs})
        keep = {k for k in models if k.startswith("bank:")} | {ad2.NOMKEY, k_ad, k3, kb, ki} | \
            {v["key"] for v in library.values()}
        decs = {k: v for k, v in decs.items() if k in keep}
        models = {k: v for k, v in models.items() if k in keep}
    (run / "archives").mkdir(parents=True, exist_ok=True)
    arc = run / "archives" / f"{s}_e{e}.npz"
    np.savez_compressed(arc, **bits)
    rec = {"schedule": s, "episode": e, "mode": mode, "params": prm, "states": [truth(t) for t in range(C.BLOCKS)],
           "true_changes": C.changes(s, prm) if mode == "dev" else None, "arms": list(C.ARMS), "eval_per_block": n_eval, "seeds": seeds_used,
           "static_key": static, "changes_detected": changes, "g": {str(k): v for k, v in sorted(gs.items())},
           "blocks": blocks, "archive": f"archives/{arc.name}",
           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest(),
           "timing": {"decode_s": round(dec_s, 1), "control_s": round(est_s, 1)},
           "seconds": round(time.perf_counter() - t0, 1)}
    import ad2 as _a
    import studykit as SK
    SK.write_once_json(out, _a._jsonable(rec))
    return out.name


# ------------------------------------------------------------------ fidelity: AD/AD3 vs the committed rehearsal
def cmd_fidelity():
    run = WORK / "fidelity"
    (run / "records").mkdir(parents=True, exist_ok=False)
    episode_job(("fidelity", "S2", 0, str(run)))
    mine = json.loads((run / "records" / "S2_e0.json").read_text(encoding="utf-8"))
    ref = json.loads((C.ADR / "work" / "ad3" / "rehearsal" / "records" / "S2_e0.json").read_text(encoding="utf-8"))
    z0, z1 = np.load(C.ADR / "work" / "ad3" / "rehearsal" / ref["archive"]), np.load(run / mine["archive"])
    by = {b["block"]: b for b in ref["blocks"]}
    res = {"changes_detected": mine["changes_detected"] == ref["changes_detected"], "blocks": {}}
    for b in mine["blocks"]:
        r = by[b["block"]]
        res["blocks"][b["block"]] = {
            "errors_AD": b["errors"]["AD"] == r["errors"]["AD"], "errors_AD3": b["errors"]["AD3"] == r["errors"]["AD3"],
            "estimate": b["estimate"] == r["estimate"], "estimate_ad3": b["estimate_ad3"] == r["estimate_ad3"],
            "bits_AD": bool(np.array_equal(z0[f"b{b['block']:02d}_AD"], z1[f"b{b['block']:02d}_AD"])),
            "bits_AD3": bool(np.array_equal(z0[f"b{b['block']:02d}_AD3"], z1[f"b{b['block']:02d}_AD3"]))}
    res["all_pass"] = bool(res["changes_detected"] and all(all(v.values()) for v in res["blocks"].values()))
    import studykit as SK
    SK.write_once_json(C.ROOT / "FIDELITY.json", res)
    print(json.dumps({"all_pass": res["all_pass"], "changes": res["changes_detected"]}))


# ------------------------------------------------------------------ development run
def cmd_dev(workers):
    import studykit as SK
    if not SK.tree_clean():
        raise SystemExit("working tree not clean; commit the plan and code first")
    run = WORK / "dev"
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    (run / "records").mkdir(parents=True, exist_ok=True)
    js = [("dev", s, e, str(run)) for s in C.SCHEDULES for e in range(C.EPISODES[s])]
    status = {"head": SK.git_head(), "workers": workers, "state": "running",
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": {}}
    SK.dump_json(st, status)
    t0 = time.perf_counter()
    try:
        with get_context("spawn").Pool(workers) as pool:
            hs = [(f"{j[1]}_e{j[2]}", pool.apply_async(episode_job, (j,))) for j in js]
            for i, (nm, h) in enumerate(hs, 1):
                h.get(timeout=12_000)
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


# ------------------------------------------------------------------ analysis
EVENT_ARMS = ("BANK", "BANK_ID", "AD3", "AD", "STATIC")


def event_type(prev, new, seen):
    if new == "E":
        return "unknown_onset"
    if new == "OFF":
        return "off"
    if prev == "OFF":
        return "recurrent_on" if new in seen else "first_on"
    return "relocation"


def events(r):
    """Per true change: type and, per arm, delay to the first scored block in its own segment with an acceptable
    key (None if none before the next change)."""
    by = {b["block"]: b for b in r["blocks"]}
    st, ch, out = r["states"], r["true_changes"], []
    for i, c in enumerate(ch):
        end = ch[i + 1] if i + 1 < len(ch) else C.BLOCKS
        seen = {st[t] for t in range(c) if st[t] != "OFF"}
        ev = {"change": c, "type": event_type(st[c - 1], st[c], seen), "from": st[c - 1], "to": st[c], "delay": {}}
        for a in EVENT_ARMS:
            ev["delay"][a] = next((b - c for b in range(max(c, C.WINDOW), end) if by[b]["acceptable"][a]), None)
        out.append(ev)
    return out


def analyze(run):
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    if len(recs) != st["n_jobs"]:
        raise SystemExit("record count != jobs")
    for r in recs:
        if hashlib.sha256((run / r["archive"]).read_bytes()).hexdigest() != r["archive_sha256"]:
            raise ValueError("archive hash")
        z = np.load(run / r["archive"])
        for b in r["blocks"]:
            for a in r["arms"]:
                if int(np.unpackbits(z[f"b{b['block']:02d}_{a}"])[: r["eval_per_block"]].sum()) != b["errors"][a]:
                    raise ValueError("count mismatch")
    bseed = int.from_bytes(hashlib.sha256(C.BOOT_SEED_LABEL.encode()).digest()[:8], "big")
    out = {"schema": "qshift-decoder-bank-db1-analysis-v1", "run_status": {k: st.get(k) for k in
           ("head", "started", "finished", "wall_seconds", "n_jobs")}, "schedules": {}, "events": {}, "criteria": {}}
    timeline = {"schema": "qshift-decoder-bank-db1-timeline-v1", "blocks": list(C.SCORED), "schedules": {}}
    T = list(C.SCORED)
    for si, s in enumerate(C.SCHEDULES):
        rr = sorted([r for r in recs if r["schedule"] == s], key=lambda r: r["episode"])
        n = rr[0]["eval_per_block"]
        tot = {a: [sum(b["errors"][a] for b in r["blocks"]) for r in rr] for a in C.ARMS}
        rng = np.random.default_rng(bseed + si)
        idx = rng.integers(0, len(rr), size=(C.BOOT_REPS, len(rr)))

        def diff(a, b):
            d = np.array(tot[a], float) - np.array(tot[b], float)
            per = d / (len(T) * n)
            bs = d[idx].sum(axis=1) / (len(rr) * len(T) * n)
            return {"estimate": float(per.mean()), "per_episode": [float(v) for v in per],
                    "upper_97_5": float(np.quantile(bs, 0.975)), "episodes_le_0": int((d <= 0).sum()),
                    "episodes": len(rr)}

        switches = {a: [sum(r["blocks"][i]["keys"][a] != r["blocks"][i - 1]["keys"][a] for i in range(1, len(r["blocks"])))
                        for r in rr] for a in ("BANK", "BANK_ID", "AD3", "AD")}
        wrong = {a: sum(b["burst_action"][a] and not b["acceptable"][a] for r in rr for b in r["blocks"])
                 for a in EVENT_ARMS}
        src = {a: {} for a in ("BANK", "BANK_ID", "AD3")}
        for r in rr:
            for b in r["blocks"]:
                for a in src:
                    src[a][b["source"][a]] = src[a].get(b["source"][a], 0) + 1
        evs = [ev for r in rr for ev in (events(r) if r["true_changes"] else [])]
        out["schedules"][s] = {
            "episodes": len(rr), "params": [r["params"] for r in rr], "eval_per_block": n,
            "errors": {a: int(sum(v)) for a, v in tot.items()}, "errors_per_episode": tot,
            "ler": {a: float(sum(v) / (len(rr) * len(T) * n)) for a, v in tot.items()},
            "BANK_minus_AD3": diff("BANK", "AD3"), "BANK_minus_STATIC": diff("BANK", "STATIC"),
            "BANK_minus_AD": diff("BANK", "AD"), "BANK_ID_minus_AD3": diff("BANK_ID", "AD3"),
            "BANK_minus_BANK_ID": diff("BANK", "BANK_ID"), "AD3_minus_AD": diff("AD3", "AD"),
            "STATIC_minus_AD3": diff("STATIC", "AD3"),
            "key_switches_per_episode": switches, "wrong_bank_burst_blocks": wrong, "sources": src,
            "changes_detected": [r["changes_detected"] for r in rr], "true_changes": [r["true_changes"] for r in rr]}
        out["events"][s] = evs
        timeline["schedules"][s] = {
            "state": [[b["state"] for b in r["blocks"]] for r in rr],
            "arms": {a: {"ler_mean": [float(np.mean([r["blocks"][i]["errors"][a] / n for r in rr])) for i in range(len(T))]}
                     for a in C.ARMS},
            "acceptable_fraction": {a: [float(np.mean([r["blocks"][i]["acceptable"][a] for r in rr]))
                                        for i in range(len(T))] for a in EVENT_ARMS}}
    out["event_summary"] = _event_summary(out["events"])
    out["criteria"] = _criteria(out)
    return out, timeline


def _event_summary(evs):
    res = {}
    for s, el in evs.items():
        for ev in el:
            for a, d in ev["delay"].items():
                t = res.setdefault(ev["type"], {}).setdefault(a, {"n": 0, "timely_le1": 0, "le2": 0, "missed": 0,
                                                                  "delays": []})
                t["n"] += 1
                t["delays"].append(d)
                t["timely_le1"] += int(d is not None and d <= 1)
                t["le2"] += int(d is not None and d <= 2)
                t["missed"] += int(d is None)
    return res


def _criteria(out):
    S = out["schedules"]
    ev = out["event_summary"]
    rec = ev.get("recurrent_on", {})
    tf = lambda a: rec[a]["timely_le1"] / rec[a]["n"] if rec.get(a, {}).get("n") else None   # noqa: E731
    null_static = sum(S[s]["errors"]["BANK"] - S[s]["errors"]["STATIC"] for s in C.STATIC_SCHED) / \
        sum(S[s]["episodes"] * len(C.SCORED) * S[s]["eval_per_block"] for s in C.STATIC_SCHED)
    c = {
        "D1_R_BANK_minus_AD3_le_-0.001": S["R"]["BANK_minus_AD3"]["estimate"] <= -0.001
        and S["R"]["BANK_minus_AD3"]["episodes_le_0"] == S["R"]["episodes"],
        "D2_R_BANK_minus_STATIC_le_-0.001": S["R"]["BANK_minus_STATIC"]["estimate"] <= -0.001,
        "D3_null_BANK_minus_STATIC_le_+0.0005": null_static <= 0.0005,
        "D3_null_zero_BANK_switches": all(v == 0 for s in C.STATIC_SCHED for v in S[s]["key_switches_per_episode"]["BANK"]),
        "D4_recurrent_on_timely_gain_ge_0.20": (tf("BANK") is not None and tf("AD3") is not None
                                                and tf("BANK") - tf("AD3") >= 0.20),
        "D5_U_BANK_minus_AD3_le_+0.001": S["U"]["BANK_minus_AD3"]["estimate"] <= 0.001,
        "D6_S1_S4_BANK_minus_AD3_le_0": all(S[s]["BANK_minus_AD3"]["estimate"] <= 0 for s in ("S1", "S4"))}
    c = {k: bool(v) for k, v in c.items()}
    c["null_BANK_minus_STATIC_ler"] = null_static
    c["recurrent_on_timely"] = {a: tf(a) for a in EVENT_ARMS}
    c["ADVANCE"] = all(v for k, v in c.items() if k.startswith("D"))
    return c


def cmd_analyze(out_dir):
    res, tl = analyze(WORK / "dev")
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    import studykit as SK
    SK.write_once_json(o / "ANALYSIS.json", res)
    SK.write_once_json(o / "TIMELINE.json", tl)
    print(json.dumps(res["criteria"], indent=1))


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
