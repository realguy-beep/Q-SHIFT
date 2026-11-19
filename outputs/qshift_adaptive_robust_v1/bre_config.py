"""BRE burst-robust estimation development study: fixed configuration (PLAN_BRE.md, BRE_PROTOCOL.md). No sampling."""
from __future__ import annotations

import dev2_config as D  # noqa: F401  (sys.path setup, shared constants)

QS = D.QS
DET_PER_Q, LAB_PER_Q, Q0_ROWS = D.DET_PER_Q, D.LAB_PER_Q, D.Q0_ROWS
NOMINAL = D.NOMINAL
N_CAL = 3 * DET_PER_Q                      # unlabelled calibration rows per burst pool (fit weights in the census)

# id: (true-model kwargs, in_family). Values deliberately differ from RE1's.
CONDITIONS = {
    "B1": (dict(gate_p=0.0026, measurement_p=0.0026), True),
    "B2c": (dict(gate_p=0.0034, measurement_p=0.0034), True),
    "B3": (dict(gate_p=0.003, measurement_p=0.003, regime="z_biased", bias_ratio=4.0), True),
    "B4": (dict(gate_p=0.003, measurement_p=0.003, regime="z_biased", bias_ratio=10.0), True),
    "B5": (dict(gate_p=0.0028, measurement_p=0.0028, regime="z_biased", bias_ratio=6.0), True),
    "BX": (dict(gate_p=0.003, measurement_p=0.003, regime="x_biased", bias_ratio=10.0), False),
    "BM": (dict(gate_p=0.003, measurement_p=0.009), False),
}
IN_FAMILY = tuple(c for c, v in CONDITIONS.items() if v[1])
PREFLIGHT_DROP = ("BM",)                   # pre-declared fallback if the preflight exceeds the budget

# Bursts. T = tuning (sets thresholds), V = held out (verdict only). Random members are drawn by prepare_bre.py.
FIXED_T = {"K": (23, 31, 34), "M0": (12, 34, 45), "M1": (1, 23, 45), "CR": (25, 27, 29)}
N_RANDOM_T, N_V = 8, 12
POOLS_PER_BURST = 2
Q0_POOLS = 48                              # per condition; 0-23 tuning, 24-47 held out
Q0_TUNING = range(0, 24)
FOOTPRINT_STRATA = ((0, 15), (16, 20), (21, 25), (26, 10_000))   # detectors raised >10% at q=0.02

# Estimators
E1_CUTOFF = 4.0                            # standardized one-sided residual cutoff (fixed a priori; see protocol)
E1_MAX_IT = 10
E1_START_DROP = 30                         # largest burst detector set over all classes (BRE-0 change)
FOOTPRINT_RISE = 0.10
ARMS = ("B2", "E1", "E2", "E3")
PREFERENCE = ("E1", "E3", "E2")            # simplest first, if several arms pass

# Endpoints (held-out V, in-family conditions)
LEARN_MIN_OVERALL, LEARN_MIN_PER_COND = 0.95, 22      # of 24 V burst pools per condition
MAX_FALSE_ACCEPT, MAX_FALSE_FLAG = 1, 1               # per condition, of 24
OOF_MIN_FLAG = 23                                     # of 24 V burst pools per out-of-family condition
BUDGET_S, JOB_TIMEOUT_S = 18_000, 3_600

REHEARSAL = [("B3", "burst", "K", 0), ("B4", "burst", "M1", 0), ("BX", "q0", None, 0)]


def spec(**kw):
    return D.spec(**kw)


def burst_key(c, b, k, qi):
    return f"bre:{c}:{b}:p{k}:q{qi}"


def q0_key(c, k):
    return f"bre:{c}:q0:{k:02d}"


def burst_ids(bursts):
    return list(bursts["T"]) + list(bursts["V"])


def all_keys(bursts):
    keys = []
    for c in CONDITIONS:
        keys += [burst_key(c, b, k, qi) for b in burst_ids(bursts) for k in range(POOLS_PER_BURST) for qi in range(3)]
        keys += [q0_key(c, k) for k in range(Q0_POOLS)]
    return keys


def rehearsal_keys():
    keys = []
    for c, kind, b, k in REHEARSAL:
        keys += [burst_key(c, b, k, qi) for qi in range(3)] if kind == "burst" else [q0_key(c, k)]
    return keys
