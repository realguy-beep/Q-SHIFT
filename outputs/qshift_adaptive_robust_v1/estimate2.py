"""Arm B2 estimator (PLAN_DEV2.md): H-E1b grid fit, then continuous refinement of p and bias; misspecification flag.

Detector-only. Given unlabeled detector rows x, returns (p_hat, b_hat, objective, flagged). Model family:
z_biased(p, b) with gate p = measurement p, b >= 1 (b = 1 is balanced).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

import dev2_config as D  # noqa: F401  (sets sys.path)
import he1 as H
import he1b as HB
from adaptive.estimation import _trimmed_mean

ROOT = Path(__file__).resolve().parent
P_LO, P_HI = 0.0012, 0.0075
B_LO, B_HI = 1.0, 30.0
ALTERNATIONS, BISECT_IT, GOLDEN_IT = 2, 30, 20
P_STEPS = 3                        # p refinement interval: +-3 grid steps (p and b trade off)


@lru_cache(maxsize=4096)
def _log_rates(p: float, b: float) -> np.ndarray:
    from outputs.qshift_correlated_decoder_v1_6 import learner as L
    return np.log(H.detector_rates(L.base_dem(HB.spec_at(p, b))))


def _key(p, b):
    return round(float(p), 9), round(float(b), 6)


def objective(lo, w, p, b):
    r2 = (lo - _log_rates(*_key(p, b))) ** 2 * w
    k = int(np.floor(HB.TRIM * len(r2)))
    return float(np.sort(r2)[: len(r2) - k].sum())


def p_root(lo, b):
    """H-E1 1-D root in log p of trimmed_mean(lo - log rate(p, b)) = 0, by bisection."""
    a, c = np.log(P_LO), np.log(P_HI)
    f = lambda lp: _trimmed_mean(lo - _log_rates(*_key(np.exp(lp), b)), H.TRIM)   # noqa: E731
    if f(a) < 0 or f(c) > 0:
        raise ValueError("p root outside range")
    for _ in range(BISECT_IT):
        mid = (a + c) / 2
        a, c = (mid, c) if f(mid) > 0 else (a, mid)
    return float(np.exp((a + c) / 2))


def p_golden(lo, w, b, p_lo, p_hi):
    """Golden-section minimisation of the SAME trimmed objective over log p in [p_lo, p_hi] at fixed b.

    Replaces the plan's H-E1 root for the p step (pre-freeze change found in rehearsal: the root optimises a
    different criterion and raised the objective; see DEV2_PROTOCOL.md, deviations)."""
    g = (np.sqrt(5) - 1) / 2
    a, c = np.log(p_lo), np.log(p_hi)
    f = lambda lp: objective(lo, w, np.exp(lp), b)   # noqa: E731
    x1, x2 = c - g * (c - a), a + g * (c - a)
    f1, f2 = f(x1), f(x2)
    for _ in range(GOLDEN_IT):
        if f1 <= f2:
            c, x2, f2 = x2, x1, f1
            x1 = c - g * (c - a)
            f1 = f(x1)
        else:
            a, x1, f1 = x1, x2, f2
            x2 = a + g * (c - a)
            f2 = f(x2)
    return float(np.exp((a + c) / 2))


def b_golden(lo, w, p, b_lo, b_hi):
    g = (np.sqrt(5) - 1) / 2
    x1, x2 = b_hi - g * (b_hi - b_lo), b_lo + g * (b_hi - b_lo)
    f1, f2 = objective(lo, w, p, x1), objective(lo, w, p, x2)
    for _ in range(GOLDEN_IT):
        if f1 <= f2:
            b_hi, x2, f2 = x2, x1, f1
            x1 = b_hi - g * (b_hi - b_lo)
            f1 = objective(lo, w, p, x1)
        else:
            b_lo, x1, f1 = x1, x2, f2
            x2 = b_lo + g * (b_hi - b_lo)
            f2 = objective(lo, w, p, x2)
    return float((b_lo + b_hi) / 2)


def flag_threshold() -> float:
    return float(json.loads((ROOT / "FLAG_THRESHOLD.json").read_text(encoding="utf-8"))["threshold"])


def fit_b2(x):
    x = np.asarray(x, dtype=np.uint8)
    n = len(x)
    obs = np.maximum(x.mean(axis=0), 0.5 / n)
    lo, w = np.log(obs), n * obs
    p0, b0, obj0 = HB.fit(x)
    grid = list(HB.B_GRID)
    i = grid.index(b0)
    b_lo, b_hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
    pg = list(HB.P_GRID)
    j = int(np.argmin(np.abs(np.asarray(pg) - p0)))
    p_lo, p_hi = pg[max(j - P_STEPS, 0)], pg[min(j + P_STEPS, len(pg) - 1)]
    p, b = p0, b0
    for _ in range(ALTERNATIONS):
        p = p_golden(lo, w, b, p_lo, p_hi)
        b = b_golden(lo, w, p, b_lo, b_hi) if b_hi > b_lo else b
    p = p_golden(lo, w, b, p_lo, p_hi)
    obj = objective(lo, w, p, b)
    return {"p_grid": p0, "b_grid": b0, "obj_grid": obj0, "p_hat": p, "b_hat": b, "objective": obj,
            "flagged": bool(obj > flag_threshold())}
