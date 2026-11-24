"""IDENT1 section 6, M3: deterministic decode of noiseless burst signatures. Not a logical error rate."""
from __future__ import annotations

import json
import sys

import numpy as np

import split as S
from split import C, OUT, SPEC, m

sys.path.insert(0, str(OUT / "qshift_decoder_bank_v10"))
import decoder_factory as DF  # noqa: E402

Q = 0.01
BANK = C.STATES


def decoders():
    return {k: DF.build_l2(SPEC, C.support(k)) for k in BANK}


def wrong_rounds(sup, dec):
    """Number of the five single-round burst signatures whose observable the decoder gets wrong."""
    if not sup:
        return 0
    ev = m.extract_burst_events(SPEC, tuple(sup))
    x = np.zeros((len(ev), SPEC.detectors), np.uint8)
    for i, e in enumerate(ev):
        x[i, list(e.detector_ids)] = 1
    import re1
    return int((re1.predict(dec, x, "l2") != np.array([e.observable_flip for e in ev], np.uint8)).sum())


def bank_check():
    """Section 8: rho(s, k) - rho(s, s) against DB1's risk table, 20 off-diagonal entries, tolerance 0.005."""
    risk = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["risk"]
    dec = decoders()
    rows = []
    for s in BANK:
        rho = {k: Q * wrong_rounds(C.support(s), dec[k]) for k in BANK}
        for k in BANK:
            if k != s:
                a, b = rho[k] - rho[s], risk[s][k] - risk[s][s]
                rows.append({"state": s, "key": k, "proxy": round(a, 6), "risk_table": round(b, 6), "ok": abs(a - b) <= 0.005})
    return {"passed": sum(r["ok"] for r in rows), "of": len(rows), "ok": sum(r["ok"] for r in rows) >= 18, "rows": rows}


__all__ = ["S", "bank_check", "decoders", "wrong_rounds"]
