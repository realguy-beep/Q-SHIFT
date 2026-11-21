"""DB2 configuration (PLAN_DB2.md, as amended before any DB2 sample). Development only; no seal is read.

Reuses DB1 (outputs/qshift_decoder_bank_v1: db_config, db_core, TRAINING.json) and, through it, AD2/AD3,
all read-only."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB1 = ROOT.parent / "qshift_decoder_bank_v1"
if str(DB1) not in sys.path:
    sys.path.insert(0, str(DB1))

import db_config as C1  # noqa: E402  (also puts AD2/AD3 on sys.path)

ADR = C1.ADR
BLOCKS, WINDOW, SCORED = C1.BLOCKS, C1.WINDOW, C1.SCORED
DET_PER_BLOCK, LAB_PER_BLOCK, EVAL_PER_BLOCK = C1.DET_PER_BLOCK, C1.LAB_PER_BLOCK, C1.EVAL_PER_BLOCK
STATES = C1.STATES
support = C1.support
spec, P0, NOMINAL = C1.spec, C1.P0, C1.NOMINAL
AD3_TAU = C1.AD3_TAU

# ---- the transition-aware gate (fixed rules; nothing tuned on any validation episode)
HAZ_A0, HAZ_B0 = 1.0, 29.0     # Beta prior on leaving a state per block: "one change per 30-block episode"
DEST_ALPHA = 0.25              # Dirichlet pseudo-count per possible next state once a change out has been seen
KAPPA_DB2 = 0.0                # amended: no hysteresis (PLAN_DB2.md, amendment A1)
KAPPA_PLAN = C1.KAPPA          # the approved rule, kept as arm DB2_PLAN (0.0005, worst case always)

# ---- development panels (fresh DB2 seeds)
EPISODES = {"C0": 2, "N": 3, "R": 4, "R_long": 2, "RB": 2, "RX": 4, "S1": 2, "S4": 2, "U": 2}
SCHEDULES = tuple(EPISODES)
STATIC_SCHED = ("C0", "N")
ARMS = ("DB2", "DB2_PLAN", "BANK", "AD3", "STATIC", "ORACLE", "A_nominal")
EVENT_ARMS = ("DB2", "DB2_PLAN", "BANK", "AD3", "STATIC")
BOOT_REPS, BOOT_SEED_LABEL = 20_000, "qshift-decoder-bank-v2:db2:boot"


def episode_params(s, e, rng_seed):
    """Per-episode schedule parameters (generator/scorer only; never shown to a policy)."""
    import numpy as np
    rng = np.random.default_rng(rng_seed)
    if s == "N":
        return {"state": STATES[int(rng.integers(0, len(STATES)))]}
    if s in ("R", "RB"):
        return {"on1": int(rng.integers(6, 8)), "dwell": [int(rng.integers(4, 6)) for _ in range(3)]}
    if s == "R_long":
        return {"on1": int(rng.integers(6, 8)), "dwell": [int(rng.integers(4, 6))]}
    if s == "RX":
        return {"on1": int(rng.integers(6, 8)), "dwell": [int(rng.integers(4, 6)) for _ in range(5)]}
    if s == "U":
        return {"onset": int(rng.integers(8, 13))}
    return {}


def _seq(on1, dwell, states):
    """Piecewise schedule: OFF before on1, then states[i] for dwell[i] blocks, then OFF."""
    out, t = ["OFF"] * BLOCKS, on1
    for st, d in zip(states, dwell):
        for u in range(t, min(t + d, BLOCKS)):
            out[u] = st
        t += d
    return out


def block_state(s, t, prm):
    if s == "C0":
        return "A"
    if s == "N":
        return prm["state"]
    if s == "S1":
        return "A" if t < 15 else "B"
    if s == "S4":
        return "B" if t < 10 else "C" if t < 20 else "D"
    if s == "U":
        return "A" if t < prm["onset"] else "E"
    if s == "R":
        return _seq(prm["on1"], prm["dwell"], ["A", "OFF", "A"])[t]
    if s == "RB":
        return _seq(prm["on1"], prm["dwell"], ["B", "OFF", "B"])[t]
    if s == "R_long":
        return _seq(prm["on1"], prm["dwell"], ["A"])[t]
    if s == "RX":
        return _seq(prm["on1"], prm["dwell"], ["A", "OFF", "B", "OFF", "A"])[t]
    raise KeyError(s)


def changes(s, prm):
    st = [block_state(s, t, prm) for t in range(BLOCKS)]
    return [t for t in range(1, BLOCKS) if st[t] != st[t - 1]]


PARTS = ("det", "lab", "eval")


def block_key(s, e, t, part):
    return f"db2:{s}:e{e}:b{t:02d}:{part}"


def all_keys():
    ks = [f"db2:params:{s}:e{e}" for s in SCHEDULES for e in range(EPISODES[s])]
    return ks + [block_key(s, e, t, p) for s in SCHEDULES for e in range(EPISODES[s]) for t in range(BLOCKS) for p in PARTS]
