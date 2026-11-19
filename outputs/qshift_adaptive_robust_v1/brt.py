"""BRT-1 threshold-free E1 flag, fresh held-out development run (PLAN_BRT.md, BRT_PROTOCOL.md).

  python brt.py run <eval|rehearsal> --expected-head <sha> [--workers 8]
  python brt.py analyze <eval|rehearsal> <out_dir>
  python brt.py recount <eval|rehearsal> <analysis.json>

Each job samples one calibration pool, fits B2 and E1 (with its excluded set), learns on both fits, and records the
subset-rule structural checks. Arms: E1T (candidate: cap OR S1 OR S2), E1S and E1 (BRE-frozen threshold), B2.
Nothing is tuned; every pool is held out. Write-once records under work/brt/<mode>/ (git-ignored).
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

import brt_config as C

D = C.D
ROOT = D.ROOT
WORK = ROOT / "work" / "brt"
NO_LEARN = {"class_index": None, "flip": None, "support": None, "class_correct": False, "learned_correct": False}


def git(*a):
    return subprocess.run(["git", *a], cwd=D.REPO, capture_output=True, text=True).stdout.strip()


def verify_freeze(head):
    if git("rev-parse", "HEAD") != head:
        raise SystemExit("HEAD != --expected-head")
    fz = json.loads((ROOT / "BRT_FREEZE.json").read_text(encoding="utf-8"))
    for rel, h in fz["files"].items():
        if hashlib.sha256((D.REPO / rel).read_bytes()).hexdigest() != h:
            raise SystemExit(f"freeze hash mismatch: {rel}")


def bursts():
    return json.loads((ROOT / "BRT_BURSTS.json").read_text(encoding="utf-8"))


def support_of(bid):
    return tuple(bursts()["V"][bid])


def seed(mode, key):
    s = json.loads((ROOT / "BRT_SEEDS.json").read_text(encoding="utf-8"))
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
    import estimate4 as E4
    obs, n = E3.rates_from_rows(xu)
    L = lambda spec: learn(spec, xu, classes, truth, labx, laby)   # noqa: E731
    b2 = E3.fit_masked(obs, n)
    e1 = E4.e1_with_set(obs, n)
    rec = {"cond": c, "kind": kind, "burst": bid, "pool": k, "seeds": used, "role": C.CONDITIONS[c][1],
           "true_class": truth[0], "fit": {"B2": b2, "E1": e1}}
    rec["learn"] = {"B2": L(zspec(b2["p_hat"], b2["b_hat"])), "E1": L(zspec(e1["p_hat"], e1["b_hat"]))}
    rec["structural"] = E4.structural_flags(e1["excluded_set"], rec["learn"]["E1"]["class_index"])
    rec["seconds"] = round(time.perf_counter() - t0, 1)
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out.name


def plan_jobs(mode, head, run):
    b = bursts()
    if mode == "rehearsal":
        ids = sorted(b["V"])
        return [(mode, c, kind, ids[i] if kind == "burst" else "q0", 0 if kind == "burst" else i, head, run)
                for c, kind, i in C.REHEARSAL]
    js = []
    for c in C.CONDITIONS:
        js += [(mode, c, "burst", bid, k, head, run) for bid in b["V"] for k in range(C.POOLS_PER_BURST)]
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
def outcome(r, arm):
    """(flagged, final learner outcome) under one arm. Thresholds are frozen from BRE; on a flag, no burst."""
    import estimate4 as E4
    if arm == "B2":
        fl = r["fit"]["B2"]["objective"] > C.B2_THRESHOLD
        return fl, (NO_LEARN if fl else r["learn"]["B2"])
    if arm == "E1T":
        import estimate5 as E5
        fl = E5.e1t_flag(r["fit"]["E1"], r["structural"])
        return fl, (NO_LEARN if fl else r["learn"]["E1"])
    fl = E4.e1_flag(r["fit"]["E1"])
    if arm == "E1S":
        fl = fl or r["structural"]["S1_shape"] or r["structural"]["S2_consistency"]
    return fl, (NO_LEARN if fl else r["learn"]["E1"])


def analyze(mode, run):
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    seeds = json.loads((ROOT / "BRT_SEEDS.json").read_text(encoding="utf-8"))
    pool = seeds["rehearsal_seeds"] if mode == "rehearsal" else seeds["seeds"]
    for r in recs:
        for k, v in r["seeds"].items():
            if pool[k] != v:
                raise ValueError("seed mismatch")
    if mode == "eval" and len(recs) != st["n_jobs"]:
        raise SystemExit("record count != jobs")
    fps = bursts()["footprint"]
    out = {"schema": "qshift-adaptive-robust-brt-analysis-v1", "mode": mode,
           "thresholds_frozen_from_bre": {"E1_stat": C.E1_STAT_THRESHOLD, "E1_max_excluded": C.E1_MAX_EXCLUDED,
                                          "B2": C.B2_THRESHOLD},
           "e1_set_matches_count": all(r["fit"]["E1"]["set_matches_count"] for r in recs), "arms": {}}
    for arm in C.ARMS:
        rows = {}
        for c in C.CONDITIONS:
            b = [r for r in recs if r["cond"] == c and r["kind"] == "burst"]
            z = [r for r in recs if r["cond"] == c and r["kind"] == "q0"]
            ob, oz = [outcome(r, arm) for r in b], [outcome(r, arm) for r in z]
            rows[c] = {"burst_pools": len(b), "learned_exactly": sum(o[1]["learned_correct"] for o in ob),
                       "flagged_burst": sum(o[0] for o in ob), "q0_pools": len(z),
                       "false_accepts_q0": sum(o[1]["class_index"] is not None for o in oz),
                       "flagged_q0": sum(o[0] for o in oz),
                       "learned_by_footprint": {str(fp): sum(o[1]["learned_correct"] for r, o in zip(b, ob)
                                                             if fps[r["burst"]] == fp)
                                                for fp in sorted(set(fps.values()))}}
        out["arms"][arm] = {"conditions": rows,
                            "in_family_learned": [sum(rows[c]["learned_exactly"] for c in C.IN_FAMILY),
                                                  sum(rows[c]["burst_pools"] for c in C.IN_FAMILY)]}
    A = out["arms"]["E1T"]["conditions"]
    tl, tn = out["arms"]["E1T"]["in_family_learned"]
    e1l = out["arms"]["E1"]["in_family_learned"][0]
    full = lambda c, need: need * A[c]["burst_pools"] / (C.POOLS_PER_BURST * len(bursts()["V"]))   # noqa: E731
    ends = {
        "learn": bool(tn) and tl >= C.LEARN_MIN_OVERALL * tn and
        all(A[c]["learned_exactly"] >= full(c, C.LEARN_MIN_PER_COND) for c in C.IN_FAMILY),
        "false_accept": all(A[c]["false_accepts_q0"] <= C.MAX_FALSE_ACCEPT for c in C.IN_FAMILY),
        "false_flag": all(A[c]["flagged_burst"] <= C.MAX_FALSE_FLAG and A[c]["flagged_q0"] <= C.MAX_FALSE_FLAG
                          for c in C.IN_FAMILY),
        "out_of_family": all(A[c]["flagged_burst"] >= full(c, C.OOF_MIN_FLAG) and
                             A[c]["false_accepts_q0"] <= C.MAX_FALSE_ACCEPT for c in C.OOF_GATED),
        "TM15_false_accept": A["TM15"]["false_accepts_q0"] <= C.MAX_FALSE_ACCEPT,
        "no_loss_vs_E1": tl >= e1l - C.NO_LOSS_VS_E1,
    }
    inf_ok = ends["learn"] and ends["false_accept"] and ends["false_flag"] and ends["no_loss_vs_E1"]
    out["E1T_endpoints"] = ends
    out["verdict"] = "BRT_SUPPORTED" if all(ends.values()) else "BRT_PARTIAL" if inf_ok else "BRT_NOT_SUPPORTED"
    out["run_status"] = {k: st.get(k) for k in ("head", "started", "finished", "wall_seconds", "n_jobs")}
    return out


def cmd_analyze(mode, out_dir):
    res = analyze(mode, WORK / mode)
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    (o / "ANALYSIS.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": res["verdict"], **res["E1T_endpoints"]}))


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
