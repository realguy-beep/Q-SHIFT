"""OG + E2E development studies: fixed configuration (PLAN_DEV2.md, DEV2_PROTOCOL.md). No sampling here."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTS = ROOT.parent
REPO = OUTS.parent
for p in (ROOT, OUTS / "qshift_d5_model_mismatch_v1", OUTS / "qshift_d5_learned_support_v1", REPO):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

QS = (0.0, 0.01, 0.02)
POOLS = 24
DET_PER_Q, LAB_PER_Q, Q0_ROWS = 4_000, 500, 12_000      # Phase A / Phase C calibration recipe
E2E_ROOTS, E2E_EVAL_SHOTS = 6, 4_000
L2_PRIOR, ASTAR_Q_DEC = 0.01, 0.0025                      # Phase C static decoder settings, unchanged
NOMINAL = dict(gate_p=0.003, measurement_p=0.003, regime="balanced", bias_ratio=10.0)

# id: (spec kwargs, in_family); OFF_GRID names the parameter(s) each in-family condition is designed to put off the grid
OFF_GRID = {"OG1": ("p",), "OG2": ("p",), "OG3": ("b",), "OG4": ("b",), "OG5": ("p", "b")}
OG = {
    "OG1": (dict(gate_p=0.0027, measurement_p=0.0027), True),
    "OG2": (dict(gate_p=0.00334, measurement_p=0.00334), True),   # plan said 0.0033; moved off-grid by the build check
    "OG3": (dict(gate_p=0.003, measurement_p=0.003, regime="z_biased", bias_ratio=6.0), True),
    "OG4": (dict(gate_p=0.003, measurement_p=0.003, regime="z_biased", bias_ratio=12.0), True),
    "OG5": (dict(gate_p=0.0027, measurement_p=0.0027, regime="z_biased", bias_ratio=6.0), True),
    "OG6": (dict(gate_p=0.003, measurement_p=0.003, regime="x_biased", bias_ratio=10.0), False),
    "OG7": (dict(gate_p=0.003, measurement_p=0.009), False),
}
E2E = {
    "Mlo": dict(gate_p=0.0025, measurement_p=0.0025),
    "Mhi": dict(gate_p=0.0035, measurement_p=0.0035),
    "Mz": dict(gate_p=0.003, measurement_p=0.003, regime="z_biased", bias_ratio=10.0),
    "CTRL": dict(gate_p=0.003, measurement_p=0.003),
}
E2E_ARMS = ("L2L_B2", "Astar_B2", "L2L_N", "Astar_N", "L2s_true", "Astar_true", "A_nominal")

REHEARSAL = {"og": [("OG3", "burst", 0), ("OG6", "q0", 0)], "e2e": [("Mz", 0)], "e2e_eval_shots": 200}


def spec(**kw):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    base = dict(distance=5, regime="balanced", bias_ratio=10.0)
    base.update(kw)
    return m.CodeSpec(**base)


def og_burst_key(c, k, qi):
    return f"d2:og:{c}:burst{k:02d}:q{qi}"


def og_q0_key(c, k):
    return f"d2:og:{c}:q0{k:02d}"


def e2e_key(c, r, part, qi):
    return f"d2:e2e:{c}:r{r}:{part}:q{qi}"


def all_keys():
    keys = []
    for c in OG:
        keys += [og_burst_key(c, k, qi) for k in range(POOLS) for qi in range(3)] + [og_q0_key(c, k) for k in range(POOLS)]
    for c in E2E:
        keys += [e2e_key(c, r, part, qi) for r in range(E2E_ROOTS) for part in ("cal", "eval") for qi in range(3)]
    return keys


def rehearsal_keys():
    keys = []
    for c, kind, k in REHEARSAL["og"]:
        keys += [og_burst_key(c, k, qi) for qi in range(3)] if kind == "burst" else [og_q0_key(c, k)]
    for c, r in REHEARSAL["e2e"]:
        keys += [e2e_key(c, r, part, qi) for part in ("cal", "eval") for qi in range(3)]
    return keys
