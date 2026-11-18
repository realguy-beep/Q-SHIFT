"""Broad-benchmark endpoints and gates (STATISTICAL_PROTOCOL.md). Pure numpy; no sampling.

Primary endpoint: pooled weighted relative reduction
    R_pool = 1 - sum_c w_c * LER_c(candidate) / sum_c w_c * LER_c(comparator)
over ELIGIBLE conditions, computed from pooled failures and shots, not by averaging per-condition R.
Uncertainty: paired root-cluster bootstrap (roots resampled within condition, all arms together).
Gates (both one-sided lower bounds, never point estimates):
    G_AGG  : lower bound of R_pool >= target at level alpha_agg
    G_EVERY: for every eligible condition, lower bound of R_c >= target, Holm-adjusted across conditions
Eligibility: a condition is eligible only if the comparator's EXPECTED failures (frozen pre-evaluation
projection) reach `min_expected_comparator_failures`; ineligible (near-zero-error) conditions are reported
descriptively and excluded from gates, never silently dropped after seeing results.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt

import numpy as np


@dataclass(frozen=True)
class ConditionData:
    name: str
    weight: float
    shots: np.ndarray                 # [roots] shots per root
    failures: dict[str, np.ndarray]   # arm -> [roots] failures per root (paired: same rows for every arm)
    expected_comparator_failures: float   # frozen projection, used ONLY for eligibility


def eligible(conds: list[ConditionData], min_expected: float) -> list[ConditionData]:
    return [c for c in conds if c.expected_comparator_failures >= min_expected]


def _ler(c: ConditionData, arm: str, idx: np.ndarray | None = None) -> float:
    f, s = c.failures[arm], c.shots
    if idx is not None:
        f, s = f[idx], s[idx]
    return float(f.sum() / s.sum())


def pooled_reduction(conds: list[ConditionData], cand: str, comp: str, idx: dict[str, np.ndarray] | None = None) -> float:
    w = np.array([c.weight for c in conds], dtype=float)
    w = w / w.sum()
    a = sum(wi * _ler(c, cand, None if idx is None else idx[c.name]) for wi, c in zip(w, conds))
    b = sum(wi * _ler(c, comp, None if idx is None else idx[c.name]) for wi, c in zip(w, conds))
    return float("nan") if b == 0 else 1 - a / b


def condition_reduction(c: ConditionData, cand: str, comp: str, idx: np.ndarray | None = None) -> float:
    b = _ler(c, comp, idx)
    return float("nan") if b == 0 else 1 - _ler(c, cand, idx) / b


def bootstrap(conds: list[ConditionData], cand: str, comp: str, *, reps: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    pooled, per = [], {c.name: [] for c in conds}
    for _ in range(reps):
        idx = {c.name: rng.integers(0, len(c.shots), len(c.shots)) for c in conds}
        pooled.append(pooled_reduction(conds, cand, comp, idx))
        for c in conds:
            per[c.name].append(condition_reduction(c, cand, comp, idx[c.name]))
    return {"pooled": np.array(pooled), "per_condition": {k: np.array(v) for k, v in per.items()}}


def lower_bound(samples: np.ndarray, alpha: float) -> float:
    s = samples[np.isfinite(samples)]
    if len(s) < 0.99 * len(samples):
        return float("nan")            # too many undefined replicates: bound not reported
    return float(np.quantile(s, alpha))


def holm(pvals: dict[str, float], alpha: float) -> dict[str, bool]:
    order = sorted(pvals, key=pvals.get)
    m, out, stop = len(order), {}, False
    for i, k in enumerate(order):
        ok = (not stop) and pvals[k] <= alpha / (m - i)
        stop = stop or not ok
        out[k] = ok
    return out


def gates(conds: list[ConditionData], cand: str, comp: str, *, target: float, alpha_agg: float, alpha_every: float,
          min_expected: float, reps: int, seed: int) -> dict:
    el = eligible(conds, min_expected)
    if not el:
        return {"eligible": [], "G_AGG": "UNDEFINED", "G_EVERY": "UNDEFINED"}
    bs = bootstrap(el, cand, comp, reps=reps, seed=seed)
    agg_lb = lower_bound(bs["pooled"], alpha_agg)
    # bootstrap p-value for H0: R_c <= target  ==  fraction of replicates at or below target
    pv = {k: float(np.mean(~(v > target))) for k, v in bs["per_condition"].items()}
    hv = holm(pv, alpha_every)
    worst = min(condition_reduction(c, cand, comp) for c in el)
    macro = float(np.mean([condition_reduction(c, cand, comp) for c in el]))
    return {
        "eligible": [c.name for c in el],
        "ineligible": [c.name for c in conds if c not in el],
        "R_pool": pooled_reduction(el, cand, comp), "R_pool_lower": agg_lb,
        "G_AGG": "PASS" if np.isfinite(agg_lb) and agg_lb >= target else "FAIL",
        "per_condition": {c.name: {"R": condition_reduction(c, cand, comp), "p_le_target": pv[c.name],
                                   "holm_reject": hv[c.name]} for c in el},
        "G_EVERY": "PASS" if all(hv.values()) else "FAIL",
        "worst_condition_R": worst, "macro_R": macro,
    }


def required_comparator_failures(true_r: float, target: float, alpha: float, z: float | None = None) -> float:
    """Approximate comparator failures needed so the one-sided lower bound on R clears `target`
    with ~50% power at true reduction `true_r` (log-ratio delta method, Poisson counts, pairing ignored,
    which is conservative). Use 2x for ~80% power planning margins.
    """
    from statistics import NormalDist
    z = z if z is not None else NormalDist().inv_cdf(1 - alpha)
    if not 0 < target < true_r < 1:
        raise ValueError("need 0 < target < true_r < 1")
    gap = log(1 - target) - log(1 - true_r)       # room on the log-ratio scale
    se_needed = gap / z
    # se^2 = 1/E_cand + 1/E_comp, E_cand = (1 - true_r) * E_comp
    return (1 / (1 - true_r) + 1) / se_needed ** 2


def ratio_se(e_cand: float, e_comp: float) -> float:
    return sqrt(1 / max(e_cand, 1e-9) + 1 / max(e_comp, 1e-9))
