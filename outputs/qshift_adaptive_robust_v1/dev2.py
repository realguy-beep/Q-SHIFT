"""OG (off-grid screen) and E2E (end-to-end decode under mismatch) development studies (DEV2_PROTOCOL.md).

  python dev2.py run <og|e2e> <eval|rehearsal> --expected-head <sha> [--workers 8]
  python dev2.py analyze <og|e2e> <eval|rehearsal> <out_dir>

Write-once records under work/dev2/<study>_<mode>/ (git-ignored). A launch is refused if RUN_STATUS.json exists.
Each job re-verifies HEAD and every DEV2_FREEZE.json hash (mode eval).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from math import comb
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import dev2_config as D

ROOT = D.ROOT
WORK = ROOT / "work" / "dev2"


# ---------------------------------------------------------------- integrity
def git(*a):
    return subprocess.run(["git", *a], cwd=D.REPO, capture_output=True, text=True).stdout.strip()


def verify_freeze(expected_head: str):
    if git("rev-parse", "HEAD") != expected_head:
        raise SystemExit("HEAD != --expected-head")
    fz = json.loads((ROOT / "DEV2_FREEZE.json").read_text(encoding="utf-8"))
    for rel, h in fz["files"].items():
        if hashlib.sha256((D.REPO / rel).read_bytes()).hexdigest() != h:
            raise SystemExit(f"freeze hash mismatch: {rel}")


def seed(mode, key):
    s = json.loads((ROOT / "DEV2_SEEDS.json").read_text(encoding="utf-8"))
    return int((s["rehearsal_seeds"] if mode == "rehearsal" else s["seeds"])[key])


# ---------------------------------------------------------------- shared primitives
def sample(spec, q, n, s):
    import mm_contract as K
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    d, o = m.build_candidate_circuit(spec, q, K.SUPPORT).compile_detector_sampler(seed=s).sample(
        shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def calibration_pool(spec, keyf, mode):
    dets, labx, laby, used = [], [], [], {}
    for qi, q in enumerate(D.QS):
        k = keyf(qi)
        used[k] = seed(mode, k)
        x, y = sample(spec, q, D.DET_PER_Q + D.LAB_PER_Q, used[k])
        dets.append(x[: D.DET_PER_Q])
        labx.append(x[D.DET_PER_Q:])
        laby.append(y[D.DET_PER_Q:])
    return dets, labx, laby, used


def learn(spec, dets, labx=None, laby=None):
    """Phase C two-stage learner on `spec` (tau unchanged). Returns selection, flip, support, correctness."""
    import learner_d5 as LD
    import mm_contract as K
    from outputs.qshift_correlated_decoder_v1_6 import learner as L
    classes = K.B.load_classes()
    lr = LD.FastParityLearner(classes, L.base_dem(spec), K.tau())
    x = dets if labx is None else np.vstack(dets)
    sel = lr.select(x)
    out = {"class_index": sel["class_index"], "delta": sel["delta"], "no_burst": sel["class_index"] is None}
    if labx is None:
        return out
    t_idx, t_flip = K.B.truth(classes, K.SUPPORT)
    flip, support = None, None
    if sel["class_index"] is not None:
        flip = LD.learn_flip(spec, classes[sel["class_index"]], np.vstack(labx), np.concatenate(laby))["flip"]
        support = [int(v) for v in classes[sel["class_index"]].representative(flip)]
    out.update({"class_correct": sel["class_index"] == t_idx, "flip": flip, "support": support,
                "learned_correct": bool(sel["class_index"] == t_idx and flip == t_flip)})
    return out


def arm_b2(x_unlabeled, spec_learn_args):
    import estimate2 as E
    f = E.fit_b2(x_unlabeled)
    if f["flagged"]:
        return f, None
    return f, D.spec(gate_p=f["p_hat"], measurement_p=f["p_hat"], regime="z_biased", bias_ratio=f["b_hat"])


# ---------------------------------------------------------------- OG job
def og_job(args):
    mode, c, kind, k, head, run = args
    if mode == "eval":
        verify_freeze(head)
    import he1b as HB
    out = run / "records" / f"{c}_{kind}{k:02d}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    t0 = time.perf_counter()
    true = D.spec(**D.OG[c][0])
    if kind == "burst":
        dets, labx, laby, used = calibration_pool(true, lambda qi: D.og_burst_key(c, k, qi), mode)
        xu = np.vstack(dets)
        np.savez_compressed(run / "arrays" / f"{c}_burst{k:02d}.npz",
                            **{f"det_q{i}": np.packbits(v, axis=1) for i, v in enumerate(dets)},
                            **{f"labx_q{i}": np.packbits(v, axis=1) for i, v in enumerate(labx)},
                            **{f"laby_q{i}": v for i, v in enumerate(laby)})
    else:
        key = D.og_q0_key(c, k)
        used = {key: seed(mode, key)}
        xu, _ = sample(true, 0.0, D.Q0_ROWS, used[key])
        dets, labx, laby = xu, None, None
        np.savez_compressed(run / "arrays" / f"{c}_q0{k:02d}.npz", det=np.packbits(xu, axis=1))
    rec = {"cond": c, "kind": kind, "pool": k, "seeds": used, "in_family": D.OG[c][1]}
    rec["N"] = learn(D.spec(**D.NOMINAL), dets, labx, laby)
    pb, bb, ob = HB.fit(xu)
    rec["B"] = {"p_hat": pb, "b_hat": bb, "objective": ob, **learn(HB.spec_at(pb, bb), dets, labx, laby)}
    f, s2 = arm_b2(xu, None)
    rec["B2"] = {**f, **(learn(s2, dets, labx, laby) if s2 is not None else
                         {"class_index": None, "no_burst": True, "class_correct": False, "learned_correct": False,
                          "fallback": "flagged"})}
    rec["seconds"] = round(time.perf_counter() - t0, 1)
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out.name


# ---------------------------------------------------------------- E2E job
def _decoders(spec_model, support):
    """(L2 decoder, correlated matching) built on `spec_model` with burst `support` (None -> base model)."""
    import learner_d5 as LD
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD
    if support is None:
        circ_l2 = circ_m = m.build_base_circuit(spec_model)
    else:
        circ_l2 = m.build_candidate_circuit(spec_model, D.L2_PRIOR, tuple(support))
        circ_m = m.build_candidate_circuit(spec_model, D.ASTAR_Q_DEC, tuple(support))
    l2 = LdpcBPOSD(circ_l2.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True), LD.L2)
    mt = m.build_matching(m.build_decomposed_dem(circ_m))
    return l2, mt


def e2e_job(args):
    mode, c, r, head, run = args
    if mode == "eval":
        verify_freeze(head)
    import mm_contract as K
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    out = run / "records" / f"{c}_r{r}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    t0 = time.perf_counter()
    true = D.spec(**D.E2E[c])
    nominal = D.spec(**D.NOMINAL)
    dets, labx, laby, used = calibration_pool(true, lambda qi: D.e2e_key(c, r, "cal", qi), mode)
    xu = np.vstack(dets)
    f, s2 = arm_b2(xu, None)
    lb2 = learn(s2, dets, labx, laby) if s2 is not None else {"support": None, "fallback": "flagged"}
    ln = learn(nominal, dets, labx, laby)
    model_b2 = s2 if s2 is not None else nominal          # flagged -> nominal base model, no burst
    dec = {}
    dec["L2L_B2"], dec["Astar_B2"] = _decoders(model_b2, lb2.get("support"))
    dec["L2L_N"], _ = _decoders(nominal, ln.get("support"))
    _, dec["Astar_N"] = _decoders(nominal, K.SUPPORT)
    dec["L2s_true"], dec["Astar_true"] = _decoders(true, K.SUPPORT)
    a_nom = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(nominal)))
    n_eval = D.REHEARSAL["e2e_eval_shots"] if mode == "rehearsal" else D.E2E_EVAL_SHOTS
    per_q, bits = {}, {}
    for qi, q in enumerate(D.QS):
        k = D.e2e_key(c, r, "eval", qi)
        used[k] = seed(mode, k)
        x, y = sample(true, q, n_eval, used[k])
        err, secs = {}, {}
        for a in D.E2E_ARMS:
            t = time.perf_counter()
            if a.startswith("L2"):
                pred = np.asarray(dec[a].decode_batch(x)[:, 0], np.uint8)
            elif a == "A_nominal":
                pred = np.asarray(a_nom.decode_batch(x, enable_correlations=False)).reshape(-1).astype(np.uint8)
            else:
                pred = np.asarray(dec[a].decode_batch(x, enable_correlations=True)).reshape(-1).astype(np.uint8)
            secs[a] = round(time.perf_counter() - t, 2)
            err[a] = pred != y
            bits[f"q{qi}_{a}"] = np.packbits(err[a])
        per_q[str(q)] = {"shots": n_eval, "errors": {a: int(e.sum()) for a, e in err.items()}, "seconds": secs}
    np.savez_compressed(run / "arrays" / f"{c}_r{r}_errbits.npz", **bits)
    rec = {"cond": c, "root": r, "seeds": used, "fit_b2": f, "learn_B2": lb2, "learn_N": ln,
           "per_q": per_q, "seconds": round(time.perf_counter() - t0, 1)}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out.name


# ---------------------------------------------------------------- runner
def jobs(study, mode, head, run):
    if study == "og":
        items = (D.REHEARSAL["og"] if mode == "rehearsal" else
                 [(c, kind, k) for c in D.OG for kind in ("burst", "q0") for k in range(D.POOLS)])
        return og_job, [(mode, c, kind, k, head, run) for c, kind, k in items]
    items = D.REHEARSAL["e2e"] if mode == "rehearsal" else [(c, r) for c in D.E2E for r in range(D.E2E_ROOTS)]
    return e2e_job, [(mode, c, r, head, run) for c, r in items]


def cmd_run(study, mode, head, workers):
    if mode == "eval":
        if git("status", "--porcelain"):
            raise SystemExit("working tree not clean")
        verify_freeze(head)
    run = WORK / f"{study}_{mode}"
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    (run / "records").mkdir(parents=True, exist_ok=True)
    (run / "arrays").mkdir(parents=True, exist_ok=True)
    status = {"study": study, "mode": mode, "head": git("rev-parse", "HEAD"), "expected_head": head,
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "workers": workers, "state": "running"}
    st.write_text(json.dumps(status, indent=2), encoding="utf-8")
    fn, js = jobs(study, mode, head, run)
    t0 = time.perf_counter()
    try:
        with get_context("spawn").Pool(workers) as pool:
            for i, name in enumerate(pool.imap_unordered(fn, js), 1):
                print(name, f"{i}/{len(js)}", f"{time.perf_counter() - t0:.0f}s", flush=True)
        status["state"] = "ready_for_analysis"
    except BaseException as e:                      # noqa: BLE001  (recorded, never retried)
        status["state"], status["error"] = "failed", repr(e)
        raise
    finally:
        status["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status["wall_seconds"] = round(time.perf_counter() - t0, 1)
        status["jobs"] = len(js)
        st.write_text(json.dumps(status, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- analysis
def mcnemar_less(b, c):
    """One-sided exact p-value that the candidate has fewer errors: P(X <= b), X ~ Bin(b + c, 1/2)."""
    n = b + c
    return 1.0 if n == 0 else sum(comb(n, k) for k in range(b + 1)) / 2 ** n


def analyze_og(run):
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    out = {"schema": "qshift-adaptive-robust-dev2-og-v1", "conditions": {}}
    for c in sorted({r["cond"] for r in recs}):
        b = [r for r in recs if r["cond"] == c and r["kind"] == "burst"]
        z = [r for r in recs if r["cond"] == c and r["kind"] == "q0"]
        row = {"in_family": D.OG[c][1], "pools": [len(b), len(z)]}
        for arm in ("N", "B", "B2"):
            row[arm] = {"class_correct": sum(bool(r[arm].get("class_correct")) for r in b),
                        "learned_correct": sum(bool(r[arm].get("learned_correct")) for r in b),
                        "false_accepts": sum(not r[arm]["no_burst"] for r in z)}
        row["B2"]["flagged"] = sum(r["B2"]["flagged"] for r in b + z)
        ph, bh = [r["B2"]["p_hat"] for r in b + z], [r["B2"]["b_hat"] for r in b + z]
        row["B2"]["p_hat"] = [float(np.mean(ph)), float(np.std(ph, ddof=1)) if len(ph) > 1 else 0.0]
        row["B2"]["b_hat"] = [float(np.mean(bh)), float(np.std(bh, ddof=1)) if len(bh) > 1 else 0.0]
        row["B2"]["objective_max"] = max(r["B2"]["objective"] for r in b + z)
        B2 = row["B2"]
        if D.OG[c][1]:
            row["verdict"] = ("PASS" if B2["class_correct"] >= 20 and B2["false_accepts"] <= 1 and B2["flagged"] <= 1
                              else "FAIL")
        else:
            row["verdict"] = "SAFE" if B2["false_accepts"] <= 1 else "UNSAFE"
        out["conditions"][c] = row
    fam = [v["verdict"] for c, v in out["conditions"].items() if D.OG[c][1]]
    oof = [v["verdict"] for c, v in out["conditions"].items() if not D.OG[c][1]]
    safe = all(x == "SAFE" for x in oof)
    out["overall"] = ("OG_SUPPORTED" if fam and all(x == "PASS" for x in fam) and safe else
                      "OG_PARTIAL" if sum(x == "PASS" for x in fam) >= 3 and safe else "OG_NOT_SUPPORTED")
    return out


def analyze_e2e(run, reps=20_000, boot_seed=20261120):
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    rng = np.random.default_rng(boot_seed)
    out = {"schema": "qshift-adaptive-robust-dev2-e2e-v1", "conditions": {}}
    for c in sorted({r["cond"] for r in recs}):
        rr = sorted([r for r in recs if r["cond"] == c], key=lambda r: r["root"])
        tot = {a: [0, 0, 0] for a in D.E2E_ARMS}
        pair = {"B2_vs_N": [0, 0], "B2_vs_true": [0, 0], "B2_vs_AstarB2": [0, 0]}
        q0pair = {"B2_vs_true": [0, 0], "B2_vs_Anom": [0, 0]}
        per_root_nz = {a: [] for a in ("L2L_B2", "Astar_B2")}
        for r in rr:
            z = np.load(run / "arrays" / f"{c}_r{r['root']}_errbits.npz")
            n = r["per_q"]["0.0"]["shots"]
            e = {(qi, a): np.unpackbits(z[f"q{qi}_{a}"])[:n].astype(bool) for qi in range(3) for a in D.E2E_ARMS}
            for qi, q in enumerate(D.QS):
                for a in D.E2E_ARMS:
                    if int(e[(qi, a)].sum()) != r["per_q"][str(q)]["errors"][a]:
                        raise ValueError("recorded count mismatch")
                    tot[a][qi] += int(e[(qi, a)].sum())
            for qi in (1, 2):
                for key, other in (("B2_vs_N", "L2L_N"), ("B2_vs_true", "L2s_true"), ("B2_vs_AstarB2", "Astar_B2")):
                    pair[key][0] += int((e[(qi, "L2L_B2")] & ~e[(qi, other)]).sum())
                    pair[key][1] += int((e[(qi, other)] & ~e[(qi, "L2L_B2")]).sum())
            for key, other in (("B2_vs_true", "L2s_true"), ("B2_vs_Anom", "A_nominal")):
                q0pair[key][0] += int((e[(0, "L2L_B2")] & ~e[(0, other)]).sum())
                q0pair[key][1] += int((e[(0, other)] & ~e[(0, "L2L_B2")]).sum())
            for a in per_root_nz:
                per_root_nz[a].append(int(e[(1, a)].sum() + e[(2, a)].sum()))
        cand, comp = np.array(per_root_nz["L2L_B2"]), np.array(per_root_nz["Astar_B2"])
        boots = []
        for _ in range(reps):
            i = rng.integers(0, len(rr), len(rr))
            boots.append(1 - cand[i].sum() / comp[i].sum() if comp[i].sum() > 0 else np.nan)
        boots = np.array(boots)
        nz = {a: tot[a][1] + tot[a][2] for a in D.E2E_ARMS}
        oracle = nz["L2s_true"]
        excess = pair["B2_vs_true"][0] - pair["B2_vs_true"][1]
        margin = 3 if oracle <= 12 else 0.25 * oracle
        p_repair = mcnemar_less(pair["B2_vs_N"][0], pair["B2_vs_N"][1])
        within = excess <= margin
        row = {"roots": len(rr), "errors_q0_q1_q2": tot, "nonzero_errors": nz,
               "discordance_nonzero": pair, "discordance_q0": q0pair,
               "repair_p_one_sided": p_repair, "excess_vs_oracle": excess, "oracle_margin": margin,
               "R_L2LB2_vs_AstarB2": {"estimate": (1 - nz["L2L_B2"] / nz["Astar_B2"]) if nz["Astar_B2"] else None,
                                      "95ci": [float(np.nanquantile(boots, 0.025)), float(np.nanquantile(boots, 0.975))]
                                      if np.isfinite(boots).any() else None},
               "flagged_roots": sum(bool(r["fit_b2"]["flagged"]) for r in rr),
               "learned_correct_B2": sum(r["learn_B2"].get("support") is not None and r["learn_B2"].get("learned_correct", False) for r in rr),
               "learned_correct_N": sum(bool(r["learn_N"].get("learned_correct")) for r in rr)}
        if c in ("Mlo", "Mz"):
            row["verdict"] = "REPAIRED" if p_repair < 0.01 and within else "NOT_REPAIRED"
        else:
            row["verdict"] = "NO_DEGRADATION" if within else "DEGRADED"
        out["conditions"][c] = row
    v = [x["verdict"] for x in out["conditions"].values()]
    good = [x in ("REPAIRED", "NO_DEGRADATION") for x in v]
    out["overall"] = "E2E_SUPPORTED" if good and all(good) else "E2E_PARTIAL" if any(good) else "E2E_NOT_SUPPORTED"
    return out


def cmd_analyze(study, mode, out_dir):
    run = WORK / f"{study}_{mode}"
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    res = analyze_og(run) if study == "og" else analyze_e2e(run)
    res["run_status"] = {k: st[k] for k in ("head", "started", "finished", "wall_seconds", "jobs")}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{study.upper()}.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"overall": res["overall"], **{c: v["verdict"] for c, v in res["conditions"].items()}}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("study", choices=["og", "e2e"])
    ap.add_argument("mode", choices=["eval", "rehearsal"])
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--expected-head", default="")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "run":
        cmd_run(a.study, a.mode, a.expected_head, a.workers)
    else:
        cmd_analyze(a.study, a.mode, a.out_dir)
