"""ROB1 (PROTOCOL_ROB1.md, draft 2).

  python rob1.py time                 # TIMING.json: random matrices of the real sizes only
  python rob1.py freeze               # ROB1_FREEZE.json; computes nothing for any unknown X
  python rob1.py run <new folder>     # separate approval
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

import model as R  # noqa: I001  (blocks every sampler)
import t1 as T1
import t2 as T2
from model import C, IDENT, M, Q, ROOT, S
import ident1 as I

REPO = I.REPO
FREEZE = ROOT / "ROB1_FREEZE.json"
OWN = ("PROTOCOL_ROB1.md", "model.py", "t1.py", "t2.py", "rob1.py", "TIMING.json", "tests/test_rob1.py")
NS = (2_000, 4_000, 12_000)
CUT = (377, 209)
STATES = C.STATES


# ------------------------------------------------------------------ freeze
def ident_ok():
    fz = json.loads(I.FREEZE.read_text(encoding="utf-8"))
    return all(I.sha(REPO / f) == h for f, h in fz["files"].items()) and fz["runtime"] == I.runtime()


def files():
    stage1 = [f"results/stage1_run1/{n}.json" for n in ("F0", "F1")]
    return sorted(set(I.files()) | {(ROOT / f).relative_to(REPO).as_posix() for f in OWN} |
                  {(IDENT / f).relative_to(REPO).as_posix() for f in ("IDENT1_FREEZE.json", "CORRECTION_1.md", *stage1)})


def target_list():
    """[(group, weight, support, signature)]: DESIGN weight 1-3, SEEN, 200 DESIGN weight 4. HELD never appears."""
    cls, _ = S.classes(4)
    xs = I.targets("F1")                                  # asserts that HELD stays closed
    sp = S.split()
    key = lambda x: hashlib.sha256(("qshift-rob1:" + json.dumps(sorted(list(v) for v in cls[x[3]]))).encode()).hexdigest()  # noqa: E731
    four = sorted((x for x in xs if x[0] == "DESIGN" and x[1] == 4), key=key)[:200]
    out = [("DESIGN_1_3", *x[1:]) for x in xs if x[0] == "DESIGN" and x[1] <= 3]
    out += [("SEEN", *x[1:]) for x in xs if x[0] == "SEEN"] + [("DESIGN_4", *x[1:]) for x in four]
    if any(sp[x[3]] == "HELD" for x in out):
        raise AssertionError("HELD must stay closed")
    if Counter(x[0] for x in out) != {"DESIGN_1_3": 418, "SEEN": 84, "DESIGN_4": 200}:
        raise AssertionError("target counts")
    return out


def target_hash():
    return hashlib.sha256(json.dumps([[a, b, list(c)] for a, b, c, _ in target_list()]).encode()).hexdigest()


def freeze():
    if not ident_ok():
        raise SystemExit("IDENT1 differs from its freeze")
    doc = {"schema": "qshift-rob1-freeze-1", "files": {f: I.sha(REPO / f) for f in files()}, "runtime": I.runtime(),
           "targets_sha256": target_hash(), "main_grid": R.main_grid(), "slice_grid": R.slice_grid(), "q_x": R.QX, "n": NS,
           "cut_offs": CUT, "alpha": T2.ALPHA, "timing": json.loads((ROOT / "TIMING.json").read_text(encoding="utf-8"))}
    with open(FREEZE, "x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")


def verify():
    fz = json.loads(FREEZE.read_text(encoding="utf-8"))
    bad = [f for f in sorted(set(fz["files"]) | set(files())) if fz["files"].get(f) != I.sha(REPO / f)]
    if bad or fz["runtime"] != I.runtime() or fz["targets_sha256"] != target_hash() or not ident_ok():
        raise SystemExit(f"differs from the freeze: {bad}")
    git = lambda *a: subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True, check=True).stdout.strip()  # noqa: E731
    if git("status", "--porcelain", "--untracked-files=no") or not git("ls-files", FREEZE.relative_to(REPO).as_posix()):
        raise SystemExit("the freeze is not committed, or tracked files are modified")
    return {"head": git("rev-parse", "HEAD"), "freeze_sha256": I.sha(FREEZE), "runtime": I.runtime()}


# ------------------------------------------------------------------ timing on random matrices
def timing():
    rng = np.random.default_rng(0)
    k, pts, nx = 2138, len(R.main_grid()) + len(R.slice_grid()), 702 * len(R.QX)
    A = rng.normal(size=(k, k))
    K = A @ A.T + k * np.eye(k)
    L = K / K.max()
    D = rng.normal(size=(T1.BLOCK, k))
    B = rng.choice([-1.0, 1.0], (k, 5))

    class Fake:
        lm, L = np.zeros(k), None
    Fake.L = L

    def clock(f, reps):
        t = time.time()
        for _ in range(reps):
            f()
        return (time.time() - t) / reps
    form = clock(lambda: Q.model_cov(Fake, B, 0.01), 3)
    solve = clock(lambda: Q.Solver(K).solve(D.T), 3)
    W = rng.normal(size=(pts, k))
    var = clock(lambda: np.einsum("ij,ij->i", W @ K, W), 3)
    blocks = -(-nx // T1.BLOCK)
    t1 = blocks * pts * (form + solve) + nx * (form + var)
    r = rng.random((pts, k)) * 0.1
    t = time.time()
    lo, hi = T2.interval(2000, r, T2.tail(k))
    x = rng.random((nx, k)) * 0.1
    T2.least(T2.accept(2000, x, *T2.hull(lo, hi)))
    t2 = time.time() - t
    doc = {"note": "random matrices only", "features": k, "bank_points": pts, "models": nx, "block": T1.BLOCK,
           "seconds_form": round(form, 3), "seconds_solve": round(solve, 3), "seconds_variance": round(var, 3),
           "t1_f1_minutes": round(t1 / 60, 1), "t2_minutes_bound": round(t2 * 5 * 2 * 3 / 60, 1),
           "statistics_memory_gb": round(T1.BLOCK * pts * k * 8 / 1e9, 2)}
    (ROOT / "TIMING.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(doc)


# ------------------------------------------------------------------ run
def own(sig, st, banks):
    return st != "OFF" and banks[st] == sig


def feature_kind(f, co):
    if len(f) == 1:
        return "single"
    a, b = co[f[0]], co[f[1]]
    return f"pair distance {max(abs(a[0] - b[0]), abs(a[1] - b[1])):g} rounds {abs(a[2] - b[2]):g}"


def direct_accept(n, x, lo, hi):
    """Binomial probability of lo..hi by summing the mass function from logs (second method)."""
    if x <= 0:
        return float(lo <= 0 <= hi)
    s = [math.exp(math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * math.log(x) + (n - j) * math.log1p(-x))
         for j in range(int(lo), int(hi) + 1)]
    return math.fsum(s)


def family(fam, xs, log):
    feats = R.features(fam)
    banks, bank = R.bank_signatures(), R.bank_signs(feats)
    BX = [Q.burst_signs(x[3], feats) for x in xs]
    models = [(B, q) for B in BX for q in R.QX]
    grids = {"main": R.main_grid(), "slice": R.slice_grid()}
    pts = grids["main"] + grids["slice"]
    # 20 (point, SEEN model) pairs for the T1 variance check
    seen = [i for i, x in enumerate(xs) if x[0] == "SEEN"]
    keep = {(17 * j % len(pts), seen[4 * j] * len(R.QX) + j % len(R.QX)) for j in range(20)}
    J, dropped, kept = T1.j_values(pts, feats, models, R.ExactBase, log, keep=keep)
    for (i, j), (w, v) in kept.items():                    # direct covariance of the full exact model (not base + burst)
        B, q = models[j]
        E, lw = R.exact_errors(xs[j // len(R.QX)][2], C.P0, C.P0, q)
        d = float(w @ M.covariance(M.signs(E, feats), lw) @ w)
        if abs(v - d) > 1e-8 * abs(d) + 1e-12:
            raise RuntimeError(f"check failed: T1 variance {fam} {i} {j} {v} {d}")
    if len(kept) != len(keep):
        raise RuntimeError("check failed: T1 variance pairs missing")
    log(f"{fam} T1 variance check passed")
    bases = {p: R.ExactBase(feats, p) for p in sorted({p for _, p, _ in pts})}
    x0 = bases[(C.P0, C.P0)]
    rx = R.rates(np.array([Q.model_mean(x0, B, q) for B, q in models]), feats)
    co = R.m.build_base_circuit(S.SPEC).get_detector_coordinates()
    kind = [feature_kind(f, co) for f in feats]
    res = [{"group": g, "weight": w, "support": list(sup), "own": [s for s in STATES if own(sig, s, banks)],
            "q": {str(q): {"T1": {}, "T2": {}} for q in R.QX}} for g, w, sup, sig in xs]
    checked, off = 0, 0
    for name, grid in grids.items():
        for st in STATES:
            ix = [i for i, pt in enumerate(grid) if pt[0] == st]
            sub = J[[off + i for i in ix]]
            at = sub.argmin(axis=0)
            rb = R.rates(np.array([Q.model_mean(bases[grid[i][1]], bank[st], grid[i][2]) for i in ix]), feats)
            t2 = {n: T2.bound(n, rx, rb) for n in NS}
            for j in range(len(models)):
                e = res[j // len(R.QX)]["q"][str(R.QX[j % len(R.QX)])]
                pt = grid[ix[at[j]]]
                e["T1"].setdefault(name, {})[st] = {"J": float(sub[at[j], j]), "at": pt[1:],
                                                   "edge": bool(name == "main" and R.is_edge(pt))}
                o = {}
                for n, (B, f, (lo, hi)) in t2.items():
                    c = int(f[j])
                    ends = [[ix[i] for i in np.flatnonzero(v[:, c] == z)] for v, z in ((lo, lo[:, c].min()), (hi, hi[:, c].max()))]
                    # an end counts as an edge end if any grid point that sets it is at the grid edge
                    o[str(n)] = {"B": float(B[j]), "feature": kind[c], "ends": [grid[v[0]][1:] for v in ends],
                                 "edge": [bool(name == "main" and any(R.is_edge(grid[i]) for i in v)) for v in ends]}
                e["T2"].setdefault(name, {})[st] = o
            if name == "main":                             # 10 SEEN models per state: 50 pairs, every feature by a second method
                lo, hi = t2[2000][2]
                a, b = lo.min(axis=0), hi.max(axis=0)
                for u in range(10):
                    j = seen[8 * u] * len(R.QX) + u % len(R.QX)
                    d = min(direct_accept(2000, rx[j, c], a[c], b[c]) for c in range(len(feats)))
                    if abs(d - t2[2000][0][j]) > 1e-9:
                        raise RuntimeError(f"check failed: T2 probability {fam} {st} {j}")
                    checked += 1
            log(f"{fam} {name} {st} done")
        off += len(grid)
    if checked != 50:
        raise RuntimeError("check failed: T2 pairs missing")
    return res, {"features": len(feats), "dropped_directions": dropped, "t1_variance_pairs": len(kept), "t2_pairs": checked}


def reading(c):
    return "SURVIVES" if c >= CUT[0] else "PARTIAL" if c >= CUT[1] else "FAILS"


def passes(e, q, test, grid, n):
    t = e["q"][str(q)][test][grid]
    st = [s for s in STATES if s not in e["own"]]
    if test == "T1":
        return all(n * t[s]["J"] >= Q.SEPARATED for s in st)
    return all(t[s][str(n)]["B"] <= Q.ACCEPT for s in st)


def summarise(res):
    out = {}
    for g in ("DESIGN_1_3", "SEEN", "DESIGN_4"):
        sel = [e for e in res if e["group"] == g]
        o = out[g] = {"classes": len(sel)}
        for test in ("T1", "T2"):
            for grid in ("main", "slice"):
                for n in NS:
                    c = {str(q): sum(passes(e, q, test, grid, n) for e in sel) for q in R.QX}
                    small = Counter(str(next((q for q in R.QX if passes(e, q, test, grid, n)), "none")) for e in sel)
                    d = o[f"{test}/{grid}/{n}"] = {"pass": c, "smallest_q_x": dict(sorted(small.items()))}
                    if test == "T2" and grid == "main":
                        d["edge_ends"] = {str(q): dict(sorted(Counter(sum(e["q"][str(q)]["T2"]["main"][s][str(n)]["edge"])
                                          for e in sel for s in STATES if s not in e["own"]).items())) for q in R.QX}
                        d["feature"] = {str(q): dict(sorted(Counter(e["q"][str(q)]["T2"]["main"][s][str(n)]["feature"]
                                        for e in sel for s in STATES if s not in e["own"]).items())) for q in R.QX}
                    if test == "T1" and grid == "main":
                        d["edge_limited"] = {str(q): sum(e["q"][str(q)]["T1"]["main"][s]["edge"] for e in sel for s in STATES if s not in e["own"])
                                             for q in R.QX}
                    if g == "DESIGN_1_3" and grid == "main" and n == 2000:
                        d["failing_at_0.01"] = [e["support"] for e in sel if not passes(e, 0.01, test, grid, n)]
    return out


def named(res):
    """Classes accepted in stage 1 under F1 (M2 > 5%), and the DB8 states."""
    st1 = json.loads((IDENT / "results/stage1_run1/F1.json").read_text(encoding="utf-8"))["classes"]
    acc = [e["support"] for e in st1 if e["half"] == "DESIGN" and
           any(Q.accept_probability(2000 * v["ncp"], v["dim"]) > Q.ACCEPT for v in e["states"].values())]
    one = S.single_signatures()
    by = {S.signature(e["support"], one)[0]: e for e in res}
    out = {"stage1_accepted_supports": acc}
    for sup in acc:
        e = by.get(S.signature(sup, one)[0])
        out[str(tuple(sup))] = "weight 4, not in the 200" if e is None else e["q"]["0.01"]
    for nm, sup in (("X09", (7, 14, 42)), ("E", (9, 25, 53)), ("V06", (1, 42, 47)), ("X03", (3, 25, 34))):
        out[nm] = by[S.signature(sup, one)[0]]["q"]
    return out


def run(folder):
    prov = verify()
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()

    def log(x):
        with open(out / "progress.txt", "a", encoding="utf-8", newline="\n") as f:
            f.write(f"{time.time() - t0:8.0f} {x}\n")

    def write(name, obj):
        with open(out / name, "x", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(obj, sort_keys=True, default=float) + "\n")
    xs = target_list()
    got = {}
    try:
        for fam in ("F0", "F1"):
            got[fam] = family(fam, xs, log)
    except RuntimeError as err:
        write("CHECK_FAILED.json", {"error": str(err), **prov})
        raise
    write("PROVENANCE.json", prov)                         # nothing is written before every check has passed
    for fam, (res, info) in got.items():
        sm = summarise(res)
        write(f"{fam}.json", {"info": info, "classes": res})
        write(f"{fam}_SUMMARY.json", sm)
        write(f"{fam}_NAMED.json", named(res))
    p = sm["DESIGN_1_3"]
    write("READING.json", {"family": "F1", "n": 2000, "q_x": 0.01, **{t: {"pass": p[f"{t}/main/2000"]["pass"]["0.01"],
          "of": 418, "reading": reading(p[f"{t}/main/2000"]["pass"]["0.01"])} for t in ("T2", "T1")}})
    log("done")


if __name__ == "__main__":
    if sys.argv[1] == "freeze":
        freeze()
    elif sys.argv[1] == "time":
        timing()
    elif sys.argv[1] == "run":
        run(sys.argv[2])
    else:
        raise SystemExit(__doc__)
