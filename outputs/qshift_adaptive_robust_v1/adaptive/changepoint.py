"""Sequential change detection on detector-event counts (hypothesis H-E2).

A two-sided binomial CUSUM (Page 1954) on the total detector-event count per block. Under the in-control
rate r0 (estimated during a calibration window, detector-only) the statistic drifts down; after a change to
r1 = r0 * (1 +/- delta) it drifts up. The alarm threshold h is chosen for a target in-control average run
length (ARL0) by simulation on the binomial null; `calibrate_threshold` does this deterministically.

Detector-only. Logical labels are never used. Block counts are sufficient for a global rate change; a
localized burst changes the total count only slightly, so it is better caught by per-detector statistics
(estimation.py outliers). Both feed the controller.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def _llr_terms(r0: float, r1: float) -> tuple[float, float]:
    """Per-event and per-non-event log-likelihood ratio of rate r1 vs r0."""
    return float(np.log(r1 / r0)), float(np.log((1 - r1) / (1 - r0)))


@dataclass
class BinomialCUSUM:
    r0: float                       # in-control per-trial event rate
    delta: float                    # relative change to detect, both directions
    threshold: float                # alarm threshold h
    trials_per_block: int           # detectors * shots per block
    up: float = 0.0
    down: float = 0.0
    t: int = 0
    alarms: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 < self.r0 < 0.5 or not 0 < self.delta < 1 or self.threshold <= 0 or self.trials_per_block <= 0:
            raise ValueError("invalid CUSUM parameters")
        self._hi = _llr_terms(self.r0, self.r0 * (1 + self.delta))
        self._lo = _llr_terms(self.r0, self.r0 * (1 - self.delta))

    def update(self, events: int) -> bool:
        """Feed one block's event count. Returns True on alarm (and resets both arms)."""
        if events < 0 or events > self.trials_per_block:
            raise ValueError("event count out of range")
        non = self.trials_per_block - events
        self.up = max(0.0, self.up + events * self._hi[0] + non * self._hi[1])
        self.down = max(0.0, self.down + events * self._lo[0] + non * self._lo[1])
        self.t += 1
        if self.up > self.threshold or self.down > self.threshold:
            self.alarms.append(self.t)
            self.up = self.down = 0.0
            return True
        return False


def run_length(cusum: BinomialCUSUM, counts: np.ndarray) -> int | None:
    for i, c in enumerate(counts, start=1):
        if cusum.update(int(c)):
            return i
    return None


def calibrate_threshold(r0: float, delta: float, trials_per_block: int, target_arl0: int, *,
                        seed: int, runs: int = 200, grid: tuple[float, ...] | None = None) -> float:
    """Smallest threshold whose simulated median in-control run length >= target_arl0 (deterministic)."""
    rng = np.random.default_rng(seed)
    grid = grid or tuple(np.round(np.arange(1.0, 20.01, 0.5), 2))
    horizon = 2 * target_arl0
    sims = rng.binomial(trials_per_block, r0, size=(runs, horizon))
    for h in grid:
        rls = []
        for row in sims:
            rl = run_length(BinomialCUSUM(r0, delta, h, trials_per_block), row)
            rls.append(horizon + 1 if rl is None else rl)
        if np.median(rls) >= target_arl0:
            return float(h)
    raise ValueError("no threshold in grid meets the target ARL0")
