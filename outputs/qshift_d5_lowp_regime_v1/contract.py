"""Stage S constants for the d=5 low-p regime screen (STAGE_S_PROTOCOL.md). No sampling here."""
from __future__ import annotations

DISTANCE = 5
QS = (0.0, 0.01, 0.02)
CONDITIONS = {                      # id: (burst family, base p for gates and measurements)
    "L10": ("scaled_v1", 0.001),
    "L15": ("scaled_v1", 0.0015),
}
DEV_SHOTS = 200_000                 # per (condition, q)
DEV_REHEARSAL_SHOTS = 300
Q_DEC_MATCH = tuple(round(0.0025 * k, 4) for k in range(9))      # Phase 1 Astar grid, unchanged
L2_PRIORS = (0.001, 0.0025, 0.01)                                 # extended down for low p; 3 values bound cost
L2 = {"bp_method": "product_sum", "schedule": "serial", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10}
STOP_R = 0.90                       # in-sample R at L10 below this -> STOP
TARGET_R = 0.95
MIN_L2_NONZERO_ERRORS = 30          # Stage E sizing target at L10 (both nonzero q together)
ROOTS_PER_Q = 24


def spec(cond: str):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    fam, p = CONDITIONS[cond]
    s = m.CodeSpec(distance=DISTANCE, gate_p=p, measurement_p=p)
    return s, m.burst_qubits(s, fam)


def dev_key(cond: str, qi: int) -> str:
    return f"d5lowp:dev:{cond}:q{QS[qi]:.2f}"
