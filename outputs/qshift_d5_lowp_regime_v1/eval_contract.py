"""Frozen constants for the Stage E evaluation (PROTOCOL.md). Selections copied from DEV_SELECTION.json (tested)."""
from __future__ import annotations

from dataclasses import dataclass, field

import contract as D

QS = D.QS
CONDITIONS = tuple(D.CONDITIONS)                       # ("L10", "L15")
SELECTION = {                                          # from DEV_SELECTION.json (ef5cc2455)
    "L10": {"astar_q_dec": 0.0025, "astar_correlations": True, "l2_prior": 0.001},
    "L15": {"astar_q_dec": 0.0025, "astar_correlations": True, "l2_prior": 0.0025},
}
L2 = D.L2
ARMS = ("Astar", "A_nominal", "L2s", "L2o")
CANDIDATE, COMPARATOR = "L2s", "Astar"
CONTRASTS = (("L2s", "Astar"), ("L2o", "Astar"), ("L2s", "L2o"), ("L2s", "A_nominal"))
SAFETY_RELATIVE_MARGIN = 0.05
BOOTSTRAPS = 20_000
QUANTILE_METHOD = "linear"
ALPHA_BONFERRONI = 0.05 / 2
TARGET_R = D.TARGET_R                                  # 0.95
TARGET_CONDITION = "L10"


@dataclass(frozen=True)
class Allocation:
    roots_per_q: int
    shots_per_root: dict = field(hash=False)           # by condition

    def shots(self, cond: str) -> int:
        return self.shots_per_root[cond]

    @property
    def jobs(self) -> int:
        return self.roots_per_q * len(QS) * len(CONDITIONS)

    @property
    def total_shots(self) -> int:
        return self.roots_per_q * len(QS) * sum(self.shots_per_root[c] for c in CONDITIONS)

    def as_dict(self) -> dict:
        return {"roots_per_q": self.roots_per_q, "shots_per_root": dict(self.shots_per_root)}


# Stage S sizing (DEV_SELECTION.json stage_e_N_per_q): 750,000 and 214,296 per q, as 24 roots.
FROZEN = Allocation(24, {"L10": 31_250, "L15": 8_929})          # 2,892,888 shots in 144 jobs
REHEARSAL = Allocation(1, {"L10": 1_000, "L15": 1_000})
FAKE = Allocation(24, {"L10": 30, "L15": 30})
MODES = {"eval": FROZEN, "rehearsal": REHEARSAL, "fake": FAKE}


def root_key(cond: str, qi: int, r: int) -> str:
    return f"d5lowp:eval:{cond}:q{QS[qi]:.2f}:root{r}"


def stem(cond: str, qi: int, r: int) -> str:
    return f"{cond}_q{qi}_r{r:02d}"


def stats_keys(cond: str) -> tuple[str, str]:
    return f"d5lowp:stats:{cond}:nonzero", f"d5lowp:stats:{cond}:zero"


def jobs(alloc: Allocation) -> list[tuple[str, int, int]]:
    # Larger L10 jobs first so the pool's tail is short.
    return [(c, qi, r) for c in CONDITIONS for qi in range(len(QS)) for r in range(alloc.roots_per_q)]
