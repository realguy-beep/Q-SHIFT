"""CF1 analysis (PLAN_CF1.md section 2): H1-H4 by paired sign-flip tests on episode totals, Holm over the family.

  python cf1_analyze.py <out_dir>        # CF1_ANALYSIS.json from work/cf1 (run twice -> byte-identical)

Unit: the episode. d = W0F errors - comparator errors over scored blocks 6-29 (24 errors = 0.001 LER).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np

import cf1_config as C


# ------------------------------------------------------------------ statistics
def signflip_p(d, margin, n_flips=C.N_FLIPS, seed=C.PERM_SEED, exact_max_n=C.EXACT_MAX_N):
    """One-sided p for H0: mean(d) >= margin against mean(d) < margin. Exact enumeration when n <= exact_max_n."""
    x = np.asarray(d, dtype=float) - margin
    n = len(x)
    obs = x.mean()
    tol = 1e-9
    if n <= exact_max_n:
        signs = np.array(list(itertools.product((1.0, -1.0), repeat=n)))
        null = signs @ x / n
        return float(np.sum(null <= obs + tol) / len(null)), "exact"
    rng = np.random.default_rng(seed)
    hits, done, chunk = 0, 0, 20_000
    while done < n_flips:
        m = min(chunk, n_flips - done)
        s = rng.choice((1.0, -1.0), size=(m, n))
        hits += int(np.sum(s @ x / n <= obs + tol))
        done += m
    return float((1 + hits) / (1 + n_flips)), "monte_carlo"


def boot_upper(d, n_boot=C.N_BOOT, seed=C.BOOT_SEED, level=0.95):
    """One-sided percentile-bootstrap upper bound on mean(d)."""
    x = np.asarray(d, dtype=float)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(axis=1)
    return float(np.quantile(means, level))


def holm(ps, alpha=C.ALPHA):
    """-> {name: reject} by Holm's step-down procedure."""
    order = sorted(ps, key=lambda k: (ps[k], k))
    out, go = {}, True
    for i, k in enumerate(order):
        go = go and ps[k] <= alpha / (len(order) - i)
        out[k] = bool(go)
    return out


# ------------------------------------------------------------------ records
def episode_totals(run, episodes):
    """Verify archives against stored counts and return {schedule: {arm: [errors per episode]}}."""
    run = Path(run)
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    if len(recs) != sum(episodes.values()):
        raise SystemExit(f"{len(recs)} records, expected {sum(episodes.values())}")
    out = {}
    for r in recs:
        if hashlib.sha256((run / r["archive"]).read_bytes()).hexdigest() != r["archive_sha256"]:
            raise ValueError("archive hash")
        z = np.load(run / r["archive"])
        for b in r["blocks"]:
            for a in r["arms"]:
                if int(np.unpackbits(z[f"b{b['block']:02d}_{a}"])[: r["eval_per_block"]].sum()) != b["errors"][a]:
                    raise ValueError("count mismatch")
    for s in episodes:
        rr = sorted([r for r in recs if r["schedule"] == s], key=lambda r: r["episode"])
        if [r["episode"] for r in rr] != list(range(episodes[s])):
            raise SystemExit(f"episodes of {s} incomplete")
        out[s] = {a: [sum(b["errors"][a] for b in r["blocks"]) for r in rr] for a in rr[0]["arms"]}
        out[s]["_switches_W0F"] = [sum(r["blocks"][i]["keys"]["W0F"] != r["blocks"][i - 1]["keys"]["W0F"]
                                       for i in range(1, len(r["blocks"]))) for r in rr]
        out[s]["_triggers_W0F"] = [sum(b["source"]["W0F"] == "static_fallback" for b in r["blocks"]) for r in rr]
    return out


def hypotheses(T):
    res, ps = {}, {}
    for name, kind, comp, panels, margin in C.HYPOTHESES:
        d = [x - y for s in panels for x, y in zip(T[s][C.TEST_ARM], T[s][comp])]
        p, how = signflip_p(d, margin)
        res[name] = {"kind": kind, "comparator": comp, "panels": list(panels), "margin": margin, "n": len(d),
                     "d": d, "mean_d": float(np.mean(d)), "upper95": boot_upper(d), "p": p, "p_method": how}
        ps[name] = p
    rej = holm(ps)
    for k in res:
        res[k]["holm_reject_H0"] = rej[k]
    return res


def analyze(run):
    st = json.loads((Path(run) / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    T = episode_totals(run, C.EPISODES)
    n_rows = len(C.SCORED) * C.EVAL_PER_BLOCK
    per = {s: {"episodes": C.EPISODES[s],
               "errors": {a: int(sum(v)) for a, v in T[s].items() if not a.startswith("_")},
               "errors_per_episode": {a: v for a, v in T[s].items() if not a.startswith("_")},
               "ler": {a: float(sum(v) / (len(v) * n_rows)) for a, v in T[s].items() if not a.startswith("_")},
               "W0F_switches": T[s]["_switches_W0F"], "W0F_triggers": T[s]["_triggers_W0F"]} for s in C.SCHEDULES}
    return {"schema": "qshift-decoder-bank-cf1-analysis-v1",
            "run_status": {k: st.get(k) for k in ("head", "started", "finished", "wall_seconds", "n_jobs", "reruns")},
            "hypotheses": hypotheses(T), "panels": per}


def main(out_dir):
    import studykit as SK
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    res = analyze(C.ROOT / "work" / "cf1")
    SK.write_once_json(o / "CF1_ANALYSIS.json", res)
    print(json.dumps({k: {f: v[f] for f in ("mean_d", "upper95", "p", "holm_reject_H0")}
                      for k, v in res["hypotheses"].items()}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
