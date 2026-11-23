"""DB8 rule arms (pure functions of block t's detector-only counts, DB6's lookahead result and W0F's base key)."""
from __future__ import annotations

import db_core as D
import db8_config as C


def single_fit(cnt, t, tpl):
    """Single-block (L = 1) fit of block t's detector counts to every bank template. Reads cnt[t] only."""
    k1, n1 = cnt[t]
    return {s: D.g_fit(k1, n1, tpl[s]) for s in C.STATES}


def rule_key(base_key, la, gf1, cap):
    """LA_R1 (cap None): fire iff DB6's alarm, P1 = {s} and bank:s differs from W0F's key.
    LA_R2 (cap c): LA_R1 and g_s <= c. -> (key, source)."""
    if la["alarm"] and len(la["P1"]) == 1:
        s = la["P1"][0]
        k = "bank:" + s
        if k != base_key and (cap is None or gf1[s] <= cap):
            return k, "lookahead"
    return base_key, "base"


def cb_key(gf1, tau_fit, risk, prev, w0f_key):
    """CB: DB1's bank_decide on the single-block fit (L = 1) with CB's own previous key; empty set -> W0F's key.
    -> (key, source, next prev)."""
    kb, _ = D.bank_decide(gf1, 1, tau_fit, risk, prev)
    if kb is None:
        return w0f_key, "w0f", prev
    return "bank:" + kb, "cb", kb
