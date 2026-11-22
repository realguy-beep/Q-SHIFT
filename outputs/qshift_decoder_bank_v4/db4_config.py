"""DB4 configuration (PLAN_DB4.md): static fallback on the unknown path. Development only; no seal is read.

Reuses DB3 (outputs/qshift_decoder_bank_v3: db3_config, db3_core) and, through it, DB2, DB1 and AD2/AD3,
read-only. The only new logic is the W0F arm's unknown-path rule (db4_core.fallback_key)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB3 = ROOT.parent / "qshift_decoder_bank_v3"
if str(DB3) not in sys.path:
    sys.path.insert(0, str(DB3))

import db3_config as C3  # noqa: E402  (also puts DB2, DB1 and AD2/AD3 on sys.path)

C2 = C3.C2
DB2, DB1 = C3.DB2, C3.DB1
BLOCKS, WINDOW, SCORED = C3.BLOCKS, C3.WINDOW, C3.SCORED
DET_PER_BLOCK, LAB_PER_BLOCK, EVAL_PER_BLOCK = C3.DET_PER_BLOCK, C3.LAB_PER_BLOCK, C3.EVAL_PER_BLOCK
STATES = C3.STATES
support, spec, P0, NOMINAL, AD3_TAU = C3.support, C3.spec, C3.P0, C3.NOMINAL, C3.AD3_TAU

# ---- bank-family gates (mode, kappa); W0F = W0's gate with the static fallback (FALLBACK_ARMS)
CANDIDATES = {**C3.CANDIDATES, "W0F": C3.CANDIDATES["W0"]}
FALLBACK_ARMS = ("W0F",)
ARMS = ("W0F",) + C3.ARMS
BANK_ARMS = C3.BANK_ARMS + ("W0F",)

# ---- panels (fresh DB4 seeds): DB3's six plus DB2's S1, S4 and U
EPISODES = {"N_OFF": 2, "N_C": 2, "AA": 4, "BB": 2, "AB": 2, "BA": 2, "S1": 2, "S4": 2, "U": 3}
SCHEDULES = tuple(EPISODES)
NULL_SCHED = C3.NULL_SCHED
DB2_PANELS = ("S1", "S4", "U")
G4_PANELS = ("BB", "AB", "BA", "S1", "S4", "N_C")


def episode_params(s, e, rng_seed):
    """Per-episode schedule parameters (generator/scorer only; never shown to a policy)."""
    if s in DB2_PANELS:
        return C2.episode_params(s, e, rng_seed)
    return C3.episode_params(s, e, rng_seed)


def block_state(s, t, prm):
    if s in DB2_PANELS:
        return C2.block_state(s, t, prm)
    return C3.block_state(s, t, prm)


def changes(s, prm):
    st = [block_state(s, t, prm) for t in range(BLOCKS)]
    return [t for t in range(1, BLOCKS) if st[t] != st[t - 1]]


PARTS = ("det", "lab", "eval")


def block_key(s, e, t, part):
    return f"db4:{s}:e{e}:b{t:02d}:{part}"


def all_keys():
    ks = [f"db4:params:{s}:e{e}" for s in SCHEDULES for e in range(EPISODES[s])]
    return ks + [block_key(s, e, t, p) for s in SCHEDULES for e in range(EPISODES[s]) for t in range(BLOCKS) for p in PARTS]
