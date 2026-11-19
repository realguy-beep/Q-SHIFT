"""RE1 frozen evaluation of the mismatch-robust learned-support pipeline (RE1_PROTOCOL.md).

  python re1.py run <eval|rehearsal> --expected-head <sha> [--open-hidden-seal] [--workers 8]
  python re1.py analyze <eval|rehearsal> <out_dir>
  python re1.py recount <eval|rehearsal> <analysis.json> [--open-hidden-seal]

Records: work/re1/<mode>/ (git-ignored). Single attempt: RUN_STATUS.json refuses a relaunch. Eval jobs re-verify
HEAD and every RE1_FREEZE.json hash. R6's true support is the sealed H2: in eval mode it is read only inside jobs,
and only with --open-hidden-seal; in rehearsal mode R6 uses the public rehearsal support.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from math import comb
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import re1_config as R

D = R.D
ROOT = D.ROOT
WORK = ROOT / "work" / "re1"


def git(*a):
    return subprocess.run(["git", *a], cwd=D.REPO, capture_output=True, text=True).stdout.strip()


def verify_freeze(head):
    if git("rev-parse", "HEAD") != head:
        raise SystemExit("HEAD != --expected-head")
    fz = json.loads((ROOT / "RE1_FREEZE.json").read_text(encoding="utf-8"))
    for rel, h in fz["files"].items():
        if hashlib.sha256((D.REPO / rel).read_bytes()).hexdigest() != h:
            raise SystemExit(f"freeze hash mismatch: {rel}")


def seed(mode, key):
    s = json.loads((ROOT / "RE1_SEEDS.json").read_text(encoding="utf-8"))
    return int((s["rehearsal_seeds"] if mode == "rehearsal" else s["seeds"])[key])


def true_support(c, mode, hidden_ok):
    if R.CONDITIONS[c][1] == "K":
        return R.KNOWN
    import re1_seal
    if mode == "rehearsal":
        return re1_seal.rehearsal_support()
    if not hidden_ok:
        raise SystemExit("R6 in eval mode needs --open-hidden-seal (owner authorization)")
    return re1_seal.open_seal()


def sample(spec, q, support, n, s):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    d, o = m.build_candidate_circuit(spec, q, tuple(support)).compile_detector_sampler(seed=s).sample(
        shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def learn(spec, truth, dets, labx, laby):
    """Phase C two-stage learner on `spec` (tau unchanged)."""
    import learner_d5 as LD
    import mm_contract as K
    from outputs.qshift_correlated_decoder_v1_6 import learner as L
    classes = K.B.load_classes()
    sel = LD.FastParityLearner(classes, L.base_dem(spec), K.tau()).select(np.vstack(dets))
    t_idx, t_flip = K.B.truth(classes, tuple(truth))
    flip = support = None
    if sel["class_index"] is not None:
        flip = LD.learn_flip(spec, classes[sel["class_index"]], np.vstack(labx), np.concatenate(laby))["flip"]
        support = [int(v) for v in classes[sel["class_index"]].representative(flip)]
    return {"class_index": sel["class_index"], "delta": sel["delta"], "flip": flip, "support": support,
            "class_correct": sel["class_index"] == t_idx,
            "learned_correct": bool(sel["class_index"] == t_idx and flip == t_flip)}


def decoders(spec_model, support):
    """(BP+OSD, correlated matching) on `spec_model` with burst `support`; None -> base model (no burst)."""
    import learner_d5 as LD
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD
    if support is None:
        c2 = cm = m.build_base_circuit(spec_model)
    else:
        c2 = m.build_candidate_circuit(spec_model, R.L2_PRIOR, tuple(support))
        cm = m.build_candidate_circuit(spec_model, R.ASTAR_Q_DEC, tuple(support))
    l2 = LdpcBPOSD(c2.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True), LD.L2)
    return l2, m.build_matching(m.build_decomposed_dem(cm))


def predict(dec, x, kind):
    if kind == "l2":
        return np.asarray(dec.decode_batch(x)[:, 0], np.uint8)
    return np.asarray(dec.decode_batch(x, enable_correlations=(kind == "corr"))).reshape(-1).astype(np.uint8)


def root_job(args):
    mode, c, r, head, hidden_ok, run, n_eval = args
    if mode == "eval":
        verify_freeze(head)
    import estimate2 as E
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    out = run / "roots" / f"{c}_r{r:02d}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    t0 = time.perf_counter()
    kw, _, _, _ = R.CONDITIONS[c]
    true, nominal = R.spec(**kw), R.spec(**R.NOMINAL)
    truth = true_support(c, mode, hidden_ok)
    dets, labx, laby, used = [], [], [], {}
    for qi, q in enumerate(R.QS):
        k = R.root_key(c, r, "cal", qi)
        used[k] = seed(mode, k)
        x, y = sample(true, q, truth, R.DET_PER_Q + R.LAB_PER_Q, used[k])
        dets.append(x[: R.DET_PER_Q])
        labx.append(x[R.DET_PER_Q:])
        laby.append(y[R.DET_PER_Q:])
    fit = E.fit_b2(np.vstack(dets))
    model = nominal if fit["flagged"] else R.spec(gate_p=fit["p_hat"], measurement_p=fit["p_hat"],
                                                  regime="z_biased", bias_ratio=fit["b_hat"])
    lr = learn(model, truth, dets, labx, laby) if not fit["flagged"] else {"support": None, "fallback": "flagged",
                                                                          "class_correct": False, "learned_correct": False}
    ln = learn(nominal, truth, dets, labx, laby)
    dec = {}
    dec["L2L_R"], dec["Astar_Rm"] = decoders(model, lr["support"])
    _, dec["Astar_Nm"] = decoders(nominal, lr["support"])
    dec["L2s_true"], dec["Astar_true"] = decoders(true, truth)
    dec["L2L_N"], _ = decoders(nominal, ln["support"])
    dec["A_nominal"] = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(nominal)))
    kinds = {"L2L_R": "l2", "Astar_Rm": "corr", "Astar_Nm": "corr", "L2s_true": "l2", "Astar_true": "corr",
             "L2L_N": "l2", "A_nominal": "plain"}
    # S* selection on this root's labelled calibration rows (deployable; same labels the flip stage uses)
    lx, ly = np.vstack(labx), np.concatenate(laby)
    sel_err = {a: int((predict(dec[a], lx, "corr") != ly).sum()) for a in ("Astar_Rm", "Astar_Nm")}
    s_star = "Astar_Rm" if sel_err["Astar_Rm"] <= sel_err["Astar_Nm"] else "Astar_Nm"   # tie -> estimated model
    per_q, bits = {}, {}
    for qi, q in enumerate(R.QS):
        k = R.root_key(c, r, "eval", qi)
        used[k] = seed(mode, k)
        x, y = sample(true, q, truth, n_eval, used[k])
        errs, secs = {}, {}
        for a in R.ARMS:
            t = time.perf_counter()
            e = predict(dec[a], x, kinds[a]) != y
            secs[a] = round(time.perf_counter() - t, 2)
            errs[a] = int(e.sum())
            bits[f"q{qi}_{a}"] = np.packbits(e)
        per_q[str(q)] = {"shots": n_eval, "errors": errs, "seconds": secs}
    arc = run / "archives" / f"{c}_r{r:02d}.npz"
    np.savez_compressed(arc, **bits)
    rec = {"cond": c, "root": r, "seeds": used, "fit": fit, "learn_R": lr, "learn_N": ln,
           "s_star": s_star, "s_star_selection_errors": sel_err, "per_q": per_q,
           "archive": f"archives/{arc.name}", "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest(),
           "seconds": round(time.perf_counter() - t0, 1)}
    if R.CONDITIONS[c][1] == "H2" and mode != "rehearsal":
        rec["learn_R"] = {k: v for k, v in lr.items() if k != "support"} | {"support": "SEALED"}
        rec["learn_N"] = {k: v for k, v in ln.items() if k != "support"} | {"support": "SEALED"}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out.name


def plan_jobs(mode, head, hidden_ok, run):
    if mode == "rehearsal":
        return [(mode, c, 0, head, hidden_ok, run, R.REHEARSAL_EVAL_SHOTS) for c in R.CONDITIONS]
    return [(mode, c, r, head, hidden_ok, run, R.EVAL_SHOTS) for c, v in R.CONDITIONS.items() for r in range(v[3])]


def cmd_run(mode, head, hidden_ok, workers):
    if mode == "eval":
        if git("status", "--porcelain"):
            raise SystemExit("working tree not clean")
        verify_freeze(head)
        if not hidden_ok:
            raise SystemExit("eval needs --open-hidden-seal (R6 samples from the sealed H2)")
    run = WORK / mode
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    for d in ("roots", "archives"):
        (run / d).mkdir(parents=True, exist_ok=True)
    js = plan_jobs(mode, head, hidden_ok, run)
    status = {"mode": mode, "head": git("rev-parse", "HEAD"), "expected_head": head, "workers": workers,
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "state": "running", "jobs": {}}
    st.write_text(json.dumps(status, indent=2), encoding="utf-8")
    t0 = time.perf_counter()
    try:
        with get_context("spawn").Pool(workers) as pool:
            res = {j[1] + f"_r{j[2]:02d}": pool.apply_async(root_job, (j,)) for j in js}
            for name, h in res.items():
                h.get(timeout=R.JOB_TIMEOUT_S + 600)       # per-job wall bound (queueing included)
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
        st.write_text(json.dumps(status, indent=2), encoding="utf-8")


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
        e = {(qi, a): np.unpackbits(z[f"q{qi}_{a}"])[:n].astype(bool) for qi in range(3) for a in R.ARMS}
        for qi, q in enumerate(R.QS):
            for a in R.ARMS:
                if int(e[(qi, a)].sum()) != r["per_q"][str(q)]["errors"][a]:
                    raise ValueError("recorded count mismatch")
        e.update({(qi, "S_star"): e[(qi, r["s_star"])] for qi in range(3)})
        arrs[(r["cond"], r["root"])] = e
    return recs, arrs


def mcnemar_less(b, c):
    n = b + c
    return 1.0 if n == 0 else sum(comb(n, k) for k in range(b + 1)) / 2 ** n


def analyze(mode, run):
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs, arrs = _load(run)
    seeds = json.loads((ROOT / "RE1_SEEDS.json").read_text(encoding="utf-8"))
    pool = seeds["rehearsal_seeds"] if mode == "rehearsal" else seeds["seeds"]
    for r in recs:
        for k, v in r["seeds"].items():
            if pool[k] != v:
                raise ValueError("seed mismatch")
    arms = R.ARMS + ("S_star",)
    out = {"schema": "qshift-adaptive-robust-re1-analysis-v1", "mode": mode, "alpha_one_sided": R.ALPHA_ONE_SIDED,
           "ni_margin_fraction": R.NI_MARGIN, "bootstrap_replicates": R.BOOT_REPS, "conditions": {}}
    for c, (_, burst, gated, _) in R.CONDITIONS.items():
        rr = sorted([r for r in recs if r["cond"] == c], key=lambda r: r["root"])
        if not rr:
            continue
        n = rr[0]["per_q"]["0.0"]["shots"]
        f = {a: np.array([[arrs[(c, r["root"])][(qi, a)].sum() for qi in range(3)] for r in rr]) for a in arms}
        nz = {a: f[a][:, 1:].sum(axis=1) for a in arms}           # per root, nonzero q pooled
        q0 = {a: f[a][:, 0] for a in arms}
        rng = np.random.default_rng(int(seeds["seeds"][R.stats_key(c)]) if c in R.GATED else 0)
        idx = rng.integers(0, len(rr), size=(R.BOOT_REPS, len(rr)))
        ler_nz = lambda a, i=None: (nz[a] if i is None else nz[a][i]).sum(axis=-1) / (2 * n * (len(rr)))  # noqa: E731
        ler_q0 = lambda a, i=None: (q0[a] if i is None else q0[a][i]).sum(axis=-1) / (n * len(rr))        # noqa: E731
        ni_d, sup_d, safe_d = (ler_nz("L2L_R", idx) - ler_nz("L2s_true", idx), ler_nz("L2L_R", idx) - ler_nz("S_star", idx),
                               ler_q0("L2L_R", idx) - ler_q0("A_nominal", idx))
        oracle = float(ler_nz("L2s_true"))
        ni_margin = R.NI_MARGIN * oracle
        safe_margin = max(R.SAFETY_FRACTION * float(ler_q0("A_nominal")),
                          R.SAFETY_FLOOR_ERRORS / (n * len(rr)))     # absolute floor: 3 errors over q0 shots
        hi = 1 - R.ALPHA_ONE_SIDED
        ni = {"estimate": float(ler_nz("L2L_R") - oracle), "upper": float(np.quantile(ni_d, hi)), "margin": ni_margin}
        ni["passes"] = ni["upper"] < ni_margin
        sup = {"estimate": float(ler_nz("L2L_R") - ler_nz("S_star")), "upper": float(np.quantile(sup_d, hi))}
        sup["passes"] = sup["upper"] < 0
        safe = {"estimate": float(ler_q0("L2L_R") - ler_q0("A_nominal")), "p95": float(np.quantile(safe_d, 0.95)),
                "margin": safe_margin}
        safe["passes"] = safe["p95"] <= 0 or safe["p95"] <= safe_margin
        e = arrs
        disc = lambda a, b: [int(sum((e[(c, r["root"])][(qi, a)] & ~e[(c, r["root"])][(qi, b)]).sum()  # noqa: E731
                                     for r in rr for qi in (1, 2))),
                             int(sum((e[(c, r["root"])][(qi, b)] & ~e[(c, r["root"])][(qi, a)]).sum()
                                     for r in rr for qi in (1, 2)))]
        rep = disc("L2L_R", "L2L_N")
        sstar = float(ler_nz("S_star"))
        rb = 1 - ler_nz("L2L_R", idx) / np.where(ler_nz("S_star", idx) > 0, ler_nz("S_star", idx), np.nan)
        row = {"burst": "H2 (sealed)" if burst == "H2" else "K", "gated": gated, "roots": len(rr), "shots_per_q_per_root": n,
               "errors_q0_q1_q2": {a: f[a].sum(axis=0).tolist() for a in arms},
               "ler_nonzero": {a: float(ler_nz(a)) for a in arms}, "ler_q0": {a: float(ler_q0(a)) for a in arms},
               "NI": ni, "SUP": sup, "SAFETY_q0": safe,
               "R_vs_S_star": {"estimate": (1 - float(ler_nz("L2L_R")) / sstar) if sstar else None,
                               "95ci": [float(np.nanquantile(rb, 0.025)), float(np.nanquantile(rb, 0.975))]},
               "repair_vs_L2L_N": {"discordant_R_only_N_only": rep, "mcnemar_one_sided_p": mcnemar_less(*rep)},
               "disc_vs_oracle": disc("L2L_R", "L2s_true"),
               "learned_exactly_R": sum(bool(r["learn_R"].get("learned_correct")) for r in rr),
               "learned_exactly_N": sum(bool(r["learn_N"].get("learned_correct")) for r in rr),
               "flagged": sum(bool(r["fit"]["flagged"]) for r in rr),
               "s_star_choice": {a: sum(r["s_star"] == a for r in rr) for a in ("Astar_Rm", "Astar_Nm")},
               "p_hat": [float(np.mean([r["fit"]["p_hat"] for r in rr])), float(np.std([r["fit"]["p_hat"] for r in rr]))],
               "b_hat": [float(np.mean([r["fit"]["b_hat"] for r in rr])), float(np.std([r["fit"]["b_hat"] for r in rr]))]}
        if gated:
            allp = ni["passes"] and sup["passes"] and safe["passes"]
            wrong = ni["estimate"] > ni_margin or safe["estimate"] > safe_margin or sup["estimate"] >= 0
            row["status"] = "PASS" if allp else "FAIL_DIRECTION" if wrong else "NOT_SHOWN"
        out["conditions"][c] = row
    g = [out["conditions"][c]["status"] for c in R.GATED if c in out["conditions"]]
    out["overall_verdict"] = ("CONFIRMED" if g and all(s == "PASS" for s in g) else
                              "NOT_CONFIRMED" if any(s == "FAIL_DIRECTION" for s in g) else
                              "PARTIAL" if any(s == "PASS" for s in g) else "INCONCLUSIVE")
    out["run_status"] = {k: st[k] for k in ("head", "started", "finished", "wall_seconds", "n_jobs")}
    return out


def cmd_analyze(mode, out_dir):
    res = analyze(mode, WORK / mode)
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=True)
    (o / "ANALYSIS.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"overall": res["overall_verdict"],
                      **{c: v.get("status", "descriptive") for c, v in res["conditions"].items()}}))


def cmd_recount(mode, analysis_path, hidden_ok):
    """Recount totals from archives and re-decode root 0 of every condition bit-identically (into a temp run)."""
    run = WORK / mode
    recs, arrs = _load(run)
    a = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    ok = True
    for c, row in a["conditions"].items():
        for arm, tot in row["errors_q0_q1_q2"].items():
            got = [int(sum(arrs[(c, r["root"])][(qi, arm)].sum() for r in recs if r["cond"] == c)) for qi in range(3)]
            ok &= got == tot
    tmp = WORK / f"{mode}_redecode"
    if tmp.exists():
        raise SystemExit(f"{tmp.name} exists; re-decode runs once")
    for d in ("roots", "archives"):
        (tmp / d).mkdir(parents=True, exist_ok=True)
    n = R.REHEARSAL_EVAL_SHOTS if mode == "rehearsal" else R.EVAL_SHOTS
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    replay_mode = "rehearsal" if mode == "rehearsal" else "replay"      # replay: study seeds, no freeze re-check
    jobs = [(replay_mode, c, 0, st["head"], hidden_ok, tmp, n) for c in R.CONDITIONS]
    with get_context("spawn").Pool(min(8, len(jobs))) as pool:
        pool.map(root_job, jobs)
    bit = {}
    for c in R.CONDITIONS:
        z0, z1 = np.load(run / "archives" / f"{c}_r00.npz"), np.load(tmp / "archives" / f"{c}_r00.npz")
        bit[c] = sorted(z0.files) == sorted(z1.files) and all(np.array_equal(z0[k], z1[k]) for k in z0.files)
    res = {"recount_matches_analysis": bool(ok), "redecode_root0_bit_identical": bit,
           "all_pass": bool(ok and all(bit.values()))}
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
