"""RE2 frozen evaluation of the E1T pipeline with two new sealed bursts: fixed configuration (PLAN_RE2.md rev 2,
RE2_PROTOCOL.md). No sampling here."""
from __future__ import annotations

import brt_config as T  # noqa: F401  (sys.path setup; E1T constants)
import re1_config as R1  # noqa: F401  (RE1 calibration recipe, decoder settings, nominal model)

D = R1.D
ROOT = D.ROOT
QS = R1.QS
DET_PER_Q, LAB_PER_Q = R1.DET_PER_Q, R1.LAB_PER_Q          # 4,000 + 500 per q -> 12,000 + 1,500 per root
L2_PRIOR, ASTAR_Q_DEC = R1.L2_PRIOR, R1.ASTAR_Q_DEC
NOMINAL = R1.NOMINAL
KNOWN = R1.KNOWN                                         # K = (23, 31, 34)

# id: (true-model kwargs, burst: "K" | "H3" | "H4", gated, roots)
CONDITIONS = {
    "G1": (dict(gate_p=0.0023, measurement_p=0.0023), "K", True, 12),
    "G2": (dict(gate_p=0.0032, measurement_p=0.0032, regime="z_biased", bias_ratio=6.0), "K", True, 12),
    "G3": (dict(gate_p=0.0028, measurement_p=0.0028, regime="z_biased", bias_ratio=4.0), "H3", True, 12),
    "G4": (dict(gate_p=0.00335, measurement_p=0.00335), "H3", True, 12),
    "G5": (dict(gate_p=0.0026, measurement_p=0.0026, regime="z_biased", bias_ratio=5.0), "H4", True, 12),
    "X2": (dict(gate_p=0.003, measurement_p=0.003, regime="x_biased", bias_ratio=8.0), "K", False, 6),
}
REPEATS_R6 = "G3"                                       # deliberately R6's base model (asserted, not a collision)
HIDDEN = ("H3", "H4")
GATED = tuple(c for c, v in CONDITIONS.items() if v[2])
B2_CONDS = ("G3", "G4")                                 # descriptive L2L_B2 arm (RE1's pipeline) only here

EVAL_SHOTS = 4_000
REHEARSAL_EVAL_SHOTS = 300
BASE_ARMS = ("L2L_E", "Astar_Em", "Astar_Nm", "L2s_true", "Astar_true", "A_nominal")


def arms(c, drop_b2=False):
    return BASE_ARMS + (("L2L_B2",) if c in B2_CONDS and not drop_b2 else ())


ALPHA_ONE_SIDED = 0.025 / (2 * len(GATED))              # 5 gated conditions x 2 co-primaries = 0.0025
NI_MARGIN = 0.25
NI_FLOOR_ERRORS = 10                                     # PLAN_RE2 rev 2: max(0.25 x oracle, 10 / N_nz)
SAFETY_FRACTION = 0.05
SAFETY_FLOOR_ERRORS = 3                                  # RE1 deviation 2, unchanged
BOOT_REPS, JOB_TIMEOUT_S, BUDGET_S = 20_000, 3_600, 18_000
FALLBACK = "drop L2L_B2"                                 # pre-declared, if the preflight exceeds the budget
STRATA = {"H3": (25, 10_000), "H4": (0, 20)}             # detector footprint ranges


def spec(**kw):
    return D.spec(**kw)


def root_key(c, r, part, qi):
    return f"re2:{c}:r{r:02d}:{part}:q{qi}"


def stats_key(c):
    return f"re2:stats:{c}"


def all_keys():
    keys = [root_key(c, r, part, qi) for c, v in CONDITIONS.items() for r in range(v[3])
            for part in ("cal", "eval") for qi in range(len(QS))]
    return keys + [stats_key(c) for c in GATED]


def rehearsal_keys():
    return [root_key(c, 0, part, qi) for c in CONDITIONS for part in ("cal", "eval") for qi in range(len(QS))]
