"""CF1 configuration (PLAN_CF1.md): confirmatory run of W0F. No seal is read.

Reuses DB4 (outputs/qshift_decoder_bank_v4: db4_config, db4_core, db4_run) and, through it, DB3, DB2, DB1 and
AD2/AD3, read-only. Changes from DB4: the episode counts and the seed namespace ("cf1:"). Nothing else."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB4 = ROOT.parent / "qshift_decoder_bank_v4"
if str(DB4) not in sys.path:
    sys.path.insert(0, str(DB4))

import db4_config as C4  # noqa: E402  (also puts DB3, DB2, DB1 and AD2/AD3 on sys.path)

DB3, DB2, DB1 = C4.DB3, C4.DB2, C4.DB1
BLOCKS, SCORED, EVAL_PER_BLOCK = C4.BLOCKS, C4.SCORED, C4.EVAL_PER_BLOCK
ARMS = C4.ARMS
PARTS = C4.PARTS

# ---- PLAN_CF1.md section 3 (48 episodes)
EPISODES = {"AA": 6, "AB": 6, "BA": 6, "BB": 6, "S1": 4, "S4": 4, "U": 6, "N_C": 5, "N_OFF": 5}
SCHEDULES = tuple(EPISODES)
NULL_SCHED = C4.NULL_SCHED

# ---- PLAN_CF1.md section 2: (name, kind, comparator, panels, margin)
HYPOTHESES = (
    ("H1", "superiority", "STATIC", ("AB", "BA", "BB", "S1", "S4", "N_C", "U"), 0.0),
    ("H2", "superiority", "BANK", ("AA", "AB", "BA"), 0.0),
    ("H3", "non_inferiority", "AD3", ("U",), 24.0),
    ("H4", "non_inferiority", "W0", SCHEDULES, 2.0),
)
TEST_ARM = "W0F"
ALPHA = 0.05
N_FLIPS = 200_000
EXACT_MAX_N = 16
N_BOOT = 20_000
PERM_SEED = 20261122_01
BOOT_SEED = 20261122_02


def block_key(s, e, t, part):
    return f"cf1:{s}:e{e}:b{t:02d}:{part}"


def all_keys():
    ks = [f"cf1:params:{s}:e{e}" for s in SCHEDULES for e in range(EPISODES[s])]
    return ks + [block_key(s, e, t, p) for s in SCHEDULES for e in range(EPISODES[s]) for t in range(BLOCKS) for p in PARTS]
