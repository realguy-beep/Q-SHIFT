"""Roadmap step 1: full re-decode of Stage S DEVELOPMENT shots with two pre-declared variants (REDECODE_PROTOCOL.md).

  python redecode.py run [--workers 8]   decode every (condition, q, variant) chunk; write-once outputs in work/redecode
  python redecode.py analyze             paired comparison with the saved Stage S L2 error bits -> results/redecode

Reads only qshift_d5_lowp_regime_v1/work/dev (Stage S). Never reads Stage E. No sampling.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))

BASE = {"bp_method": "product_sum", "schedule": "serial", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10}
VARIANTS = {                                   # pre-declared; do not edit after the pre-registration commit
    "V1_min_sum_0.9": {**BASE, "bp_method": "minimum_sum", "ms_scaling_factor": 0.9},
    "V2_osd_cs40_bp200": {**BASE, "max_iter": 200, "osd_order": 40},
}
CHUNK = 25_000
IDENTITY_CHECK_SHOTS = 2_000                    # baseline re-decode on the first shots of each file
BOOT_REPS, BOOT_SEED = 20_000, 20261119
WORK, OUT = ROOT / "work" / "redecode", ROOT / "results" / "redecode"


def tasks():
    import floor_diagnostic as F
    out = []
    for cond in F.CONDS:
        for qi in range(3):
            n = len(F.load(cond, qi)[1])
            for v in VARIANTS:
                out += [(cond, qi, v, s, min(s + CHUNK, n)) for s in range(0, n, CHUNK)]
            out.append((cond, qi, "identity_check", 0, IDENTITY_CHECK_SHOTS))
    return out


def run_task(t):
    import floor_diagnostic as F
    from ldpc import BpOsdDecoder
    cond, qi, v, a, b = t
    path = WORK / f"{cond}_q{qi}_{v}_{a:06d}.npz"
    if path.exists():
        raise SystemExit(f"{path.name} exists; refusing to rerun")
    det, y, _ = F.load(cond, qi)
    dm = F.build(cond, qi)
    import scipy.sparse as sp
    H, L = sp.csr_matrix(dm.H), np.asarray(dm.L, dtype=np.int64).reshape(-1)
    cfg = BASE if v == "identity_check" else VARIANTS[v]
    dec = BpOsdDecoder(H, error_channel=list(map(float, dm.p)), **cfg)
    t0 = time.perf_counter()
    pred = np.empty(b - a, dtype=np.uint8)
    for k, i in enumerate(range(a, b)):
        e = np.asarray(dec.decode((det[i] ^ dm.offset_detectors).astype(np.uint8)), dtype=np.int64)
        pred[k] = (int(e @ L) % 2) ^ dm.offset_logical
    sec = time.perf_counter() - t0
    err = pred != y[a:b]
    np.savez_compressed(path, err=np.packbits(err), n=b - a, seconds=sec)
    return {"task": list(t), "errors": int(err.sum()), "seconds": round(sec, 1)}


def cmd_run(workers: int) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    ts = tasks()
    t0 = time.perf_counter()
    log = []
    with get_context("spawn").Pool(workers) as pool:
        for r in pool.imap_unordered(run_task, ts):
            log.append(r)
            print(json.dumps(r), f"{len(log)}/{len(ts)} {time.perf_counter() - t0:.0f}s", flush=True)
    (WORK / "RUN_LOG.json").write_text(json.dumps({"tasks": len(ts), "done": len(log), "log": log,
                                                   "wall_seconds": round(time.perf_counter() - t0, 1)}, indent=1))


def load_err(cond, qi, v, n):
    parts = sorted(WORK.glob(f"{cond}_q{qi}_{v}_*.npz"))
    errs = []
    for p in parts:
        with np.load(p) as z:
            errs.append(np.unpackbits(z["err"])[: int(z["n"])].astype(bool))
    e = np.concatenate(errs)
    if len(e) != n:
        raise ValueError(f"{cond} q{qi} {v}: {len(e)} shots, expected {n}")
    return e


def cmd_analyze() -> None:
    import floor_diagnostic as F
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(BOOT_SEED)
    res = {"schema": "qshift-adaptive-robust-redecode-v1", "protocol": "REDECODE_PROTOCOL.md",
           "data": "Stage S development arrays only", "variants": VARIANTS, "files": {}, "pooled": {}, "decision": {}}
    disc = {v: {"all": [], "q0": []} for v in VARIANTS}
    for cond in F.CONDS:
        for qi in range(3):
            _, y, base = F.load(cond, qi)
            idc = load_err(cond, qi, "identity_check", IDENTITY_CHECK_SHOTS)
            row = {"shots": int(len(y)), "L2_errors": int(base.sum()),
                   "identity_check_bit_equal": bool(np.array_equal(idc, base[:IDENTITY_CHECK_SHOTS]))}
            for v in VARIANTS:
                ev = load_err(cond, qi, v, len(y))
                vo, bo = int((ev & ~base).sum()), int((base & ~ev).sum())
                row[v] = {"errors": int(ev.sum()), "variant_only": vo, "L2_only": bo, "net": vo - bo}
                d = (ev.astype(np.int8) - base.astype(np.int8))[ev != base]     # +1 variant-only, -1 L2-only
                disc[v]["all"].append((d, len(y)))
                if qi == 0:
                    disc[v]["q0"].append((d, len(y)))
            res["files"][f"{cond}_q{qi}"] = row
    from math import comb

    def mcnemar_one_sided(vo, bo):        # P(X <= vo) for X ~ Bin(vo+bo, 1/2): evidence variant has fewer errors
        n = vo + bo
        return 1.0 if n == 0 else sum(comb(n, k) for k in range(vo + 1)) / 2 ** n

    for v in VARIANTS:
        out = {}
        for scope in ("all", "q0"):
            ds = disc[v][scope]
            d = np.concatenate([x for x, _ in ds]) if ds else np.array([], np.int8)
            shots = sum(n for _, n in ds)
            vo, bo = int((d > 0).sum()), int((d < 0).sum())
            # iid-shot paired bootstrap of the net count: resample discordant outcomes among `shots` shots
            # (non-discordant shots contribute 0); multinomial over {+1, -1, 0}
            probs = np.array([vo, bo, shots - vo - bo], dtype=float) / shots
            draws = rng.multinomial(shots, probs, size=BOOT_REPS)
            net = draws[:, 0] - draws[:, 1]
            out[scope] = {"shots": shots, "variant_only": vo, "L2_only": bo, "net": vo - bo,
                          "net_95ci": [float(np.quantile(net, 0.025)), float(np.quantile(net, 0.975))],
                          "net_upper_95_one_sided": float(np.quantile(net, 0.95)),
                          "mcnemar_one_sided_p": mcnemar_one_sided(vo, bo)}
        res["pooled"][v] = out
        advance = out["all"]["net_95ci"][1] < 0 and out["q0"]["net"] <= 0
        res["decision"][v] = "ADVANCE_TO_FRESH_VALIDATION" if advance else "DO_NOT_ADVANCE"
    res["identity_checks_all_pass"] = all(r["identity_check_bit_equal"] for r in res["files"].values())
    res["overall"] = ("H-F1_SUPPORTED" if any(x == "ADVANCE_TO_FRESH_VALIDATION" for x in res["decision"].values())
                      else "H-F2_FLOOR_DEGENERACY_DOMINATED")
    if not res["identity_checks_all_pass"]:
        res["overall"] = "INVALID_IDENTITY_CHECK_FAILED"
    log = json.loads((WORK / "RUN_LOG.json").read_text())
    res["wall_seconds"] = log["wall_seconds"]
    res["cpu_seconds_by_variant"] = {v: round(sum(r["seconds"] for r in log["log"] if r["task"][2] == v), 1)
                                     for v in list(VARIANTS) + ["identity_check"]}
    (OUT / "REDECODE.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    cmd_run(a.workers) if a.cmd == "run" else cmd_analyze()
