"""BRE-0: deterministic footprint census (PLAN_BRE.md). No sampling.

For every weight-3 support in the RE1 candidate pool plus K, M0, M1, CR, and for each BRE condition plus the nominal
model: exact detector rates of the burst circuit at q in {0, 0.01, 0.02} (he1.detector_rates), the expected
calibration pool (equal q mix), its footprint, and the H-E1b grid fit on the EXPECTED rates (weights n = 12,000).
A stratified subsample (SUB per footprint stratum per condition) also gets the refined B2 fit and E1.

  python bre_census.py run [--workers 8]     per-support rows -> work/bre/census/ROWS.json (git-ignored)
  python bre_census.py recheck [--workers 8] the final E1 (one-sided start, a BRE-0 build change) on the SAME
                                             subsample -> work/bre/census/REFINED_E1_FINAL.json
  python bre_census.py summarize             aggregates only -> results/bre/census/CENSUS.json

Only aggregates are published, so per-support values cannot be matched against RE1's published R6 objectives.
"""
from __future__ import annotations

import argparse
import json
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import bre_config as C

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work" / "bre" / "census"
RES = ROOT / "results" / "bre" / "census"
CONDS = {"NOM": C.NOMINAL} | {c: v[0] for c, v in C.CONDITIONS.items()}
SUB = 10                                    # per stratum per condition, for the refined fits
SUB_SEED = 20261119                         # public; selects the census subsample only


def supports():
    import re1_seal
    return sorted(set(re1_seal.candidate_pool()) | set(C.FIXED_T.values()))


def _rates(spec, q, sup):
    import he1 as H
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    c = m.build_candidate_circuit(spec, q, tuple(sup)) if q > 0 else m.build_base_circuit(spec)
    return H.detector_rates(c.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True))


def stratum(fp):
    return next(i for i, (a, b) in enumerate(C.FOOTPRINT_STRATA) if a <= fp <= b)


def job(args):
    cond, sups = args
    import estimate3 as E3
    import he1b as HB
    spec = C.spec(**CONDS[cond])
    base = _rates(spec, 0.0, None)
    rows = []
    for s in sups:
        r1, r2 = _rates(spec, 0.01, s), _rates(spec, 0.02, s)
        obs = (base + r1 + r2) / 3
        n = C.N_CAL
        lo, w = np.log(obs), n * obs
        g = ((lo[None, None, :] - HB.grid()) ** 2 * w)
        k = int(np.floor(HB.TRIM * g.shape[-1]))
        og = np.sort(g, axis=-1)[..., : g.shape[-1] - k].sum(axis=-1)
        bi, pi = np.unravel_index(int(np.argmin(og)), og.shape)
        rows.append({"cond": cond, "support": list(s), "footprint": E3.footprint(base, r2),
                     "grid_obj": float(og[bi, pi]), "grid_p": float(HB.P_GRID[pi]), "grid_b": float(HB.B_GRID[bi])})
    return rows


def refine_job(args):
    cond, s = args
    import estimate3 as E3
    spec = C.spec(**CONDS[cond])
    base = _rates(spec, 0.0, None)
    obs = (base + _rates(spec, 0.01, s) + _rates(spec, 0.02, s)) / 3
    b2 = E3.fit_masked(obs, C.N_CAL)
    e1 = E3.fit_e1(obs, C.N_CAL)
    keep = ("p_hat", "b_hat", "objective")
    return {"cond": cond, "support": list(s), "B2": {k: b2[k] for k in keep},
            "E1": {k: e1[k] for k in keep + ("excluded", "stat", "stable")}}


def recheck_job(args):
    cond, s = args
    import estimate3 as E3
    spec = C.spec(**CONDS[cond])
    base = _rates(spec, 0.0, None)
    obs = (base + _rates(spec, 0.01, s) + _rates(spec, 0.02, s)) / 3
    e1 = E3.fit_e1(obs, C.N_CAL)
    return {"cond": cond, "support": list(s),
            "E1": {k: e1[k] for k in ("p_hat", "b_hat", "objective", "excluded", "stat", "stable")}}


def cmd_recheck(workers):
    out = WORK / "REFINED_E1_FINAL.json"
    if out.exists():
        raise SystemExit("recheck exists")
    d = json.loads((WORK / "ROWS.json").read_text(encoding="utf-8"))
    picks = [(r["cond"], tuple(r["support"])) for r in d["refined"]]
    with get_context("spawn").Pool(workers) as pool:
        res = pool.map(recheck_job, picks)
    out.write_text(json.dumps({"refined": res}) + "\n", encoding="utf-8")
    print(len(res), "rechecked")


def cmd_run(workers):
    out = WORK / "ROWS.json"
    if out.exists():
        raise SystemExit("census rows exist; BRE-0 runs once")
    WORK.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    sups = supports()
    chunks = [(c, sups[i::workers]) for c in CONDS for i in range(workers)]
    rows = []
    with get_context("spawn").Pool(workers) as pool:
        for r in pool.imap_unordered(job, chunks):
            rows += r
    rng = np.random.default_rng(SUB_SEED)
    picks = []
    for c in CONDS:
        by = {}
        for r in rows:
            if r["cond"] == c:
                by.setdefault(stratum(r["footprint"]), []).append(tuple(r["support"]))
        for st in sorted(by):
            pool_s = sorted(by[st])
            for i in rng.choice(len(pool_s), size=min(SUB, len(pool_s)), replace=False):
                picks.append((c, pool_s[int(i)]))
    with get_context("spawn").Pool(workers) as pool:
        refined = list(pool.imap_unordered(refine_job, picks))
    out.write_text(json.dumps({"rows": rows, "refined": refined, "n_supports": len(sups),
                               "wall_seconds": round(time.perf_counter() - t0, 1)}) + "\n", encoding="utf-8")
    print(len(rows), "rows;", len(refined), "refined;", f"{time.perf_counter() - t0:.0f}s")


def _q(v):
    v = np.asarray(v, float)
    return {"min": float(v.min()), "p50": float(np.median(v)), "p90": float(np.quantile(v, 0.9)), "max": float(v.max()),
            "n": int(len(v))}


def cmd_summarize():
    import estimate2 as E
    d = json.loads((WORK / "ROWS.json").read_text(encoding="utf-8"))
    thr = E.flag_threshold()
    median_dev = json.loads((ROOT / "FLAG_THRESHOLD.json").read_text(encoding="utf-8"))["median"]
    excess_cut = thr - median_dev
    fp_ = WORK / "REFINED_E1_FINAL.json"
    fin = json.loads(fp_.read_text(encoding="utf-8"))["refined"] if fp_.exists() else None
    out = {"schema": "qshift-adaptive-robust-bre-census-v1", "n_supports": d["n_supports"],
           "flag_threshold": thr, "dev_median_objective": median_dev,
           "excess_rule": "a support is 'likely flagged' when its expected-rate grid objective exceeds threshold - "
                          "median development objective (sampling noise adds about the median); heuristic",
           "strata": [list(s) for s in C.FOOTPRINT_STRATA], "conditions": {}}
    for c in CONDS:
        rows = [r for r in d["rows"] if r["cond"] == c]
        tru = CONDS[c]
        fps = sorted({r["footprint"] for r in rows})
        by_fp = {}
        for f in fps:
            rr = [r for r in rows if r["footprint"] == f]
            by_fp[str(f)] = {"supports": len(rr), "grid_obj": _q([r["grid_obj"] for r in rr]),
                             "likely_flagged": sum(r["grid_obj"] > excess_cut for r in rr),
                             "grid_b": {str(b): sum(r["grid_b"] == b for r in rr) for b in sorted({r["grid_b"] for r in rr})}}
        ref = [r for r in d["refined"] if r["cond"] == c]
        out["conditions"][c] = {
            "true": tru, "supports": len(rows), "footprint": {str(f): sum(r["footprint"] == f for r in rows) for f in fps},
            "likely_flagged_fraction": float(np.mean([r["grid_obj"] > excess_cut for r in rows])),
            "by_footprint": by_fp,
            "refined_subsample": {
                "n": len(ref),
                "B2_objective": _q([r["B2"]["objective"] for r in ref]),
                "E1_objective": _q([r["E1"]["objective"] for r in ref]),
                "B2_b_hat": _q([r["B2"]["b_hat"] for r in ref]), "E1_b_hat": _q([r["E1"]["b_hat"] for r in ref]),
                "B2_p_hat": _q([r["B2"]["p_hat"] for r in ref]), "E1_p_hat": _q([r["E1"]["p_hat"] for r in ref]),
                "E1_excluded": _q([r["E1"]["excluded"] for r in ref]),
                "E1_stable": sum(r["E1"]["stable"] for r in ref)}}
        if fin is not None:
            ff = [r for r in fin if r["cond"] == c]
            tb = CONDS[c].get("bias_ratio", 1.0) if CONDS[c].get("regime") == "z_biased" else 1.0
            out["conditions"][c]["refined_subsample"]["E1_final"] = {
                "objective": _q([r["E1"]["objective"] for r in ff]), "b_hat": _q([r["E1"]["b_hat"] for r in ff]),
                "p_hat": _q([r["E1"]["p_hat"] for r in ff]), "excluded": _q([r["E1"]["excluded"] for r in ff]),
                "stable": sum(r["E1"]["stable"] for r in ff),
                "b_within_2pct": sum(abs(r["E1"]["b_hat"] / tb - 1) <= 0.02 for r in ff)}
    out["wall_seconds"] = d["wall_seconds"]
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "CENSUS.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({c: {"likely_flagged": v["likely_flagged_fraction"], "footprint": v["footprint"]}
                      for c, v in out["conditions"].items()}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "recheck", "summarize"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    {"run": lambda: cmd_run(a.workers), "recheck": lambda: cmd_recheck(a.workers), "summarize": cmd_summarize}[a.cmd]()
