"""AD3 Phase 1 calibration screen (PLAN_AD3.md) -> AD3_SCREEN.json (write-once). Unlabelled detector rows for
tau; E1T + learner on short static windows for M. No evaluation decoding; screen seeds only; no seal.

  tau    20 static streams (4 per state A, B, C, D, none), 30 blocks: G of each block u >= 1 against the preceding
         min(6, u) blocks. tau = the smallest value with at most 1% of comparisons above it.
  power  (reported; stop rule) 20 streams with a change at block 15 (A->B, A->none, none->A, B->C, C->D), run
         online with tau (segment resets): detection within 1 and 2 blocks. Below 80% within 2 -> stop.
  M      windows of 1, 2, 3 blocks: 20 per burst A-D (+10 burst-free, descriptive). M = the smallest length with
         learned-exactly >= 95% and flags <= 5% over A-D; none qualifies -> M = 6.
"""
from __future__ import annotations

import json
import time
from multiprocessing import get_context

import numpy as np

import ad3
import ad3_config as C
import studykit as SK

SEEDS = None


def _seed(k):
    global SEEDS
    if SEEDS is None:
        SEEDS = json.loads((C.ROOT / "AD3_SEEDS.json").read_text(encoding="utf-8"))["screen_seeds"]
    return int(SEEDS[k])


def _st(x):
    return "none" if x is None else x


def stream_counts(kind, label, i, states):
    """Per-block detector counts for one stream; states[t] = burst name or None."""
    return [ad3.counts(ad3.sample_state(states[t], C.DET_PER_BLOCK,
                                        _seed(f"ad3screen:{kind}:{label}:{i}:b{t:02d}:det"))[0]) for t in range(C.BLOCKS)]


def null_job(args):
    st, i = args
    cs = stream_counts("null", _st(st), i, [st] * C.BLOCKS)
    return [ad3.g_stat(*cs[u], *ad3.pool(cs[max(0, u - C.WINDOW):u])) for u in range(1, C.BLOCKS)]


def power_job(args):
    a, b, i, tau = args
    states = [a if t < C.SCREEN_CHANGE_AT else b for t in range(C.BLOCKS)]
    cs = stream_counts("power", f"{_st(a)}-{_st(b)}", i, states)
    seg0, det = 0, []
    for u in range(1, C.BLOCKS):
        if ad3.g_stat(*cs[u], *ad3.pool(cs[ad3.segment_lo(seg0, u):u])) > tau:
            seg0 = u
            det.append(u)
    after = [u for u in det if u >= C.SCREEN_CHANGE_AT]
    return {"change": [_st(a), _st(b)], "i": i, "detected": det,
            "delay": (after[0] - C.SCREEN_CHANGE_AT) if after else None,
            "false_before": len([u for u in det if u < C.SCREEN_CHANGE_AT])}


def m_job(args):
    L, st, i = args
    import mm_contract as K
    classes = K.B.load_classes()
    d, lx, ly = [], [], []
    for t in range(L):
        d.append(ad3.sample_state(st, C.DET_PER_BLOCK, _seed(f"ad3screen:m{L}:{_st(st)}:{i}:b{t}:det"))[0])
        x, y = ad3.sample_state(st, C.LAB_PER_BLOCK, _seed(f"ad3screen:m{L}:{_st(st)}:{i}:b{t}:lab"))
        lx.append(x)
        ly.append(y)
    sup = C.BURSTS[st]["support"] if st else None
    t0 = time.perf_counter()
    _, _, est = ad3.ad2.estimate(d, lx, ly, classes, sup)
    return {"L": L, "state": _st(st), "i": i, "flagged": est["flagged"], "learned_correct": est["learned_correct"],
            "class_index": est["class_index"], "true_class": est["true_class"],
            "seconds": round(time.perf_counter() - t0, 1)}


def main(workers=8):
    out_p = C.ROOT / "AD3_SCREEN.json"
    if out_p.exists():
        raise SystemExit("AD3_SCREEN.json exists")
    t0 = time.perf_counter()
    with get_context("spawn").Pool(workers) as pool:
        gs = sorted(g for v in pool.map(null_job, [(st, i) for st in C.SCREEN_STATES
                                                    for i in range(C.SCREEN_NULL_PER_STATE)]) for g in v)
        allowed = int(np.floor(C.SCREEN_FALSE_ALARM_MAX * len(gs)))
        tau = float(gs[len(gs) - 1 - allowed])           # at most `allowed` comparisons strictly above tau
        power = pool.map(power_job, [(a, b, i, tau) for a, b in C.SCREEN_CHANGES
                                     for i in range(C.SCREEN_POWER_PER_CHANGE)])
        mres = pool.map(m_job, [(L, st, i) for L in C.SCREEN_M_LENGTHS for st in ("A", "B", "C", "D", None)
                                for i in range(C.SCREEN_M_PER_BURST if st else C.SCREEN_M_NONE)])
    within = {k: float(np.mean([p["delay"] is not None and p["delay"] <= k for p in power])) for k in (0, 1)}
    by_L = {}
    for L in C.SCREEN_M_LENGTHS:
        rb = [r for r in mres if r["L"] == L and r["state"] != "none"]
        rn = [r for r in mres if r["L"] == L and r["state"] == "none"]
        by_L[L] = {"learned_exactly": float(np.mean([r["learned_correct"] for r in rb])),
                   "flagged": float(np.mean([r["flagged"] for r in rb])),
                   "per_burst": {b: {"learned": sum(r["learned_correct"] for r in rb if r["state"] == b),
                                     "flagged": sum(r["flagged"] for r in rb if r["state"] == b),
                                     "n": sum(r["state"] == b for r in rb)} for b in "ABCD"},
                   "none": {"flagged": sum(r["flagged"] for r in rn),
                            "burst_accepted": sum((not r["flagged"]) and r["class_index"] is not None for r in rn),
                            "n": len(rn)}}
        by_L[L]["qualifies"] = bool(by_L[L]["learned_exactly"] >= C.SCREEN_M_LEARN_MIN
                                    and by_L[L]["flagged"] <= C.SCREEN_M_FLAG_MAX)
    M = next((L for L in C.SCREEN_M_LENGTHS if by_L[L]["qualifies"]), C.M_DEFAULT)
    stop = within[1] < C.SCREEN_POWER_MIN
    res = {"schema": "qshift-adaptive-robust-ad3-screen-v1",
           "null": {"comparisons": len(gs), "allowed_above": allowed, "max": gs[-1],
                    "quantiles": {str(q): float(np.quantile(gs, q)) for q in (0.5, 0.9, 0.99)}},
           "power": {"streams": power, "detected_same_block": within[0], "detected_within_2_blocks": within[1],
                     "false_before_change": sum(p["false_before"] for p in power)},
           "m": {"by_length": {str(L): v for L, v in by_L.items()}, "records": mres},
           "rule": {"tau": tau, "M": M, "stop": stop},
           "seconds": round(time.perf_counter() - t0, 1)}
    SK.write_once_json(out_p, ad3.ad2._jsonable(res))
    print(json.dumps({"tau": tau, "M": M, "stop": stop, "within": within,
                      "by_length": {L: {k: v[k] for k in ("learned_exactly", "flagged", "qualifies")}
                                    for L, v in by_L.items()}}, indent=1))


if __name__ == "__main__":
    main()
