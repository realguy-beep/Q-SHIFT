"""RE1 frozen evaluation: fixed configuration (PLAN_EVAL.md, RE1_PROTOCOL.md). No sampling here."""
from __future__ import annotations

import dev2_config as D  # noqa: F401  (sys.path setup, shared constants)

QS = D.QS
DET_PER_Q, LAB_PER_Q = D.DET_PER_Q, D.LAB_PER_Q
L2_PRIOR, ASTAR_Q_DEC = D.L2_PRIOR, D.ASTAR_Q_DEC
NOMINAL = D.NOMINAL
KNOWN = (23, 31, 34)

# id: (true-model kwargs, burst: "K" or "H2", gated, roots)
CONDITIONS = {
    "R1": (dict(gate_p=0.0026, measurement_p=0.0026), "K", True, 12),
    "R2": (dict(gate_p=0.0034, measurement_p=0.0034), "K", True, 12),
    "R3": (dict(gate_p=0.003, measurement_p=0.003, regime="z_biased", bias_ratio=8.0), "K", True, 12),
    "R4": (dict(gate_p=0.0028, measurement_p=0.0028, regime="z_biased", bias_ratio=4.0), "K", True, 12),
    "R5": (dict(gate_p=0.003, measurement_p=0.003), "K", True, 12),
    "R6": (dict(gate_p=0.0028, measurement_p=0.0028, regime="z_biased", bias_ratio=4.0), "H2", True, 12),
    "X1": (dict(gate_p=0.003, measurement_p=0.003, regime="x_biased", bias_ratio=10.0), "K", False, 6),
}
EVAL_SHOTS = 4_000
ARMS = ("L2L_R", "Astar_Rm", "Astar_Nm", "L2s_true", "Astar_true", "L2L_N", "A_nominal")   # S* derived per root
GATED = tuple(c for c, v in CONDITIONS.items() if v[2])
ALPHA_ONE_SIDED = 0.025 / (2 * len(GATED))      # 6 conditions x 2 co-primaries
NI_MARGIN = 0.25
SAFETY_FRACTION = 0.05
SAFETY_FLOOR_ERRORS = 3              # build-time addition (RE1_PROTOCOL.md deviation 2)
BOOT_REPS, JOB_TIMEOUT_S, BUDGET_S = 20_000, 3_600, 18_000
PREFLIGHT_DROP_L2L_N = ("R2", "R5")               # pre-declared fallback if the preflight exceeds the budget

REHEARSAL_EVAL_SHOTS = 300


def spec(**kw):
    return D.spec(**kw)


def root_key(c, r, part, qi):
    return f"re1:{c}:r{r:02d}:{part}:q{qi}"


def stats_key(c):
    return f"re1:stats:{c}"


def all_keys():
    keys = [root_key(c, r, part, qi) for c, v in CONDITIONS.items() for r in range(v[3])
            for part in ("cal", "eval") for qi in range(3)]
    return keys + [stats_key(c) for c in GATED]


def rehearsal_keys():
    return [root_key(c, 0, part, qi) for c in CONDITIONS for part in ("cal", "eval") for qi in range(3)]
