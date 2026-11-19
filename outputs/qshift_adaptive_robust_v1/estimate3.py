"""BRE candidate estimators (PLAN_BRE.md). Detector-only; every function works on observed rates (obs, n), so the
deterministic census (expected rates) and sampled pools (row means) share one code path.

  fit_masked(obs, n, mask, trim)   the B2 algorithm restricted to detectors in `mask`; with mask all-True and
                                   trim = he1b.TRIM it reproduces estimate2.fit_b2 (tested)
  fit_e1(obs, n)                   one-sided adaptive exclusion: iteratively drop detectors whose standardized
                                   residual is ABOVE +E1_CUTOFF (a burst only raises rates), refit untrimmed
  fit_e2_refit(obs, n, detectors)  B2 refit with the learned class's burst detectors excluded
estimate2.py is imported, not modified.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

import bre_config as C
import estimate2 as E
import he1b as HB


def rates_from_rows(x):
    x = np.asarray(x, dtype=np.uint8)
    return x.mean(axis=0), len(x)


def _prep(obs, n):
    obs = np.maximum(np.asarray(obs, dtype=float), 0.5 / n)
    return np.log(obs), n * obs


def _obj(lo, w, p, b, mask, trim, drop_top=0):
    if drop_top:                          # one-sided: drop the `drop_top` largest SIGNED residuals, square the rest
        r = ((lo - E._log_rates(*E._key(p, b))) * np.sqrt(w))[mask]
        return float((np.sort(r)[: len(r) - drop_top] ** 2).sum())
    r2 = ((lo - E._log_rates(*E._key(p, b))) ** 2 * w)[mask]
    k = int(np.floor(trim * len(r2)))
    return float(np.sort(r2)[: len(r2) - k].sum())


def _golden(f, a, c):
    g = (np.sqrt(5) - 1) / 2
    x1, x2 = c - g * (c - a), a + g * (c - a)
    f1, f2 = f(x1), f(x2)
    for _ in range(E.GOLDEN_IT):
        if f1 <= f2:
            c, x2, f2 = x2, x1, f1
            x1 = c - g * (c - a)
            f1 = f(x1)
        else:
            a, x1, f1 = x1, x2, f2
            x2 = a + g * (c - a)
            f2 = f(x2)
    return (a + c) / 2


def fit_masked(obs, n, mask=None, trim=HB.TRIM, drop_top=0):
    """B2 (grid fit, then golden refinement of p within +-3 grid steps and b within the neighbouring cells).
    drop_top > 0 replaces the symmetric trim by a one-sided one (E1's start)."""
    lo, w = _prep(obs, n)
    mask = np.ones(len(lo), bool) if mask is None else np.asarray(mask, bool)
    if drop_top:
        r = ((lo[None, None, :] - HB.grid()) * np.sqrt(w))[..., mask]
        og = (np.sort(r, axis=-1)[..., : r.shape[-1] - drop_top] ** 2).sum(axis=-1)
    else:
        r2 = (lo[None, None, :] - HB.grid()) ** 2 * w
        if not mask.all():                       # (all-True keeps he1b.fit's exact summation order)
            r2 = r2[..., mask]
        k = int(np.floor(trim * r2.shape[-1]))
        og = np.sort(r2, axis=-1)[..., : r2.shape[-1] - k].sum(axis=-1)
    bi, pi = np.unravel_index(int(np.argmin(og)), og.shape)
    p0, b0, obj0 = float(HB.P_GRID[pi]), float(HB.B_GRID[bi]), float(og[bi, pi])
    grid = list(HB.B_GRID)
    i = grid.index(b0)
    b_lo, b_hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
    pg = list(HB.P_GRID)
    j = int(np.argmin(np.abs(np.asarray(pg) - p0)))
    p_lo, p_hi = pg[max(j - E.P_STEPS, 0)], pg[min(j + E.P_STEPS, len(pg) - 1)]
    fp = lambda b: float(np.exp(_golden(lambda lp: _obj(lo, w, np.exp(lp), b, mask, trim, drop_top),  # noqa: E731
                                        np.log(p_lo), np.log(p_hi))))
    p, b = p0, b0
    for _ in range(E.ALTERNATIONS):
        p = fp(b)
        b = float(_golden(lambda bb: _obj(lo, w, p, bb, mask, trim, drop_top), b_lo, b_hi)) if b_hi > b_lo else b
    p = fp(b)
    return {"p_grid": p0, "b_grid": b0, "obj_grid": obj0, "p_hat": p, "b_hat": b,
            "objective": _obj(lo, w, p, b, mask, trim, drop_top), "n_used": int(mask.sum())}


def std_residuals(obs, n, p, b):
    lo, w = _prep(obs, n)
    return (lo - E._log_rates(*E._key(p, b))) * np.sqrt(w)


def fit_e1(obs, n, cutoff=C.E1_CUTOFF, max_it=C.E1_MAX_IT, drop_top=C.E1_START_DROP):
    """Start from a one-sided fit that drops the `drop_top` largest positive residuals at every candidate (p, b)
    (drop_top = the largest burst footprint, 30; BRE-0 showed a B2 start can lock onto a biased fixed point); then
    repeat {exclude r > +cutoff; untrimmed masked refit} to a fixed point.
    Statistic for the flag: mean squared standardized residual over the included detectors."""
    f = fit_masked(obs, n, trim=0.0, drop_top=drop_top)
    mask = np.ones(len(obs), bool)
    it, stable = 0, False
    while it < max_it:
        it += 1
        new = std_residuals(obs, n, f["p_hat"], f["b_hat"]) <= cutoff
        if np.array_equal(new, mask) and it > 1:
            stable = True
            break
        mask = new
        f = fit_masked(obs, n, mask, trim=0.0)
    r = std_residuals(obs, n, f["p_hat"], f["b_hat"])
    return {**f, "excluded": int((~mask).sum()), "iterations": it, "stable": stable,
            "stat": float(np.mean(r[mask] ** 2))}


@lru_cache(maxsize=4096)
def burst_detectors(support):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    ev = m.extract_burst_events(C.spec(**C.NOMINAL), tuple(int(v) for v in support))
    return tuple(sorted({d for e in ev for d in e.detector_ids}))


def class_detectors(cls):
    """Detectors of a learned signature class (union of its per-round burst events); same for both flips."""
    return tuple(sorted({int(d) for e in cls.events for d in e}))


def fit_e2_refit(obs, n, detectors):
    mask = np.ones(len(obs), bool)
    mask[list(detectors)] = False
    return {**fit_masked(obs, n, mask), "excluded": int((~mask).sum())}


def footprint(base_rates, burst_rates_q2):
    return int(((burst_rates_q2 - base_rates) / base_rates > C.FOOTPRINT_RISE).sum())
