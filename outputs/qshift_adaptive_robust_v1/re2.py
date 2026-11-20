"""RE2 frozen evaluation of the E1T pipeline with two new sealed bursts (PLAN_RE2.md rev 2, RE2_PROTOCOL.md).

  python re2.py run <eval|rehearsal> --expected-head <sha> [--open-hidden-seal] [--workers 8]
  python re2.py analyze <eval|rehearsal> <out_dir>
  python re2.py recount <eval|rehearsal> <analysis.json> [--open-hidden-seal]

Records: work/re2/<mode>/ (git-ignored). Single attempt: RUN_STATUS.json refuses a relaunch. Eval jobs re-verify
HEAD, a clean tree and every RE2_FREEZE.json hash (studykit). H3/H4 are read only inside jobs, only with
--open-hidden-seal, from RE2's own seal; RE1's seal is never read. Rehearsal uses re2_pool's public rehearsal bursts.
Hidden-burst records keep only booleans and fit scalars (no class index, flip, support or excluded detector set).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import re2_config as C
import studykit as SK

ROOT = C.ROOT
WORK = ROOT / "work" / "re2"
FREEZE = ROOT / "RE2_FREEZE.json"


def seed(mode, key):
    s = json.loads((ROOT / "RE2_SEEDS.json").read_text(encoding="utf-8"))
    return int((s["rehearsal_seeds"] if mode == "rehearsal" else s["seeds"])[key])


def drop_b2():
    p = ROOT / "RE2_PREFLIGHT.json"
    return bool(json.loads(p.read_text(encoding="utf-8"))["fallback_applied"]) if p.exists() else False


def true_support(c, mode, hidden_ok):
    b = C.CONDITIONS[c][1]
    if b == "K":
        return tuple(C.KNOWN)
    import re2_pool as P
    if mode == "rehearsal":
        return tuple(P.rehearsal_bursts()[b])
    if not hidden_ok:
        raise SystemExit(f"{c} in {mode} mode needs --open-hidden-seal (owner authorization)")
    import re2_seal
    return tuple(re2_seal.open_seal()[b])


def estimate_e1t(xu, labx, laby, classes, truth):
    """E1T -> learner (+ flip) -> structural flags. Flagged: nominal model, no burst (RE1's rule)."""
    import brt
    import estimate3 as E3
    import estimate4 as E4
    import estimate5 as E5
    obs, n = E3.rates_from_rows(xu)
    f = E4.e1_with_set(obs, n)
    lr = brt.learn(brt.zspec(f["p_hat"], f["b_hat"]), xu, classes, truth, labx, laby)
    st = E4.structural_flags(f["excluded_set"], lr["class_index"])
    flagged = E5.e1t_flag(f, st)
    rec = {"p_hat": f["p_hat"], "b_hat": f["b_hat"], "excluded": f["excluded"], "excluded_set": f["excluded_set"],
           "flagged": flagged, "S1": st["S1_shape"], "S2": st["S2_consistency"], "class_index": lr["class_index"],
           "flip": lr["flip"], "support": lr["support"], "class_correct": bool(lr["class_correct"] and not flagged),
           "learned_correct": bool(lr["learned_correct"] and not flagged)}
    if flagged:
        return C.spec(**C.NOMINAL), None, rec
    return brt.zspec(f["p_hat"], f["b_hat"]), lr["support"], rec


def estimate_b2(xu, dets, labx, laby, truth_support):
    """RE1's B2 pipeline, unchanged (descriptive arm)."""
    import estimate2 as E2
    import re1
    fit = E2.fit_b2(xu)
    rec = {"p_hat": fit["p_hat"], "b_hat": fit["b_hat"], "objective": fit["objective"], "flagged": fit["flagged"]}
    if fit["flagged"]:
        return C.spec(**C.NOMINAL), None, rec | {"learned_correct": False, "class_correct": False, "support": None}
    model = C.spec(gate_p=fit["p_hat"], measurement_p=fit["p_hat"], regime="z_biased", bias_ratio=fit["b_hat"])
    lr = re1.learn(model, truth_support, dets, labx, laby)
    return model, lr["support"], rec | {k: lr[k] for k in ("learned_correct", "class_correct", "support", "class_index",
                                                            "flip")}


PUBLIC_HIDDEN_FIELDS = ("p_hat", "b_hat", "excluded", "flagged", "S1", "S2", "class_correct", "learned_correct",
                        "objective")


def scrub(rec):
    return {k: v for k, v in rec.items() if k in PUBLIC_HIDDEN_FIELDS}


def root_job(args):
    mode, c, r, head, hidden_ok, run, n_eval, no_b2 = args
    if mode == "eval":
        SK.require_frozen_head(FREEZE, head)
    import mm_contract as K
    import re1
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    out = run / "roots" / f"{c}_r{r:02d}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    t0 = time.perf_counter()
    kw, burst, _, _ = C.CONDITIONS[c]
    true, nominal = C.spec(**kw), C.spec(**C.NOMINAL)
    tsup = true_support(c, mode, hidden_ok)
    classes = K.B.load_classes()
    truth = K.B.truth(classes, tsup)
    dets, labx, laby, used = [], [], [], {}
    for qi, q in enumerate(C.QS):
        k = C.root_key(c, r, "cal", qi)
        used[k] = seed(mode, k)
        x, y = re1.sample(true, q, tsup, C.DET_PER_Q + C.LAB_PER_Q, used[k])
        dets.append(x[: C.DET_PER_Q])
        labx.append(x[C.DET_PER_Q:])
        laby.append(y[C.DET_PER_Q:])
    xu, lx, ly = np.vstack(dets), np.vstack(labx), np.concatenate(laby)
    t_fit = time.perf_counter()
    model, sup, est = estimate_e1t(xu, lx, ly, classes, truth)
    arms = C.arms(c, no_b2)
    dec = {}
    dec["L2L_E"], dec["Astar_Em"] = re1.decoders(model, sup)
    _, dec["Astar_Nm"] = re1.decoders(nominal, sup)
    dec["L2s_true"], dec["Astar_true"] = re1.decoders(true, tsup)
    dec["A_nominal"] = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(nominal)))
    kinds = {"L2L_E": "l2", "Astar_Em": "corr", "Astar_Nm": "corr", "L2s_true": "l2", "Astar_true": "corr",
             "A_nominal": "plain", "L2L_B2": "l2"}
    b2 = None
    if "L2L_B2" in arms:
        mb, sb, b2 = estimate_b2(xu, dets, labx, laby, tsup)
        dec["L2L_B2"], _ = re1.decoders(mb, sb)
    sel_err = {a: int((re1.predict(dec[a], lx, "corr") != ly).sum()) for a in ("Astar_Em", "Astar_Nm")}
    s_star = "Astar_Em" if sel_err["Astar_Em"] <= sel_err["Astar_Nm"] else "Astar_Nm"    # tie -> estimated model
    setup_s = round(time.perf_counter() - t_fit, 1)
    per_q, bits = {}, {}
    for qi, q in enumerate(C.QS):
        k = C.root_key(c, r, "eval", qi)
        used[k] = seed(mode, k)
        x, y = re1.sample(true, q, tsup, n_eval, used[k])
        errs, secs = {}, {}
        for a in arms:
            t = time.perf_counter()
            e = re1.predict(dec[a], x, kinds[a]) != y
            secs[a] = round(time.perf_counter() - t, 2)
            errs[a] = int(e.sum())
            bits[f"q{qi}_{a}"] = np.packbits(e)
        per_q[str(q)] = {"shots": n_eval, "errors": errs, "seconds": secs}
    arc = run / "archives" / f"{c}_r{r:02d}.npz"
    np.savez_compressed(arc, **bits)
    hidden = burst in C.HIDDEN and mode != "rehearsal"
    rec = {"cond": c, "root": r, "seeds": used, "arms": list(arms), "e1t": scrub(est) if hidden else est,
           "b2": (scrub(b2) if hidden else b2) if b2 is not None else None,
           "true_support": "SEALED" if hidden else list(tsup), "s_star": s_star, "s_star_selection_errors": sel_err,
           "per_q": per_q, "archive": f"archives/{arc.name}",
           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest(), "setup_seconds": setup_s,
           "seconds": round(time.perf_counter() - t0, 1)}
    out.write_text(json.dumps(rec, indent=2, sort_keys=True, default=_jsonable) + "\n", encoding="utf-8", newline="\n")
    return out.name


def _jsonable(o):
    if isinstance(o, np.generic):
        return o.item()
    raise TypeError(f"not JSON serializable: {type(o)}")


def plan_jobs(mode, head, hidden_ok, run):
    nb = drop_b2()
    if mode == "rehearsal":
        return [(mode, c, 0, head, hidden_ok, run, C.REHEARSAL_EVAL_SHOTS, nb) for c in C.CONDITIONS]
    return [(mode, c, r, head, hidden_ok, run, C.EVAL_SHOTS, nb) for c, v in C.CONDITIONS.items() for r in range(v[3])]


def cmd_run(mode, head, hidden_ok, workers):
    if mode == "eval":
        SK.require_frozen_head(FREEZE, head)
        if not hidden_ok:
            raise SystemExit("eval needs --open-hidden-seal (G3-G5 sample from the sealed H3/H4)")
    run = WORK / mode
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    for d in ("roots", "archives"):
        (run / d).mkdir(parents=True, exist_ok=True)
    js = plan_jobs(mode, head, hidden_ok, run)
    status = {"mode": mode, "head": SK.git_head(), "expected_head": head, "workers": workers,
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "state": "running", "jobs": {},
              "drop_b2": drop_b2()}
    SK.dump_json(st, status)
    t0 = time.perf_counter()
    try:
        with get_context("spawn").Pool(workers) as pool:
            res = {j[1] + f"_r{j[2]:02d}": pool.apply_async(root_job, (j,)) for j in js}
            for name, h in res.items():
                h.get(timeout=C.JOB_TIMEOUT_S + 600)
                status["jobs"][name] = {"returncode": 0}
                print(name, f"{len(status['jobs'])}/{len(js)}", f"{time.perf_counter() - t0:.0f}s", flush=True)
        status["state"] = "ready_for_analysis"
    except BaseException as e:      # noqa: BLE001  (recorded; never retried)
        status["state"], status["error"] = "failed", repr(e)
        raise
    finally:
        status["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status["wall_seconds"] = round(time.perf_counter() - t0, 1)
        status["n_jobs"] = len(js)
        SK.dump_json(st, status)


# ------------------------------------------------------------------ analysis
def _load(run):
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "roots").glob("*.json"))]
    arrs = {}
    for r in recs:
        p = run / r["archive"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != r["archive_sha256"]:
            raise ValueError(f"archive hash mismatch {p.name}")
        z = np.load(p)
        n = r["per_q"]["0.0"]["shots"]
        e = {(qi, a): np.unpackbits(z[f"q{qi}_{a}"])[:n].astype(bool) for qi in range(3) for a in r["arms"]}
        for qi, q in enumerate(C.QS):
            for a in r["arms"]:
                if int(e[(qi, a)].sum()) != r["per_q"][str(q)]["errors"][a]:
                    raise ValueError("recorded count mismatch")
        e.update({(qi, "S_star"): e[(qi, r["s_star"])] for qi in range(3)})
        arrs[(r["cond"], r["root"])] = e
    return recs, arrs


def analyze(mode, run):
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs, arrs = _load(run)
    seeds = json.loads((ROOT / "RE2_SEEDS.json").read_text(encoding="utf-8"))
    pool = seeds["rehearsal_seeds"] if mode == "rehearsal" else seeds["seeds"]
    for r in recs:
        for k, v in r["seeds"].items():
            if pool[k] != v:
                raise ValueError("seed mismatch")
    out = {"schema": "qshift-adaptive-robust-re2-analysis-v1", "mode": mode, "alpha_one_sided": C.ALPHA_ONE_SIDED,
           "ni_margin_fraction": C.NI_MARGIN, "ni_floor_errors": C.NI_FLOOR_ERRORS,
           "bootstrap_replicates": C.BOOT_REPS, "conditions": {}}
    for c, (_, burst, gated, _) in C.CONDITIONS.items():
        rr = sorted([r for r in recs if r["cond"] == c], key=lambda r: r["root"])
        if not rr:
            continue
        arms = tuple(rr[0]["arms"]) + ("S_star",)
        n = rr[0]["per_q"]["0.0"]["shots"]
        f = {a: np.array([[arrs[(c, r["root"])][(qi, a)].sum() for qi in range(3)] for r in rr]) for a in arms}
        nz = {a: f[a][:, 1:].sum(axis=1) for a in arms}
        q0 = {a: f[a][:, 0] for a in arms}
        rng = np.random.default_rng(int(pool[C.stats_key(c)]) if c in C.GATED and mode == "eval" else 0)
        idx = rng.integers(0, len(rr), size=(C.BOOT_REPS, len(rr)))
        n_nz, n_q0 = 2 * n * len(rr), n * len(rr)
        ler_nz = lambda a, i=None: (nz[a] if i is None else nz[a][i]).sum(axis=-1) / n_nz  # noqa: E731
        ler_q0 = lambda a, i=None: (q0[a] if i is None else q0[a][i]).sum(axis=-1) / n_q0  # noqa: E731
        ni_d = ler_nz("L2L_E", idx) - ler_nz("L2s_true", idx)
        sup_d = ler_nz("L2L_E", idx) - ler_nz("S_star", idx)
        safe_d = ler_q0("L2L_E", idx) - ler_q0("A_nominal", idx)
        oracle = float(ler_nz("L2s_true"))
        strict_margin = C.NI_MARGIN * oracle
        ni_margin = max(strict_margin, C.NI_FLOOR_ERRORS / n_nz)
        safe_margin = max(C.SAFETY_FRACTION * float(ler_q0("A_nominal")), C.SAFETY_FLOOR_ERRORS / n_q0)
        hi = 1 - C.ALPHA_ONE_SIDED
        ni_up = float(np.quantile(ni_d, hi))
        ni = {"estimate": float(ler_nz("L2L_E") - oracle), "upper": ni_up, "margin": ni_margin,
              "floor_binds": ni_margin > strict_margin, "passes": ni_up < ni_margin}
        ni_strict = {"margin": strict_margin, "passes": ni_up < strict_margin}
        sup = {"estimate": float(ler_nz("L2L_E") - ler_nz("S_star")), "upper": float(np.quantile(sup_d, hi))}
        sup["passes"] = sup["upper"] < 0
        safe = {"estimate": float(ler_q0("L2L_E") - ler_q0("A_nominal")), "p95": float(np.quantile(safe_d, 0.95)),
                "margin": safe_margin}
        safe["passes"] = safe["p95"] <= 0 or safe["p95"] <= safe_margin
        e = arrs
        disc = lambda a, b: [int(sum((e[(c, r["root"])][(qi, a)] & ~e[(c, r["root"])][(qi, b)]).sum()  # noqa: E731
                                     for r in rr for qi in (1, 2))),
                             int(sum((e[(c, r["root"])][(qi, b)] & ~e[(c, r["root"])][(qi, a)]).sum()
                                     for r in rr for qi in (1, 2)))]
        sstar = float(ler_nz("S_star"))
        rb = 1 - ler_nz("L2L_E", idx) / np.where(ler_nz("S_star", idx) > 0, ler_nz("S_star", idx), np.nan)
        row = {"burst": f"{burst} (sealed)" if burst in C.HIDDEN else burst, "gated": gated, "roots": len(rr),
               "shots_per_q_per_root": n, "errors_q0_q1_q2": {a: f[a].sum(axis=0).tolist() for a in arms},
               "ler_nonzero": {a: float(ler_nz(a)) for a in arms}, "ler_q0": {a: float(ler_q0(a)) for a in arms},
               "NI": ni, "NI_strict": ni_strict, "SUP": sup, "SAFETY_q0": safe,
               "NI_excess_fraction": (float(ler_nz("L2L_E")) / oracle - 1) if oracle else None,
               "R_vs_S_star": {"estimate": (1 - float(ler_nz("L2L_E")) / sstar) if sstar else None,
                               "95ci": [float(np.nanquantile(rb, 0.025)), float(np.nanquantile(rb, 0.975))]},
               "disc_vs_oracle": disc("L2L_E", "L2s_true"),
               "learned_exactly": sum(bool(r["e1t"]["learned_correct"]) for r in rr),
               "flagged": sum(bool(r["e1t"]["flagged"]) for r in rr),
               "s_star_choice": {a: sum(r["s_star"] == a for r in rr) for a in ("Astar_Em", "Astar_Nm")},
               "p_hat": [float(np.mean([r["e1t"]["p_hat"] for r in rr])), float(np.std([r["e1t"]["p_hat"] for r in rr]))],
               "b_hat": [float(np.mean([r["e1t"]["b_hat"] for r in rr])), float(np.std([r["e1t"]["b_hat"] for r in rr]))]}
        if "L2L_B2" in arms:
            row["L2L_B2"] = {"ler_nonzero": float(ler_nz("L2L_B2")),
                             "learned_exactly": sum(bool(r["b2"]["learned_correct"]) for r in rr),
                             "flagged": sum(bool(r["b2"]["flagged"]) for r in rr),
                             "disc_vs_L2L_E": disc("L2L_B2", "L2L_E")}
        if gated:
            allp = ni["passes"] and sup["passes"] and safe["passes"]
            wrong = ni["estimate"] > ni_margin or safe["estimate"] > safe_margin or sup["estimate"] >= 0
            row["status"] = "PASS" if allp else "FAIL_DIRECTION" if wrong else "NOT_SHOWN"
        out["conditions"][c] = row
    g = [out["conditions"][c]["status"] for c in C.GATED if c in out["conditions"]]
    out["overall_verdict"] = ("CONFIRMED" if g and len(g) == len(C.GATED) and all(s == "PASS" for s in g) else
                              "NOT_CONFIRMED" if any(s == "FAIL_DIRECTION" for s in g) else
                              "PARTIAL" if any(s == "PASS" for s in g) else "INCONCLUSIVE")
    out["independence"] = ("hidden-burst claims are conditional on H3/H4 being independent of RE1's sealed H2 "
                           "(results/re2/OVERLAP.json); re2_contamination.py runs only after 'Open the RE1 seal'")
    out["run_status"] = {k: st[k] for k in ("head", "started", "finished", "wall_seconds", "n_jobs")}
    return out


def cmd_analyze(mode, out_dir):
    a = analyze(mode, WORK / mode)
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=True)
    SK.write_once_json(o / "ANALYSIS.json", a)
    print(json.dumps({"verdict": a["overall_verdict"], **{c: v.get("status", "descriptive")
                                                           for c, v in a["conditions"].items()}}))


def cmd_recount(mode, analysis_path, hidden_ok):
    """Re-derive the analysis; re-decode root 0 of every condition end to end, bit-identically (separate dir)."""
    run = WORK / mode
    a = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    same = json.dumps(analyze(mode, run), sort_keys=True) == json.dumps(a, sort_keys=True)
    tmp = WORK / f"{mode}_redecode"
    if tmp.exists():
        raise SystemExit(f"{tmp.name} exists; re-decode runs once")
    for d in ("roots", "archives"):
        (tmp / d).mkdir(parents=True, exist_ok=True)
    n = C.REHEARSAL_EVAL_SHOTS if mode == "rehearsal" else C.EVAL_SHOTS
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    rm = "rehearsal" if mode == "rehearsal" else "replay"       # replay: study seeds, no freeze re-check
    jobs = [(rm, c, 0, st["head"], hidden_ok, tmp, n, st["drop_b2"]) for c in C.CONDITIONS]
    with get_context("spawn").Pool(min(8, len(jobs))) as pool:
        pool.map(root_job, jobs)
    ident = {}
    for c in C.CONDITIONS:
        r0 = json.loads((run / "roots" / f"{c}_r00.json").read_text(encoding="utf-8"))
        r1 = json.loads((tmp / "roots" / f"{c}_r00.json").read_text(encoding="utf-8"))
        for r in (r0, r1):
            r.pop("seconds"), r.pop("setup_seconds")
            for q in r["per_q"].values():
                q.pop("seconds")
        z0, z1 = np.load(run / r0["archive"]), np.load(tmp / r1["archive"])
        ident[c] = r0 == r1 and sorted(z0.files) == sorted(z1.files) and all(np.array_equal(z0[k], z1[k]) for k in z0.files)
    res = {"reanalysis_identical": same, "redecode_root0_identical": ident, "all_pass": bool(same and all(ident.values()))}
    print(json.dumps(res))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze", "recount"])
    ap.add_argument("mode", choices=["eval", "rehearsal"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--expected-head", default="")
    ap.add_argument("--open-hidden-seal", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    x = ap.parse_args()
    if x.cmd == "run":
        cmd_run(x.mode, x.expected_head, x.open_hidden_seal, x.workers)
    elif x.cmd == "analyze":
        cmd_analyze(x.mode, x.path)
    else:
        cmd_recount(x.mode, x.path, x.open_hidden_seal)
