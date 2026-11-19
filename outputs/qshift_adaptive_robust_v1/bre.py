"""BRE-1 burst-robust estimation development study (PLAN_BRE.md, BRE_PROTOCOL.md).

  python bre.py run <eval|rehearsal> --expected-head <sha> [--workers 8]
  python bre.py analyze <eval|rehearsal> <out_dir>
  python bre.py recount <eval|rehearsal> <analysis.json>

Each job samples one calibration pool and records every arm's fit statistics and every learner outcome the arms can
need (nominal, on the B2 fit, on the E1 fit, on the E2 refit). Flags, thresholds and the on-flag policies are applied
in the analysis, with thresholds set on the tuning (T) pools only, so each pool is sampled and learned once.
Write-once records under work/bre/<mode>/ (git-ignored). RUN_STATUS.json refuses a relaunch.
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

import bre_config as C

D = C.D
ROOT = D.ROOT
WORK = ROOT / "work" / "bre"
NO_LEARN = {"class_index": None, "flip": None, "support": None, "class_correct": False, "learned_correct": False}


def git(*a):
    return subprocess.run(["git", *a], cwd=D.REPO, capture_output=True, text=True).stdout.strip()


def verify_freeze(head):
    if git("rev-parse", "HEAD") != head:
        raise SystemExit("HEAD != --expected-head")
    fz = json.loads((ROOT / "BRE_FREEZE.json").read_text(encoding="utf-8"))
    for rel, h in fz["files"].items():
        if hashlib.sha256((D.REPO / rel).read_bytes()).hexdigest() != h:
            raise SystemExit(f"freeze hash mismatch: {rel}")


def bursts():
    return json.loads((ROOT / "BRE_BURSTS.json").read_text(encoding="utf-8"))


def support_of(bid):
    b = bursts()
    return tuple(b["T"].get(bid) or b["V"][bid])


def seed(mode, key):
    s = json.loads((ROOT / "BRE_SEEDS.json").read_text(encoding="utf-8"))
    return int((s["rehearsal_seeds"] if mode == "rehearsal" else s["seeds"])[key])


def sample(spec, q, support, n, s):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    c = m.build_candidate_circuit(spec, q, tuple(support)) if q > 0 else m.build_base_circuit(spec)
    d, o = c.compile_detector_sampler(seed=s).sample(shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def learn(spec, x, classes, truth, labx=None, laby=None):
    """Phase C two-stage learner on `spec` (tau unchanged). Flip stage only when labels are given."""
    import learner_d5 as LD
    import mm_contract as K
    from outputs.qshift_correlated_decoder_v1_6 import learner as L
    sel = LD.FastParityLearner(classes, L.base_dem(spec), K.tau()).select(x)
    out = {"class_index": sel["class_index"], "delta": sel["delta"], "flip": None, "support": None}
    if sel["class_index"] is not None and labx is not None:
        out["flip"] = LD.learn_flip(spec, classes[sel["class_index"]], labx, laby)["flip"]
        out["support"] = [int(v) for v in classes[sel["class_index"]].representative(out["flip"])]
    t_idx, t_flip = truth
    out["class_correct"] = t_idx is not None and sel["class_index"] == t_idx
    out["learned_correct"] = bool(out["class_correct"] and out["flip"] == t_flip)
    return out


def zspec(p, b):
    return C.spec(gate_p=p, measurement_p=p, regime="z_biased", bias_ratio=b)


def pool_job(args):
    mode, c, kind, bid, k, head, run = args
    if mode == "eval":
        verify_freeze(head)
    import estimate3 as E3
    import mm_contract as K
    name = f"{c}_{bid}_p{k}" if kind == "burst" else f"{c}_q0_{k:02d}"
    out = run / "records" / f"{name}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    t0 = time.perf_counter()
    true = C.spec(**C.CONDITIONS[c][0])
    classes = K.B.load_classes()
    used = {}
    if kind == "burst":
        sup = support_of(bid)
        truth = K.B.truth(classes, sup)
        dets, lx, ly = [], [], []
        for qi, q in enumerate(C.QS):
            key = C.burst_key(c, bid, k, qi)
            used[key] = seed(mode, key)
            x, y = sample(true, q, sup, C.DET_PER_Q + C.LAB_PER_Q, used[key])
            dets.append(x[: C.DET_PER_Q])
            lx.append(x[C.DET_PER_Q:])
            ly.append(y[C.DET_PER_Q:])
        xu, labx, laby = np.vstack(dets), np.vstack(lx), np.concatenate(ly)
        np.savez_compressed(run / "arrays" / f"{name}.npz", det=np.packbits(xu, axis=1), labx=np.packbits(labx, axis=1),
                            laby=laby)
    else:
        sup, truth = None, (None, None)
        key = C.q0_key(c, k)
        used[key] = seed(mode, key)
        xu, _ = sample(true, 0.0, (), C.Q0_ROWS, used[key])
        labx = laby = None
        np.savez_compressed(run / "arrays" / f"{name}.npz", det=np.packbits(xu, axis=1))
    obs, n = E3.rates_from_rows(xu)
    L = lambda spec: learn(spec, xu, classes, truth, labx, laby)   # noqa: E731
    b2 = E3.fit_masked(obs, n)
    e1 = E3.fit_e1(obs, n)
    rec = {"cond": c, "kind": kind, "burst": bid, "pool": k, "tuning": None, "seeds": used,
           "in_family": C.CONDITIONS[c][1], "fit": {"B2": b2, "E1": e1}}
    rec["learn"] = {"N": L(C.spec(**C.NOMINAL)), "B2": L(zspec(b2["p_hat"], b2["b_hat"])),
                    "E1": L(zspec(e1["p_hat"], e1["b_hat"]))}
    ci = rec["learn"]["B2"]["class_index"]
    if ci is not None:
        e2 = E3.fit_e2_refit(obs, n, E3.class_detectors(classes[ci]))
        rec["fit"]["E2"] = {**e2, "refit": True}
        rec["learn"]["E2"] = L(zspec(e2["p_hat"], e2["b_hat"]))
    else:
        rec["fit"]["E2"] = {**b2, "refit": False, "excluded": 0}
        rec["learn"]["E2"] = rec["learn"]["B2"]
    rec["tuning"] = (bid in bursts()["T"]) if kind == "burst" else (k in C.Q0_TUNING)
    rec["seconds"] = round(time.perf_counter() - t0, 1)
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out.name


def plan_jobs(mode, head, run):
    if mode == "rehearsal":
        return [(mode, c, kind, b if b else "q0", k, head, run) for c, kind, b, k in C.REHEARSAL]
    b = bursts()
    js = []
    for c in C.CONDITIONS:
        js += [(mode, c, "burst", bid, k, head, run) for bid in C.burst_ids(b) for k in range(C.POOLS_PER_BURST)]
        js += [(mode, c, "q0", "q0", k, head, run) for k in range(C.Q0_POOLS)]
    return js


def cmd_run(mode, head, workers):
    if mode == "eval":
        if git("status", "--porcelain"):
            raise SystemExit("working tree not clean")
        verify_freeze(head)
    run = WORK / mode
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    for d in ("records", "arrays"):
        (run / d).mkdir(parents=True, exist_ok=True)
    js = plan_jobs(mode, head, run)
    status = {"mode": mode, "head": git("rev-parse", "HEAD"), "expected_head": head, "workers": workers,
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "state": "running", "jobs": 0}
    st.write_text(json.dumps(status, indent=2), encoding="utf-8")
    t0 = time.perf_counter()
    try:
        with get_context("spawn").Pool(workers) as pool:
            hs = [pool.apply_async(pool_job, (j,)) for j in js]
            for i, h in enumerate(hs, 1):
                name = h.get(timeout=C.JOB_TIMEOUT_S + 600)
                status["jobs"] = i
                if i % 24 == 0 or i == len(js):
                    print(name, f"{i}/{len(js)}", f"{time.perf_counter() - t0:.0f}s", flush=True)
        status["state"] = "ready_for_analysis"
    except BaseException as e:      # noqa: BLE001  (recorded; never retried)
        status["state"], status["error"] = "failed", repr(e)
        raise
    finally:
        status["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status["wall_seconds"] = round(time.perf_counter() - t0, 1)
        status["n_jobs"] = len(js)
        st.write_text(json.dumps(status, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ analysis
def thresholds(recs):
    """Per-arm flag thresholds: max statistic over IN-FAMILY TUNING pools (T bursts + q0 pools 0-23)."""
    t = [r for r in recs if r["in_family"] and r["tuning"]]
    if not t:
        raise SystemExit("no in-family tuning pools")
    return {"B2": json.loads((ROOT / "FLAG_THRESHOLD.json").read_text(encoding="utf-8"))["threshold"],   # frozen
            "E1": max(r["fit"]["E1"]["stat"] for r in t),
            "E1_max_excluded": bursts()["e1_max_excluded"],
            "E2": max(r["fit"]["E2"]["objective"] for r in t)}


def outcome(r, arm, thr):
    """(flagged, final learner outcome) for one pool under one arm's flag rule and on-flag policy."""
    f = r["fit"]
    if arm == "B2":
        fl = f["B2"]["objective"] > thr["B2"]
        return fl, (NO_LEARN if fl else r["learn"]["B2"])
    if arm in ("E1", "E3"):
        fl = f["E1"]["excluded"] > thr["E1_max_excluded"] or f["E1"]["stat"] > thr["E1"]
        if not fl:
            return fl, r["learn"]["E1"]
        return fl, (NO_LEARN if arm == "E1" else r["learn"]["N"])
    fl = f["E2"]["objective"] > thr["E2"]
    return fl, (r["learn"]["N"] if fl else r["learn"]["E2"])


def analyze(mode, run):
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    seeds = json.loads((ROOT / "BRE_SEEDS.json").read_text(encoding="utf-8"))
    pool = seeds["rehearsal_seeds"] if mode == "rehearsal" else seeds["seeds"]
    for r in recs:
        for k, v in r["seeds"].items():
            if pool[k] != v:
                raise ValueError("seed mismatch")
    if mode == "eval" and len(recs) != st["n_jobs"]:
        raise SystemExit("record count != jobs")
    thr = thresholds(recs)
    out = {"schema": "qshift-adaptive-robust-bre-analysis-v1", "mode": mode, "thresholds": thr, "arms": {}}
    for arm in C.ARMS:
        rows, ends = {}, {}
        for c in C.CONDITIONS:
            cell = {}
            for split, tun in (("T", True), ("V", False)):
                b = [r for r in recs if r["cond"] == c and r["kind"] == "burst" and r["tuning"] == tun]
                z = [r for r in recs if r["cond"] == c and r["kind"] == "q0" and r["tuning"] == tun]
                ob, oz = [outcome(r, arm, thr) for r in b], [outcome(r, arm, thr) for r in z]
                cell[split] = {"burst_pools": len(b), "learned_exactly": sum(o[1]["learned_correct"] for o in ob),
                               "class_correct": sum(o[1]["class_correct"] for o in ob),
                               "flagged_burst": sum(o[0] for o in ob), "q0_pools": len(z),
                               "false_accepts_q0": sum(o[1]["class_index"] is not None for o in oz),
                               "flagged_q0": sum(o[0] for o in oz)}
            kk = [r for r in recs if r["cond"] == c and r["kind"] == "burst" and r["burst"] == "K"]
            cell["K_learned"] = [sum(outcome(r, arm, thr)[1]["learned_correct"] for r in kk), len(kk)]
            rows[c] = cell
        inf = [c for c in C.IN_FAMILY if c in rows]
        oof = [c for c, v in C.CONDITIONS.items() if not v[1] and c in rows]
        V = lambda c, key: rows[c]["V"][key]   # noqa: E731
        tot_l = sum(V(c, "learned_exactly") for c in inf)
        tot_n = sum(V(c, "burst_pools") for c in inf)
        tT = sum(rows[c]["T"]["learned_exactly"] for c in inf)
        nT = sum(rows[c]["T"]["burst_pools"] for c in inf)
        ends["learn"] = bool(tot_n and tot_l >= C.LEARN_MIN_OVERALL * tot_n and
                             all(V(c, "learned_exactly") >= C.LEARN_MIN_PER_COND * V(c, "burst_pools") / 24 for c in inf))
        ends["false_accept"] = all(V(c, "false_accepts_q0") <= C.MAX_FALSE_ACCEPT for c in inf)
        ends["false_flag"] = all(V(c, "flagged_burst") <= C.MAX_FALSE_FLAG and V(c, "flagged_q0") <= C.MAX_FALSE_FLAG
                                 for c in inf)
        ends["out_of_family"] = all(V(c, "flagged_burst") >= C.OOF_MIN_FLAG * V(c, "burst_pools") / 24 and
                                    V(c, "false_accepts_q0") <= C.MAX_FALSE_ACCEPT for c in oof)
        ends["no_regression_K"] = all(rows[c]["K_learned"][0] == rows[c]["K_learned"][1] for c in inf) and \
            bool(nT) and tT >= C.LEARN_MIN_OVERALL * nT
        out["arms"][arm] = {"conditions": rows, "V_in_family_learned": [tot_l, tot_n], "T_in_family_learned": [tT, nT],
                            "endpoints": ends, "passes_all": all(ends.values())}
    passing = [a for a in C.PREFERENCE if out["arms"][a]["passes_all"]]
    core = [a for a in C.PREFERENCE if out["arms"][a]["endpoints"]["learn"] and out["arms"][a]["endpoints"]["false_accept"]]
    out["chosen_arm"] = passing[0] if passing else None
    out["verdict"] = "BRE_SUPPORTED" if passing else "BRE_PARTIAL" if core else "BRE_NOT_SUPPORTED"
    out["run_status"] = {k: st.get(k) for k in ("head", "started", "finished", "wall_seconds", "n_jobs")}
    return out


def cmd_analyze(mode, out_dir):
    res = analyze(mode, WORK / mode)
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    (o / "ANALYSIS.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": res["verdict"], "chosen": res["chosen_arm"],
                      **{a: res["arms"][a]["endpoints"] for a in C.ARMS}}))


def cmd_recount(mode, analysis_path):
    """Re-derive the analysis from the records, and re-run the first burst pool and first q0 pool of every
    condition into a replay directory; records must match exactly (timing excluded) and arrays bit-for-bit."""
    run = WORK / mode
    a = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    re_an = analyze(mode, run)
    same = json.dumps(re_an, sort_keys=True) == json.dumps(a, sort_keys=True)
    tmp = WORK / f"{mode}_replay"
    if tmp.exists():
        raise SystemExit(f"{tmp.name} exists; replay runs once")
    for d in ("records", "arrays"):
        (tmp / d).mkdir(parents=True)
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    js = plan_jobs(mode, st["head"], tmp)
    seen, pick = set(), []
    for j in js:
        if (j[1], j[2]) not in seen:
            seen.add((j[1], j[2]))
            pick.append(("rehearsal" if mode == "rehearsal" else "replay",) + j[1:])
    with get_context("spawn").Pool(min(8, len(pick))) as pool:
        names = pool.map(pool_job, pick)
    ident = {}
    for nm in names:
        r0 = json.loads((run / "records" / nm).read_text(encoding="utf-8"))
        r1 = json.loads((tmp / "records" / nm).read_text(encoding="utf-8"))
        r0.pop("seconds"), r1.pop("seconds")
        z0, z1 = np.load(run / "arrays" / nm.replace(".json", ".npz")), np.load(tmp / "arrays" / nm.replace(".json", ".npz"))
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
