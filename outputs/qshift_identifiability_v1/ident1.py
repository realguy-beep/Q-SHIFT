"""IDENT1 (PROTOCOL_IDENT1.md with amendments A1 and A2).

  python ident1.py freeze                  # IDENT1_FREEZE.json (build step; computes nothing for any support)
  python ident1.py run <new folder> F0,F1[,F2]   # stage 1; separate approval. DESIGN, SEEN and the bank only
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import numpy as np

import split as S  # noqa: I001  (blocks every sampler)
import measures as Q
import moments as M
from split import C, OUT, ROOT

REPO = OUT.parent
FREEZE = ROOT / "IDENT1_FREEZE.json"
PACKAGES = ("numpy", "scipy", "stim", "pymatching", "ldpc")
DATA = ("outputs/qshift_d5_learned_support_v1/CLASSES_D5.json", "outputs/qshift_decoder_bank_v1/TRAINING.json",
        *(f"outputs/qshift_adaptive_robust_v1/{f}_BURSTS.json" for f in ("BRS", "BRT", "BRE")))
OWN = ("PROTOCOL_IDENT1.md", "AMENDMENT_A1.md", "AMENDMENT_A2.md", "HARM_CHECK_FAILED.json", "GAUSSIAN_CHECK.json",
       "split.py", "moments.py", "measures.py", "harm.py", "ident1.py", "tests/test_ident1.py", "tests/test_measures.py")
NS = (2_000, 4_000, 12_000)


def runtime():
    return {"python": platform.python_version(), "platform": platform.platform(), **{p: version(p) for p in PACKAGES}}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def files():
    mods = {Path(x.__file__).resolve() for x in list(sys.modules.values()) if getattr(x, "__file__", None)}
    rel = {p.relative_to(REPO).as_posix() for p in mods if p.is_relative_to(REPO)}
    return sorted(rel | set(DATA) | {(ROOT / f).relative_to(REPO).as_posix() for f in OWN})


def split_list():
    cls, _ = S.classes(4)
    sp = S.split()
    return sorted([sp[s], [list(x) for x in v]] for s, v in cls.items())


def freeze():
    doc = {"schema": "qshift-ident1-freeze-1", "files": {f: sha(REPO / f) for f in files()}, "runtime": runtime(),
           "split_counts": dict(Counter(x[0] for x in split_list())),
           "split_sha256": hashlib.sha256(json.dumps(split_list()).encode()).hexdigest(),
           "p_grid": Q.P_GRID, "q_grid": Q.Q_GRID, "n": Q.N, "thresholds": [Q.AMBIGUOUS, Q.SEPARATED, Q.ACCEPT]}
    with open(FREEZE, "x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")


def verify():
    fz = json.loads(FREEZE.read_text(encoding="utf-8"))
    bad = [f for f in sorted(set(fz["files"]) | set(files())) if fz["files"].get(f) != sha(REPO / f)]
    if bad or fz["runtime"] != runtime():
        raise SystemExit(f"differs from the freeze: {bad} {runtime()}")
    if hashlib.sha256(json.dumps(split_list()).encode()).hexdigest() != fz["split_sha256"]:
        raise SystemExit("split differs from the freeze")
    git = lambda *a: subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True, check=True).stdout.strip()  # noqa: E731
    rel = FREEZE.relative_to(REPO).as_posix()
    if git("status", "--porcelain", "--untracked-files=no") or not git("ls-files", rel):
        raise SystemExit("the freeze is not committed, or tracked files are modified")
    return {"head": git("rev-parse", "HEAD"), "freeze_sha256": sha(FREEZE)}


# ------------------------------------------------------------------ structure (Q1)
def aliasing():
    single, (cls, hidden) = S.single_signatures(), S.classes(4)
    both = {s for s, v in cls.items() if len({S.signature(x, single)[1] for x in v}) == 2}
    bank = {}
    for st in C.STATES[1:]:
        s, f = S.signature(C.support(st), single)
        opp = [list(x) for x in cls[s] if S.signature(x, single)[1] != f]
        bank[st] = {"class_size": len(cls[s]), "opposite_flip": len(opp),
                    "opposite_flip_weight_le_3": sum(len(x) <= 3 for x in opp)}
    cat = {s for s, v in cls.items() if min(map(len, v)) <= 3}
    return {"classes": len(cls), "both_flips": len(both), "catalogue_classes": len(cat),
            "catalogue_both_flips_weight_le_3": sum(len({S.signature(x, single)[1] for x in cls[s] if len(x) <= 3}) == 2 for s in cat),
            "invisible_supports": len(hidden), "bank": bank}


# ------------------------------------------------------------------ M1, M2
def targets(fam):
    cls, _ = S.classes(4)
    sp = S.split()
    out = []
    for s, v in cls.items():
        w = min(map(len, v))
        if sp[s] == "HELD" or (fam == "F2" and w == 4):
            continue
        out.append((sp[s], w, sorted(v)[0] if w == 4 else sorted(x for x in v if len(x) == w)[0], s))
    if any(x[0] not in ("DESIGN", "SEEN") for x in out):
        raise AssertionError("HELD must stay closed")
    return sorted(out, key=lambda x: (x[0], x[1], x[2]))


def compute(fam, log):
    """-> per target and bank state: J and ncp per row (minimum over the grid, and at the nominal point)."""
    feats = M.families()[fam]
    xs = targets(fam)
    single = S.single_signatures()
    sig = {st: S.signature(C.support(st), single)[0] for st in C.STATES[1:]}
    BX = [Q.burst_signs(x[3], feats) for x in xs]
    x0 = Q.Base(feats, C.P0)
    mu_x = np.array([Q.model_mean(x0, B, 0.01) for B in BX])
    points = [(st, p, q) for p in Q.P_GRID for st in C.STATES for (pp, q) in Q.grid(st) if pp == p]
    k, nx, info = len(feats), len(xs), {"dim": [], "dropped": 0}
    ncp = np.zeros((len(points), nx))
    varx = np.zeros((len(points), nx))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        W = np.lib.format.open_memmap(Path(d) / "w.npy", "w+", np.float64, (nx, len(points), k))
        base = None
        for i, (st, p, q) in enumerate(points):
            if base is None or base[0] != p:
                base = (p, Q.Base(feats, p))
            B = None if st == "OFF" else Q.burst_signs(sig[st], feats)
            sol = Q.Solver(Q.model_cov(base[1], B, q))
            info["dim"].append(sol.dim)
            info["dropped"] += sol.dropped
            D = mu_x - Q.model_mean(base[1], B, q)
            w = sol.solve(D.T).T
            ncp[i] = np.einsum("ij,ij->i", w, D)               # = w.d = var_s of the statistic
            W[:, i, :] = w
            log(f"{fam} bank point {i + 1}/{len(points)}")
        for j in range(nx):
            K = Q.model_cov(x0, BX[j], 0.01)
            w = np.array(W[j])
            varx[:, j] = np.einsum("ij,ij->i", w @ K, w)
            if j % 50 == 0:
                log(f"{fam} target {j}/{nx}")
        del W
    J = Q.j_stat(ncp, ncp, varx)
    dims = np.array(info["dim"])
    res = []
    for j, (hf, wt, sup, s) in enumerate(xs):
        e = {"half": hf, "weight": wt, "support": list(sup), "states": {}}
        for st in C.STATES:
            idx = [i for i, pt in enumerate(points) if pt[0] == st]
            nom = next(i for i in idx if points[i][1] == C.P0 and points[i][2] in (None, 0.01))
            a, b = idx[int(np.argmin(J[idx, j]))], idx[int(np.argmin(ncp[idx, j]))]
            e["states"][st] = {"own_class": st != "OFF" and sig[st] == s, "J": J[a, j], "J_nominal": J[nom, j], "at": points[a][1:],
                               "ncp": ncp[b, j], "ncp_nominal": ncp[nom, j], "dim": int(dims[b])}
        res.append(e)
    return res, {"features": k, "targets": nx, "dropped_directions": info["dropped"]}


def second_pass(log):
    """A2: F0 only. Worst case over X's own grid as well as the bank state's."""
    feats, xs, single = M.families()["F0"], targets("F0"), S.single_signatures()
    bases = {p: Q.Base(feats, p) for p in Q.P_GRID}
    sig = {st: S.signature(C.support(st), single)[0] for st in C.STATES[1:]}
    worst = np.full((len(xs), len(C.STATES)), np.inf)
    BX = [Q.burst_signs(x[3], feats) for x in xs]
    models = [(j, p, q) for j in range(len(xs)) for p in Q.P_GRID for q in Q.Q_GRID]
    mu = np.array([Q.model_mean(bases[p], BX[j], q) for j, p, q in models])
    cov = np.array([Q.model_cov(bases[p], BX[j], q) for j, p, q in models], dtype=np.float32) if len(models) < 10 ** 6 else None
    for a, st in enumerate(C.STATES):
        for p, q in Q.grid(st):
            B = None if st == "OFF" else Q.burst_signs(sig[st], feats)
            D = mu - Q.model_mean(bases[p], B, q)
            w = Q.Solver(Q.model_cov(bases[p], B, q)).solve(D.T).T
            wd = np.einsum("ij,ij->i", w, D)
            vx = np.einsum("ni,nij,nj->n", w, cov, w, optimize=True)
            J = Q.j_stat(wd, wd, vx).reshape(len(xs), -1).min(axis=1)
            worst[:, a] = np.minimum(worst[:, a], J)
        log(f"second pass {st}")
    return [{"support": list(x[2]), "J": dict(zip(C.STATES, worst[j]))} for j, x in enumerate(xs)]


def template_pass():
    """Section 3's sensitivity: F0 open-set distance to DB1's sampled templates instead of the model means (nominal point)."""
    feats, xs, single = M.families()["F0"], targets("F0"), S.single_signatures()
    x0 = Q.Base(feats, C.P0)
    tpl = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["templates"]
    mu = np.array([Q.model_mean(x0, Q.burst_signs(x[3], feats), 0.01) for x in xs])
    out = {}
    for st in C.STATES:
        B = None if st == "OFF" else Q.burst_signs(S.signature(C.support(st), single)[0], feats)
        D = mu - (1 - 2 * np.array(tpl[st]))
        out[st] = np.einsum("ij,ij->i", Q.Solver(Q.model_cov(x0, B, 0.01)).solve(D.T).T, D)
    return [{"support": list(x[2]), "ncp": {st: out[st][j] for st in C.STATES}} for j, x in enumerate(xs)]


def named_check():
    """X09 against B: DB8's lambda (28.2) and Codex's published D117 and D117/D119 rates."""
    tpl = np.array(json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["templates"]["B"])
    r = M.single_rates((7, 14, 42))
    lam = float(2 * Q.N * (r * np.log(r / tpl) + (1 - r) * np.log((1 - r) / (1 - tpl))).sum())
    E, w = M.dem_errors((7, 14, 42))
    a, b, ab = M.means(M.signs(E, [(117,), (119,), (117, 119)]), w)
    cof = (1 - a - b + ab) / 4
    return {"lambda": lam, "D117": float((1 - a) / 2), "D117_D119": float(cof),
            "ok": abs(lam - 28.2) < 0.05 and abs((1 - a) / 2 - 0.035063) < 5e-6 and abs(cof - 0.013487) < 5e-6}


def summarise(res, n):
    """Counts per half, weight group and state. A bank state's own class is ALIASED."""
    out = {}
    for hf in ("DESIGN", "SEEN"):
        for wg in ("weight_1_3", "weight_4"):
            sel = [e for e in res if e["half"] == hf and (e["weight"] == 4) == (wg == "weight_4")]
            tab = {}
            for st in C.STATES:
                c = Counter()
                for e in sel:
                    v = e["states"][st]
                    lab = "ALIASED" if v["own_class"] else Q.label(n * v["J"])
                    rej = Q.accept_probability(n * v["ncp"], v["dim"]) <= Q.ACCEPT
                    c[lab] += 1
                    c["REJECTABLE"] += rej
                    c[f"{lab}_and_REJECTABLE"] += rej
                    c[f"nominal_{'ALIASED' if v['own_class'] else Q.label(n * v['J_nominal'])}"] += 1
                tab[st] = dict(sorted(c.items()))
            tab["nearest"] = dict(sorted(Counter(min(C.STATES, key=lambda st: e["states"][st]["J"]) for e in sel).items()))
            tab["not_separated_from_some_state"] = sum(any(not v["own_class"] and n * v["J"] < Q.SEPARATED for v in e["states"].values()) for e in sel)
            tab["accepted_by_some_state"] = sum(any(Q.accept_probability(n * v["ncp"], v["dim"]) > Q.ACCEPT for v in e["states"].values()) for e in sel)
            out[f"{hf}/{wg}"] = {"classes": len(sel), "table": tab}
    return out


def run(folder, fams):
    prov = verify()
    g = Q.best_detector_check()
    nc = named_check()
    if not nc["ok"]:
        raise SystemExit(f"named check failed: {nc}")
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()

    def log(x):
        with open(out / "progress.txt", "a", encoding="utf-8", newline="\n") as f:
            f.write(f"{time.time() - t0:8.0f} {x}\n")

    def write(name, obj):
        with open(out / name, "x", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(obj, sort_keys=True, default=float) + "\n")
    write("PROVENANCE.json", {**prov, "runtime": runtime(), "gaussian_check_ok": g["ok"],
                              "M1_status": "approximate error" if g["ok"] else "index only", "named_check": nc})
    write("ALIASING.json", aliasing())
    for fam in fams:
        res, info = compute(fam, log)
        write(f"{fam}.json", {"info": info, "classes": res})
        write(f"{fam}_SUMMARY.json", {str(n): summarise(res, n) for n in NS})
        if fam == "F0":
            write("F0_SECOND_PASS.json", second_pass(log))
            write("F0_TEMPLATES.json", template_pass())
    log("done")


if __name__ == "__main__":
    if sys.argv[1] == "freeze":
        freeze()
    elif sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3].split(","))
    else:
        raise SystemExit(__doc__)
