"""CF2 configuration (PLAN_CF2.md): confirmatory run of LA_W0F. No seal read; CF1 is used only to screen seeds.

Everything is DB6's (db6_config: arms, generators, LA overlay, decoders), read-only. CF2 changes only the episode
counts, the seed namespace ("cf2:") and the pre-registered decision constants below. Operating contract: block
t's evaluation shots are decoded after block t's own detection-only shots are available (one block of latency)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB6 = ROOT.parent / "qshift_decoder_bank_v6"
if str(DB6) not in sys.path:
    sys.path.insert(0, str(DB6))

import db6_config as C6  # noqa: E402  (also puts DB5, DB4, DB3, DB2, DB1 and AD2/AD3 on sys.path)

C4 = C6.C4
DB1, DB4, DB5 = C6.DB1, C6.DB4, C6.DB5
BLOCKS, WINDOW, SCORED = C6.BLOCKS, C6.WINDOW, C6.SCORED
EVAL_PER_BLOCK = C6.EVAL_PER_BLOCK
STATES = C6.STATES
ARMS = C6.ARMS
LA_ARMS, LA2_ARMS, BANK_ARMS = C6.LA_ARMS, C6.LA2_ARMS, C6.BANK_ARMS
NULL_SCHED = C6.NULL_SCHED
PARTS = C6.PARTS
episode_params, block_state, changes = C6.episode_params, C6.block_state, C6.changes

# ---- panels (PLAN_CF2.md section 4)
EPISODES = {"AA": 4, "AB": 6, "BA": 6, "BB": 5, "S1": 3, "S4": 4, "U": 5, "N_C": 3, "N_OFF": 4, "RX": 8}
SCHEDULES = tuple(EPISODES)


def block_key(s, e, t, part):
    return f"cf2:{s}:e{e}:b{t:02d}:{part}"


def all_keys():
    ks = [f"cf2:params:{s}:e{e}" for s in SCHEDULES for e in range(EPISODES[s])]
    return ks + [block_key(s, e, t, p) for s in SCHEDULES for e in range(EPISODES[s]) for t in range(BLOCKS) for p in PARTS]


# ---- pre-registered hypotheses (PLAN_CF2.md section 3): (name, comparator, pooled panels)
HYPOTHESES = (("C1", "W0F", SCHEDULES),
              ("C2", "LA_STATIC", ("AB", "BA", "BB", "S1", "S4", "N_C", "U")),
              ("C3", "LA_BANK", ("AA", "AB", "BA", "RX")))
ALPHA = 0.05            # Holm family-wise, over C1-C3, one-sided exact sign tests on nonzero episodes
C1_MEAN = -3.0          # C1 also needs mean(LA_W0F - W0F) <= -3 errors per episode
G1_EPISODE_CAP = 24     # no episode LA_W0F - W0F > +24
G2_BLOCK_CAP = 24       # no block LA_W0F - W0F > +24
G3_HARM_MAX = 2         # at most 2 episodes with LA_W0F - W0F > 0
G4_WRONG_CP_MAX = 0.05  # one-sided 95% Clopper-Pearson upper bound on wrong-state LA uses
G5_RX_EPISODE_CAP = 12  # RX: pooled <= 0 and every episode <= +12
G6_U_EPISODE_CAP = 12   # U: pooled <= 0 and every episode <= +12
OOB_SCHED = ("U",)      # out-of-bank panel: every LA use there counts as wrong
BOOT_RESAMPLES = 20_000
BOOT_SEED = 20261123    # descriptive bootstrap interval only
