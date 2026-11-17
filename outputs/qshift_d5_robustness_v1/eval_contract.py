"""Frozen constants for the Step E evaluation (PROTOCOL.md). Selections copied from DEV_SELECTION.json (tested)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import contract as D

QS = D.QS
CONDITIONS = tuple(D.CONDITIONS)                       # ("F2", "P2", "P4")
SELECTION = {                                          # from DEV_SELECTION.json (f9bbb77c0)
    "F2": {"astar_q_dec": 0.0175, "astar_correlations": True, "l2_prior": 0.01},
    "P2": {"astar_q_dec": 0.0025, "astar_correlations": True, "l2_prior": 0.0025},
    "P4": {"astar_q_dec": 0.0025, "astar_correlations": True, "l2_prior": 0.005},
}
L2 = D.L2
ARMS = ("Astar", "A_nominal", "L2s", "L2o")
CANDIDATE, COMPARATOR = "L2s", "Astar"
CONTRASTS = (("L2s", "Astar"), ("L2o", "Astar"), ("L2s", "L2o"), ("L2s", "A_nominal"))
SAFETY_RELATIVE_MARGIN = 0.05
BOOTSTRAPS = 20_000
QUANTILE_METHOD = "linear"
ALPHA_BONFERRONI = 0.05 / 3


@dataclass(frozen=True)
class Allocation:
    roots_per_q: int
    shots_per_root: int

    @property
    def jobs(self) -> int:
        return self.roots_per_q * len(QS) * len(CONDITIONS)

    def as_dict(self) -> dict:
        return asdict(self)


FROZEN = Allocation(roots_per_q=24, shots_per_root=8_334)      # 200,016 per (condition, q); 1,800,144 total
REHEARSAL = Allocation(roots_per_q=1, shots_per_root=1_000)
FAKE = Allocation(roots_per_q=24, shots_per_root=30)
MODES = {"eval": FROZEN, "rehearsal": REHEARSAL, "fake": FAKE}


def root_key(cond: str, qi: int, r: int) -> str:
    return f"d5rob:eval:{cond}:q{QS[qi]:.2f}:root{r}"


def stem(cond: str, qi: int, r: int) -> str:
    return f"{cond}_q{qi}_r{r:02d}"


def stats_keys(cond: str) -> tuple[str, str]:
    return f"d5rob:stats:{cond}:nonzero", f"d5rob:stats:{cond}:zero"


def jobs(alloc: Allocation) -> list[tuple[str, int, int]]:
    return [(c, qi, r) for c in CONDITIONS for qi in range(len(QS)) for r in range(alloc.roots_per_q)]
