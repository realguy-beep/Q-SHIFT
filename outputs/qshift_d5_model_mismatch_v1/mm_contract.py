"""d=5 base-model mismatch study: constants (PROTOCOL.md). No sampling here.

The learner, tau, every decoder and the static priors are Phase C's, unchanged, and all assume the nominal
base model (d=5, p=0.003, balanced). Only the sampler uses a mismatched TRUE base model.
"""
from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PHASE_C = REPO / "outputs" / "qshift_d5_learned_support_v1"
sys.path.insert(0, str(PHASE_C))
sys.path.insert(0, str(REPO))
import c_contract as C  # noqa: E402  (Phase C frozen constants)
import contract as B  # noqa: E402    (Phase B constants, classes)
from learner_d5 import m  # noqa: E402

NOMINAL_SPEC = C.SPEC                           # what the learner and every decoder assume
assert (NOMINAL_SPEC.distance, NOMINAL_SPEC.gate_p, NOMINAL_SPEC.measurement_p, NOMINAL_SPEC.regime) == \
    (5, 0.003, 0.003, "balanced")
TRUE_SPECS = {                                  # what the sampler uses
    "Mlo": m.CodeSpec(distance=5, gate_p=0.0025, measurement_p=0.0025),
    "Mhi": m.CodeSpec(distance=5, gate_p=0.0035, measurement_p=0.0035),
    "Mz": m.CodeSpec(distance=5, gate_p=0.003, measurement_p=0.003, regime="z_biased", bias_ratio=10.0),
}
CONDITIONS = tuple(TRUE_SPECS)
SUPPORT = C.KNOWN_SUPPORT                       # (23, 31, 34), scaled_v1
QS = C.QS                                       # (0, 0.01, 0.02)
ARMS = C.ARMS

# ---- Phase A diagnostic (informational; cannot change the method)
DIAG_POOLS = 24
DET_PER_Q, LAB_PER_Q = C.CAL_DET_PER_Q, C.CAL_LAB_PER_Q   # 4,000 + 500 per q, the calibration recipe
Q0_POOL_SHOTS = 3 * DET_PER_Q                   # 12,000 burst-free rows, the size tau was calibrated at
DIAG_DECODE_ROOTS, DIAG_DECODE_SHOTS = 3, 2_000


@dataclass(frozen=True)
class Allocation:
    roots_per_q: int
    shots_per_root: int

    def as_dict(self) -> dict:
        return asdict(self)


FROZEN = Allocation(24, 8_334)                  # 200,016 per (condition, q); 1,800,288 total
REHEARSAL = Allocation(1, 1_000)
FAKE = Allocation(24, 30)
MODES = {"eval": FROZEN, "rehearsal": REHEARSAL, "fake": FAKE}


def diag_burst_key(c, k, qi):
    return f"d5mm:A:{c}:burst:pool{k:02d}:q{QS[qi]:.2f}"


def diag_q0_key(c, k):
    return f"d5mm:A:{c}:q0:pool{k:02d}"


def diag_decode_key(c, qi, r):
    return f"d5mm:A:{c}:decode:q{QS[qi]:.2f}:root{r}"


def diag_keys():
    return ([diag_burst_key(c, k, qi) for c in CONDITIONS for k in range(DIAG_POOLS) for qi in range(len(QS))]
            + [diag_q0_key(c, k) for c in CONDITIONS for k in range(DIAG_POOLS)]
            + [diag_decode_key(c, qi, r) for c in CONDITIONS for qi in range(len(QS))
               for r in range(DIAG_DECODE_ROOTS)])


def root_key(c, qi, r):
    return f"d5mm:B:eval:{c}:q{QS[qi]:.2f}:root{r}"


def cal_key(c, qi):
    return f"d5mm:B:cal:{c}:q{QS[qi]:.2f}"


def stats_keys(c):
    return f"d5mm:B:stats:{c}:nonzero", f"d5mm:B:stats:{c}:zero"


def jobs(alloc):
    return [(c, qi, r) for c in CONDITIONS for qi in range(len(QS)) for r in range(alloc.roots_per_q)]


def eval_keys(alloc):
    return ([root_key(*j) for j in jobs(alloc)] + [cal_key(c, qi) for c in CONDITIONS for qi in range(len(QS))]
            + [k for c in CONDITIONS for k in stats_keys(c)])


def tau() -> float:
    return C.tau()                              # 1,561.218 (NULL_THRESHOLD.json, B2), unchanged
