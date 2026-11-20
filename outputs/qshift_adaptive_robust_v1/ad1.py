"""AD1 adaptive decoding under drifting noise (PLAN_AD1.md, AD1_PROTOCOL.md).

  python ad1.py run <eval|rehearsal> --expected-head <sha> [--workers 8]
  python ad1.py analyze <eval|rehearsal> <out_dir>
  python ad1.py recount <eval|rehearsal> <analysis.json>

One job = one episode of 24 blocks. For each scored block t (6-23) the AD arm estimates on the window of blocks
t-6..t-1 only (E1T -> Phase C learner + flip -> BP+OSD on the estimated model; flagged -> nominal, no burst); ONCE
is AD's block-6 estimate, frozen; ORACLE decodes with block t's true model and support. All arms decode the same
evaluation shots. Write-once records under work/ad1/<mode>/ (git-ignored). RUN_STATUS.json refuses a relaunch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import ad1_config as C
import ad1_stream as ST

D = C.D
ROOT = C.ROOT
WORK = ROOT / "work" / "ad1"


def git(*a):
    return subprocess.run(["git", *a], cwd=D.REPO, capture_output=True, text=True).stdout.strip()


def verify_freeze(head):
    if git("rev-parse", "HEAD") != head:
        raise SystemExit("HEAD != --expected-head")
    fz = json.loads((ROOT / "AD1_FREEZE.json").read_text(encoding="utf-8"))
    for rel, h in fz["files"].items():
        if hashlib.sha256((D.REPO / rel).read_bytes()).hexdigest() != h:
            raise SystemExit(f"freeze hash mismatch: {rel}")


def seed(mode, key):
    s = json.loads((ROOT / "AD1_SEEDS.json").read_text(encoding="utf-8"))
    return int((s["rehearsal_seeds"] if mode == "rehearsal" else s["seeds"])[key])


def estimate_window(dets, labx, laby, classes, truth_support):
    """E1T on one window -> (model spec, support or None, record). Detector rows and the window's labels only."""
    import brt
    import estimate3 as E3
    import estimate4 as E4
    import estimate5 as E5
    import mm_contract as K
    xu = np.vstack(dets)
    obs, n = E3.rates_from_rows(xu)
    f = E4.e1_with_set(obs, n)
    truth = K.B.truth(classes, tuple(truth_support)) if truth_support else (None, None)
    lr = brt.learn(brt.zspec(f["p_hat"], f["b_hat"]), xu, classes, truth, np.vstack(labx), np.concatenate(laby))
    st = E4.structural_flags(f["excluded_set"], lr["class_index"])
    flagged = E5.e1t_flag(f, st)
    rec = {"p_hat": f["p_hat"], "b_hat": f["b_hat"], "excluded": f["excluded"], "flagged": flagged,
           "S1": st["S1_shape"], "S2": st["S2_consistency"], "class_index": lr["class_index"], "flip": lr["flip"],
           "true_class": truth[0], "learned_correct": lr["learned_correct"] and not flagged}
    if flagged:
        return C.spec(**C.NOMINAL), None, rec
    return brt.zspec(f["p_hat"], f["b_hat"]), lr["support"], rec


def episode_job(args):
    mode, s, e, head, run, n_eval = args
    if mode == "eval":
        verify_freeze(head)
    import mm_contract as K
    import re1
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    name = f"{s}_e{e}"
    out = run / "records" / f"{name}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    t0 = time.perf_counter()
    classes = K.B.load_classes()
    used, dets, labx, laby = {}, [], [], []
    a_nom = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(C.spec(**C.NOMINAL))))
    oracle_cache, once, blocks, bits = {}, None, [], {}
    for t in range(C.BLOCKS):
        kw, sup = ST.block_truth(s, t)
        for part, nrow in (("det", C.DET_PER_BLOCK), ("lab", C.LAB_PER_BLOCK)):
            key = C.block_key(s, e, t, part)
            used[key] = seed(mode, key)
            x, y = ST.sample_block(s, t, nrow, used[key])
            (dets if part == "det" else labx).append(x)
            if part == "lab":
                laby.append(y)
        if t < C.WINDOW:
            continue
        w0 = t - C.WINDOW                                   # causal window: blocks w0 .. t-1
        win_sup = next((ST.block_truth(s, u)[1] for u in range(w0, t) if ST.block_truth(s, u)[1]), None)
        model, est_sup, est = estimate_window(dets[w0:t], labx[w0:t], laby[w0:t], classes, win_sup)
        ad_l2, ad_m = re1.decoders(model, est_sup)
        if once is None:
            once = (ad_l2, est)
        okey = json.dumps([kw, sup], sort_keys=True)
        if okey not in oracle_cache:
            oracle_cache[okey] = re1.decoders(C.spec(**kw), sup)[0]
        key = C.block_key(s, e, t, "eval")
        used[key] = seed(mode, key)
        x, y = ST.sample_block(s, t, n_eval, used[key])
        dec = {"AD": (ad_l2, "l2"), "ONCE": (once[0], "l2"), "ORACLE": (oracle_cache[okey], "l2"),
               "AD_M": (ad_m, "corr"), "A_nominal": (a_nom, "plain")}
        errs = {}
        for a, (d, kind) in dec.items():
            err = re1.predict(d, x, kind) != y
            errs[a] = int(err.sum())
            bits[f"b{t:02d}_{a}"] = np.packbits(err)
        blocks.append({"block": t, "true": kw, "burst_on": sup is not None, "window_burst": win_sup is not None,
                       "estimate": est, "errors": errs})
    arc = run / "archives" / f"{name}.npz"
    np.savez_compressed(arc, **bits)
    rec = {"schedule": s, "episode": e, "seeds": used, "eval_per_block": n_eval, "once_estimate": once[1],
           "blocks": blocks, "archive": f"archives/{arc.name}",
           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest(), "seconds": round(time.perf_counter() - t0, 1)}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out.name


def plan_jobs(mode, head, run):
    if mode == "rehearsal":
        return [(mode, s, e, head, run, C.REHEARSAL_EVAL_PER_BLOCK) for s, e in C.REHEARSAL]
    return [(mode, s, e, head, run, C.EVAL_PER_BLOCK) for s in C.SCHEDULES for e in range(C.EPISODES)]


def cmd_run(mode, head, workers):
    if mode == "eval":
        if git("status", "--porcelain"):
            raise SystemExit("working tree not clean")
        verify_freeze(head)
    run = WORK / mode
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    for d in ("records", "archives"):
        (run / d).mkdir(parents=True, exist_ok=True)
    js = plan_jobs(mode, head, run)
    status = {"mode": mode, "head": git("rev-parse", "HEAD"), "expected_head": head, "workers": workers,
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "state": "running", "jobs": 0}
    st.write_text(json.dumps(status, indent=2), encoding="utf-8")
    t0 = time.perf_counter()
    try:
        with get_context("spawn").Pool(workers) as pool:
            hs = [pool.apply_async(episode_job, (j,)) for j in js]
            for i, h in enumerate(hs, 1):
                name = h.get(timeout=C.JOB_TIMEOUT_S + 600)
                status["jobs"] = i
                print(name, f"{i}/{len(js)}", f"{time.perf_counter() - t0:.0f}s", flush=True)
        status["state"] = "ready_for_analysis"
    except BaseException as ex:      # noqa: BLE001  (recorded; never retried)
        status["state"], status["error"] = "failed", repr(ex)
        raise
    finally:
        status["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status["wall_seconds"] = round(time.perf_counter() - t0, 1)
        status["n_jobs"] = len(js)
        st.write_text(json.dumps(status, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ analysis
def _load(run):
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    for r in recs:
        p = run / r["archive"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != r["archive_sha256"]:
            raise ValueError(f"archive hash mismatch {p.name}")
        z = np.load(p)
        for b in r["blocks"]:
            for a in C.ARMS:
                if int(np.unpackbits(z[f"b{b['block']:02d}_{a}"])[: r["eval_per_block"]].sum()) != b["errors"][a]:
                    raise ValueError("recorded count mismatch")
    return recs


def _latency(r, start, cond):
    for b in r["blocks"]:
        if b["block"] >= start and cond(b):
            return b["block"] - start
    return None


def analyze(mode, run):
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs = _load(run)
    seeds = json.loads((ROOT / "AD1_SEEDS.json").read_text(encoding="utf-8"))
    pool = seeds["rehearsal_seeds"] if mode == "rehearsal" else seeds["seeds"]
    for r in recs:
        for k, v in r["seeds"].items():
            if pool[k] != v:
                raise ValueError("seed mismatch")
    if mode == "eval" and len(recs) != st["n_jobs"]:
        raise SystemExit("record count != jobs")
    bseed = int.from_bytes(hashlib.sha256(C.BOOT_SEED_LABEL.encode()).digest()[:8], "big")
    out = {"schema": "qshift-adaptive-robust-ad1-analysis-v1", "mode": mode, "schedules": {}, "endpoints": {}}
    for s in C.SCHEDULES:
        rr = sorted([r for r in recs if r["schedule"] == s], key=lambda r: r["episode"])
        if not rr:
            continue
        n_shots = sum(r["eval_per_block"] * len(r["blocks"]) for r in rr)
        per_ep = {a: np.array([sum(b["errors"][a] for b in r["blocks"]) for r in rr]) for a in C.ARMS}
        ep_shots = np.array([r["eval_per_block"] * len(r["blocks"]) for r in rr])
        ler = {a: float(per_ep[a].sum() / n_shots) for a in C.ARMS}
        rng = np.random.default_rng(bseed + list(C.SCHEDULES).index(s))
        idx = rng.integers(0, len(rr), size=(C.BOOT_REPS, len(rr)))
        bl = lambda a: per_ep[a][idx].sum(axis=1) / ep_shots[idx].sum(axis=1)   # noqa: E731
        d_once = bl("AD") - bl("ONCE")
        d_or = bl("AD") - bl("ORACLE")
        excess = (ler["AD"] - ler["ORACLE"]) / ler["ORACLE"] if ler["ORACLE"] else None
        settled = lambda t: len({ST.block_truth(s, u)[1] is not None for u in range(t - C.WINDOW, t)}) == 1   # noqa: E731
        flags = [sum(b["estimate"]["flagged"] for b in r["blocks"] if settled(b["block"])) for r in rr]
        tflags = [sum(b["estimate"]["flagged"] for b in r["blocks"] if not settled(b["block"])) for r in rr]
        mis = sum(1 for r in rr for b in r["blocks"]
                  if b["estimate"]["class_index"] is not None and not b["estimate"]["flagged"]
                  and b["estimate"]["class_index"] != b["estimate"]["true_class"])
        row = {"episodes": len(rr), "scored_shots_per_arm": n_shots, "errors": {a: int(per_ep[a].sum()) for a in C.ARMS},
               "ler": ler, "AD_excess_over_ORACLE": excess,
               "AD_minus_ORACLE_95ci": [float(np.quantile(d_or, 0.025)), float(np.quantile(d_or, 0.975))],
               "AD_minus_ONCE": {"estimate": ler["AD"] - ler["ONCE"], "upper_97_5": float(np.quantile(d_once, 0.975)),
                                 "95ci": [float(np.quantile(d_once, 0.025)), float(np.quantile(d_once, 0.975))]},
               "R_AD_vs_AD_M": (1 - ler["AD"] / ler["AD_M"]) if ler["AD_M"] else None,
               "flagged_settled_windows_per_episode": flags, "flagged_transition_windows_per_episode": tflags,
               "mislearned_windows": mis,
               "learned_exactly_windows": sum(b["estimate"]["learned_correct"] for r in rr for b in r["blocks"]),
               "windows": sum(len(r["blocks"]) for r in rr),
               "per_block_ler": {a: [float(sum(next(b for b in r["blocks"] if b["block"] == t)["errors"][a] for r in rr)
                                         / sum(r["eval_per_block"] for r in rr)) for t in C.SCORED] for a in C.ARMS},
               "per_block_p_hat": [float(np.mean([next(b for b in r["blocks"] if b["block"] == t)["estimate"]["p_hat"]
                                                  for r in rr])) for t in C.SCORED],
               "per_block_b_hat": [float(np.mean([next(b for b in r["blocks"] if b["block"] == t)["estimate"]["b_hat"]
                                                  for r in rr])) for t in C.SCORED]}
        if s == "D3":
            on = [_latency(r, C.ONSET, lambda b: b["estimate"]["learned_correct"]) for r in rr]
            off = [_latency(r, C.OFFSET, lambda b: b["estimate"]["class_index"] is None or b["estimate"]["flagged"])
                   for r in rr]
            row["onset_latency"] = on
            row["offset_latency"] = off
            off_blocks = [b for r in rr for b in r["blocks"] if b["block"] >= C.OFFSET]
            row["off_segment_errors"] = {a: sum(b["errors"][a] for b in off_blocks) for a in C.ARMS}
        out["schedules"][s] = row
    S = out["schedules"]
    E = {}
    med = lambda v: float(np.median([x if x is not None else 99 for x in v]))   # noqa: E731
    for s in C.TRACKING:
        if s in S:
            E[f"tracking_{s}"] = bool(S[s]["AD_excess_over_ORACLE"] is not None and
                                      S[s]["AD_excess_over_ORACLE"] <= C.TRACK_EXCESS_MAX and
                                      S[s]["AD_minus_ONCE"]["upper_97_5"] < 0)
    if "C0" in S:
        E["no_harm_C0"] = S["C0"]["errors"]["AD"] <= C.NO_HARM_FACTOR * S["C0"]["errors"]["ONCE"] + C.NO_HARM_SLACK
    if "D3" in S:
        E["burst_onset_D3"] = med(S["D3"]["onset_latency"]) <= C.ONSET_MAX and S["D3"]["mislearned_windows"] == 0
        E["burst_offset_D3"] = med(S["D3"]["offset_latency"]) <= C.OFFSET_MAX
    E["flags_settled"] = all(max(S[s]["flagged_settled_windows_per_episode"]) <= C.MAX_FLAGGED_WINDOWS_PER_EPISODE
                             for s in S)
    out["endpoints"] = E
    tr = [E[k] for k in E if k.startswith("tracking_")]
    out["verdict"] = ("AD1_SUPPORTED" if E and all(E.values()) and len(tr) == len(C.TRACKING) else
                      "AD1_PARTIAL" if sum(tr) >= 2 and E.get("no_harm_C0") else "AD1_NOT_SUPPORTED")
    out["run_status"] = {k: st.get(k) for k in ("head", "started", "finished", "wall_seconds", "n_jobs")}
    return out


def cmd_analyze(mode, out_dir):
    res = analyze(mode, WORK / mode)
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    (o / "ANALYSIS.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": res["verdict"], **res["endpoints"]}))


def cmd_recount(mode, analysis_path):
    """Re-derive the analysis; re-run episode 0 of every schedule into a replay dir (records and bits identical)."""
    run = WORK / mode
    a = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    same = json.dumps(analyze(mode, run), sort_keys=True) == json.dumps(a, sort_keys=True)
    tmp = WORK / f"{mode}_replay"
    if tmp.exists():
        raise SystemExit(f"{tmp.name} exists; replay runs once")
    for d in ("records", "archives"):
        (tmp / d).mkdir(parents=True)
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    n = C.REHEARSAL_EVAL_PER_BLOCK if mode == "rehearsal" else C.EVAL_PER_BLOCK
    rm = "rehearsal" if mode == "rehearsal" else "replay"
    picks = [(rm, s, e, st["head"], tmp, n) for s, e in ([(s, 0) for s in C.SCHEDULES] if mode == "eval" else C.REHEARSAL)]
    with get_context("spawn").Pool(min(8, len(picks))) as pool:
        names = pool.map(episode_job, picks)
    ident = {}
    for nm in names:
        r0 = json.loads((run / "records" / nm).read_text(encoding="utf-8"))
        r1 = json.loads((tmp / "records" / nm).read_text(encoding="utf-8"))
        r0.pop("seconds"), r1.pop("seconds")
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
