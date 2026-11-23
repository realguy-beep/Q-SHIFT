"""DB8-dev configuration (PROTOCOL_DB8.md). Development only; no seal read; CF2 seeds are used only for screening.

Everything is DB6's (db6_config: bank, generators, LA overlay, decoders), read-only, plus:
  - LA_R1 / LA_R2 / LA_R2_170 rule arms, the CB current-block bank baseline and FIX_<state> fixed-key arms;
  - three new out-of-bank states (UF = V06 under amendment A3 [was X03], UO = V01 + qubit 3, UN = X09) chosen analytically (select_unknowns.py);
  - two diagnostics-only extensions installed at import, so the new states can be sampled and scored:
      * support(name) also knows UF, UO, UN (db_config's support is wrapped; bank and E unchanged);
      * the class-truth lookup returns (None, None) for a support outside the learner catalog (UO). Truth feeds
        correctness diagnostics only (ad1/brt/ad3/db_core.acceptable), never a decision (sampler-free test).
Operating contract: block t's evaluation shots are decoded after block t's detector-only shots (one block latency).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB6 = ROOT.parent / "qshift_decoder_bank_v6"
V8 = ROOT.parent / "qshift_decoder_bank_v8"
for _p in (DB6, V8):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import db6_config as C6  # noqa: E402  (also puts DB5-DB1 and AD2/AD3 on sys.path)
import db_config as DC  # noqa: E402  (DB1's config: the sampler's support())
import mm_contract as K  # noqa: E402

C4, C2 = C6.C4, C6.C2
DB1, DB4, DB5 = C6.DB1, C6.DB4, C6.DB5
BLOCKS, WINDOW, SCORED = C6.BLOCKS, C6.WINDOW, C6.SCORED
DET_PER_BLOCK, LAB_PER_BLOCK, EVAL_PER_BLOCK = C6.DET_PER_BLOCK, C6.LAB_PER_BLOCK, C6.EVAL_PER_BLOCK
STATES = C6.STATES                                    # the bank: OFF, A, B, C, D (unchanged)
spec, P0, NOMINAL, AD3_TAU = C6.spec, C6.P0, C6.NOMINAL, C6.AD3_TAU
CANDIDATES, FALLBACK_ARMS, BANK_ARMS = C6.CANDIDATES, C6.FALLBACK_ARMS, C6.BANK_ARMS
LA_ARMS, LA2_ARMS = C6.LA_ARMS, C6.LA2_ARMS
PARTS, NULL_SCHED = C6.PARTS, C6.NULL_SCHED

# ---- unknown states (PROTOCOL_DB8.md section 3; reproduced by select_unknowns.py, tested)
NEW_UNKNOWN = {"UF": (1, 42, 47), "UO": (1, 3, 12, 38), "UN": (7, 14, 42)}
UNKNOWN_LABELS = {"E": "W06", "UF": "V06", "UO": "V01+q3", "UN": "X09"}
U_PANELS = {"U_E": "E", "U_FAR": "UF", "U_OUT": "UO", "U_NEAR": "UN"}

_support0 = DC.support
_truth0 = K.B.truth


def support(name):
    if name in NEW_UNKNOWN:
        return tuple(NEW_UNKNOWN[name])
    return _support0(name)


def truth(classes, sup):
    try:
        return _truth0(classes, sup)
    except KeyError:
        if tuple(sorted(int(q) for q in sup)) == tuple(sorted(NEW_UNKNOWN["UO"])):
            return (None, None)                       # outside the learner catalog: no class (diagnostics only)
        raise


DC.support = support                                  # db_core.sample / acceptable look these up at call time
K.B.truth = truth

# ---- arms
RULE_ARMS = ("LA_R1", "LA_R2", "LA_R2_170")
FIX_ARMS = tuple("FIX_" + s for s in STATES)
ARMS = C6.ARMS + RULE_ARMS + ("CB",) + FIX_ARMS
R2_CAP, R2_CAP_SECONDARY = 180.0, 170.0

# ---- panels (PROTOCOL_DB8.md section 3)
INBANK = {"AA": 2, "AB": 3, "BA": 3, "BB": 3, "S1": 2, "S4": 2, "N_C": 2, "N_OFF": 2, "RX": 5}
UNKNOWN_EP = {"U_E": 8, "U_FAR": 12, "U_OUT": 12, "U_NEAR": 8}
EPISODES = {**INBANK, **UNKNOWN_EP}
SCHEDULES = tuple(EPISODES)


def episode_params(s, e, rng_seed):
    if s in U_PANELS:
        import numpy as np
        return {"onset": int(np.random.default_rng(rng_seed).integers(8, 13))}     # DB1's U rule
    return C6.episode_params(s, e, rng_seed)


def block_state(s, t, prm):
    if s in U_PANELS:
        return "A" if t < prm["onset"] else U_PANELS[s]
    return C6.block_state(s, t, prm)


def changes(s, prm):
    st = [block_state(s, t, prm) for t in range(BLOCKS)]
    return [t for t in range(1, BLOCKS) if st[t] != st[t - 1]]


def block_key(s, e, t, part):
    return f"db8:{s}:e{e}:b{t:02d}:{part}"


def all_keys():
    ks = [f"db8:params:{s}:e{e}" for s in SCHEDULES for e in range(EPISODES[s])]
    return ks + [block_key(s, e, t, p) for s in SCHEDULES for e in range(EPISODES[s]) for t in range(BLOCKS) for p in PARTS]


# ---- pre-registered advance criteria (PROTOCOL_DB8.md section 5)
A1_RETENTION, A1_ALPHA = 0.90, 0.05
A2_PANELS, A2_MAX_EPISODES = ("U_FAR", "U_OUT"), 2
A3_EPISODE_CAP, A3_BLOCK_CAP, A3_UNKNOWN_EPISODE_CAP = 24, 24, 12
A4_BASELINES = ("CB", "LA_DB2")
