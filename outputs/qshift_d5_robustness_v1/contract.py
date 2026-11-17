"""Frozen constants for the d=5 robustness study (see DEV_PROTOCOL.md / PROTOCOL.md)."""
from __future__ import annotations

DISTANCE = 5
QS = (0.0, 0.01, 0.02)
CONDITIONS = {                      # id: (burst family, base p for gates and measurements)
    "F2": ("centre_row", 0.003),
    "P2": ("scaled_v1", 0.002),
    "P4": ("scaled_v1", 0.004),
}
DEV_SHOTS = 30_000                  # per (condition, q)
DEV_REHEARSAL_SHOTS = 300
Q_DEC_MATCH = tuple(round(0.0025 * k, 4) for k in range(9))
L2_PRIORS = (0.0025, 0.005, 0.01, 0.02)
L2 = {"bp_method": "product_sum", "schedule": "serial", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10}


def spec(cond: str):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    fam, p = CONDITIONS[cond]
    s = m.CodeSpec(distance=DISTANCE, gate_p=p, measurement_p=p)
    return s, m.burst_qubits(s, fam)


def dev_key(cond: str, qi: int) -> str:
    return f"d5rob:dev:{cond}:q{QS[qi]:.2f}"
