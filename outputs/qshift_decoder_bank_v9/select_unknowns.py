"""PROTOCOL_DB8.md section 3: the unknown-state selection, from analytic detector rates (stim DEM; no sampling).

  python select_unknowns.py      # prints the table; tests require it to equal db8_config.NEW_UNKNOWN

lambda(X, s) = 2 n sum_d KL(r_X,d || template_s,d) at n = 2,000 detector rows, against DB1's bank templates.
Excluded labels: the bank (W01, W05, W09, W14), E (W06), W13, X13.

Amendment A3 (AMENDMENT_A3.md), fixed before any U_FAR data existed: the far state must also have buildable
decoders (re1.decoders) and must not be the base label of the out-of-catalog state. Under the original rule X03 was
chosen; its correlated-matching decoder cannot be built, which stopped DB8 attempt 2. SELECTION.json keeps the
original table; SELECTION_A3.json holds this one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
import db8_config as C  # noqa: E402,I001
import db_core as D  # noqa: E402

EXCLUDED = {"W01", "W05", "W09", "W14", "W06", "W13", "X13"}
N = C.DET_PER_BLOCK
OUT_RANGE = (60.0, 140.0)


def _tpl():
    tr = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))
    return {k: np.array(v) for k, v in tr["templates"].items()}


def rates(sup):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    DCF = D.C
    sp = DCF.spec(gate_p=DCF.P0, measurement_p=DCF.P0)
    c = m.build_candidate_circuit(sp, DCF.BURST_Q, tuple(sup))
    dem = c.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
    prod = np.ones(c.num_detectors)
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        p = inst.args_copy()[0]
        for tg in inst.targets_copy():
            if tg.is_relative_detector_id():
                prod[tg.val] *= 1 - 2 * p
    return (1 - prod) / 2


def lam(r, p):
    r, p = np.clip(r, 1e-12, 1 - 1e-12), np.clip(p, 1e-12, 1 - 1e-12)
    return float(2 * N * (r * np.log(r / p) + (1 - r) * np.log((1 - r) / (1 - p))).sum())


def nearest(sup, tpl):
    r = rates(sup)
    ls = {s: lam(r, tpl[s]) for s in C.STATES}
    b = min(ls, key=lambda s: (ls[s], s))
    return b, ls[b]


def in_catalog(sup, classes):
    try:
        C._truth0(classes, tuple(sup))
        return True
    except KeyError:
        return False


def builds(sup):
    import re1
    try:
        re1.decoders(D.C.spec(gate_p=D.C.P0, measurement_p=D.C.P0), tuple(sup))
        return True
    except ValueError:
        return False


def public():
    out = {}
    for f in ("BRS_BURSTS.json", "BRT_BURSTS.json", "BRE_BURSTS.json"):
        d = json.loads((C.DB1.parent / "qshift_adaptive_robust_v1" / f).read_text(encoding="utf-8"))
        out.update({k: tuple(int(q) for q in v) for k, v in d["V"].items()})
    return out


def select():
    import mm_contract as K
    tpl, pub, classes = _tpl(), public(), K.B.load_classes()
    E = tuple(C.support("E"))
    lamE = nearest(E, tpl)[1]
    cand = {lab: nearest(sup, tpl) for lab, sup in sorted(pub.items()) if lab not in EXCLUDED}
    near = min(cand, key=lambda lab: (cand[lab][1], lab))
    qs = sorted({q for sup in pub.values() for q in sup})
    out_sup, out_lab = None, None
    for lab in sorted(cand):
        sup = pub[lab]
        for q in qs:
            if q in sup:
                continue
            s4 = tuple(sorted(sup + (q,)))
            if in_catalog(s4, classes):
                continue
            b, lv = nearest(s4, tpl)
            if OUT_RANGE[0] <= lv <= OUT_RANGE[1] and b != "A":
                out_sup, out_lab = s4, f"{lab}+q{q}"
                break
        if out_sup:
            break
    out_base = out_lab.split("+")[0]
    far_order = sorted((lab for lab, (b, _) in cand.items() if b != "A"), key=lambda lab: (abs(cand[lab][1] - lamE), lab))
    skipped = []
    for far in far_order:
        if far == out_base:
            skipped.append({"label": far, "reason": "base of the out-of-catalog state"})
        elif not builds(pub[far]):
            skipped.append({"label": far, "reason": "decoders do not build"})
        else:
            break
    return {"E": {"label": "W06", "support": list(E), "nearest": list(nearest(E, tpl)), "in_catalog": in_catalog(E, classes)},
            "UF": {"label": far, "support": list(pub[far]), "nearest": list(cand[far]), "in_catalog": in_catalog(pub[far], classes),
                   "skipped_A3": skipped},
            "UO": {"label": out_lab, "support": list(out_sup), "nearest": list(nearest(out_sup, tpl)),
                   "in_catalog": in_catalog(out_sup, classes)},
            "UN": {"label": near, "support": list(pub[near]), "nearest": list(cand[near]),
                   "in_catalog": in_catalog(pub[near], classes)}}


if __name__ == "__main__":
    res = select()
    print(json.dumps(res, indent=1))
    if "--write" in sys.argv:
        import studykit as SK
        SK.write_once_json(ROOT / "SELECTION_A3.json", {"schema": "qshift-decoder-bank-db8-selection-a3-v1", "n_rows": N,
                                                     "excluded": sorted(EXCLUDED), "out_range": list(OUT_RANGE),
                                                     "states": res})
    sys.exit(0)
