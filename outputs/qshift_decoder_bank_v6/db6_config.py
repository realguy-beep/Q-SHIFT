"""DB6 configuration (PROPOSAL_DB6.md): alarm-gated block-lookahead overlay (LA). Development only; no seal read.

Reuses DB4 (db4_config, db4_core, db4_run's loop) and through it DB3, DB2, DB1 and AD2/AD3, read-only.
New: the LA arms (overlays on W0F, BANK, DB2, STATIC; LA2-W0F exploratory), the RX challenge panel (DB2's
generator), fresh "db6:" seeds. Operating contract: block t's evaluation shots are decoded after block t's own
detection-only shots are available (one block of decoding latency)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB4 = ROOT.parent / "qshift_decoder_bank_v4"
DB5 = ROOT.parent / "qshift_decoder_bank_v5"
for _p in (DB4, DB5):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import db4_config as C4  # noqa: E402  (also puts DB3, DB2, DB1 and AD2/AD3 on sys.path)

C3, C2 = C4.C3, C4.C2
DB3, DB2, DB1 = C4.DB3, C4.DB2, C4.DB1
BLOCKS, WINDOW, SCORED = C4.BLOCKS, C4.WINDOW, C4.SCORED
DET_PER_BLOCK, LAB_PER_BLOCK, EVAL_PER_BLOCK = C4.DET_PER_BLOCK, C4.LAB_PER_BLOCK, C4.EVAL_PER_BLOCK
STATES = C4.STATES
support, spec, P0, NOMINAL, AD3_TAU = C4.support, C4.spec, C4.P0, C4.NOMINAL, C4.AD3_TAU

CANDIDATES = C4.CANDIDATES
FALLBACK_ARMS = C4.FALLBACK_ARMS
BANK_ARMS = C4.BANK_ARMS

# ---- LA overlays: arm -> base arm. LA uses the lookahead key only when AD3's change test fires on block t's own
# detection counts and DB1's plausible set fitted on block t alone (L = 1) is a singleton. LA2 drops the alarm gate.
LA_ARMS = {"LA_W0F": "W0F", "LA_BANK": "BANK", "LA_DB2": "DB2", "LA_STATIC": "STATIC"}
LA2_ARMS = {"LA2_W0F": "W0F"}
ARMS = C4.ARMS + tuple(LA_ARMS) + tuple(LA2_ARMS)

# ---- panels (PROPOSAL_DB6.md section 4)
EPISODES = {"AA": 3, "AB": 3, "BA": 3, "BB": 3, "S1": 2, "S4": 2, "U": 2, "N_C": 2, "N_OFF": 3, "RX": 4}
SCHEDULES = tuple(EPISODES)
NULL_SCHED = C4.NULL_SCHED
C2_PANELS = ("RX",)


def episode_params(s, e, rng_seed):
    if s in C2_PANELS:
        return C2.episode_params(s, e, rng_seed)
    return C4.episode_params(s, e, rng_seed)


def block_state(s, t, prm):
    if s in C2_PANELS:
        return C2.block_state(s, t, prm)
    return C4.block_state(s, t, prm)


def changes(s, prm):
    st = [block_state(s, t, prm) for t in range(BLOCKS)]
    return [t for t in range(1, BLOCKS) if st[t] != st[t - 1]]


PARTS = C4.PARTS


def block_key(s, e, t, part):
    return f"db6:{s}:e{e}:b{t:02d}:{part}"


def all_keys():
    ks = [f"db6:params:{s}:e{e}" for s in SCHEDULES for e in range(EPISODES[s])]
    return ks + [block_key(s, e, t, p) for s in SCHEDULES for e in range(EPISODES[s]) for t in range(BLOCKS) for p in PARTS]


# ---- pre-registered decision (PROPOSAL_DB6.md section 4)
E1_MEAN = -3.0          # LA_W0F - W0F errors per episode
E1_ALPHA = 0.05         # one-sided exact sign test on nonzero episodes
S1_EPISODE_CAP = 24     # no episode LA_W0F - W0F > +24
S2_BLOCK_CAP = 24       # no block where LA's key costs > +24 over W0F's key
S3_WRONG_MAX = 0.05     # wrong-state LA uses / LA uses
S4_RX_EPISODE_CAP = 12  # RX: no episode > +12, pooled <= 0
