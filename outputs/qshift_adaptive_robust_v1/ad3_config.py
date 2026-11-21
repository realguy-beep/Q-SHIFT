"""AD3 faster reaction to a change: fixed configuration (PLAN_AD3.md, AD3_PROTOCOL.md).
No sampling. AD2's public bursts and schedules, unchanged; no seal is read."""
from __future__ import annotations

import json

import ad2_config as A2

ROOT = A2.ROOT
BURSTS, SCHEDULES, CHANGING, CHANGES = A2.BURSTS, A2.SCHEDULES, A2.CHANGING, A2.CHANGES
BLOCKS, WINDOW, SCORED = A2.BLOCKS, A2.WINDOW, A2.SCORED
DET_PER_BLOCK, LAB_PER_BLOCK, EVAL_PER_BLOCK = A2.DET_PER_BLOCK, A2.LAB_PER_BLOCK, A2.EVAL_PER_BLOCK
REHEARSAL_EVAL_PER_BLOCK = A2.REHEARSAL_EVAL_PER_BLOCK
PERIODIC_AT, NOMINAL = A2.PERIODIC_AT, A2.NOMINAL
block_truth, state, spec, PARTS = A2.block_truth, A2.state, A2.spec, A2.PARTS

EPISODES, EPISODES_FALLBACK = 6, 5
ARMS = ("AD3", "AD", "PERIODIC", "ONCE", "ORACLE", "A_nominal")

# ---- Phase 1 screen (PLAN_AD3.md): fixed sizes and rules
SCREEN_NULL_PER_STATE = 4                 # static streams per state (A, B, C, D, none) -> 20 streams
SCREEN_STATES = ("A", "B", "C", "D", None)
SCREEN_FALSE_ALARM_MAX = 0.01             # at most 1 false detection per 100 block comparisons
SCREEN_CHANGES = (("A", "B"), ("A", None), (None, "A"), ("B", "C"), ("C", "D"))
SCREEN_POWER_PER_CHANGE = 4               # 20 change streams, change at block 15
SCREEN_CHANGE_AT = 15
SCREEN_POWER_MIN = 0.80                   # detection within 2 blocks; below -> stop and return to the owner
SCREEN_M_LENGTHS = (1, 2, 3)
SCREEN_M_PER_BURST = 20                   # static windows per burst A-D per length
SCREEN_M_NONE = 10                        # burst-free windows per length (descriptive)
SCREEN_M_LEARN_MIN, SCREEN_M_FLAG_MAX = 0.95, 0.05
M_DEFAULT = 6                             # no length qualifies -> AD3 = change detection + recall + AD's window

# ---- endpoints
NO_HARM_FACTOR, NO_HARM_SLACK = 1.1, 3    # F3
LATENCY_MAX = 2                           # F5
BOOT_REPS, BOOT_SEED_LABEL = 20_000, "qshift-adaptive-robust-v1:ad3:boot"
BUDGET_S, JOB_TIMEOUT_S, CONTENTION = 21_600, 9_000, 1.25
REHEARSAL = [("C0", 0), ("S2", 0)]
FALLBACK = "5 episodes per schedule"


def block_key(s, e, t, part):
    return f"ad3:{s}:e{e}:b{t:02d}:{part}"


def all_keys(episodes=EPISODES):
    return [block_key(s, e, t, p) for s in SCHEDULES for e in range(episodes) for t in range(BLOCKS) for p in PARTS]


def rehearsal_keys():
    return [block_key(s, e, t, p) for s, e in REHEARSAL for t in range(BLOCKS) for p in PARTS]


def _st(name):
    return "none" if name is None else name


def screen_keys():
    ks = []
    for st in SCREEN_STATES:
        for i in range(SCREEN_NULL_PER_STATE):
            ks += [f"ad3screen:null:{_st(st)}:{i}:b{t:02d}:det" for t in range(BLOCKS)]
    for a, b in SCREEN_CHANGES:
        for i in range(SCREEN_POWER_PER_CHANGE):
            ks += [f"ad3screen:power:{_st(a)}-{_st(b)}:{i}:b{t:02d}:det" for t in range(BLOCKS)]
    for L in SCREEN_M_LENGTHS:
        for st in ("A", "B", "C", "D", None):
            for i in range(SCREEN_M_PER_BURST if st else SCREEN_M_NONE):
                ks += [f"ad3screen:m{L}:{_st(st)}:{i}:b{t}:{p}" for t in range(L) for p in ("det", "lab")]
    return ks


def screen_params():
    """tau and M from AD3_SCREEN.json (written once by screen_ad3.py, frozen)."""
    d = json.loads((ROOT / "AD3_SCREEN.json").read_text(encoding="utf-8"))
    return float(d["rule"]["tau"]), int(d["rule"]["M"])
