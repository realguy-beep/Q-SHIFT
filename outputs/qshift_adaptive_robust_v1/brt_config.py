"""BRT threshold-free E1 flag: fixed configuration (PLAN_BRT.md, BRT_PROTOCOL.md). No sampling here."""
from __future__ import annotations

import bre_config as B  # noqa: F401  (sys.path setup, shared constants)
import brs_config as S  # noqa: F401  (frozen BRS constants, for the E1S/E1 reference arms)

D = B.D
QS = B.QS
DET_PER_Q, LAB_PER_Q, Q0_ROWS = B.DET_PER_Q, B.LAB_PER_Q, B.Q0_ROWS
NOMINAL = B.NOMINAL

# Reference-arm thresholds frozen from BRE (as in BRS). E1T itself uses only E1_MAX_EXCLUDED (a code property).
E1_STAT_THRESHOLD = 2.334772545348441
E1_MAX_EXCLUDED = 30
B2_THRESHOLD = 118.43178519191359

# id: (true-model kwargs, role) role in {"in", "oof", "oof_report"}. p range widened beyond every prior study.
CONDITIONS = {
    "T1": (dict(gate_p=0.0020, measurement_p=0.0020), "in"),
    "T2": (dict(gate_p=0.0040, measurement_p=0.0040), "in"),
    "T3": (dict(gate_p=0.0030, measurement_p=0.0030, regime="z_biased", bias_ratio=3.0), "in"),
    "T4": (dict(gate_p=0.0033, measurement_p=0.0033, regime="z_biased", bias_ratio=12.0), "in"),
    "TM25": (dict(gate_p=0.003, measurement_p=0.0075), "oof"),
    "TM2": (dict(gate_p=0.0036, measurement_p=0.0072), "oof"),
    "TM15": (dict(gate_p=0.003, measurement_p=0.0045), "oof_report"),
    "TX": (dict(gate_p=0.003, measurement_p=0.003, regime="x_biased", bias_ratio=4.0), "oof"),
}
IN_FAMILY = tuple(c for c, v in CONDITIONS.items() if v[1] == "in")
OOF_GATED = tuple(c for c, v in CONDITIONS.items() if v[1] == "oof")

PER_STRATUM = 4
FOOTPRINT_STRATA = B.FOOTPRINT_STRATA
POOLS_PER_BURST = 2
Q0_POOLS = 32
ARMS = ("B2", "E1", "E1S", "E1T")

LEARN_MIN_OVERALL, LEARN_MIN_PER_COND = 0.95, 30      # of 32 burst pools per in-family condition
MAX_FALSE_ACCEPT, MAX_FALSE_FLAG = 1, 1               # of 32, per condition
OOF_MIN_FLAG = 30                                     # of 32 burst pools
NO_LOSS_VS_E1 = 2
BUDGET_S, JOB_TIMEOUT_S = 10_800, 3_600

REHEARSAL = [("T2", "burst", 0), ("TM2", "q0", 0), ("TX", "burst", 0)]   # burst index into the drawn set


def spec(**kw):
    return D.spec(**kw)


def burst_key(c, b, k, qi):
    return f"brt:{c}:{b}:p{k}:q{qi}"


def q0_key(c, k):
    return f"brt:{c}:q0:{k:02d}"


def all_keys(bursts):
    keys = []
    for c in CONDITIONS:
        keys += [burst_key(c, b, k, qi) for b in bursts["V"] for k in range(POOLS_PER_BURST) for qi in range(3)]
        keys += [q0_key(c, k) for k in range(Q0_POOLS)]
    return keys


def rehearsal_keys(bursts):
    ids = sorted(bursts["V"])
    keys = []
    for c, kind, i in REHEARSAL:
        keys += [burst_key(c, ids[i], 0, qi) for qi in range(3)] if kind == "burst" else [q0_key(c, i)]
    return keys
