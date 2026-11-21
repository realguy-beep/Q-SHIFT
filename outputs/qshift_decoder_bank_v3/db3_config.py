"""DB3 configuration (PLAN_DB3.md): tiebreak between the DB2 risk-gate rules. Development only; no seal is read.

Reuses DB2 (outputs/qshift_decoder_bank_v2: db2_config, db2_core) and, through it, DB1 and AD2/AD3, read-only.
No new parameter values: W0 is DB2's gate in "worst" mode with kappa 0; DB2 and DB2_PLAN keep their DB2 values."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB2 = ROOT.parent / "qshift_decoder_bank_v2"
if str(DB2) not in sys.path:
    sys.path.insert(0, str(DB2))

import db2_config as C2  # noqa: E402  (also puts DB1 and AD2/AD3 on sys.path)

DB1 = C2.DB1
BLOCKS, WINDOW, SCORED = C2.BLOCKS, C2.WINDOW, C2.SCORED
DET_PER_BLOCK, LAB_PER_BLOCK, EVAL_PER_BLOCK = C2.DET_PER_BLOCK, C2.LAB_PER_BLOCK, C2.EVAL_PER_BLOCK
STATES = C2.STATES
support, spec, P0, NOMINAL, AD3_TAU = C2.support, C2.spec, C2.P0, C2.NOMINAL, C2.AD3_TAU

# ---- candidates (gate mode, kappa), in simplicity order (PLAN_DB3.md)
CANDIDATES = {"W0": ("worst", 0.0), "DB2_PLAN": ("worst", C2.KAPPA_PLAN), "DB2": ("hybrid", C2.KAPPA_DB2)}
SIMPLICITY = ("W0", "DB2_PLAN", "DB2")
MARGIN = 12            # errors per episode (= 0.0005 LER at 24,000 rows): E2 margin and the simplicity tie-break

# ---- panels (fresh DB3 seeds)
EPISODES = {"N_OFF": 3, "N_C": 2, "AA": 2, "BB": 4, "AB": 3, "BA": 4}
SCHEDULES = tuple(EPISODES)
NULL_SCHED = ("N_OFF", "N_C")
TWO = {"AA": ("A", "A"), "BB": ("B", "B"), "AB": ("A", "B"), "BA": ("B", "A")}
ARMS = ("W0", "DB2", "DB2_PLAN", "BANK", "AD3", "STATIC", "ORACLE", "A_nominal")
BANK_ARMS = ("BANK", "W0", "DB2", "DB2_PLAN")


def episode_params(s, e, rng_seed):
    """Per-episode schedule parameters (generator/scorer only; never shown to a policy)."""
    import numpy as np
    rng = np.random.default_rng(rng_seed)
    if s in TWO:      # burst 1, OFF gap, burst 2: each 4-5 blocks, first onset at block 6 or 7 (as DB2)
        return {"on1": int(rng.integers(6, 8)), "dwell": [int(rng.integers(4, 6)) for _ in range(3)]}
    return {}


def block_state(s, t, prm):
    if s == "N_OFF":
        return "OFF"
    if s == "N_C":
        return "C"
    if s in TWO:
        x, y = TWO[s]
        return C2._seq(prm["on1"], prm["dwell"], [x, "OFF", y])[t]
    raise KeyError(s)


def changes(s, prm):
    st = [block_state(s, t, prm) for t in range(BLOCKS)]
    return [t for t in range(1, BLOCKS) if st[t] != st[t - 1]]


PARTS = ("det", "lab", "eval")


def block_key(s, e, t, part):
    return f"db3:{s}:e{e}:b{t:02d}:{part}"


def all_keys():
    ks = [f"db3:params:{s}:e{e}" for s in SCHEDULES for e in range(EPISODES[s])]
    return ks + [block_key(s, e, t, p) for s in SCHEDULES for e in range(EPISODES[s]) for t in range(BLOCKS) for p in PARTS]
