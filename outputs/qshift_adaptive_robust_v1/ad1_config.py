"""AD1 adaptive decoding under drifting noise: fixed configuration (PLAN_AD1.md, AD1_PROTOCOL.md). No sampling."""
from __future__ import annotations

import json
from pathlib import Path

import brt_config as T  # noqa: F401  (sys.path setup; E1T configuration)

D = T.D
ROOT = Path(__file__).resolve().parent
NOMINAL = T.NOMINAL
L2_PRIOR, ASTAR_Q_DEC = D.L2_PRIOR, D.ASTAR_Q_DEC

BLOCKS, WINDOW = 24, 6                    # window = 6 blocks = 12,000 unlabelled + 1,500 labelled rows
DET_PER_BLOCK, LAB_PER_BLOCK, EVAL_PER_BLOCK = 2_000, 250, 1_000
REHEARSAL_EVAL_PER_BLOCK = 200
SCORED = range(WINDOW, BLOCKS)            # blocks 6-23
BURST_Q = 0.01
EPISODES = 6
EPISODES_FALLBACK = 5                     # pre-declared, if the preflight exceeds the budget


def _bursts():
    brs = json.loads((ROOT / "BRS_BURSTS.json").read_text(encoding="utf-8"))["V"]
    brt = json.loads((ROOT / "BRT_BURSTS.json").read_text(encoding="utf-8"))["V"]
    return {"K": (23, 31, 34), "X13": tuple(brt["X13"]), "W13": tuple(brs["W13"])}


BURSTS = _bursts()


def lin(a, b, t):
    return a + (b - a) * t / (BLOCKS - 1)


# schedule -> function(block t) -> (true-model kwargs, burst id or None)
SCHEDULES = {
    "C0": lambda t: (dict(gate_p=0.003, measurement_p=0.003), "K"),
    "D1": lambda t: (dict(gate_p=lin(0.0025, 0.0035, t), measurement_p=lin(0.0025, 0.0035, t)), "K"),
    "D2": lambda t: (dict(gate_p=0.003, measurement_p=0.003, regime="z_biased", bias_ratio=lin(1.0, 8.0, t)), "X13"),
    "D3": lambda t: (dict(gate_p=0.003, measurement_p=0.003), "W13" if 8 <= t <= 15 else None),
    "D4": lambda t: (dict(gate_p=0.0025 if t < 12 else 0.0035, measurement_p=0.0025 if t < 12 else 0.0035), "K"),
}
TRACKING = ("D1", "D2", "D4")
ONSET, OFFSET = 8, 16                      # D3 burst on in blocks 8-15
ARMS = ("AD", "ONCE", "ORACLE", "AD_M", "A_nominal")
L2_ARMS = ("AD", "ONCE", "ORACLE")

TRACK_EXCESS_MAX = 0.25                   # AD - ORACLE <= 25% of ORACLE LER
NO_HARM_FACTOR, NO_HARM_SLACK = 1.1, 3
ONSET_MAX, OFFSET_MAX = 6, 6              # median latency, blocks (onset 3 -> 6: rehearsal-driven, owner-approved)
MAX_FLAGGED_WINDOWS_PER_EPISODE = 1       # counted over SETTLED windows only (all 6 blocks in one burst state);
                                          # transition-window flags are reported, not gated (owner-approved)
BOOT_REPS, BOOT_SEED_LABEL = 20_000, "qshift-adaptive-robust-v1:ad1:boot"
BUDGET_S, JOB_TIMEOUT_S = 18_000, 7_200

REHEARSAL = [("C0", 0), ("D3", 0)]


def spec(**kw):
    return D.spec(**kw)


def block_key(s, e, t, part):
    return f"ad1:{s}:e{e}:b{t:02d}:{part}"


PARTS = ("det", "lab", "eval")


def all_keys(episodes=EPISODES):
    return [block_key(s, e, t, p) for s in SCHEDULES for e in range(episodes) for t in range(BLOCKS) for p in PARTS]


def rehearsal_keys():
    return [block_key(s, e, t, p) for s, e in REHEARSAL for t in range(BLOCKS) for p in PARTS]
