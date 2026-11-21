"""DB1 causal decoder bank: fixed configuration (PLAN_DB1.md). Development only; no seal is read.

Reuses the AD2/AD3 stream, estimator and decoders from outputs/qshift_adaptive_robust_v1 (read-only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADR = ROOT.parent / "qshift_adaptive_robust_v1"
if str(ADR) not in sys.path:
    sys.path.insert(0, str(ADR))

import ad2_config as A2  # noqa: E402  (sets the shared sys.path through ad1_config/brt_config)

BLOCKS, WINDOW, SCORED = A2.BLOCKS, A2.WINDOW, A2.SCORED              # 30, 6, blocks 6-29
DET_PER_BLOCK, LAB_PER_BLOCK, EVAL_PER_BLOCK = 2_000, 250, 1_000
P0, BURST_Q, NOMINAL = A2.P0, A2.BURST_Q, A2.NOMINAL
spec = A2.spec

# ---- bank states (closed bank of characterised states; disclosed advance information)
BURSTS = A2.BURSTS                                                    # A=W01, B=W05, C=W09, D=W14
STATES = ("OFF", "A", "B", "C", "D")                                  # OFF = burst-free at p0 (= nominal)


def support(name):
    return None if name in (None, "OFF") else tuple(_all_supports()[name])


def _all_supports():
    out = {k: tuple(v["support"]) for k, v in BURSTS.items()}
    out["E"] = tuple(UNKNOWN["support"])
    return out


def _choose_unknown():
    """U panel burst, by a fixed rule written before any DB1 sample: the first public burst in label order
    (BRS before BRT) with footprint 16-25 that is not A-D and not AD1's K, W13 or X13. Never in the bank,
    never in training."""
    used = {v["label"] for v in BURSTS.values()} | {"K", "W13", "X13"}
    for f in ("BRS_BURSTS.json", "BRT_BURSTS.json"):
        d = json.loads((ADR / f).read_text(encoding="utf-8"))
        for lab in sorted(d["V"]):
            if lab not in used and 16 <= int(d["footprint"][lab]) <= 25:
                return {"label": lab, "support": [int(q) for q in d["V"][lab]], "footprint": int(d["footprint"][lab])}
    raise RuntimeError("no unknown burst")


UNKNOWN = _choose_unknown()

# ---- training (separate training seeds; never the validation episodes)
TEMPLATE_BLOCKS = 20          # per state: 40,000 detector rows -> per-detector rate template
FIT_STREAMS, FIT_BLOCKS = 4, 30   # per state: static streams for the fit thresholds tau_fit[L]
FIT_QUANTILE = 0.995          # tau_fit[L] = max over states of this quantile of own-state G_fit
RISK_ROWS = 5_000             # per state: labelled rows decoded by every bank key -> risk table R[state][key]
KAPPA = 0.0005                # hysteresis: keep the current key unless another lowers worst-case risk by > KAPPA

# ---- AD3 (frozen values, reused unchanged)
AD3_TAU, AD3_M = 163.13055125732944, 6

# ---- validation schedules (development episodes, fresh seeds)
EPISODES = {"C0": 2, "N": 2, "S1": 3, "S4": 3, "R": 4, "U": 2}
SCHEDULES = tuple(EPISODES)
STATIC_SCHED = ("C0", "N")
ARMS = ("BANK", "BANK_ID", "AD3", "AD", "STATIC", "ORACLE", "A_nominal")
BOOT_REPS, BOOT_SEED_LABEL = 20_000, "qshift-decoder-bank-v1:db1:boot"
REHEARSAL_EVAL_PER_BLOCK = 200


def episode_params(s, e, rng_seed):
    """Per-episode schedule parameters from a seeded RNG (generator/scorer only; never shown to a policy)."""
    import numpy as np
    rng = np.random.default_rng(rng_seed)
    if s == "N":
        return {"state": STATES[int(rng.integers(0, len(STATES)))]}
    if s == "R":
        o1 = int(rng.integers(6, 8))
        d = [int(rng.integers(4, 6)) for _ in range(3)]
        return {"on1": o1, "dwell": d}
    if s == "U":
        return {"onset": int(rng.integers(8, 13))}
    return {}


def block_state(s, t, prm):
    """True burst-state name at block t ("OFF", "A"-"D" or "E"); background is p0 throughout."""
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
        c1 = prm["on1"]
        c2, c3, c4 = c1 + prm["dwell"][0], c1 + sum(prm["dwell"][:2]), c1 + sum(prm["dwell"])
        return "A" if (c1 <= t < c2 or c3 <= t < c4) else "OFF"
    raise KeyError(s)


def changes(s, prm):
    st = [block_state(s, t, prm) for t in range(BLOCKS)]
    return [t for t in range(1, BLOCKS) if st[t] != st[t - 1]]


def block_key(s, e, t, part):
    return f"db1:{s}:e{e}:b{t:02d}:{part}"


PARTS = ("det", "lab", "eval")


def all_keys():
    ks = [f"db1:params:{s}:e{e}" for s in SCHEDULES for e in range(EPISODES[s])]
    return ks + [block_key(s, e, t, p) for s in SCHEDULES for e in range(EPISODES[s]) for t in range(BLOCKS) for p in PARTS]


def train_keys():
    ks = []
    for st in STATES:
        ks += [f"db1train:tpl:{st}:b{b:02d}" for b in range(TEMPLATE_BLOCKS)]
        ks += [f"db1train:fit:{st}:{i}:b{b:02d}" for i in range(FIT_STREAMS) for b in range(FIT_BLOCKS)]
        ks += [f"db1train:risk:{st}"]
    return ks
