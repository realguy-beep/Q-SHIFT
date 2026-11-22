"""DB6 pure functions: the block-lookahead features and the LA overlay rule.

Inputs are detection-only counts per block (ad3.counts of the 2,000 detection rows), the AD3 segment start seg0
as it stands before block t's own change test, DB1's templates and tau_fit. No labels, no evaluation rows, no
truth: the signature admits nothing else."""
from __future__ import annotations

import ad3
import db_core as D

import db6_config as C


def lookahead(cnt, seg0, t, tpl, tau_fit):
    """-> {"g": change statistic of block t, "alarm": g > AD3_TAU, "P1": DB1 plausible set fitted on block t alone}.
    `cnt` must hold blocks 0..t (block t's detection counts included); entries beyond t are never read."""
    k0, n0 = ad3.pool(cnt[ad3.segment_lo(seg0, t):t])
    g = ad3.g_stat(*cnt[t], k0, n0)
    k1, n1 = cnt[t]
    gf = {st: D.g_fit(k1, n1, tpl[st]) for st in C.STATES}
    return {"g": g, "alarm": bool(g > C.AD3_TAU), "P1": D.plausible(gf, 1, tau_fit)}


def la_key(base_key, la, gated=True):
    """LA overlay: bank key of the single-block singleton if (alarm or not gated), else the base arm's key."""
    if (la["alarm"] or not gated) and len(la["P1"]) == 1:
        return "bank:" + la["P1"][0], "lookahead"
    return base_key, "base"
