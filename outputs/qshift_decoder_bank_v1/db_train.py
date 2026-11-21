"""DB1 training on training seeds only -> TRAINING.json (write-once). No validation episode is touched.

  templates  per bank state, 20 blocks x 2,000 detector rows -> per-detector rate template
  tau_fit[L] per state, 4 static streams x 30 blocks; windows of L = 1..6 consecutive blocks; G_fit against the
             state's own template; tau_fit[L] = max over states of the 99.5% quantile. Confusion diagnostics on
             the same windows (plausible-set size; best-fit accuracy).
  risk       per state, 5,000 labelled rows decoded by every bank key (paired rows) -> LER table R[state][key]
  static     the single bank key with the lowest mean LER over the five states (equal weights)
"""
from __future__ import annotations

import json
import time
from multiprocessing import get_context

import numpy as np

import db_config as C
import db_core as D

_S = None


def tseed(k):
    global _S
    if _S is None:
        _S = json.loads((C.ROOT / "DB1_SEEDS.json").read_text(encoding="utf-8"))["train_seeds"]
    return int(_S[k])


def tpl_fit_job(st):
    tk, tn = D.pool([D.counts(D.sample(st, C.DET_PER_BLOCK, tseed(f"db1train:tpl:{st}:b{b:02d}"))[0])
                     for b in range(C.TEMPLATE_BLOCKS)])
    fit = [[[int(v) for v in D.counts(D.sample(st, C.DET_PER_BLOCK, tseed(f"db1train:fit:{st}:{i}:b{b:02d}"))[0])[0]]
            for b in range(C.FIT_BLOCKS)] for i in range(C.FIT_STREAMS)]
    return st, D.template(tk, tn).tolist(), fit


def risk_job(args):
    st, key = args
    import re1
    x, y = D.sample(st, C.RISK_ROWS, tseed(f"db1train:risk:{st}"))
    t0 = time.perf_counter()
    dec = re1.decoders(C.spec(gate_p=C.P0, measurement_p=C.P0), C.support(key))[0]
    err = int((re1.predict(dec, x, "l2") != y).sum())
    return st, key, err, round(time.perf_counter() - t0, 1)


def main(workers=8):
    out_p = C.ROOT / "TRAINING.json"
    if out_p.exists():
        raise SystemExit("TRAINING.json exists")
    t0 = time.perf_counter()
    with get_context("spawn").Pool(workers) as pool:
        rj = pool.map_async(risk_job, [(s, a) for s in C.STATES for a in C.STATES])
        tf = pool.map(tpl_fit_job, C.STATES)
        risk_rows = rj.get()
    tpl = {s: np.array(t) for s, t, _ in tf}
    fit = {s: f for s, _, f in tf}
    n1 = C.DET_PER_BLOCK
    own, cross = {}, {}
    for L in range(1, C.WINDOW + 1):
        for s in C.STATES:
            for stream in fit[s]:
                for b0 in range(C.FIT_BLOCKS - L + 1):
                    k = np.sum(stream[b0:b0 + L], axis=0)
                    g = {a: D.g_fit(k, n1 * L, tpl[a]) for a in C.STATES}
                    own.setdefault(L, {}).setdefault(s, []).append(g[s])
                    cross.setdefault(L, {}).setdefault(s, []).append(g)
    tau = {str(L): float(max(np.quantile(own[L][s], C.FIT_QUANTILE) for s in C.STATES)) for L in own}
    diag = {}
    for L in own:
        d = {}
        for s in C.STATES:
            gs = cross[L][s]
            P = [[a for a in C.STATES if g[a] <= tau[str(L)]] for g in gs]
            d[s] = {"windows": len(gs), "own_in_plausible": float(np.mean([s in p for p in P])),
                    "plausible_size_mean": float(np.mean([len(p) for p in P])),
                    "others_plausible": {a: float(np.mean([a in p for p in P])) for a in C.STATES if a != s},
                    "best_fit_correct": float(np.mean([min(C.STATES, key=lambda a: g[a]) == s for g in gs])),
                    "own_g_median": float(np.median(own[L][s]))}
        diag[str(L)] = d
    errs = {s: {} for s in C.STATES}
    secs = 0.0
    for s, a, e, sec in risk_rows:
        errs[s][a] = e
        secs += sec
    risk = {s: {a: errs[s][a] / C.RISK_ROWS for a in C.STATES} for s in C.STATES}
    mean = {a: float(np.mean([risk[s][a] for s in C.STATES])) for a in C.STATES}
    static = min(C.STATES, key=lambda a: (mean[a], C.STATES.index(a)))
    res = {"schema": "qshift-decoder-bank-db1-training-v1", "templates": {s: tpl[s].tolist() for s in C.STATES},
           "tau_fit": tau, "fit_quantile": C.FIT_QUANTILE, "fit_diagnostics": diag,
           "risk_rows": C.RISK_ROWS, "risk_errors": errs, "risk": risk, "static_mean_ler": mean, "static_key": static,
           "decode_seconds": round(secs, 1), "seconds": round(time.perf_counter() - t0, 1)}
    import studykit as SK
    SK.write_once_json(out_p, res)
    print(json.dumps({"tau_fit": tau, "static": static, "mean": mean, "risk_errors": errs,
                      "own_in_P_L1": {s: diag["1"][s]["own_in_plausible"] for s in C.STATES},
                      "Psize_L1": {s: diag["1"][s]["plausible_size_mean"] for s in C.STATES},
                      "best_fit_L1": {s: diag["1"][s]["best_fit_correct"] for s in C.STATES}}, indent=1))


if __name__ == "__main__":
    main()
