"""Frozen constants for the d=5 Phase 2 evaluation (see PROTOCOL.md). No sampler, no decoder construction."""
from __future__ import annotations

from dataclasses import asdict, dataclass

DISTANCE = 5
QS = (0.0, 0.01, 0.02)
BURST_FAMILY = "scaled_v1"

ASTAR_Q_DEC = 0.0025            # Phase 1 selection: correlated PyMatching
STATIC_Q_DEC = 0.01             # Step 0 selection (PHASE2_D5_PRIOR.json)
BOFF_PRIOR = 0.00125            # Phase 1 BoffStatic_5 selection
L2 = {"bp_method": "product_sum", "schedule": "serial", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10}
L0 = {"bp_method": "product_sum", "schedule": "parallel", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10}

ARMS = ("Astar", "A_nominal", "L2s", "L2o", "L0s", "BoffStatic")
CANDIDATE, COMPARATOR = "L2s", "Astar"
CONTRASTS = (("L2s", "Astar"), ("L2o", "Astar"), ("L2s", "L2o"), ("L2s", "L0s"), ("L2s", "BoffStatic"),
             ("L2s", "A_nominal"))
SAFETY_RELATIVE_MARGIN = 0.05   # q=0: 95th percentile of L2s - Astar must be < 0.05 * Astar's q=0 LER
BOOTSTRAPS = 20_000
QUANTILE_METHOD = "linear"


@dataclass(frozen=True)
class Allocation:
    roots_per_q: int
    shots_per_root: int

    @property
    def jobs(self) -> int:
        return self.roots_per_q * len(QS)

    def as_dict(self) -> dict:
        return asdict(self)


FROZEN = Allocation(roots_per_q=24, shots_per_root=8_334)      # 200,016 per q; 600,048 total
REHEARSAL = Allocation(roots_per_q=1, shots_per_root=1_000)    # real rehearsal on rehearsal seeds
FAKE = Allocation(roots_per_q=24, shots_per_root=40)           # numpy DEM sampler; pipeline test only
MODES = {"eval": FROZEN, "rehearsal": REHEARSAL, "fake": FAKE}


def root_key(qi: int, r: int) -> str:
    return f"p2d5:q{QS[qi]:.2f}:root{r}"


def stem(qi: int, r: int) -> str:
    return f"q{qi}_r{r:02d}"


STATS_KEYS = ("p2d5:stats:nonzero", "p2d5:stats:zero")
