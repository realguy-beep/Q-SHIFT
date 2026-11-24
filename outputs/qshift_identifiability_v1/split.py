"""IDENT1 section 4: signature classes, symmetry groups and the DESIGN/HELD split. Structure only: no moments, no sampling.

  python split.py      # prints group statistics (names and counts only)"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent
for _p in (OUT.parent, OUT / "qshift_decoder_bank_v9", ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import stim  # noqa: E402


def _no(*a, **k):
    raise AssertionError("stim sampling is forbidden in IDENT1")


stim.Circuit.compile_detector_sampler = stim.Circuit.compile_sampler = stim.DetectorErrorModel.compile_sampler = _no
import db8_config as C  # noqa: E402,I001
import mm_contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402

SPEC = C.spec(gate_p=C.P0, measurement_p=C.P0)
TAG = "qshift-ident-v1:"
MAX_GROUP = 0.20


def grid():
    """{(i, j): qubit} on the 5x5 data-qubit grid, i and j in 0..4."""
    g = m.data_qubit_grid(SPEC)
    xs, ys = sorted({x for x, _ in g}), sorted({y for _, y in g})
    return {(xs.index(x), ys.index(y)): q for (x, y), q in g.items()}


def symmetries():
    """The eight maps of the grid, as {qubit: qubit}."""
    g, n = grid(), 4
    fs = [lambda i, j: (i, j), lambda i, j: (n - j, i), lambda i, j: (n - i, n - j), lambda i, j: (j, n - i),
          lambda i, j: (n - i, j), lambda i, j: (i, n - j), lambda i, j: (j, i), lambda i, j: (n - j, n - i)]
    return [{q: g[f(i, j)] for (i, j), q in g.items()} for f in fs]


def single_signatures():
    """{qubit: (frozenset of (round, detector) , observable flip)}; a support's signature is the XOR of its qubits'."""
    out = {}
    for q in sorted(grid().values()):
        ev = m.extract_burst_events(SPEC, (q,))
        ev = sorted(ev, key=lambda e: e.detector_ids)
        out[q] = (frozenset((r, d) for r, e in enumerate(ev) for d in e.detector_ids), ev[0].observable_flip)
        assert len({e.observable_flip for e in ev}) == 1
    return out


def signature(sup, single):
    s, f = frozenset(), 0
    for q in sup:
        s, f = s ^ single[q][0], f ^ single[q][1]
    return s, f


def classes(max_weight=4):
    """{signature: sorted supports} for every visible support of weight 1..max_weight, and the invisible supports."""
    single, out, hidden = single_signatures(), {}, []
    for w in range(1, max_weight + 1):
        for sup in itertools.combinations(sorted(single), w):
            s, _ = signature(sup, single)
            (out.setdefault(s, []) if s else hidden).append(sup)
    return out, hidden


def groups(cls, maps):
    """Merge classes linked by any symmetry image of any of their supports. -> [sorted list of signatures]."""
    where = {sup: s for s, sups in cls.items() for sup in sups}
    parent = {s: s for s in cls}

    def find(s):
        while parent[s] is not s:
            parent[s] = parent[parent[s]]
            s = parent[s]
        return s
    for sup, s in where.items():
        for f in maps:
            t = where.get(tuple(sorted(f[q] for q in sup)))      # an image can be invisible
            if t is not None:
                a, b = find(s), find(t)
                if a is not b:
                    parent[a] = b
    g = {}
    for s in cls:
        g.setdefault(find(s), []).append(s)
    return list(g.values())


def half(cls, group):
    sups = sorted(x for s in group for x in cls[s])
    return "DESIGN" if hashlib.sha256((TAG + json.dumps(sups)).encode()).digest()[0] % 2 == 0 else "HELD"


def public():
    out = {}
    for f in ("BRS", "BRT", "BRE"):
        d = json.loads((OUT / f"qshift_adaptive_robust_v1/{f}_BURSTS.json").read_text(encoding="utf-8"))
        out.update({k: tuple(sorted(int(q) for q in v)) for k, v in d["V"].items()})
    return out


def report(cls, maps):
    gs = groups(cls, maps)
    sizes = sorted((len(g) for g in gs), reverse=True)
    return {"classes": len(cls), "groups": len(gs), "largest_groups": sizes[:5], "largest_fraction": round(sizes[0] / len(cls), 4),
            "rule_ok": sizes[0] <= MAX_GROUP * len(cls)}


def class_maps():
    """Amendment A1: the grid maps that send every signature class onto exactly one class."""
    cls, _ = classes(4)
    where = {sup: s for s, v in cls.items() for sup in v}
    return [f for f in symmetries()
            if all(len({where.get(tuple(sorted(f[q] for q in sup))) for sup in v}) == 1 for v in cls.values())]


_SPLIT = None


def split():
    """{signature: DESIGN | HELD | SEEN} over weight 1-4 classes (amendment A1)."""
    global _SPLIT
    if _SPLIT is None:
        cls, _ = classes(4)
        maps = class_maps()
        if not report(cls, maps)["rule_ok"]:
            raise SystemExit("split rule: a group exceeds the limit")
        pub, _SPLIT = set(public().values()), {}
        for g in groups(cls, maps):
            seen = any(x in pub for s in g for x in cls[s])
            for s in g:
                _SPLIT[s] = "SEEN" if seen else half(cls, g)
    return _SPLIT


if __name__ == "__main__":
    maps = symmetries()
    single = single_signatures()
    fs = classes(3)
    cat = K.B.load_classes()
    mine = {frozenset(x) for x in fs[0].values()}
    theirs = {frozenset(tuple(sorted(s)) for s in c.supports_flip0 + c.supports_flip1) for c in cat}
    print("catalogue reproduced:", mine == theirs, len(mine), len(theirs))
    flips_ok = all(signature(s, single)[1] == f for c in cat for f, ss in ((0, c.supports_flip0), (1, c.supports_flip1)) for s in ss)
    print("flips reproduced:", flips_ok)
    for w in (3, 4):
        cls, hidden = fs if w == 3 else classes(4)
        print("weight <=", w, "hidden", Counter(map(len, hidden)), "as drafted (8 maps):", report(cls, maps))
