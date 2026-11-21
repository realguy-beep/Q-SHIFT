"""DB2 core: causal hazard tracker and the transition-aware risk gate (pure functions; PLAN_DB2.md).

Per decision block t, with DB1's plausible set P (from blocks < t only):
  risk(k) = max over s in P of [ (1 - h_s) R[s][k] + h_s * next_s(k) ]
  h_s     = (A0 + changes out of s) / (A0 + B0 + decisions at which P = {s})
  next_s  = worst case max_{d != s} R[d][k] until a change out of s has been seen   ("worst" mode: always)
            then the mixture sum_d w_d R[d][k], w_d proportional to DEST_ALPHA + observed changes s -> d
Key = argmin risk (ties by bank order); keep the previous key unless another is better by more than kappa.
With h = 0 and kappa = DB1's KAPPA this is DB1's bank_decide (tested).
"""
from __future__ import annotations

import db2_config as C


class Tracker:
    """Causal identity/hazard state. A change s -> d is counted when, after an AD3 alarm, the new segment's
    plausible set first becomes a singleton {d} with d != s (s = the last singleton identity)."""

    def __init__(self):
        self.cur = None
        self.pending = False
        self.occ = {s: 0 for s in C.STATES}
        self.outs = {s: [] for s in C.STATES}

    def observe(self, P, alarm):
        """Call once per decision, before deciding; `alarm` = a new segment started since the last call."""
        if alarm:
            self.pending = True
        if len(P) == 1:
            s = P[0]
            if self.pending:
                if self.cur is not None and s != self.cur:
                    self.outs[self.cur].append(s)
                self.pending = False
            self.cur = s

    def commit(self, P):
        """Call after deciding: occupancy counts this decision for the identified state."""
        if len(P) == 1:
            self.occ[P[0]] += 1

    def hazard(self, s):
        return (C.HAZ_A0 + len(self.outs[s])) / (C.HAZ_A0 + C.HAZ_B0 + self.occ[s])

    def snapshot(self):
        return {"cur": self.cur, "occ": dict(self.occ), "outs": {k: list(v) for k, v in self.outs.items() if v},
                "h": {s: round(self.hazard(s), 6) for s in C.STATES}}


def next_risk(s, k, risk, outs, mode):
    others = [d for d in C.STATES if d != s]
    if mode == "worst" or not outs:
        return max(risk[d][k] for d in others)
    w = {d: C.DEST_ALPHA + outs.count(d) for d in others}
    z = sum(w.values())
    return sum(w[d] / z * risk[d][k] for d in others)


def gate(P, risk, tracker, prev, mode, kappa, hazard=None):
    """-> key (bank state name) or None if P is empty (unknown path, as DB1). `hazard` overrides h_s (tests)."""
    if not P:
        return None
    rk = {}
    for k in C.STATES:
        vals = []
        for s in P:
            h = tracker.hazard(s) if hazard is None else hazard
            vals.append((1 - h) * risk[s][k] + h * next_risk(s, k, risk, tracker.outs[s], mode))
        rk[k] = max(vals)
    best = min(C.STATES, key=lambda a: (rk[a], C.STATES.index(a)))
    if prev in rk and rk[prev] <= rk[best] + kappa:
        return prev
    return best
