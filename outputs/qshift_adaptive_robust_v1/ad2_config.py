"""AD2 adaptive decoding when the burst itself changes: fixed configuration (PLAN_AD2.md, AD2_PROTOCOL.md).
No sampling. Public development bursts only; no seal is read."""
from __future__ import annotations

import json
from pathlib import Path

import ad1_config as A1  # noqa: F401  (sys.path setup through brt_config; shared NOMINAL, spec)

D = A1.D
ROOT = Path(__file__).resolve().parent
NOMINAL = A1.NOMINAL

BLOCKS, WINDOW, WINDOW_W3 = 30, 6, 3
DET_PER_BLOCK, LAB_PER_BLOCK, EVAL_PER_BLOCK = 2_000, 250, 1_000
REHEARSAL_EVAL_PER_BLOCK = 200
SCORED = range(WINDOW, BLOCKS)            # blocks 6-29
PERIODIC_AT = (6, 12, 18, 24)
BURST_Q = 0.01
EPISODES, EPISODES_FALLBACK = 6, 5
P0 = 0.003

# ---- burst rule (PLAN_AD2.md, "Bursts"): first public burst per footprint stratum, label order, BRS before BRT,
# excluding AD1's bursts; assigned A-D in footprint order.
STRATA = ((0, 15), (16, 20), (21, 25), (26, 10_000))
EXCLUDED = ("K", "W13", "X13")


def _public():
    out = []
    for f in ("BRS_BURSTS.json", "BRT_BURSTS.json"):
        d = json.loads((ROOT / f).read_text(encoding="utf-8"))
        for lab in sorted(d["V"]):
            out.append((lab, tuple(int(q) for q in d["V"][lab]), int(d["footprint"][lab])))
    return out


def choose_bursts():
    pub = [b for b in _public() if b[0] not in EXCLUDED]
    picked = []
    for lo, hi in STRATA:
        picked.append(next(b for b in pub if lo <= b[2] <= hi))
    picked.sort(key=lambda b: (b[2], b[0]))
    return {name: {"label": b[0], "support": b[1], "footprint": b[2]} for name, b in zip("ABCD", picked)}


BURSTS = choose_bursts()


def _bg(p=P0):
    return dict(gate_p=p, measurement_p=p)


def _sched_c0(t):
    return _bg(), "A"


def _sched_s1(t):
    return _bg(), "A" if t < 15 else "B"


def _sched_s2(t):
    return _bg(), "A" if (6 <= t <= 11 or 18 <= t <= 23) else None


def _sched_s3(t):
    return _bg(0.0025 if t < 15 else 0.0035), "A" if t < 15 else "C"


def _sched_s4(t):
    return _bg(), "B" if t < 10 else "C" if t < 20 else "D"


# schedule -> function(block t) -> (true-model kwargs, burst name or None)
SCHEDULES = {"C0": _sched_c0, "S1": _sched_s1, "S2": _sched_s2, "S3": _sched_s3, "S4": _sched_s4}
CHANGING = ("S1", "S2", "S3", "S4")
CHANGES = {"S1": (15,), "S2": (6, 12, 18, 24), "S3": (15,), "S4": (10, 20)}
# E3 needs settled blocks (block t and its 6-block window in one state = 7 equal blocks). S2's segments are 6 blocks,
# so S2 has none by construction; E3 is evaluated on S1, S3, S4 (build-time clarification, AD2_PROTOCOL.md).
E3_SCHEDULES = ("S1", "S3", "S4")

ARMS = ("AD", "AD_LG", "PERIODIC", "ONCE", "ORACLE", "AD_M", "A_nominal", "AD_W3")
L2_ARMS = ("AD", "AD_LG", "PERIODIC", "ONCE", "ORACLE", "AD_W3")
ARMS_NO_W3 = tuple(a for a in ARMS if a != "AD_W3")

ORACLE_EXCESS_MAX = 0.25                  # E3, settled blocks, point estimate
LATENCY_MAX = 7                           # E4, median blocks
NO_HARM_FACTOR, NO_HARM_SLACK = 1.1, 3    # E5 (AD1's rule)
STRONG_MIN_PERIODIC = 3                   # E2 passes in >= 3 of S1-S4 -> AD2_STRONG
PARTIAL_MIN_E1 = 2
BOOT_REPS, BOOT_SEED_LABEL = 20_000, "qshift-adaptive-robust-v1:ad2:boot"
BUDGET_S, JOB_TIMEOUT_S = 28_800, 9_000   # 8 h (owner-approved after the rehearsal, before any study sample;
                                          # PLAN_AD2.md had 5 h, which no pre-declared fallback level fits)
CONTENTION = 1.25

REHEARSAL = [("C0", 0), ("S1", 0)]
FALLBACK = "drop AD_W3; then 5 episodes per schedule"


def spec(**kw):
    return D.spec(**kw)


def block_truth(schedule, t):
    """(true-model kwargs, burst name or None, burst support or None)."""
    kw, name = SCHEDULES[schedule](t)
    return kw, name, (BURSTS[name]["support"] if name else None)


def state(schedule, t):
    kw, name, _ = block_truth(schedule, t)
    return json.dumps([kw, name], sort_keys=True)


def block_key(s, e, t, part):
    return f"ad2:{s}:e{e}:b{t:02d}:{part}"


PARTS = ("det", "lab", "eval")


def all_keys(episodes=EPISODES):
    return [block_key(s, e, t, p) for s in SCHEDULES for e in range(episodes) for t in range(BLOCKS) for p in PARTS]


def rehearsal_keys():
    return [block_key(s, e, t, p) for s, e in REHEARSAL for t in range(BLOCKS) for p in PARTS]
